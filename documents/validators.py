import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_document_file(file):
    ext = os.path.splitext(file.name)[1].lower().lstrip('.')
    allowed = settings.DOCUMENT_ALLOWED_EXTENSIONS
    if ext not in allowed:
        raise ValidationError(
            f'Unsupported file type ".{ext}". Allowed types: {", ".join(sorted(allowed))}.'
        )

    max_size = settings.DOCUMENT_MAX_UPLOAD_SIZE
    if file.size > max_size:
        raise ValidationError(
            f'File is too large ({file.size / (1024 * 1024):.1f} MB). '
            f'Maximum allowed size is {max_size // (1024 * 1024)} MB.'
        )
