import re

import numpy as np
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer

from .nlp import ensure_nltk_data


def _split_sentences(text):
    if ensure_nltk_data():
        try:
            from nltk.tokenize import sent_tokenize
            return sent_tokenize(text)
        except LookupError:
            pass
    # Regex fallback: split on sentence-ending punctuation followed by whitespace.
    return re.split(r'(?<=[.!?])\s+', text)


def generate_summary(text, min_words=None, max_words=None):
    """
    Extractive summary: ranks sentences by their TF-IDF weight and keeps the
    top-scoring ones (in original order) until the word budget is met. Short
    documents are returned as-is, per the "shorter summary when there isn't
    enough text" requirement.
    """
    min_words = min_words or settings.AI_SUMMARY_MIN_WORDS
    max_words = max_words or settings.AI_SUMMARY_MAX_WORDS

    text = text.strip()
    if not text:
        return ''

    if len(text.split()) <= min_words:
        return text

    sentences = [s.strip() for s in _split_sentences(text) if s.strip()]
    if len(sentences) <= 3:
        words = text.split()
        return ' '.join(words[:max_words])

    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        words = text.split()
        return ' '.join(words[:max_words])

    sentence_scores = np.asarray(tfidf_matrix.sum(axis=1)).flatten()
    ranked_indices = sentence_scores.argsort()[::-1]

    selected_indices = []
    total_words = 0
    for idx in ranked_indices:
        selected_indices.append(int(idx))
        total_words += len(sentences[idx].split())
        if total_words >= min_words:
            break

    selected_indices.sort()
    summary = ' '.join(sentences[i] for i in selected_indices)

    words = summary.split()
    if len(words) > max_words:
        summary = ' '.join(words[:max_words]) + '...'
    return summary
