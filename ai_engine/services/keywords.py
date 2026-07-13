import re
from collections import Counter

from .nlp import ensure_nltk_data, get_spacy_nlp

BASIC_STOPWORDS = {
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her',
    'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how',
    'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did',
    'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that', 'with',
    'from', 'have', 'will', 'your', 'been', 'were', 'they', 'their', 'what',
    'when', 'where', 'which', 'there', 'these', 'those', 'into', 'also',
}

SPACY_ENTITY_LABELS = {'ORG', 'PERSON', 'GPE', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW', 'NORP'}


def extract_keywords(text, title='', max_keywords=10):
    combined = f'{title}. {text}'.strip(' .')
    if not combined:
        return []

    nlp = get_spacy_nlp()
    if nlp is not None:
        return _spacy_keywords(nlp, combined, max_keywords)
    return _fallback_keywords(combined, max_keywords)


def _clean_chunk(chunk):
    """Strip leading/trailing determiners, pronouns, and non-alphabetic
    tokens (numbers, stray punctuation from messy PDF column layouts), and
    reject anything left that's too long or not actually a phrase."""
    tokens = list(chunk)

    def _droppable(token):
        return token.is_stop and token.pos_ in {'DET', 'PRON'} or not token.is_alpha

    while tokens and _droppable(tokens[0]):
        tokens.pop(0)
    while tokens and _droppable(tokens[-1]):
        tokens.pop()

    if not tokens or len(tokens) > 4:
        return None

    phrase = ' '.join(t.text for t in tokens).strip()
    if not (2 <= len(phrase) <= 40):
        return None
    return phrase.lower()


def _spacy_keywords(nlp, text, max_keywords):
    doc = nlp(text[:100_000])  # cap length for performance on very long documents

    candidates = []
    for chunk in doc.noun_chunks:
        if chunk.root.is_stop or not chunk.root.is_alpha:
            continue
        cleaned = _clean_chunk(chunk)
        if cleaned:
            candidates.append(cleaned)

    for ent in doc.ents:
        if ent.label_ in SPACY_ENTITY_LABELS:
            cleaned = ent.text.strip().lower()
            if 2 <= len(cleaned) <= 40:
                candidates.append(cleaned)

    if not candidates:
        return _fallback_keywords(text, max_keywords)

    counter = Counter(candidates)
    return [phrase.title() for phrase, _ in counter.most_common(max_keywords)]


def _fallback_keywords(text, max_keywords):
    stop_words = BASIC_STOPWORDS
    tokens = re.findall(r"[A-Za-z]{3,}", text.lower())

    if ensure_nltk_data():
        try:
            from nltk.corpus import stopwords
            stop_words = set(stopwords.words('english'))
        except LookupError:
            pass

    filtered = [t for t in tokens if t not in stop_words]
    counter = Counter(filtered)
    return [word.title() for word, _ in counter.most_common(max_keywords)]
