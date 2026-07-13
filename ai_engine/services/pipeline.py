import hashlib
import logging
import math
import time

from django.utils import timezone

from . import categorizer, keywords as keyword_service, language as language_service
from . import similarity as similarity_service
from . import summarizer as summarizer_service
from .extraction import TextExtractionError, extract_text

logger = logging.getLogger(__name__)

WORDS_PER_MINUTE = 200


def process_document(document):
    """
    Runs the full AI pipeline for a single document: text extraction,
    metadata generation, keyword extraction, summarization, category
    detection, and similarity comparison against the owner's other
    documents. Every DB write goes through `.update()` on the queryset
    rather than `document.save()`, so this never re-triggers the
    post_save signal that calls this function in the first place.

    Designed to fail soft: any failure during extraction marks the
    document as AI Processing Failed with a human-readable reason and
    returns, instead of raising and breaking the calling request/signal.
    """
    from documents.models import Document

    start_time = time.perf_counter()
    Document.objects.filter(pk=document.pk).update(ai_status=Document.AIStatus.PROCESSING)

    try:
        document.file.open('rb')
        file_bytes = document.file.read()
        document.file.close()
    except Exception as exc:
        logger.exception('Could not read file for document %s', document.pk)
        _mark_failed(document, f'Could not read the uploaded file: {exc}')
        return

    document_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        extracted_text = extract_text(document.file_type, file_bytes)
    except TextExtractionError as exc:
        logger.warning('Text extraction failed for document %s: %s', document.pk, exc)
        _mark_failed(document, str(exc), document_hash=document_hash)
        return
    except Exception as exc:
        logger.exception('Unexpected error extracting text for document %s', document.pk)
        _mark_failed(document, f'Unexpected error while analyzing this file: {exc}', document_hash=document_hash)
        return

    word_count = len(extracted_text.split())
    reading_time = math.ceil(word_count / WORDS_PER_MINUTE) if word_count else 0
    detected_language = language_service.detect_language(extracted_text)

    try:
        extracted_keywords = keyword_service.extract_keywords(extracted_text, document.title)
    except Exception:
        logger.exception('Keyword extraction failed for document %s', document.pk)
        extracted_keywords = []

    try:
        summary = summarizer_service.generate_summary(extracted_text)
    except Exception:
        logger.exception('Summarization failed for document %s', document.pk)
        summary = extracted_text[:300]

    try:
        detected_category = categorizer.detect_category(extracted_text, document.title, document.file_type)
    except Exception:
        logger.exception('Category detection failed for document %s', document.pk)
        detected_category = Document.DetectedCategory.OTHERS

    processing_time = time.perf_counter() - start_time

    Document.objects.filter(pk=document.pk).update(
        extracted_text=extracted_text,
        summary=summary,
        keywords=', '.join(extracted_keywords),
        detected_category=detected_category,
        language=detected_language,
        word_count=word_count,
        reading_time=reading_time,
        document_hash=document_hash,
        processing_time=processing_time,
        ai_processed=True,
        ai_status=Document.AIStatus.COMPLETED,
        ai_error_message='',
        last_ai_scan=timezone.now(),
        metadata_extracted=True,
        ocr_processed=document.file_type in Document.IMAGE_EXTENSIONS,
    )
    document.refresh_from_db()

    try:
        similarity_service.compute_and_store_similarities(document)
    except Exception:
        # Similarity is an enhancement on top of a successful extraction -
        # don't let it flip an otherwise-successful run into a failure.
        logger.exception('Similarity computation failed for document %s', document.pk)


def _mark_failed(document, message, document_hash=''):
    from documents.models import Document

    Document.objects.filter(pk=document.pk).update(
        ai_status=Document.AIStatus.FAILED,
        ai_processed=False,
        ai_error_message=message[:2000],
        document_hash=document_hash,
        last_ai_scan=timezone.now(),
    )
