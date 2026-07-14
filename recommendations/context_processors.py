from .models import Notification


def notifications(request):
    """Exposes unread notification count + latest items to every template
    (used by the navbar bell dropdown, partials/_navbar.html)."""
    if not request.user.is_authenticated:
        return {}

    latest = Notification.objects.filter(user=request.user)[:8]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return {
        'nav_notifications': latest,
        'nav_unread_notifications_count': unread_count,
    }
