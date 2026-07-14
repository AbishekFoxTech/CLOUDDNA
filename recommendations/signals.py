import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from documents.models import Document

from .models import ActivityLog
from .services import create_notification, log_activity

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """
    Hooks Django's built-in auth signal rather than touching
    accounts.views - fires automatically whenever django.contrib.auth.
    login() succeeds, regardless of which view called it.
    """
    log_activity(user, ActivityLog.EventType.LOGIN, description='Logged in')


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is not None:
        log_activity(user, ActivityLog.EventType.LOGOUT, description='Logged out')


@receiver(post_save, sender=Document)
def on_document_uploaded(sender, instance, created, **kwargs):
    """
    Logs the upload + creates a notification. Connected independently of
    ai_engine.signals.trigger_ai_pipeline (both receivers run for the same
    post_save event without interfering with each other); documents.views.
    document_upload itself is never touched.
    """
    if not created:
        return

    log_activity(
        instance.owner, ActivityLog.EventType.UPLOAD, document=instance,
        description=f'Uploaded "{instance.title}"',
    )
    create_notification(
        instance.owner,
        f'"{instance.title}" was uploaded successfully.',
        'document_uploaded',
        link=f'/documents/{instance.pk}/',
    )
