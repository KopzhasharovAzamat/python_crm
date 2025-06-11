# inventory/admin.py

from django.contrib import admin
from .models import RoomType, FurnitureType, Product, ProductImage, Feedback, Review

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(FurnitureType)
class FurnitureTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'furniture_type', 'price', 'rating', 'views']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']
    list_filter = ['created_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'review']