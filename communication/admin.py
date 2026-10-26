from django.contrib import admin
from .models import ChatConversation, ChatMessage, Notification


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'conversation_type',
        'escalated', 'assigned_agent', 'is_active', 'updated_at',
    )
    list_filter = ('conversation_type', 'escalated', 'is_active')
    search_fields = ('user__username', 'subject')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender_type', 'created_at')
    list_filter = ('sender_type',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')