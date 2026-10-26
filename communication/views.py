from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from .assistant import WELCOME, match_link, nova_reply, update_extracted
from .models import ChatConversation, ChatMessage, Notification
from .notify import notify, notify_admins

MAX_LENGTH = 500


def get_conversation(user):
    """The customer's open chat (a new one is started if there is none)."""
    conversation = ChatConversation.objects.filter(user=user, is_active=True).first()
    if conversation is None:
        conversation = ChatConversation.objects.create(user=user)
        ChatMessage.objects.create(
            conversation=conversation, sender_type=ChatMessage.SenderType.AI, message=WELCOME)
    return conversation


def prepare_messages(conversation, agent_view):
    """Add the colour class and the name label that the template needs."""
    rows = []
    for m in conversation.messages.select_related('sender'):
        if m.sender_type == ChatMessage.SenderType.USER:
            css = 'ai' if agent_view else 'me'
            who = conversation.user.username if agent_view else 'You'
        elif m.sender_type == ChatMessage.SenderType.AGENT:
            css = 'me' if agent_view else 'agent'
            who = 'You (agent)' if agent_view else 'Support agent'
        else:
            css = 'agent' if agent_view else 'ai'
            who = 'Nova · AI'
        rows.append({'text': m.message, 'css': css, 'who': who, 'time': m.created_at})
    return rows


# ------------------------------------------------------------ customer side
@login_required
def chat(request):
    conversation = get_conversation(request.user)
    return render(request, 'communication/chat.html', {
        'conversation': conversation,
        'chat_messages': prepare_messages(conversation, agent_view=False),
        'known': conversation.extracted_data,
        'match_link': match_link(conversation.extracted_data),
        'agent_view': False,
    })


@login_required
@require_POST
def chat_send(request):
    conversation = get_conversation(request.user)
    text = request.POST.get('message', '').strip()[:MAX_LENGTH]
    if not text:
        return redirect('chat')

    ChatMessage.objects.create(
        conversation=conversation, sender_type=ChatMessage.SenderType.USER,
        sender=request.user, message=text)

    if not conversation.subject:
        conversation.subject = text[:80]

    # Nova only answers while no human agent is in the chat
    if not conversation.escalated:
        before = dict(conversation.extracted_data)
        conversation.extracted_data = update_extracted(before, text)
        changed = conversation.extracted_data != before
        ChatMessage.objects.create(
            conversation=conversation, sender_type=ChatMessage.SenderType.AI,
            message=nova_reply(text, conversation.extracted_data, changed))
    conversation.save()
    return redirect('chat')


@login_required
@require_POST
def chat_escalate(request):
    conversation = get_conversation(request.user)
    if not conversation.escalated:
        conversation.escalated = True
        conversation.conversation_type = ChatConversation.ConversationType.LIVE_AGENT
        conversation.save()
        ChatMessage.objects.create(
            conversation=conversation, sender_type=ChatMessage.SenderType.AI,
            message="I have asked our support team to join this chat. Please wait here, an agent will reply soon.")
        notify_admins(Notification.NotificationType.MESSAGE, 'Customer needs support',
                      f'{request.user.username} asked for a live agent.', '/communication/inbox/')
    return redirect('chat')


@login_required
@require_POST
def chat_new(request):
    ChatConversation.objects.filter(user=request.user, is_active=True).update(is_active=False)
    return redirect('chat')


# ------------------------------------------------------------ agent (admin) side
@role_required(User.Role.ADMIN)
def agent_inbox(request):
    chats = ChatConversation.objects.filter(
        escalated=True, is_active=True).select_related('user', 'assigned_agent')
    return render(request, 'communication/agent_inbox.html', {'chats': chats})


@role_required(User.Role.ADMIN)
def agent_chat(request, pk):
    conversation = get_object_or_404(ChatConversation, pk=pk, escalated=True)
    return render(request, 'communication/chat.html', {
        'conversation': conversation,
        'chat_messages': prepare_messages(conversation, agent_view=True),
        'known': conversation.extracted_data,
        'agent_view': True,
    })


@role_required(User.Role.ADMIN)
@require_POST
def agent_reply(request, pk):
    conversation = get_object_or_404(ChatConversation, pk=pk, escalated=True, is_active=True)
    text = request.POST.get('message', '').strip()[:MAX_LENGTH]
    if text:
        ChatMessage.objects.create(
            conversation=conversation, sender_type=ChatMessage.SenderType.AGENT,
            sender=request.user, message=text)
        if conversation.assigned_agent is None:
            conversation.assigned_agent = request.user
        conversation.save()
        notify(conversation.user, Notification.NotificationType.MESSAGE, 'Support replied',
               'A support agent replied to your chat.', '/communication/')
    return redirect('agent_chat', pk=pk)


@role_required(User.Role.ADMIN)
@require_POST
def agent_close(request, pk):
    conversation = get_object_or_404(ChatConversation, pk=pk, escalated=True)
    conversation.is_active = False
    conversation.save()
    messages.success(request, 'Chat closed.')
    return redirect('agent_inbox')


# ------------------------------------------------------------ notifications
@login_required
def notifications(request):
    items = list(Notification.objects.filter(user=request.user)[:50])
    for item in items:
        item.was_unread = not item.is_read
    # opening the page counts as reading them
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'communication/notifications.html', {'items': items})


@login_required
@require_POST
def notifications_clear(request):
    Notification.objects.filter(user=request.user).delete()
    messages.success(request, 'All notifications cleared.')
    return redirect('notifications')
