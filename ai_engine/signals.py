import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from documents.models import Document

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def trigger_ai_pipeline(sender, instance, created, **kwargs):
    """
    Runs the AI pipeline automatically whenever a Document is first
    created (i.e. on upload), without touching documents.views at all.
    Only fires on creation - the pipeline itself persists its results via
    queryset .update() calls, which don't re-trigger post_save, so there's
    no re-entrancy risk here.
    """
    if not created:
        return

    from .services.pipeline import process_document

    try:
        process_document(instance)
    except Exception:
        logger.exception('AI pipeline crashed unexpectedly for document %s', instance.pk)
