import logging
from collections import Counter

from django.db.models import Count, Max

from .models import ActivityLog, Notification

logger = logging.getLogger(__name__)


def log_activity(user, event_type, document=None, description=''):
    """Best-effort activity logging - never allowed to break the caller."""
    try:
        return ActivityLog.objects.create(
            user=user, event_type=event_type, document=document, description=description,
        )
    except Exception:
        logger.exception('Failed to log activity %s for user %s', event_type, user)
        return None


def create_notification(user, message, notification_type, link=''):
    """Best-effort notification creation - never allowed to break the caller."""
    try:
        return Notification.objects.create(
            user=user, message=message, notification_type=notification_type, link=link,
        )
    except Exception:
        logger.exception('Failed to create notification for user %s', user)
        return None


def get_recently_viewed(user, limit=5):
    """Distinct documents this user viewed, most recent first."""
    from documents.models import Document

    document_ids = list(
        ActivityLog.objects
        .filter(user=user, event_type=ActivityLog.EventType.VIEW, document__isnull=False)
        .values('document_id')
        .annotate(last_viewed=Max('created_at'))
        .order_by('-last_viewed')
        .values_list('document_id', flat=True)[:limit]
    )
    documents_by_id = Document.objects.in_bulk(document_ids)
    return [documents_by_id[doc_id] for doc_id in document_ids if doc_id in documents_by_id]


def get_popular_documents(user, limit=5):
    """This user's own documents, ranked by how often they've been viewed."""
    from documents.models import Document

    ranked_ids = list(
        ActivityLog.objects
        .filter(user=user, event_type=ActivityLog.EventType.VIEW, document__isnull=False)
        .values('document_id')
        .annotate(view_count=Count('id'))
        .order_by('-view_count')
        .values_list('document_id', flat=True)[:limit]
    )
    documents_by_id = Document.objects.in_bulk(ranked_ids)
    return [documents_by_id[doc_id] for doc_id in ranked_ids if doc_id in documents_by_id]


def get_view_counts(user, document_ids):
    """Bulk view-count lookup for a set of document ids, for sorting/display."""
    counts = (
        ActivityLog.objects
        .filter(user=user, event_type=ActivityLog.EventType.VIEW, document_id__in=document_ids)
        .values('document_id')
        .annotate(view_count=Count('id'))
    )
    return {row['document_id']: row['view_count'] for row in counts}


def get_recommendations_for_user(user, limit=10):
    """
    Blends several signals into a single ranked "Recommended for You" list:
    TF-IDF/relationship similarity, shared keywords/category with recently
    viewed documents, and popularity. Returns a list of
    (Document, reason) tuples.
    """
    from documents.models import Document
    from relationships.models import DocumentRelationship

    user_documents = Document.objects.filter(owner=user, ai_processed=True)
    if not user_documents.exists():
        return []

    recently_viewed = get_recently_viewed(user, limit=5)
    seed_documents = recently_viewed or list(user_documents.order_by('-uploaded_at')[:5])
    seed_ids = {doc.pk for doc in seed_documents}

    scored = {}

    # Signal 1: related documents (any relationship type) to recently
    # viewed/uploaded seed documents.
    for seed in seed_documents:
        for other, score, rel_type, _rel_pk in DocumentRelationship.get_related_documents(seed, limit=5):
            if other.pk in seed_ids:
                continue
            entry = scored.setdefault(other.pk, {'document': other, 'score': 0.0, 'reasons': set()})
            entry['score'] += score
            entry['reasons'].add(f'Related to "{seed.title}"')

    # Signal 2: shared category with seed documents.
    seed_categories = {doc.detected_category or doc.category for doc in seed_documents}
    for doc in user_documents.exclude(pk__in=seed_ids):
        if (doc.detected_category or doc.category) in seed_categories:
            entry = scored.setdefault(doc.pk, {'document': doc, 'score': 0.0, 'reasons': set()})
            entry['score'] += 0.15
            entry['reasons'].add('Matches a category you view often')

    # Signal 3: shared keywords with seed documents.
    seed_keywords = set()
    for doc in seed_documents:
        seed_keywords.update(doc.keyword_list)
    if seed_keywords:
        for doc in user_documents.exclude(pk__in=seed_ids):
            overlap = seed_keywords & set(doc.keyword_list)
            if overlap:
                entry = scored.setdefault(doc.pk, {'document': doc, 'score': 0.0, 'reasons': set()})
                entry['score'] += 0.1 * len(overlap)
                entry['reasons'].add('Shares keywords with your recent activity')

    # Signal 4: popularity as a tie-breaker / fallback when the above
    # signals are sparse (e.g. a brand-new account).
    view_counts = get_view_counts(user, list(user_documents.values_list('pk', flat=True)))
    for doc_id, count in view_counts.items():
        if doc_id in seed_ids or doc_id not in scored:
            continue
        scored[doc_id]['score'] += min(count, 5) * 0.02

    ranked = sorted(scored.values(), key=lambda entry: entry['score'], reverse=True)[:limit]
    return [(entry['document'], ' / '.join(sorted(entry['reasons']))) for entry in ranked]


def get_most_frequent_keywords(user, limit=10):
    from documents.models import Document

    counter = Counter()
    for keywords in (
        Document.objects.filter(owner=user).exclude(keywords='').values_list('keywords', flat=True)
    ):
        counter.update(kw.strip() for kw in keywords.split(',') if kw.strip())
    return counter.most_common(limit)
