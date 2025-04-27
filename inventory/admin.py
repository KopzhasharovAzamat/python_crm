# inventory/admin.py
from django.contrib import admin
from .models import Category, Subcategory, Product, Warehouse, Sale, SaleItem, Cart, CartItem, UserSettings

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner']
    list_filter = []

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'quantity', 'warehouse', 'category', 'subcategory']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'owner', 'get_items', 'get_total']
    list_filter = ['date', 'owner']

    def get_items(self, obj):
        items = obj.items.all()
        return ", ".join([f"{item.product.name} ({item.quantity} шт.)" for item in items])
    get_items.short_description = 'Товары'

    def get_total(self, obj):
        base_total, actual_total = obj.calculate_totals()
        return f"{actual_total} ₽"
    get_total.short_description = 'Итого'

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product', 'quantity', 'base_price_total', 'actual_price_total']
    list_filter = ['sale', 'product']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'created_at', 'get_items', 'get_total']
    list_filter = ['created_at', 'owner']

    def get_items(self, obj):
        items = obj.items.all()
        return ", ".join([f"{item.product.name} ({item.quantity} шт.)" for item in items])
    get_items.short_description = 'Товары'

    def get_total(self, obj):
        base_total, actual_total = obj.calculate_totals()
        return f"{actual_total} ₽"
    get_total.short_description = 'Итого'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'base_price_total', 'actual_price_total']
    list_filter = ['cart', 'product']

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'hide_cost_price']