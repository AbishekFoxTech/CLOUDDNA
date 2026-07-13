from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_document_storage():
    """
    Storage used for Document.file.

    All document types (PDF, DOCX, DOC, PPT, PPTX, XLSX, TXT, PNG, JPEG, JPG)
    are stored as Cloudinary "raw" resources rather than "image" resources.
    Cloudinary only auto-detects image transformations for the image
    resource type, which strips the extension from the returned public_id -
    that would make it impossible to reliably reconstruct the resource type
    later purely from the stored name. Using "raw" uniformly keeps the
    extension in the public_id for every file, so URL/delete lookups are
    unambiguous, while still serving images correctly (browsers render raw
    Cloudinary URLs by content-type, so <img> previews work fine).

    Falls back to local filesystem storage when Cloudinary credentials are
    not configured (see USE_CLOUDINARY in config/settings.py).
    """
    if getattr(settings, 'USE_CLOUDINARY', False):
        from cloudinary_storage.storage import RawMediaCloudinaryStorage
        return RawMediaCloudinaryStorage()
    return FileSystemStorage()
