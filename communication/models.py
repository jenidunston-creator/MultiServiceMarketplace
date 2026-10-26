from django.db import models
from django.conf import settings


class ChatConversation(models.Model):

    class ConversationType(models.TextChoices):
        AI = 'AI', 'AI Assistant'
        LIVE_AGENT = 'LIVE_AGENT', 'Live Agent'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_conversations'
    )
    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
        default=ConversationType.AI
    )
    subject = models.CharField(
        max_length=200,
        blank=True
    )
    escalated = models.BooleanField(default=False)
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_conversations'
    )
    extracted_data = models.JSONField(
        default=dict,
        blank=True
    )
    service_request = models.ForeignKey(
        'services.ServiceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_conversations'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.conversation_type}"


class ChatMessage(models.Model):

    class SenderType(models.TextChoices):
        USER = 'USER', 'User'
        AI = 'AI', 'AI Assistant'
        AGENT = 'AGENT', 'Live Agent'

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender_type = models.CharField(
        max_length=10,
        choices=SenderType.choices
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_chat_messages'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message #{self.id} - {self.sender_type}"


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        SERVICE_REQUEST = 'SERVICE_REQUEST', 'Service Request'
        QUOTATION = 'QUOTATION', 'Quotation'
        BOOKING = 'BOOKING', 'Booking'
        PAYMENT = 'PAYMENT', 'Payment'
        REVIEW = 'REVIEW', 'Review'
        MESSAGE = 'MESSAGE', 'Message'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"