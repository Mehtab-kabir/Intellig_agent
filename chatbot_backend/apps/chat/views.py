"""
Views for chat API endpoints.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.exceptions import ChatServiceError, LLMProviderError, ConversationNotFoundError
from .models import Conversation, Message, MessageFeedback
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ChatMessageInputSerializer,
    ChatMessageOutputSerializer,
    MessageSerializer,
    MessageFeedbackSerializer,
    MessageFeedbackInputSerializer
)
from .services import ChatService

logger = logging.getLogger(__name__)


class ChatViewSet(viewsets.ViewSet):
    """
    ViewSet for chat operations.
    
    Handles sending messages and receiving AI responses.
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()
    
    @extend_schema(
        request=ChatMessageInputSerializer,
        responses={
            200: ChatMessageOutputSerializer,
            400: OpenApiResponse(description='Invalid input'),
            404: OpenApiResponse(description='Conversation not found'),
            503: OpenApiResponse(description='LLM service unavailable')
        },
        description='Send a message and receive AI response',
        tags=['chat']
    )
    @action(detail=False, methods=['post'], url_path='message')
    def send_message(self, request):
        """
        Send a chat message and receive AI response.
        
        Creates a new conversation if conversation_id is not provided.
        Includes conversation history for context.
        
        Request body:
        - prompt: User's message (required)
        - conversation_id: UUID of existing conversation (optional)
        - system_prompt: Custom system prompt (optional)
        
        Returns AI response with message and conversation IDs.
        """
        serializer = ChatMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get user_id from authenticated user
            user_id = str(request.user.id)
            
            response = self.chat_service.process_message(
                prompt=serializer.validated_data['prompt'],
                conversation_id=serializer.validated_data.get('conversation_id'),
                user_id=user_id,
                system_prompt=serializer.validated_data.get('system_prompt')
            )
            
            output_serializer = ChatMessageOutputSerializer({
                'response': response.content,
                'conversation_id': response.conversation_id,
                'message_id': response.message_id,
                'tokens_used': response.tokens_used,
                'response_time_ms': response.response_time_ms,
                'model': response.model,
                'sources': response.sources
            })
            
            return Response(output_serializer.data, status=status.HTTP_200_OK)
            
        except ConversationNotFoundError as e:
            return Response(
                {'error': {'code': 'conversation_not_found', 'message': str(e)}},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            logger.warning(f"Permission denied: {e}")
            return Response(
                {'error': {'code': 'forbidden', 'message': str(e)}},
                status=status.HTTP_403_FORBIDDEN
            )
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e}")
            return Response(
                {'error': {'code': e.code, 'message': e.message, 'details': e.details}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return Response(
                {'error': {'code': 'internal_error', 'message': 'Failed to process message. Please try again.'}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    
    Supports listing, retrieving, and archiving conversations.
    """
    
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options']  # Disable PUT/POST/PATCH
    
    def get_queryset(self):
        """Get conversations for the authenticated user."""
        return Conversation.objects.filter(
            status=Conversation.Status.ACTIVE,
            user_id=self.request.user.id
        ).prefetch_related('messages').order_by('-last_message_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    @extend_schema(
        responses={200: MessageSerializer(many=True)},
        description='Get all messages in a conversation',
        tags=['conversations']
    )
    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        """Get all messages for a conversation."""
        conversation = self.get_object()
        messages = conversation.messages.filter(
            status=Message.Status.COMPLETED
        ).order_by('sequence_number')
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        description='Archive a conversation',
        responses={200: OpenApiResponse(description='Conversation archived')},
        tags=['conversations']
    )
    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        """Archive a conversation (soft delete)."""
        conversation = self.get_object()
        conversation.status = Conversation.Status.ARCHIVED
        conversation.is_archived = True
        conversation.save(update_fields=['status', 'is_archived', 'updated_at'])
        
        return Response({'status': 'archived', 'conversation_id': str(conversation.id)})
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a conversation."""
        conversation = self.get_object()
        conversation.status = Conversation.Status.DELETED
        conversation.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for message feedback."""
    
    permission_classes = [IsAuthenticated]
    queryset = MessageFeedback.objects.all()
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageFeedbackInputSerializer
        return MessageFeedbackSerializer
    
    @extend_schema(
        request=MessageFeedbackInputSerializer,
        responses={201: MessageFeedbackSerializer},
        description='Submit feedback for a message',
        tags=['feedback']
    )
    def create(self, request, *args, **kwargs):
        """Submit feedback for a message."""
        return super().create(request, *args, **kwargs)
