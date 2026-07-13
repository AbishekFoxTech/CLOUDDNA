from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from documents.models import Document
from relationships.models import DocumentRelationship

from .services.pipeline import process_document


@login_required
def ai_insights_view(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    related_documents = DocumentRelationship.get_related_documents(document)

    return render(request, 'ai_engine/insights.html', {
        'document': document,
        'related_documents': related_documents,
    })


@login_required
@require_POST
def retry_processing_view(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)

    process_document(document)
    document.refresh_from_db()

    if document.ai_status == Document.AIStatus.COMPLETED:
        messages.success(request, 'AI processing completed successfully.')
    else:
        messages.error(request, 'AI processing failed again. See the error details below.')

    return redirect('documents:detail', pk=document.pk)
