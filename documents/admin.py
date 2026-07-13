from django.contrib import admin
from django.db.models import Sum

from .models import Document


def _size_display(num_bytes):
    size = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    change_list_template = 'admin/documents/document/change_list.html'

    list_display = [
        'title', 'owner', 'category', 'detected_category', 'file_type', 'size_display',
        'favorite', 'status', 'ai_status', 'word_count', 'processing_time', 'uploaded_at',
    ]
    list_filter = [
        'category', 'detected_category', 'file_type', 'status', 'ai_status',
        'favorite', 'uploaded_at',
    ]
    search_fields = [
        'title', 'description', 'tags', 'owner__username', 'original_filename',
        'extracted_text', 'keywords', 'summary',
    ]
    readonly_fields = [
        'cloudinary_url', 'public_id', 'original_filename', 'file_type',
        'file_size', 'uploaded_at', 'updated_at', 'slug',
        'extracted_text', 'document_hash', 'processing_time', 'last_ai_scan',
        'ai_error_message', 'similarity_score', 'relationship_count',
    ]
    date_hierarchy = 'uploaded_at'
    list_per_page = 25

    fieldsets = (
        ('Document', {
            'fields': (
                'owner', 'title', 'description', 'category', 'tags', 'favorite', 'status',
            )
        }),
        ('File', {
            'fields': (
                'file', 'file_type', 'file_size', 'original_filename',
                'cloudinary_url', 'public_id', 'slug',
            )
        }),
        ('AI Analysis', {
            'fields': (
                'ai_status', 'ai_error_message', 'ai_processed', 'detected_category',
                'language', 'word_count', 'reading_time', 'processing_time',
                'document_hash', 'last_ai_scan', 'keywords', 'summary', 'extracted_text',
                'ocr_processed', 'metadata_extracted',
            )
        }),
        ('Relationships', {
            'fields': ('similarity_score', 'relationship_count'),
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at'),
        }),
    )

    actions = ['retry_ai_processing']

    @admin.action(description='Retry AI processing for selected documents')
    def retry_ai_processing(self, request, queryset):
        from ai_engine.services.pipeline import process_document

        for document in queryset:
            process_document(document)
        self.message_user(request, f'AI processing re-run for {queryset.count()} document(s).')

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        total_storage_bytes = qs.aggregate(total=Sum('file_size'))['total'] or 0

        extra_context = extra_context or {}
        extra_context.update({
            'total_documents': qs.count(),
            'total_favorites': qs.filter(favorite=True).count(),
            'total_storage_display': _size_display(total_storage_bytes),
        })
        return super().changelist_view(request, extra_context=extra_context)
