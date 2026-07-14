from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
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

    from recommendations.services import get_recommendations_for_user
    from relationships.models import DocumentRelationship

    relationship_count = DocumentRelationship.objects.filter(document__owner=request.user).count()
    recommended_documents = get_recommendations_for_user(request.user, limit=4)

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
        'relationship_count': relationship_count,
        'recommended_documents': recommended_documents,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def analytics_view(request):
    from recommendations.services import get_view_counts
    from relationships.models import DocumentRelationship

    user_documents = Document.objects.filter(owner=request.user)
    total_documents = user_documents.count()

    category_labels = dict(Document.Category.choices)
    uploads_by_category = (
        user_documents.values('category').annotate(count=Count('id')).order_by('-count')
    )
    category_chart = {
        'labels': [category_labels.get(row['category'], row['category']) for row in uploads_by_category],
        'data': [row['count'] for row in uploads_by_category],
    }

    twelve_months_ago = timezone.now() - timezone.timedelta(days=365)
    uploads_by_month = (
        user_documents.filter(uploaded_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('uploaded_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    month_chart = {
        'labels': [row['month'].strftime('%b %Y') for row in uploads_by_month],
        'data': [row['count'] for row in uploads_by_month],
    }

    ai_status_counts = (
        user_documents.values('ai_status').annotate(count=Count('id')).order_by('ai_status')
    )
    ai_status_labels = dict(Document.AIStatus.choices)
    ai_status_chart = {
        'labels': [ai_status_labels.get(row['ai_status'], row['ai_status']) for row in ai_status_counts],
        'data': [row['count'] for row in ai_status_counts],
    }

    doc_ids = list(user_documents.values_list('pk', flat=True))
    view_counts = get_view_counts(request.user, doc_ids)
    top_viewed_ids = sorted(view_counts, key=view_counts.get, reverse=True)[:8]
    documents_by_id = user_documents.in_bulk(top_viewed_ids)
    most_viewed = [
        {'document': documents_by_id[doc_id], 'views': view_counts[doc_id]}
        for doc_id in top_viewed_ids if doc_id in documents_by_id
    ]
    keyword_chart_source = _most_frequent_keywords(user_documents, limit=8)

    aggregates = user_documents.aggregate(
        avg_size=Avg('file_size'), avg_processing_time=Avg('processing_time'),
        total_storage=Sum('file_size'),
    )
    ai_processed_count = user_documents.filter(ai_processed=True).count()
    ai_processed_percentage = round((ai_processed_count / total_documents) * 100, 1) if total_documents else 0

    relationship_count = DocumentRelationship.objects.filter(document__owner=request.user).count()

    context = {
        'total_documents': total_documents,
        'favorite_documents': user_documents.filter(favorite=True).count(),
        'storage_used_display': _size_display(aggregates['total_storage'] or 0),
        'avg_document_size_display': _size_display(aggregates['avg_size'] or 0),
        'avg_processing_time': round(aggregates['avg_processing_time'] or 0, 2),
        'ai_processed_percentage': ai_processed_percentage,
        'relationship_count': relationship_count,
        'most_viewed': most_viewed,
        'category_chart': category_chart,
        'month_chart': month_chart,
        'ai_status_chart': ai_status_chart,
        'keyword_chart': {
            'labels': [kw for kw, _count in keyword_chart_source],
            'data': [count for _kw, count in keyword_chart_source],
        },
    }
    return render(request, 'dashboard/analytics.html', context)
