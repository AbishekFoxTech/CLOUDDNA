from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class DocumentRelationship(models.Model):
    """
    A directed edge between two of the same user's documents (source =
    `document`, target = `related_document`). The baseline "Similar" edges
    are computed by ai_engine.services.similarity (TF-IDF cosine) after
    each document's AI pipeline run; relationships.services.classify_
    relationships layers a `relationship_type` classification on top
    without altering that existing similarity math.
    """

    class RelationshipType(models.TextChoices):
        SIMILAR = 'similar', 'Similar'
        REFERENCED = 'referenced', 'Referenced'
        SAME_CATEGORY = 'same_category', 'Same Category'
        SAME_KEYWORDS = 'same_keywords', 'Same Keywords'
        DUPLICATE = 'duplicate', 'Duplicate'
        MANUAL = 'manual', 'Manual'

    document = models.ForeignKey(
        'documents.Document', on_delete=models.CASCADE, related_name='similarities_from',
    )
    related_document = models.ForeignKey(
        'documents.Document', on_delete=models.CASCADE, related_name='similarities_to',
    )
    similarity_score = models.FloatField(default=0.0)
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.SIMILAR,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Set only for manually-created relationships.',
    )
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-similarity_score']
        unique_together = ('document', 'related_document')
        indexes = [
            models.Index(fields=['document', '-similarity_score']),
            models.Index(fields=['relationship_type']),
        ]

    def __str__(self):
        return f'{self.document_id} ~ {self.related_document_id} ({self.get_relationship_type_display()})'

    @staticmethod
    def get_related_documents(document, limit=5):
        """
        Related documents in either direction, highest similarity first.
        Returns a list of (Document, score, relationship_type, relationship_pk)
        tuples. Filters out low scores at query time too (not just at
        compute time), so relationships stored before AI_SIMILARITY_MIN_SCORE
        existed don't resurface as "related" noise. Manual links always
        show regardless of score, since the user explicitly created them.
        """
        from documents.models import Document

        relationships = (
            DocumentRelationship.objects
            .filter(Q(document=document) | Q(related_document=document))
            .filter(
                Q(similarity_score__gte=settings.AI_SIMILARITY_MIN_SCORE)
                | Q(relationship_type=DocumentRelationship.RelationshipType.MANUAL)
            )
            .select_related('document', 'related_document')
            .order_by('-similarity_score')[:limit]
        )
        results = []
        for rel in relationships:
            other = rel.related_document if rel.document_id == document.pk else rel.document
            if isinstance(other, Document):
                results.append((other, rel.similarity_score, rel.relationship_type, rel.pk))
        return results

    @staticmethod
    def create_manual_relationship(document, related_document, user):
        """
        User-initiated link between two of their own documents. Always
        preserved by the auto-classifier in relationships.services
        (never silently overwritten by re-processing).
        """
        if document.pk == related_document.pk:
            raise ValueError('A document cannot be related to itself.')

        relationship, _created = DocumentRelationship.objects.update_or_create(
            document=document, related_document=related_document,
            defaults={
                'relationship_type': DocumentRelationship.RelationshipType.MANUAL,
                'similarity_score': 1.0,
                'created_by': user,
            },
        )
        return relationship
