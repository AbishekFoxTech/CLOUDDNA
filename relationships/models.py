from django.db import models
from django.db.models import Q


class DocumentRelationship(models.Model):
    """
    A directed edge storing the TF-IDF cosine similarity between two of the
    same user's documents. Computed by ai_engine.services.similarity after
    each document's AI pipeline run.
    """

    document = models.ForeignKey(
        'documents.Document', on_delete=models.CASCADE, related_name='similarities_from',
    )
    related_document = models.ForeignKey(
        'documents.Document', on_delete=models.CASCADE, related_name='similarities_to',
    )
    similarity_score = models.FloatField(default=0.0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-similarity_score']
        unique_together = ('document', 'related_document')
        indexes = [
            models.Index(fields=['document', '-similarity_score']),
        ]

    def __str__(self):
        return f'{self.document_id} ~ {self.related_document_id} ({self.similarity_score:.2f})'

    @staticmethod
    def get_related_documents(document, limit=5):
        """
        Related documents in either direction, highest similarity first.
        Returns a list of (Document, score) tuples. Filters out low scores
        at query time too (not just at compute time), so relationships
        stored before AI_SIMILARITY_MIN_SCORE existed don't resurface as
        "related" noise.
        """
        from django.conf import settings

        from documents.models import Document

        relationships = (
            DocumentRelationship.objects
            .filter(Q(document=document) | Q(related_document=document))
            .filter(similarity_score__gte=settings.AI_SIMILARITY_MIN_SCORE)
            .select_related('document', 'related_document')
            .order_by('-similarity_score')[:limit]
        )
        results = []
        for rel in relationships:
            other = rel.related_document if rel.document_id == document.pk else rel.document
            if isinstance(other, Document):
                results.append((other, rel.similarity_score))
        return results
