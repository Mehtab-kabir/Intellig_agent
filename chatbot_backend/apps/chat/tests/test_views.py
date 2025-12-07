"""
Tests for chat API views.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.chat.models import Conversation, Message


class ChatAPITest(TestCase):
    """Tests for Chat API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_list_conversations(self):
        """Test listing conversations."""
        # Create test conversations
        Conversation.objects.create(title="Test 1")
        Conversation.objects.create(title="Test 2")
        
        response = self.client.get('/api/v1/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_conversation_detail(self):
        """Test getting conversation details."""
        conversation = Conversation.objects.create(title="Test Chat")
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hello"
        )
        
        response = self.client.get(f'/api/v1/conversations/{conversation.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Test Chat")
    
    def test_get_conversation_messages(self):
        """Test getting conversation messages."""
        conversation = Conversation.objects.create()
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hello"
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Hi there!"
        )
        
        response = self.client.get(f'/api/v1/conversations/{conversation.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_archive_conversation(self):
        """Test archiving a conversation."""
        conversation = Conversation.objects.create()
        
        response = self.client.post(f'/api/v1/conversations/{conversation.id}/archive/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, Conversation.Status.ARCHIVED)
    
    def test_delete_conversation(self):
        """Test deleting a conversation."""
        conversation = Conversation.objects.create()
        
        response = self.client.delete(f'/api/v1/conversations/{conversation.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, Conversation.Status.DELETED)


class FeedbackAPITest(TestCase):
    """Tests for Feedback API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.conversation = Conversation.objects.create()
        self.message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="AI response"
        )
    
    def test_submit_feedback(self):
        """Test submitting message feedback."""
        response = self.client.post('/api/v1/feedback/', {
            'message': str(self.message.id),
            'feedback_type': 'thumbs_up',
            'rating': 5,
            'comment': 'Great response!'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
