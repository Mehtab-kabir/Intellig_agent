"""
URL routes for chat API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ChatViewSet, ConversationViewSet, FeedbackViewSet

router = DefaultRouter()
router.register(r'chat', ChatViewSet, basename='chat')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'feedback', FeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
]
