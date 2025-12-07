from django.contrib import admin
from .models import Conversation, Message, MessageMetadata, MessageFeedback, ConversationSummary


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['id', 'role', 'content', 'token_count', 'created_at', 'sequence_number']
    ordering = ['sequence_number']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user_id', 'status', 'message_count', 'created_at', 'last_message_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'title', 'user_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'message_count', 'total_tokens']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_id', 'role', 'short_content', 'status', 'created_at']
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['id', 'content']
    readonly_fields = ['id', 'created_at', 'sequence_number']
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content'


@admin.register(MessageMetadata)
class MessageMetadataAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_id', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost']
    readonly_fields = ['id', 'created_at']


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_id', 'feedback_type', 'rating', 'created_at']
    list_filter = ['feedback_type', 'rating', 'created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_id', 'message_range_start', 'message_range_end', 'created_at']
    readonly_fields = ['id', 'created_at']
