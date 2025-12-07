from django.contrib import admin
from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'status', 'total_chunks', 'total_pages', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['filename']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'token_count', 'page_number']
    list_filter = ['document']
    search_fields = ['content_preview', 'pinecone_id']
    readonly_fields = ['id', 'created_at']
