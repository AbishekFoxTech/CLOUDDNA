from django.contrib import admin

from .models import DocumentRelationship


@admin.register(DocumentRelationship)
class DocumentRelationshipAdmin(admin.ModelAdmin):
    list_display = ['document', 'related_document', 'similarity_score', 'computed_at']
    list_filter = ['computed_at']
    search_fields = ['document__title', 'related_document__title']
    readonly_fields = ['computed_at']
