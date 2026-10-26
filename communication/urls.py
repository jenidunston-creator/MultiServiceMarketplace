from django.urls import path

from . import views

urlpatterns = [
    path('', views.chat, name='chat'),
    path('send/', views.chat_send, name='chat_send'),
    path('escalate/', views.chat_escalate, name='chat_escalate'),
    path('new/', views.chat_new, name='chat_new'),

    path('notifications/', views.notifications, name='notifications'),
    path('notifications/clear/', views.notifications_clear, name='notifications_clear'),

    # for the support agent (admin)
    path('inbox/', views.agent_inbox, name='agent_inbox'),
    path('inbox/<int:pk>/', views.agent_chat, name='agent_chat'),
    path('inbox/<int:pk>/reply/', views.agent_reply, name='agent_reply'),
    path('inbox/<int:pk>/close/', views.agent_close, name='agent_close'),
]
