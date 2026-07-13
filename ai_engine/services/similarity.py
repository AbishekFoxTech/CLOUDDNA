from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _corpus_text(document):
    return document.extracted_text.strip() or f'{document.title} {document.description}'.strip()


def compute_and_store_similarities(document, limit=None):
    """
    Compares `document` against the same owner's other AI-processed
    documents using TF-IDF + cosine similarity, then persists the top
    matches as DocumentRelationship rows and updates the document's own
    similarity_score/relationship_count fields.

    Returns the ranked list of (other_document, score) tuples actually
    stored.
    """
    from documents.models import Document
    from relationships.models import DocumentRelationship

    limit = limit or settings.AI_SIMILARITY_TOP_N

    other_documents = list(
        Document.objects.filter(owner=document.owner, ai_processed=True)
        .exclude(pk=document.pk)
    )

    DocumentRelationship.objects.filter(document=document).delete()

    if not other_documents:
        Document.objects.filter(pk=document.pk).update(similarity_score=0.0, relationship_count=0)
        return []

    texts = [_corpus_text(document)] + [_corpus_text(doc) for doc in other_documents]
    if not any(t.strip() for t in texts):
        Document.objects.filter(pk=document.pk).update(similarity_score=0.0, relationship_count=0)
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        Document.objects.filter(pk=document.pk).update(similarity_score=0.0, relationship_count=0)
        return []

    target_vector = tfidf_matrix[0:1]
    other_vectors = tfidf_matrix[1:]
    scores = cosine_similarity(target_vector, other_vectors).flatten()

    ranked = sorted(zip(other_documents, scores), key=lambda pair: pair[1], reverse=True)
    min_score = settings.AI_SIMILARITY_MIN_SCORE
    top_matches = [(doc, float(score)) for doc, score in ranked[:limit] if score >= min_score]

    DocumentRelationship.objects.bulk_create([
        DocumentRelationship(document=document, related_document=other, similarity_score=score)
        for other, score in top_matches
    ])

    top_score = top_matches[0][1] if top_matches else 0.0
    Document.objects.filter(pk=document.pk).update(
        similarity_score=top_score,
        relationship_count=len(top_matches),
    )

    return top_matches
