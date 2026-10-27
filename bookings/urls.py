from django.urls import path

from . import views

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('payments/', views.payment_approvals, name='payment_approvals'),
    path('payments/<int:pk>/decide/', views.payment_decide, name='payment_decide'),
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/<int:pk>/respond/', views.complaint_respond, name='complaint_respond'),
    path('new/', views.booking_create, name='booking_create'),
    path('<int:pk>/pay/', views.booking_pay, name='booking_pay'),
    path('<int:pk>/status/', views.booking_status, name='booking_status'),
    path('<int:pk>/review/', views.booking_review, name='booking_review'),
    path('<int:pk>/complaint/', views.complaint_create, name='complaint_create'),
]
