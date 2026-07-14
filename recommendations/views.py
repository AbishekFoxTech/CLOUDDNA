from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from documents.models import Document

from .models import ActivityLog, Notification
from .services import (
    get_most_frequent_keywords,
    get_popular_documents,
    get_recently_viewed,
    get_recommendations_for_user,
    log_activity,
)


@login_required
def recommendations_view(request):
    from relationships.models import DocumentRelationship

    recommended = get_recommendations_for_user(request.user, limit=12)
    recently_viewed = get_recently_viewed(request.user, limit=8)
    popular = get_popular_documents(request.user, limit=8)

    related_documents = []
    related_source = recently_viewed[0] if recently_viewed else None
    if related_source:
        related_documents = DocumentRelationship.get_related_documents(related_source, limit=8)

    return render(request, 'recommendations/recommendations.html', {
        'recommended': recommended,
        'recently_viewed': recently_viewed,
        'popular_documents': popular,
        'related_documents': related_documents,
        'related_source': related_source,
    })


@login_required
def recommendation_click_view(request, pk):
    """
    A normal link-click navigation (GET) that also logs the click as an
    activity before redirecting - not a state-mutating action, so POST
    isn't required here (unlike favorite/delete/rename).
    """
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    log_activity(
        request.user, ActivityLog.EventType.RECOMMENDATION_CLICK, document=document,
        description=f'Clicked recommended document "{document.title}"',
    )
    return redirect('documents:detail', pk=document.pk)


@login_required
def activity_log_view(request):
    logs = ActivityLog.objects.filter(user=request.user).select_related('document')

    event_type = request.GET.get('event_type', '').strip()
    if event_type:
        logs = logs.filter(event_type=event_type)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'recommendations/activity_log.html', {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'event_types': ActivityLog.EventType.choices,
        'selected_event_type': event_type,
    })


@login_required
def notifications_list_api(request):
    notifications = Notification.objects.filter(user=request.user)[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.pk,
                'message': n.message,
                'type': n.notification_type,
                'link': n.link,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
            }
            for n in notifications
        ],
    })


@login_required
@require_POST
def mark_notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})
