"""
Serializers for chat API endpoints.
"""
from rest_framework import serializers
from django.conf import settings

from .models import Conversation, Message, MessageFeedback


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'token_count',
            'created_at', 'status', 'response_time_ms',
            'sequence_number'
        ]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model with messages."""
    
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'status', 'created_at',
            'updated_at', 'last_message_at', 'message_count',
            'total_tokens', 'messages'
        ]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists."""
    
    preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'status', 'created_at',
            'last_message_at', 'message_count', 'preview'
        ]
    
    def get_preview(self, obj) -> str:
        """Get preview of last message."""
        last_msg = obj.messages.filter(
            status=Message.Status.COMPLETED
        ).last()
        if last_msg:
            content = last_msg.content
            return content[:100] + ('...' if len(content) > 100 else '')
        return None


class ChatMessageInputSerializer(serializers.Serializer):
    """Serializer for chat message input."""
    
    prompt = serializers.CharField(
        max_length=settings.CHAT_SETTINGS.get('MAX_MESSAGE_LENGTH', 4000),
        min_length=1,
        help_text="User's message/prompt"
    )
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional conversation ID to continue existing conversation"
    )
    system_prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text="Optional custom system prompt"
    )


class ChatMessageOutputSerializer(serializers.Serializer):
    """Serializer for chat response output."""
    
    response = serializers.CharField(help_text="AI generated response")
    conversation_id = serializers.UUIDField(help_text="Conversation ID")
    message_id = serializers.UUIDField(help_text="Message ID of the AI response")
    tokens_used = serializers.IntegerField(help_text="Total tokens used")
    response_time_ms = serializers.FloatField(help_text="Response time in milliseconds")
    model = serializers.CharField(help_text="LLM model used")
    sources = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_null=True,
        help_text="Source documents used for RAG response"
    )


class MessageFeedbackInputSerializer(serializers.ModelSerializer):
    """Serializer for submitting message feedback."""
    
    class Meta:
        model = MessageFeedback
        fields = ['message', 'rating', 'comment', 'feedback_type']
    
    def validate_rating(self, value):
        """Ensure rating is between 1 and 5."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class MessageFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for message feedback responses."""
    
    class Meta:
        model = MessageFeedback
        fields = ['id', 'message', 'rating', 'comment', 'feedback_type', 'created_at']
        read_only_fields = ['id', 'created_at']
