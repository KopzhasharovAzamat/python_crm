# inventory/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products_list, name='products_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('feedback/', views.feedback, name='feedback'),
    path('order/<int:product_id>/', views.order_product, name='order_product'),
]