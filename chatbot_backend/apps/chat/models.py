"""
Chat models - Conversation, Message, and related models.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils import timezone


class Conversation(models.Model):
    """
    Represents a chat conversation/session.
    
    Each conversation can contain multiple messages and belongs to a user
    (user_id is nullable for Phase 1 before auth is implemented).
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        DELETED = 'deleted', 'Deleted'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="User ID (nullable for Phase 1, required after auth implementation)"
    )
    title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Conversation title, auto-generated from first message if not set"
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional conversation settings (e.g., custom system prompt)"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_archived = models.BooleanField(default=False)
    message_count = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"
    
    def generate_title(self):
        """Generate title from first user message if not set."""
        if not self.title:
            first_message = self.messages.filter(role=Message.Role.USER).first()
            if first_message:
                self.title = first_message.content[:100]
                self.save(update_fields=['title'])
    
    def update_stats(self):
        """Update conversation statistics."""
        self.message_count = self.messages.filter(
            status=Message.Status.COMPLETED
        ).count()
        self.total_tokens = self.messages.aggregate(
            total=models.Sum('token_count')
        )['total'] or 0
        self.save(update_fields=['message_count', 'total_tokens'])


class Message(models.Model):
    """
    Represents a single message in a conversation.
    
    Messages can be from user, assistant, or system.
    Each message has a sequence number for ordering.
    """
    
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        SYSTEM = 'system', 'System'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        STREAMING = 'streaming', 'Streaming'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REGENERATED = 'regenerated', 'Regenerated'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        db_index=True
    )
    content = models.TextField(
        validators=[
            MinLengthValidator(1),
            MaxLengthValidator(settings.CHAT_SETTINGS.get('MAX_MESSAGE_LENGTH', 4000))
        ]
    )
    token_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of tokens in this message"
    )
    model_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="LLM model used to generate response"
    )
    response_time_ms = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to generate response in milliseconds"
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.COMPLETED,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sequence_number = models.PositiveIntegerField(
        help_text="Order of message in conversation"
    )
    parent_message_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Parent message ID for regenerated messages"
    )
    
    class Meta:
        db_table = 'messages'
        ordering = ['sequence_number']
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'sequence_number'],
                name='unique_sequence_per_conversation'
            )
        ]
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['conversation', 'sequence_number']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence number if not set."""
        if not self.sequence_number:
            last_seq = Message.objects.filter(
                conversation=self.conversation
            ).aggregate(models.Max('sequence_number'))['sequence_number__max']
            self.sequence_number = (last_seq or 0) + 1
        super().save(*args, **kwargs)
        
        # Update conversation last_message_at
        self.conversation.last_message_at = timezone.now()
        self.conversation.save(update_fields=['last_message_at', 'updated_at'])


class MessageMetadata(models.Model):
    """
    Stores detailed metadata for AI responses.
    
    Tracks token usage, cost, and raw response data for analytics.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='metadata'
    )
    prompt_tokens = models.PositiveIntegerField(
        null=True,
        help_text="Number of tokens in the prompt"
    )
    completion_tokens = models.PositiveIntegerField(
        null=True,
        help_text="Number of tokens in the completion"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        help_text="Cost of this API call in USD"
    )
    finish_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reason for completion (stop, length, etc.)"
    )
    raw_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw response from LLM API for debugging"
    )
    latency_breakdown = models.JSONField(
        null=True,
        blank=True,
        help_text="Detailed latency metrics"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_metadata'
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)
    
    def __str__(self):
        return f"Metadata for message {self.message_id}"


class MessageFeedback(models.Model):
    """
    User feedback on AI responses.
    
    Allows users to rate responses and provide corrections.
    """
    
    class FeedbackType(models.TextChoices):
        THUMBS_UP = 'thumbs_up', 'Thumbs Up'
        THUMBS_DOWN = 'thumbs_down', 'Thumbs Down'
        REPORT = 'report', 'Report'
        CORRECTION = 'correction', 'Correction'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Rating from 1-5"
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional feedback comment"
    )
    feedback_type = models.CharField(
        max_length=50,
        choices=FeedbackType.choices,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_feedback'
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'feedback_type'],
                name='unique_feedback_per_type'
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5) | models.Q(rating__isnull=True),
                name='valid_rating_range'
            )
        ]
    
    def __str__(self):
        return f"{self.feedback_type} feedback for message {self.message_id}"


class ConversationSummary(models.Model):
    """
    Stores conversation summaries for context management.
    
    Used to maintain context for long conversations by summarizing
    older messages instead of including them directly.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='summaries'
    )
    summary = models.TextField(
        help_text="AI-generated summary of the message range"
    )
    message_range_start = models.PositiveIntegerField(
        help_text="Starting sequence number of summarized messages"
    )
    message_range_end = models.PositiveIntegerField(
        help_text="Ending sequence number of summarized messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversation_summaries'
        ordering = ['-message_range_end']
        constraints = [
            models.CheckConstraint(
                check=models.Q(message_range_start__lt=models.F('message_range_end')),
                name='valid_message_range'
            )
        ]
    
    def __str__(self):
        return f"Summary for conversation {self.conversation_id} ({self.message_range_start}-{self.message_range_end})"
