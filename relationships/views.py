from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from documents.models import Document
from recommendations.models import ActivityLog
from recommendations.services import log_activity

from .models import DocumentRelationship


@login_required
def graph_view(request):
    focus_pk = None
    raw_focus = request.GET.get('focus', '')
    if raw_focus.isdigit():
        focus_pk = int(raw_focus)
    return render(request, 'relationships/graph.html', {'focus_pk': focus_pk})


@login_required
def graph_data_api(request):
    """
    JSON node/edge data for the current user's document relationship
    graph, in a shape Cytoscape.js consumes directly.
    """
    documents = list(Document.objects.filter(owner=request.user))
    doc_ids = {doc.pk for doc in documents}

    relationships = (
        DocumentRelationship.objects
        .filter(document__owner=request.user, related_document__owner=request.user)
        .filter(
            Q(similarity_score__gte=settings.AI_SIMILARITY_MIN_SCORE)
            | Q(relationship_type=DocumentRelationship.RelationshipType.MANUAL)
        )
        .select_related('document', 'related_document')
    )

    nodes = [
        {
            'data': {
                'id': str(doc.pk),
                'label': doc.title,
                'category': doc.detected_category or doc.category,
                'file_type': doc.file_type,
                'favorite': doc.favorite,
                'ai_status': doc.ai_status,
                'url': f'/documents/{doc.pk}/',
            }
        }
        for doc in documents
    ]

    edges = []
    for rel in relationships:
        if rel.document_id not in doc_ids or rel.related_document_id not in doc_ids:
            continue
        edges.append({
            'data': {
                'id': f'e{rel.pk}',
                'source': str(rel.document_id),
                'target': str(rel.related_document_id),
                'type': rel.relationship_type,
                'type_label': rel.get_relationship_type_display(),
                'score': round(rel.similarity_score, 3),
            }
        })

    log_activity(request.user, ActivityLog.EventType.GRAPH_INTERACTION, description='Opened relationship graph')

    return JsonResponse({'nodes': nodes, 'edges': edges})


@login_required
@require_POST
def create_manual_link_view(request):
    document = get_object_or_404(Document, pk=request.POST.get('document_id'), owner=request.user)
    related_document = get_object_or_404(Document, pk=request.POST.get('related_document_id'), owner=request.user)

    try:
        DocumentRelationship.create_manual_relationship(document, related_document, request.user)
        messages.success(request, f'Linked "{document.title}" to "{related_document.title}".')
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('documents:detail', pk=document.pk)


@login_required
@require_POST
def delete_relationship_view(request, pk):
    relationship = get_object_or_404(
        DocumentRelationship.objects.filter(Q(document__owner=request.user) | Q(related_document__owner=request.user)),
        pk=pk,
    )
    document_pk = relationship.document_id
    relationship.delete()
    messages.success(request, 'Relationship removed.')
    return redirect('documents:detail', pk=document_pk)
