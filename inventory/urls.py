from django.urls import path
from . import views

urlpatterns = [
    # Login / Logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Register
    path('register/', views.register, name='register'),

    # Profile
    path('profile/', views.profile, name='profile'),

    # Product
    path('products/', views.product_list, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),

    # Warehouse
    path('warehouses/', views.warehouse_list, name='warehouses'),
    path('warehouses/add/', views.warehouse_add, name='warehouse_add'),
    path('warehouses/<int:warehouse_id>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouses/<int:warehouse_id>/delete/', views.warehouse_delete, name='warehouse_delete'),

    # Category
    path('categories/', views.category_manage, name='category_manage'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),

    # Subcategory
    path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
    path('subcategories/<int:subcategory_id>/edit/', views.subcategory_edit, name='subcategory_edit'),
    path('subcategories/delete/<int:subcategory_id>/', views.subcategory_delete, name='subcategory_delete'),

    # Sale
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:sale_id>/detail/', views.sale_detail, name='sale_detail'),
    path('sales/<int:product_id>/', views.sale_create, name='sale_create'),

    # Scan
    path('scan/', views.scan_product, name='scan_product'),

    # Statistics
    path('stats/', views.stats, name='stats'),

    # Admin panel
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-logs/', views.admin_logs, name='admin_logs'),
]