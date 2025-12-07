"""
Tests for chat models.
"""
import pytest
from django.test import TestCase
from apps.chat.models import Conversation, Message, MessageFeedback


class ConversationModelTest(TestCase):
    """Tests for Conversation model."""
    
    def test_create_conversation(self):
        """Test creating a conversation."""
        conversation = Conversation.objects.create()
        self.assertIsNotNone(conversation.id)
        self.assertEqual(conversation.status, Conversation.Status.ACTIVE)
        self.assertEqual(conversation.message_count, 0)
    
    def test_conversation_with_title(self):
        """Test conversation with title."""
        conversation = Conversation.objects.create(title="Test Chat")
        self.assertEqual(conversation.title, "Test Chat")
    
    def test_generate_title_from_first_message(self):
        """Test title generation from first user message."""
        conversation = Conversation.objects.create()
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hello, this is my first message to the chatbot"
        )
        conversation.generate_title()
        self.assertIn("Hello", conversation.title)


class MessageModelTest(TestCase):
    """Tests for Message model."""
    
    def setUp(self):
        self.conversation = Conversation.objects.create()
    
    def test_create_message(self):
        """Test creating a message."""
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Hello"
        )
        self.assertIsNotNone(message.id)
        self.assertEqual(message.sequence_number, 1)
    
    def test_message_sequence_auto_increment(self):
        """Test message sequence number auto-increment."""
        msg1 = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="First message"
        )
        msg2 = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Second message"
        )
        self.assertEqual(msg1.sequence_number, 1)
        self.assertEqual(msg2.sequence_number, 2)
    
    def test_message_status(self):
        """Test message status."""
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Hello",
            status=Message.Status.COMPLETED
        )
        self.assertEqual(message.status, Message.Status.COMPLETED)


class MessageFeedbackModelTest(TestCase):
    """Tests for MessageFeedback model."""
    
    def setUp(self):
        self.conversation = Conversation.objects.create()
        self.message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="AI response"
        )
    
    def test_create_feedback(self):
        """Test creating message feedback."""
        feedback = MessageFeedback.objects.create(
            message=self.message,
            feedback_type=MessageFeedback.FeedbackType.THUMBS_UP,
            rating=5
        )
        self.assertIsNotNone(feedback.id)
        self.assertEqual(feedback.rating, 5)
