import re

from .nlp import ensure_nltk_data

LANGUAGE_CODE_MAP = {
    'english': 'en', 'french': 'fr', 'spanish': 'es',
    'german': 'de', 'italian': 'it', 'portuguese': 'pt',
}


def detect_language(text):
    """
    Lightweight heuristic language guess based on stopword overlap - no
    dedicated language-detection library was in scope for this project, so
    this reuses the NLTK stopwords corpora we already ship. Defaults to
    English, which covers the overwhelming majority of real-world uploads
    for this app.
    """
    if not text.strip():
        return ''

    tokens = set(re.findall(r'[a-zA-Z]+', text.lower()))
    if not tokens:
        return 'en'

    if ensure_nltk_data():
        try:
            from nltk.corpus import stopwords
            best_lang, best_overlap = 'english', 0
            for lang in LANGUAGE_CODE_MAP:
                try:
                    lang_stopwords = set(stopwords.words(lang))
                except OSError:
                    continue
                overlap = len(tokens & lang_stopwords)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_lang = lang
            if best_overlap > 0:
                return LANGUAGE_CODE_MAP[best_lang]
        except LookupError:
            pass

    return 'en'
