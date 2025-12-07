"""
Chat service - handles message processing with Groq LLM and RAG.
"""
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from groq import Groq

from apps.core.exceptions import LLMProviderError, ConversationNotFoundError
from ..models import Conversation, Message, MessageMetadata

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Data class for chat response."""
    content: str
    message_id: str
    conversation_id: str
    tokens_used: int
    response_time_ms: float
    model: str
    sources: Optional[List[Dict]] = None  # RAG sources


class ChatService:
    """
    Service for handling chat operations with Groq LLM and RAG.
    
    Manages conversations, message history, and LLM interactions.
    When RAG is enabled, retrieves relevant documents from Pinecone.
    """
    
    def __init__(self):
        """Initialize the chat service with Groq client."""
        api_key = settings.CHAT_SETTINGS.get('LLM_API_KEY')
        if not api_key:
            logger.warning("LLM_API_KEY not configured, chat service will not work")
        
        self.client = Groq(api_key=api_key) if api_key else None
        self.model = settings.CHAT_SETTINGS.get('LLM_MODEL', 'llama-3.3-70b-versatile')
        self.max_history = settings.CHAT_SETTINGS.get('MAX_HISTORY_MESSAGES', 20)
        self.timeout = settings.CHAT_SETTINGS.get('LLM_TIMEOUT', 30)
        
        # RAG settings
        self.rag_enabled = getattr(settings, 'RAG_SETTINGS', {}).get('ENABLED', False)
        self._rag_agent = None
    
    @property
    def rag_agent(self):
        """Lazy load RAG agent."""
        if self._rag_agent is None and self.rag_enabled:
            try:
                from apps.rag.services import LangChainRAGAgent
                self._rag_agent = LangChainRAGAgent()
            except Exception as e:
                logger.warning(f"Failed to initialize RAG agent: {e}")
                self._rag_agent = None
        return self._rag_agent
    
    def process_message(
        self,
        prompt: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a user message and generate AI response.
        Uses RAG when enabled to retrieve relevant documents.
        
        Args:
            prompt: User's message
            conversation_id: Optional existing conversation ID
            user_id: Optional user ID for authentication
            system_prompt: Optional custom system prompt
        
        Returns:
            ChatResponse with AI response and metadata
        
        Raises:
            LLMProviderError: If LLM API call fails
            ConversationNotFoundError: If conversation_id is invalid
            PermissionError: If user doesn't own the conversation
        """
        if not self.client:
            raise LLMProviderError("LLM API key not configured")
        
        start_time = time.time()
        sources = None
        
        with transaction.atomic():
            # Get or create conversation
            conversation = self._get_or_create_conversation(
                conversation_id, user_id
            )
            
            # Save user message first
            user_message = self._save_message(
                conversation=conversation,
                role=Message.Role.USER,
                content=prompt,
                status=Message.Status.COMPLETED
            )
            
            try:
                # Check if we should use RAG
                if self.rag_enabled and self.rag_agent:
                    response_data = self._process_with_rag(
                        prompt=prompt,
                        conversation=conversation
                    )
                    sources = response_data.get('sources', [])
                else:
                    response_data = self._process_without_rag(
                        conversation=conversation,
                        system_prompt=system_prompt
                    )
                
                response_time = (time.time() - start_time) * 1000
                
                # Save assistant message
                assistant_message = self._save_message(
                    conversation=conversation,
                    role=Message.Role.ASSISTANT,
                    content=response_data['content'],
                    token_count=response_data.get('total_tokens', 0),
                    model_used=self.model,
                    response_time_ms=response_time,
                    status=Message.Status.COMPLETED
                )
                
                # Save metadata if available
                if 'prompt_tokens' in response_data:
                    self._save_metadata(
                        message=assistant_message,
                        response_data=response_data
                    )
                
                # Generate title if first exchange
                if conversation.message_count <= 2:
                    conversation.generate_title()
                
                logger.info(
                    f"Chat response generated",
                    extra={
                        'conversation_id': str(conversation.id),
                        'message_id': str(assistant_message.id),
                        'tokens': response_data.get('total_tokens', 0),
                        'response_time_ms': response_time,
                        'rag_enabled': self.rag_enabled
                    }
                )
                
                return ChatResponse(
                    content=response_data['content'],
                    message_id=str(assistant_message.id),
                    conversation_id=str(conversation.id),
                    tokens_used=response_data.get('total_tokens', 0),
                    response_time_ms=response_time,
                    model=self.model,
                    sources=sources
                )
                
            except Exception as e:
                logger.error(f"LLM call failed: {e}", exc_info=True)
                # Mark user message as failed
                user_message.status = Message.Status.FAILED
                user_message.save(update_fields=['status'])
                
                if 'rate_limit' in str(e).lower():
                    raise LLMProviderError(
                        "Rate limit exceeded. Please try again later.",
                        details={'original_error': str(e)}
                    )
                raise LLMProviderError(
                    "Failed to get response from AI",
                    details={'original_error': str(e)}
                )
    
    def _process_with_rag(
        self,
        prompt: str,
        conversation: Conversation
    ) -> Dict[str, Any]:
        """Process message using RAG agent with vector search."""
        # Get conversation history for context
        history = self._get_history_for_rag(conversation)
        
        # Use RAG agent
        result = self.rag_agent.generate_response(
            query=prompt,
            chat_history=history,
            top_k=getattr(settings, 'RAG_SETTINGS', {}).get('TOP_K_DOCUMENTS', 5)
        )
        
        return {
            'content': result['response'],
            'sources': result.get('sources', []),
            'total_tokens': 0,  # RAG doesn't expose token counts directly
        }
    
    def _process_without_rag(
        self,
        conversation: Conversation,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process message using direct Groq API call."""
        messages = self._build_context(
            conversation=conversation,
            system_prompt=system_prompt
        )
        return self._call_llm(messages)
    
    def _get_history_for_rag(
        self,
        conversation: Conversation
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for RAG agent."""
        history = conversation.messages.filter(
            status=Message.Status.COMPLETED
        ).order_by('sequence_number')[:self.max_history]
        
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in history
        ]

    
    def _get_or_create_conversation(
        self,
        conversation_id: Optional[str],
        user_id: Optional[str]
    ) -> Conversation:
        """Get existing or create new conversation."""
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    status=Conversation.Status.ACTIVE
                )
                # Verify user ownership if user_id provided
                if user_id and conversation.user_id:
                    if str(conversation.user_id) != str(user_id):
                        raise PermissionError("Conversation does not belong to user")
                return conversation
            except Conversation.DoesNotExist:
                logger.warning(f"Conversation {conversation_id} not found")
                raise ConversationNotFoundError(conversation_id)
        
        # Create new conversation
        return Conversation.objects.create(user_id=user_id)
    
    def _save_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        status: str = Message.Status.COMPLETED,
        **kwargs
    ) -> Message:
        """Save a message to the database."""
        return Message.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            status=status,
            **kwargs
        )
    
    def _build_context(
        self,
        conversation: Conversation,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build message context for LLM with conversation history.
        
        Includes system prompt and recent messages for context.
        """
        messages = []
        
        # Add system prompt
        system_content = system_prompt or self._get_default_system_prompt()
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Get recent history
        history = conversation.messages.filter(
            status=Message.Status.COMPLETED
        ).order_by('sequence_number')
        
        # Take last N messages for context
        history_list = list(history)
        if len(history_list) > self.max_history:
            history_list = history_list[-self.max_history:]
        
        # Add history in order
        for msg in history_list:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.debug(
            f"Built context with {len(messages)} messages",
            extra={'conversation_id': str(conversation.id)}
        )
        
        return messages
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the chatbot."""
        return (
            "You are a helpful, friendly, and knowledgeable AI assistant. "
            "Provide clear, accurate, and concise responses. "
            "If you don't know something, say so honestly. "
            "Be respectful and professional in all interactions."
        )
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make API call to Groq LLM.
        
        Args:
            messages: List of message dicts with role and content
        
        Returns:
            Dict with response content and token usage
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            timeout=self.timeout
        )
        
        return {
            'content': response.choices[0].message.content,
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens,
            'finish_reason': response.choices[0].finish_reason,
            'model': response.model
        }
    
    def _save_metadata(
        self,
        message: Message,
        response_data: Dict[str, Any]
    ) -> MessageMetadata:
        """Save response metadata for analytics."""
        return MessageMetadata.objects.create(
            message=message,
            prompt_tokens=response_data['prompt_tokens'],
            completion_tokens=response_data['completion_tokens'],
            finish_reason=response_data['finish_reason'],
            raw_response=response_data
        )
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: UUID of the conversation
            limit: Maximum number of messages to return
        
        Returns:
            List of message dicts
        """
        messages = Message.objects.filter(
            conversation_id=conversation_id,
            status=Message.Status.COMPLETED
        ).order_by('sequence_number')[:limit]
        
        return [
            {
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'token_count': msg.token_count
            }
            for msg in messages
        ]
    
    def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> bool:
        """
        Soft delete a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            user_id: Optional user ID for ownership verification
        
        Returns:
            True if deleted, raises exception otherwise
        """
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            if user_id and conversation.user_id and str(conversation.user_id) != str(user_id):
                raise PermissionError("Conversation does not belong to user")
            
            conversation.status = Conversation.Status.DELETED
            conversation.save(update_fields=['status', 'updated_at'])
            return True
        except Conversation.DoesNotExist:
            raise ConversationNotFoundError(conversation_id)
