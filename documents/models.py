import os

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from .storage import get_document_storage
from .validators import validate_document_file


def document_upload_path(instance, filename):
    return f'documents/user_{instance.owner_id}/{filename}'


class Document(models.Model):
    """A digital asset uploaded by a user, stored on Cloudinary."""

    class Category(models.TextChoices):
        ACADEMIC = 'academic', 'Academic'
        FINANCE = 'finance', 'Finance'
        PERSONAL = 'personal', 'Personal'
        RESEARCH = 'research', 'Research'
        REPORTS = 'reports', 'Reports'
        CONTRACTS = 'contracts', 'Contracts'
        IMAGES = 'images', 'Images'
        OTHERS = 'others', 'Others'

    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'
        ARCHIVED = 'archived', 'Archived'

    class DetectedCategory(models.TextChoices):
        """
        AI-inferred category, distinct from the user-editable `category`
        field above. Intentionally a different set of labels (adds Medical,
        Business, Legal; drops Contracts) to match what the classifier is
        actually tuned to detect, without touching the existing manual
        upload category choices.
        """
        ACADEMIC = 'academic', 'Academic'
        FINANCE = 'finance', 'Finance'
        RESEARCH = 'research', 'Research'
        MEDICAL = 'medical', 'Medical'
        BUSINESS = 'business', 'Business'
        PERSONAL = 'personal', 'Personal'
        LEGAL = 'legal', 'Legal'
        REPORTS = 'reports', 'Reports'
        IMAGES = 'images', 'Images'
        OTHERS = 'others', 'Others'

    class AIStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'AI Processing Failed'

    IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    ICON_BY_EXTENSION = {
        'pdf': 'bi-file-earmark-pdf',
        'doc': 'bi-file-earmark-word',
        'docx': 'bi-file-earmark-word',
        'ppt': 'bi-file-earmark-ppt',
        'pptx': 'bi-file-earmark-ppt',
        'xlsx': 'bi-file-earmark-excel',
        'txt': 'bi-file-earmark-text',
        'png': 'bi-file-earmark-image',
        'jpg': 'bi-file-earmark-image',
        'jpeg': 'bi-file-earmark-image',
    }

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHERS
    )
    tags = models.CharField(
        max_length=255, blank=True,
        help_text='Comma-separated tags, e.g. "invoice, 2026, client-a"',
    )

    file = models.FileField(
        upload_to=document_upload_path,
        storage=get_document_storage,
        validators=[validate_document_file],
    )
    cloudinary_url = models.URLField(blank=True)
    public_id = models.CharField(max_length=500, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveBigIntegerField(default=0, help_text='Size in bytes')

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    favorite = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.READY
    )

    ocr_processed = models.BooleanField(default=False)
    metadata_extracted = models.BooleanField(default=False)
    summary = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True)

    slug = models.SlugField(max_length=280, unique=True, blank=True)
    relationship_count = models.PositiveIntegerField(default=0)

    # --- AI pipeline fields (populated by ai_engine.services.pipeline) ---
    extracted_text = models.TextField(blank=True)
    detected_category = models.CharField(
        max_length=20, choices=DetectedCategory.choices, blank=True,
    )
    language = models.CharField(max_length=10, blank=True)
    word_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(default=0, help_text='Estimated reading time in minutes')
    ai_processed = models.BooleanField(default=False)
    ai_status = models.CharField(
        max_length=20, choices=AIStatus.choices, default=AIStatus.PENDING,
    )
    ai_error_message = models.TextField(blank=True)
    processing_time = models.FloatField(default=0.0, help_text='AI pipeline duration in seconds')
    document_hash = models.CharField(max_length=64, blank=True, db_index=True)
    similarity_score = models.FloatField(default=0.0, help_text='Highest similarity score against another document')
    last_ai_scan = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['owner', 'category']),
            models.Index(fields=['owner', 'favorite']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_creation = self._state.adding

        if is_creation and self.file:
            if not self.original_filename:
                self.original_filename = os.path.basename(self.file.name)
            self.file_type = os.path.splitext(
                self.original_filename or self.file.name
            )[1].lstrip('.').lower()
            try:
                self.file_size = self.file.size
            except (ValueError, OSError):
                pass

        if not self.slug:
            self.slug = self._generate_unique_slug()

        super().save(*args, **kwargs)

        if is_creation and self.file:
            update_fields = []
            url = self.file.url
            public_id = self.file.name
            if url != self.cloudinary_url:
                self.cloudinary_url = url
                update_fields.append('cloudinary_url')
            if public_id != self.public_id:
                self.public_id = public_id
                update_fields.append('public_id')
            if update_fields:
                Document.objects.filter(pk=self.pk).update(
                    **{field: getattr(self, field) for field in update_fields}
                )

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)[:250] or 'document'
        slug = base_slug
        counter = 1
        while Document.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            counter += 1
            slug = f'{base_slug}-{counter}'
        return slug

    @property
    def size_display(self):
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    @property
    def is_image(self):
        return self.file_type in self.IMAGE_EXTENSIONS

    @property
    def is_pdf(self):
        return self.file_type == 'pdf'

    @property
    def icon_class(self):
        return self.ICON_BY_EXTENSION.get(self.file_type, 'bi-file-earmark')

    @property
    def keyword_list(self):
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]

    @property
    def reading_time_display(self):
        if not self.reading_time:
            return 'Less than 1 min'
        return f'{self.reading_time} min read'
