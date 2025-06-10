# inventory/urls.py
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
    path('products/<int:product_id>/detail/', views.product_detail, name='product_detail'),
    path('get-product-price/', views.get_product_price, name='get_product_price'),
    path('get_product_price/', views.get_product_price, name='get_product_price_alt'),  # Альтернативный маршрут
    path('get-product-by-uuid/', views.get_product_by_uuid, name='get_product_by_uuid'),
    path('get_product_by_uuid/', views.get_product_by_uuid, name='get_product_by_uuid_alt'),  # Альтернативный маршрут
    path('get-product-by-id/', views.get_product_by_id, name='get_product_by_id'),

    # Archive
    path('products/<int:product_id>/archive/', views.product_archive, name='product_archive'),
    path('products/<int:product_id>/unarchive/', views.product_unarchive, name='product_unarchive'),
    path('products/archived/', views.archived_products, name='archived_products'),

    # Warehouse
    path('warehouses/', views.warehouse_list, name='warehouses'),
    path('warehouses/add/', views.warehouse_add, name='warehouse_add'),
    path('warehouses/<int:warehouse_id>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouses/<int:warehouse_id>/delete/', views.warehouse_delete, name='warehouse_delete'),

    # Brand Management
    path('brands/', views.brand_manage, name='brands'),
    path('brands/<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/delete/<int:brand_id>/', views.brand_delete, name='brand_delete'),

    # Model Management
    path('models/', views.model_manage, name='models'),
    path('models/<int:model_id>/edit/', views.model_edit, name='model_edit'),
    path('models/delete/<int:model_id>/', views.model_delete, name='model_delete'),

    # Specification Management
    path('specifications/', views.specification_manage, name='specifications'),
    path('specifications/<int:specification_id>/edit/', views.specification_edit, name='specification_edit'),
    path('specifications/delete/<int:specification_id>/', views.specification_delete, name='specification_delete'),

    # ProductType
    path('product-types/', views.product_types, name='product_types'),
    path('product-types/<int:product_type_id>/edit/', views.product_type_edit, name='product_type_edit'),
    path('product-types/delete/<int:product_type_id>/', views.product_type_delete, name='product_type_delete'),

    # Sale
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:sale_id>/detail/', views.sale_detail, name='sale_detail'),
    path('sales/<int:sale_id>/edit/', views.sale_edit, name='sale_edit'),
    path('sales/<int:sale_id>/return/<int:item_id>/', views.return_item, name='return_item'),
    path('sales/<int:sale_id>/comment/add/', views.sale_comment_add, name='sale_comment_add'),
    path('sales/<int:sale_id>/comment/<int:comment_id>/edit/', views.sale_comment_edit, name='sale_comment_edit'),
    path('sales/<int:sale_id>/comment/<int:comment_id>/delete/', views.sale_comment_delete, name='sale_comment_delete'),

    # Cart
    path('carts/', views.cart_list, name='cart_list'),
    path('cart/create/', views.cart_create, name='cart_create'),
    path('cart/<int:cart_id>/add_item/', views.cart_add_item, name='cart_add_item'),
    path('cart/<int:cart_id>/add/', views.cart_add_item, name='cart_add_item_alt'),  # Альтернативный маршрут
    path('cart/<int:cart_id>/remove_item/<int:item_id>/', views.cart_remove_item, name='cart_remove_item'),
    path('cart/<int:cart_id>/confirm/', views.cart_confirm, name='cart_confirm'),
    path('cart/<int:cart_id>/cancel/', views.cart_cancel, name='cart_cancel'),
    path('cart/<int:cart_id>/delete/', views.cart_delete, name='cart_delete'),
    path('cart/<int:cart_id>/comment/add/', views.cart_comment_add, name='cart_comment_add'),
    path('cart/<int:cart_id>/comment/<int:comment_id>/edit/', views.cart_comment_edit, name='cart_comment_edit'),
    path('cart/<int:cart_id>/comment/<int:comment_id>/delete/', views.cart_comment_delete, name='cart_comment_delete'),

    # Scan
    path('scan/', views.scan_product, name='scan_product'),
    path('scan-product/', views.scan_product, name='scan_product'),
    path('scan-product-confirm/', views.scan_product_confirm, name='scan_product_confirm'),

    # Statistics
    path('stats/', views.stats, name='stats'),

    # Logs
    path('logs/', views.logs, name='logs'),

    # Admin panel
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]