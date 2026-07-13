from django.conf import settings
from django.db import models


def avatar_upload_path(instance, filename):
    return f'avatars/user_{instance.user_id}/{filename}'


class Profile(models.Model):
    """Extended profile information for a Django auth User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    avatar = models.ImageField(
        upload_to=avatar_upload_path, blank=True, null=True
    )
    bio = models.TextField(max_length=500, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    organization = models.CharField(max_length=150, blank=True)
    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Profile of {self.user.username}'
