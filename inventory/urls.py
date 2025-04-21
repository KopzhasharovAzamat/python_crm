# inventory/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('products/', views.product_list, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('warehouses/', views.warehouse_list, name='warehouses'),
    path('warehouses/add/', views.warehouse_add, name='warehouse_add'),
    path('sales/<int:product_id>/', views.sale_create, name='sale_create'),
    path('scan/', views.scan_product, name='scan_product'),
    path('stats/', views.stats, name='stats'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('categories/', views.category_manage, name='category_manage'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    path('subcategories/delete/<int:subcategory_id>/', views.subcategory_delete, name='subcategory_delete'),
]