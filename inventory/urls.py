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
    path('faq/', views.faq, name='faq'),
    path('idea/', views.designers, name='designers'),
    path('portfolio/category/<int:category_id>/', views.portfolio_by_category, name='portfolio_by_category'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
]
