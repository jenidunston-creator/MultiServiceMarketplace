from django.urls import path

from . import views

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('new/', views.booking_create, name='booking_create'),
    path('<int:pk>/pay/', views.booking_pay, name='booking_pay'),
    path('<int:pk>/status/', views.booking_status, name='booking_status'),
    path('<int:pk>/review/', views.booking_review, name='booking_review'),
]
