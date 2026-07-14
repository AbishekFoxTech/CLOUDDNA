from django.contrib import admin
from django.db.models import Avg, Count

from documents.models import Document

from .models import ActivityLog, Notification


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    change_list_template = 'admin/recommendations/activitylog/change_list.html'

    list_display = ['user', 'event_type', 'document', 'description', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['user__username', 'description', 'document__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        by_event = qs.values('event_type').annotate(count=Count('id')).order_by('-count')
        event_labels = dict(ActivityLog.EventType.choices)

        ai_stats = Document.objects.aggregate(avg_processing_time=Avg('processing_time'))
        total_documents = Document.objects.count()
        ai_processed = Document.objects.filter(ai_processed=True).count()

        extra_context = extra_context or {}
        extra_context.update({
            'total_activity': qs.count(),
            'event_breakdown': [
                {'label': event_labels.get(row['event_type'], row['event_type']), 'count': row['count']}
                for row in by_event
            ],
            'ai_total_documents': total_documents,
            'ai_processed_count': ai_processed,
            'ai_avg_processing_time': round(ai_stats['avg_processing_time'] or 0, 2),
        })
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'message', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
