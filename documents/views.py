import os

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from relationships.models import DocumentRelationship

from .forms import DocumentRenameForm, DocumentUploadForm
from .models import Document


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _filtered_documents(request, force_favorites=False):
    qs = Document.objects.filter(owner=request.user)

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(category__icontains=query)
            | Q(tags__icontains=query)
            | Q(original_filename__icontains=query)
            | Q(description__icontains=query)
            | Q(extracted_text__icontains=query)
            | Q(keywords__icontains=query)
            | Q(summary__icontains=query)
            | Q(detected_category__icontains=query)
        )

    category = request.GET.get('category', '').strip()
    if category:
        qs = qs.filter(category=category)

    file_type = request.GET.get('file_type', '').strip()
    if file_type:
        qs = qs.filter(file_type=file_type)

    show_favorites = force_favorites or request.GET.get('favorites') == '1'
    if show_favorites:
        qs = qs.filter(favorite=True)

    sort = request.GET.get('sort', 'newest')
    qs = qs.order_by('uploaded_at' if sort == 'oldest' else '-uploaded_at')

    return qs, show_favorites


def _render_document_list(request, page_title, force_favorites=False, is_search_page=False):
    qs, show_favorites = _filtered_documents(request, force_favorites=force_favorites)

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)
    query_params = params.urlencode()

    file_types = (
        Document.objects.filter(owner=request.user)
        .exclude(file_type='')
        .values_list('file_type', flat=True)
        .distinct()
        .order_by('file_type')
    )

    return render(request, 'documents/list.html', {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'page_title': page_title,
        'categories': Document.Category.choices,
        'file_types': file_types,
        'show_favorites': show_favorites,
        'is_search_page': is_search_page,
        'query': request.GET.get('q', ''),
        'selected_category': request.GET.get('category', ''),
        'selected_file_type': request.GET.get('file_type', ''),
        'selected_sort': request.GET.get('sort', 'newest'),
        'query_params': query_params,
    })


@login_required
def document_list(request):
    return _render_document_list(request, page_title='My Documents')


@login_required
def document_favorites(request):
    return _render_document_list(request, page_title='Favorite Documents', force_favorites=True)


@login_required
def document_search(request):
    return _render_document_list(request, page_title='Search Documents', is_search_page=True)


@login_required
def document_upload(request):
    ajax = _is_ajax(request)

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.owner = request.user
            document.save()
            messages.success(request, f'"{document.title}" uploaded successfully.')

            if ajax:
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('documents:detail', args=[document.pk]),
                })
            return redirect('documents:detail', pk=document.pk)

        if ajax:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/upload.html', {
        'form': form,
        'max_upload_mb': settings.DOCUMENT_MAX_UPLOAD_SIZE // (1024 * 1024),
        'allowed_extensions': sorted(settings.DOCUMENT_ALLOWED_EXTENSIONS),
    })


@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    related_documents = DocumentRelationship.get_related_documents(document, limit=3)

    return render(request, 'documents/detail.html', {
        'document': document,
        'related_documents': related_documents,
    })


@login_required
def document_rename(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = DocumentRenameForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document renamed successfully.')
            return redirect('documents:detail', pk=document.pk)
    else:
        form = DocumentRenameForm(instance=document)

    return render(request, 'documents/rename.html', {'form': form, 'document': document})


@login_required
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    if request.method == 'POST':
        title = document.title
        document.file.delete(save=False)
        document.delete()
        messages.success(request, f'"{title}" was deleted.')
        return redirect('documents:list')
    return render(request, 'documents/delete_confirm.html', {'document': document})


@login_required
@require_POST
def document_toggle_favorite(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    document.favorite = not document.favorite
    document.save(update_fields=['favorite'])

    if _is_ajax(request):
        return JsonResponse({'favorite': document.favorite})

    messages.success(
        request,
        f'"{document.title}" {"added to" if document.favorite else "removed from"} favorites.',
    )
    return redirect(request.META.get('HTTP_REFERER') or reverse('documents:list'))


@login_required
def document_download(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    filename = document.original_filename or os.path.basename(document.file.name)

    if settings.USE_CLOUDINARY:
        upstream = requests.get(document.cloudinary_url, stream=True, timeout=15)
        if upstream.status_code != 200:
            messages.error(request, 'Unable to download this document right now.')
            return redirect('documents:detail', pk=document.pk)
        response = StreamingHttpResponse(
            upstream.iter_content(chunk_size=8192),
            content_type=upstream.headers.get('Content-Type', 'application/octet-stream'),
        )
    else:
        response = FileResponse(document.file.open('rb'), content_type='application/octet-stream')

    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
