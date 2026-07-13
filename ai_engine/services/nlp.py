import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_spacy_nlp = None
_spacy_load_attempted = False


def get_spacy_nlp():
    """
    Lazily load and cache the spaCy pipeline for the life of the process.
    Returns None if the model isn't installed, so callers fall back to a
    simpler NLTK/regex-based approach instead of crashing.
    """
    global _spacy_nlp, _spacy_load_attempted
    if _spacy_load_attempted:
        return _spacy_nlp

    _spacy_load_attempted = True
    try:
        import spacy
        _spacy_nlp = spacy.load(settings.AI_SPACY_MODEL)
    except Exception:
        logger.warning(
            'spaCy model "%s" unavailable; falling back to NLTK-based NLP.',
            settings.AI_SPACY_MODEL,
        )
        _spacy_nlp = None
    return _spacy_nlp


def ensure_nltk_data():
    """
    Verify required NLTK corpora are present, downloading them if missing.
    Returns True if all data is available, False otherwise (callers should
    fall back gracefully rather than crash the AI pipeline).
    """
    import nltk

    required = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords'),
    ]
    all_ok = True
    for path, package in required:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(package, quiet=True)
            except Exception:
                all_ok = False
    return all_ok
