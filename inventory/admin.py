# inventory/admin.py

from django.contrib import admin
from .models import (
    Category, Style, Design, DesignImage,
    PortfolioItem, ConsultationRequest, Tariff,
    Order, Review
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ('name',)

class DesignImageInline(admin.TabularInline):
    model = DesignImage
    extra = 1

@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'style', 'area', 'created_at')
    inlines = [DesignImageInline]

@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('design', 'show_on_main')

@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created_at')

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('client', 'category', 'style', 'area', 'tariff', 'status', 'created_at')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'city', 'created_at')
