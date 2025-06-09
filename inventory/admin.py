# inventory/admin.py
from django.contrib import admin
from .models import Brand, Model, ModelSpecification, ProductType, Product, ProductSpecification, Warehouse, Cart, CartItem, CartComment, Sale, SaleItem, SaleComment, Return, UserSettings, LogEntry

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand']
    list_filter = ['brand']
    search_fields = ['name']

@admin.register(ModelSpecification)
class ModelSpecificationAdmin(admin.ModelAdmin):
    list_display = ['model', 'engine_capacity', 'engine_code', 'horsepower', 'production_start']
    list_filter = ['model__brand']
    search_fields = ['engine_code', 'model__name']

@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ['product', 'specification']
    list_filter = ['specification__model__brand']
    search_fields = ['product__name', 'specification__engine_code']

class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    verbose_name = "Спецификация товара"
    verbose_name_plural = "Спецификации товаров"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_type', 'warehouse', 'quantity', 'selling_price']
    list_filter = ['product_type', 'warehouse']
    search_fields = ['name']
    inlines = [ProductSpecificationInline]

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['number', 'created_at', 'get_items', 'get_total']
    list_filter = ['created_at']
    search_fields = ['number']

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
    search_fields = ['product__name']

@admin.register(CartComment)
class CartCommentAdmin(admin.ModelAdmin):
    list_display = ['cart', 'owner', 'created_at']
    list_filter = ['owner', 'created_at']
    search_fields = ['text']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['number', 'owner', 'date', 'get_items', 'get_total']
    list_filter = ['owner', 'date']
    search_fields = ['number']

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
    search_fields = ['product__name']

@admin.register(SaleComment)
class SaleCommentAdmin(admin.ModelAdmin):
    list_display = ['sale', 'owner', 'created_at']
    list_filter = ['owner', 'created_at']
    search_fields = ['text']

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ['sale', 'sale_item', 'quantity', 'owner', 'returned_at']
    list_filter = ['owner', 'returned_at']
    search_fields = ['sale__number', 'sale_item__product__name']

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['owner', 'hide_cost_price', 'is_pending']
    list_filter = ['owner']
    search_fields = ['owner__username']

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['owner', 'timestamp', 'action_type', 'message']
    list_filter = ['owner', 'action_type']
    search_fields = ['message']