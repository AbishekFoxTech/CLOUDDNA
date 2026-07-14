import logging

from django.conf import settings

from .models import DocumentRelationship

logger = logging.getLogger(__name__)

SAME_KEYWORDS_THRESHOLD = 0.4
SAME_CATEGORY_SCORE = 0.2
REFERENCED_SCORE = 0.3
MIN_TITLE_LENGTH_FOR_REFERENCE = 4


def _keyword_jaccard(keywords_a, keywords_b):
    set_a, set_b = set(keywords_a), set(keywords_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def get_manual_relationships_snapshot(document):
    """
    Captures this document's manual relationships before a reprocessing
    run. ai_engine.services.similarity.compute_and_store_similarities
    clears *all* of this document's relationship rows before recomputing
    TF-IDF matches - that logic is untouched (it's the existing AI
    pipeline), so instead we snapshot manual links here and restore them
    in classify_relationships() afterward.
    """
    return list(
        DocumentRelationship.objects.filter(
            document=document,
            relationship_type=DocumentRelationship.RelationshipType.MANUAL,
        ).values('related_document_id', 'created_by_id')
    )


def classify_relationships(document, manual_snapshot=None):
    """
    Classifies this document's relationship to each of the owner's other
    AI-processed documents into a RelationshipType, layered on top of (not
    replacing) the TF-IDF similarity scores already computed by
    ai_engine.services.similarity. Called automatically after every
    upload/reprocess (see ai_engine.services.pipeline.process_document).

    Priority when multiple signals qualify for the same pair: Duplicate
    (identical file) > Same Keywords (strong keyword overlap) > Similar
    (TF-IDF) > Referenced (title mentioned in text) > Same Category.
    Manual links are always restored first and never auto-overwritten.
    """
    from documents.models import Document

    for entry in manual_snapshot or []:
        DocumentRelationship.objects.update_or_create(
            document=document, related_document_id=entry['related_document_id'],
            defaults={
                'relationship_type': DocumentRelationship.RelationshipType.MANUAL,
                'similarity_score': 1.0,
                'created_by_id': entry['created_by_id'],
            },
        )

    other_documents = list(
        Document.objects.filter(owner=document.owner, ai_processed=True).exclude(pk=document.pk)
    )
    if not other_documents:
        Document.objects.filter(pk=document.pk).update(relationship_count=0)
        return

    existing = {
        rel.related_document_id: rel
        for rel in DocumentRelationship.objects.filter(document=document)
    }

    document_keywords = document.keyword_list
    document_text = (document.extracted_text or '').lower()

    to_create = []
    rows_to_update = []
    stale_pks = []
    kept_count = 0

    for other in other_documents:
        existing_rel = existing.get(other.pk)
        if existing_rel and existing_rel.relationship_type == DocumentRelationship.RelationshipType.MANUAL:
            kept_count += 1
            continue

        relationship_type = None
        score = 0.0

        if document.document_hash and document.document_hash == other.document_hash:
            relationship_type = DocumentRelationship.RelationshipType.DUPLICATE
            score = 1.0
        else:
            keyword_score = _keyword_jaccard(document_keywords, other.keyword_list)
            if keyword_score >= SAME_KEYWORDS_THRESHOLD:
                relationship_type = DocumentRelationship.RelationshipType.SAME_KEYWORDS
                score = keyword_score
            elif existing_rel and existing_rel.similarity_score >= settings.AI_SIMILARITY_MIN_SCORE:
                relationship_type = DocumentRelationship.RelationshipType.SIMILAR
                score = existing_rel.similarity_score
            elif (
                other.title and len(other.title) >= MIN_TITLE_LENGTH_FOR_REFERENCE
                and other.title.lower() in document_text
            ):
                relationship_type = DocumentRelationship.RelationshipType.REFERENCED
                score = REFERENCED_SCORE
            elif (
                (document.category and document.category == other.category)
                or (document.detected_category and document.detected_category == other.detected_category)
            ):
                relationship_type = DocumentRelationship.RelationshipType.SAME_CATEGORY
                score = SAME_CATEGORY_SCORE

        if relationship_type is None:
            if existing_rel:
                stale_pks.append(existing_rel.pk)
            continue

        kept_count += 1
        if existing_rel:
            if existing_rel.relationship_type != relationship_type or existing_rel.similarity_score != score:
                existing_rel.relationship_type = relationship_type
                existing_rel.similarity_score = score
                rows_to_update.append(existing_rel)
        else:
            to_create.append(DocumentRelationship(
                document=document, related_document=other,
                relationship_type=relationship_type, similarity_score=score,
            ))

    if stale_pks:
        DocumentRelationship.objects.filter(pk__in=stale_pks).delete()
    for rel in rows_to_update:
        rel.save(update_fields=['relationship_type', 'similarity_score', 'computed_at'])
    if to_create:
        DocumentRelationship.objects.bulk_create(to_create)

    Document.objects.filter(pk=document.pk).update(relationship_count=kept_count)

    if to_create:
        _notify_relationships_discovered(document, to_create)


def _notify_relationships_discovered(document, new_relationships):
    """Best-effort notification when new relationships are found."""
    try:
        from recommendations.services import create_notification

        top = max(new_relationships, key=lambda rel: rel.similarity_score)
        if len(new_relationships) == 1:
            message = (
                f'"{document.title}" was linked to "{top.related_document.title}" '
                f'({top.get_relationship_type_display()}).'
            )
        else:
            message = (
                f'"{document.title}" was linked to {len(new_relationships)} other documents, '
                f'including "{top.related_document.title}".'
            )
        create_notification(
            document.owner, message, 'relationship_discovered',
            link=f'/relationships/graph/?focus={document.pk}',
        )
    except Exception:
        logger.exception('Could not create relationship-discovered notification for document %s', document.pk)
