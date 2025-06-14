# inventory/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/<int:pk>/', views.portfolio_detail, name='portfolio_detail'),
    path('services/', views.services, name='services'),
    path('consultation/', views.consultation, name='consultation'),
    path('order/', views.order, name='order'),
    path('reviews/', views.reviews, name='reviews'),
    path('add_review/<int:design_id>/', views.add_review, name='add_review'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
]
