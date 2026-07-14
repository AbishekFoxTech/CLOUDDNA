from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """
    A single audit-trail entry for a user action. Powers the Activity Log
    page, the "Recently Viewed" / "Popular Documents" recommendation
    widgets, and the dashboard's Recent Activity feed.
    """

    class EventType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        UPLOAD = 'upload', 'Upload'
        VIEW = 'view', 'View'
        DOWNLOAD = 'download', 'Download'
        DELETE = 'delete', 'Delete'
        RENAME = 'rename', 'Rename'
        FAVORITE = 'favorite', 'Favorite'
        AI_PROCESSING = 'ai_processing', 'AI Processing'
        SEARCH = 'search', 'Search'
        RECOMMENDATION_CLICK = 'recommendation_click', 'Recommendation Click'
        GRAPH_INTERACTION = 'graph_interaction', 'Graph Interaction'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs',
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    document = models.ForeignKey(
        'documents.Document', on_delete=models.CASCADE, null=True, blank=True,
        related_name='activity_logs',
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'event_type', '-created_at']),
            models.Index(fields=['document', 'event_type']),
        ]

    def __str__(self):
        target = f' on "{self.document.title}"' if self.document_id else ''
        return f'{self.user.username} {self.get_event_type_display()}{target}'


class Notification(models.Model):
    """A persistent, dismissible notification shown in the navbar bell."""

    class NotificationType(models.TextChoices):
        DOCUMENT_UPLOADED = 'document_uploaded', 'Document Uploaded'
        AI_COMPLETED = 'ai_completed', 'AI Completed'
        AI_FAILED = 'ai_failed', 'AI Processing Failed'
        RELATIONSHIP_DISCOVERED = 'relationship_discovered', 'Relationship Discovered'
        DOCUMENT_DELETED = 'document_deleted', 'Document Deleted'
        FAVORITE_UPDATED = 'favorite_updated', 'Favorite Updated'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.message}'
