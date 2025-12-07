"""
Custom pagination classes.
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list views."""
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MessageCursorPagination(CursorPagination):
    """
    Cursor pagination for messages.
    
    More efficient for real-time apps with frequently changing data.
    """
    
    page_size = 50
    ordering = '-created_at'
    cursor_query_param = 'cursor'
