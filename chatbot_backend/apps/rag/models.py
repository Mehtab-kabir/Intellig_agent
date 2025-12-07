"""
Models for tracking ingested documents.
"""
import uuid
from django.db import models


class Document(models.Model):
    """Tracks ingested PDF documents."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, unique=True)
    file_path = models.CharField(max_length=500)
    total_chunks = models.IntegerField(default=0)
    total_pages = models.IntegerField(default=0)
    file_size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rag_documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} ({self.status})"


class DocumentChunk(models.Model):
    """Tracks individual chunks stored in Pinecone."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE, 
        related_name='chunks'
    )
    chunk_index = models.IntegerField()
    pinecone_id = models.CharField(max_length=100, unique=True)
    content_preview = models.TextField(help_text='First 500 chars of chunk')
    token_count = models.IntegerField(default=0)
    page_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rag_document_chunks'
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
    
    def __str__(self):
        return f"{self.document.filename} - Chunk {self.chunk_index}"
