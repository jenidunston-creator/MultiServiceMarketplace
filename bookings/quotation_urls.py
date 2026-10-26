from django.urls import path

from . import views

urlpatterns = [
    path('', views.quotation_list, name='quotation_list'),
    path('request/<int:listing_pk>/', views.quote_request, name='quote_request'),
    path('<int:request_pk>/send/', views.quotation_send, name='quotation_send'),
    path('<int:pk>/accept/', views.quotation_accept, name='quotation_accept'),
    path('<int:pk>/decline/', views.quotation_decline, name='quotation_decline'),
]
