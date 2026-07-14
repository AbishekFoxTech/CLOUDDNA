import os

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from recommendations.models import ActivityLog
from recommendations.services import log_activity
from relationships.models import DocumentRelationship

from .forms import DocumentRenameForm, DocumentUploadForm
from .models import Document

SEARCH_FIELDS = [
    'title', 'category', 'tags', 'original_filename', 'description',
    'extracted_text', 'keywords', 'summary', 'detected_category',
]


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _term_query(term):
    query = Q()
    for field in SEARCH_FIELDS:
        query |= Q(**{f'{field}__icontains': term})
    return query


def _filtered_documents(request, force_favorites=False):
    qs = Document.objects.filter(owner=request.user)

    query = request.GET.get('q', '').strip()
    match_mode = request.GET.get('match', 'any')
    if query:
        terms = query.split()
        term_queries = [_term_query(term) for term in terms]
        if match_mode == 'all':
            combined = term_queries[0]
            for term_query in term_queries[1:]:
                combined &= term_query
        else:
            combined = term_queries[0]
            for term_query in term_queries[1:]:
                combined |= term_query
        qs = qs.filter(combined)

    category = request.GET.get('category', '').strip()
    if category:
        qs = qs.filter(category=category)

    file_type = request.GET.get('file_type', '').strip()
    if file_type:
        qs = qs.filter(file_type=file_type)

    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(uploaded_at__date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(uploaded_at__date__lte=date_to)

    show_favorites = force_favorites or request.GET.get('favorites') == '1'
    if show_favorites:
        qs = qs.filter(favorite=True)

    sort = request.GET.get('sort', 'newest')
    if sort == 'oldest':
        qs = qs.order_by('uploaded_at')
    elif sort == 'alphabetical':
        qs = qs.order_by('title')
    elif sort == 'most_similar':
        qs = qs.order_by('-similarity_score')
    elif sort == 'most_viewed':
        qs = qs.annotate(
            view_count=Count('activity_logs', filter=Q(activity_logs__event_type=ActivityLog.EventType.VIEW))
        ).order_by('-view_count')
    else:
        qs = qs.order_by('-uploaded_at')

    if query:
        log_activity(
            request.user, ActivityLog.EventType.SEARCH,
            description=f'Searched for "{query}" ({match_mode.upper()})',
        )

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
        'match_mode': request.GET.get('match', 'any'),
        'selected_category': request.GET.get('category', ''),
        'selected_file_type': request.GET.get('file_type', ''),
        'selected_sort': request.GET.get('sort', 'newest'),
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
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
    from recommendations.services import get_recommendations_for_user

    document = get_object_or_404(Document, pk=pk, owner=request.user)

    log_activity(
        request.user, ActivityLog.EventType.VIEW, document=document,
        description=f'Viewed "{document.title}"',
    )

    related_documents = DocumentRelationship.get_related_documents(document, limit=5)
    related_ids = {doc.pk for doc, _score, _type, _rel_pk in related_documents}
    recommended = [
        (doc, reason) for doc, reason in get_recommendations_for_user(request.user, limit=8)
        if doc.pk != document.pk and doc.pk not in related_ids
    ][:5]
    activity = ActivityLog.objects.filter(document=document).select_related('user')[:20]
    other_documents = (
        Document.objects.filter(owner=request.user)
        .exclude(pk__in=related_ids | {document.pk})
        .only('pk', 'title')
    )

    return render(request, 'documents/detail.html', {
        'document': document,
        'related_documents': related_documents,
        'recommended_documents': recommended,
        'document_activity': activity,
        'other_documents': other_documents,
    })


@login_required
def document_rename(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)

    if request.method == 'POST':
        old_title = document.title
        form = DocumentRenameForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            log_activity(
                request.user, ActivityLog.EventType.RENAME, document=document,
                description=f'Renamed "{old_title}" to "{document.title}"',
            )
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
        # Logged with document=None (not the soon-to-be-deleted document):
        # ActivityLog.document cascades on delete, which would otherwise
        # wipe this very record along with the rest of the doc's history.
        log_activity(
            request.user, ActivityLog.EventType.DELETE,
            description=f'Deleted "{title}"',
        )
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

    action = 'added to' if document.favorite else 'removed from'
    log_activity(
        request.user, ActivityLog.EventType.FAVORITE, document=document,
        description=f'"{document.title}" {action} favorites',
    )
    from recommendations.services import create_notification
    create_notification(
        request.user, f'"{document.title}" {action} favorites.', 'favorite_updated',
        link=f'/documents/{document.pk}/',
    )

    if _is_ajax(request):
        return JsonResponse({'favorite': document.favorite})

    messages.success(request, f'"{document.title}" {action} favorites.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('documents:list'))


@login_required
def document_download(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    filename = document.original_filename or os.path.basename(document.file.name)

    log_activity(
        request.user, ActivityLog.EventType.DOWNLOAD, document=document,
        description=f'Downloaded "{document.title}"',
    )

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
