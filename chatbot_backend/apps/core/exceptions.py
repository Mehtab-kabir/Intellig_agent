"""
Custom exception handling for consistent API error responses.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Exception raised when chat service encounters an error."""
    
    def __init__(self, message: str, code: str = 'chat_error', details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class LLMProviderError(ChatServiceError):
    """Exception raised when LLM provider returns an error."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code='llm_provider_error', details=details)


class ConversationNotFoundError(ChatServiceError):
    """Exception raised when conversation is not found."""
    
    def __init__(self, conversation_id: str):
        super().__init__(
            f"Conversation {conversation_id} not found",
            code='conversation_not_found',
            details={'conversation_id': conversation_id}
        )


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    
    Returns errors in the format:
    {
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {...}
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data = {
            'error': {
                'code': _get_error_code(response.status_code),
                'message': _get_error_message(response.data),
                'details': response.data if isinstance(response.data, dict) else None
            }
        }
    elif isinstance(exc, ChatServiceError):
        # Handle custom chat service errors
        logger.warning(f"Chat service error: {exc.message}", extra={'code': exc.code})
        response = Response(
            {
                'error': {
                    'code': exc.code,
                    'message': exc.message,
                    'details': exc.details
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    elif isinstance(exc, LLMProviderError):
        # Handle LLM provider errors
        logger.error(f"LLM provider error: {exc.message}", exc_info=True)
        response = Response(
            {
                'error': {
                    'code': exc.code,
                    'message': 'Failed to get response from AI. Please try again.',
                    'details': exc.details
                }
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    else:
        # Handle unhandled exceptions
        logger.exception(f"Unhandled exception: {exc}")
        response = Response(
            {
                'error': {
                    'code': 'internal_server_error',
                    'message': 'An unexpected error occurred. Please try again.',
                    'details': None
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response


def _get_error_code(status_code: int) -> str:
    """Map HTTP status code to error code."""
    status_map = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        429: 'rate_limited',
        500: 'internal_server_error',
        503: 'service_unavailable',
    }
    return status_map.get(status_code, 'unknown_error')


def _get_error_message(data) -> str:
    """Extract error message from response data."""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        # Get first error field
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            return f"{key}: {value}"
    return str(data)
