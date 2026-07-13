from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from documents.models import Document


def _size_display(num_bytes):
    size = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def _most_frequent_keywords(documents, limit=10):
    counter = Counter()
    for keywords in documents.exclude(keywords='').values_list('keywords', flat=True):
        counter.update(kw.strip() for kw in keywords.split(',') if kw.strip())
    return counter.most_common(limit)


@login_required
def dashboard_home(request):
    user_documents = Document.objects.filter(owner=request.user)

    total_documents = user_documents.count()
    favorite_documents = user_documents.filter(favorite=True).count()
    documents_today = user_documents.filter(uploaded_at__date=timezone.localdate()).count()
    storage_bytes = user_documents.aggregate(total=Sum('file_size'))['total'] or 0
    recent_uploads = user_documents[:5]

    recent_activity = [
        {
            'icon': 'bi-cloud-upload',
            'text': f'Uploaded "{doc.title}"',
            'timestamp': doc.uploaded_at,
        }
        for doc in recent_uploads
    ]

    documents_processed = user_documents.filter(ai_processed=True).count()
    pending_ai_processing = user_documents.filter(
        ai_status__in=[Document.AIStatus.PENDING, Document.AIStatus.PROCESSING]
    ).count()
    failed_ai_processing = user_documents.filter(ai_status=Document.AIStatus.FAILED).count()

    most_common_categories = (
        user_documents.exclude(detected_category='')
        .values('detected_category')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    category_labels = dict(Document.DetectedCategory.choices)
    most_common_categories = [
        {'label': category_labels.get(row['detected_category'], row['detected_category']), 'count': row['count']}
        for row in most_common_categories
    ]

    most_frequent_keywords = _most_frequent_keywords(user_documents)

    recent_ai_activity = list(
        user_documents.filter(ai_processed=True).order_by('-last_ai_scan')[:5]
    )

    context = {
        'total_documents': total_documents,
        'favorite_documents': favorite_documents,
        'documents_today': documents_today,
        'storage_used_display': _size_display(storage_bytes),
        'recent_uploads': recent_uploads,
        'recent_activity': recent_activity,
        'documents_processed': documents_processed,
        'pending_ai_processing': pending_ai_processing,
        'failed_ai_processing': failed_ai_processing,
        'most_common_categories': most_common_categories,
        'most_frequent_keywords': most_frequent_keywords,
        'recent_ai_activity': recent_ai_activity,
    }
    return render(request, 'dashboard/home.html', context)
