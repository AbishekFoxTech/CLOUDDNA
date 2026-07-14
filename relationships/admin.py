from django.contrib import admin
from django.db.models import Count

from .models import DocumentRelationship


@admin.register(DocumentRelationship)
class DocumentRelationshipAdmin(admin.ModelAdmin):
    change_list_template = 'admin/relationships/documentrelationship/change_list.html'

    list_display = [
        'document', 'related_document', 'relationship_type', 'similarity_score',
        'created_by', 'created_at',
    ]
    list_filter = ['relationship_type', 'computed_at']
    search_fields = ['document__title', 'related_document__title']
    readonly_fields = ['computed_at', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        by_type = qs.values('relationship_type').annotate(count=Count('id')).order_by('-count')
        type_labels = dict(DocumentRelationship.RelationshipType.choices)

        extra_context = extra_context or {}
        extra_context.update({
            'total_relationships': qs.count(),
            'relationship_type_breakdown': [
                {'label': type_labels.get(row['relationship_type'], row['relationship_type']), 'count': row['count']}
                for row in by_type
            ],
        })
        return super().changelist_view(request, extra_context=extra_context)
