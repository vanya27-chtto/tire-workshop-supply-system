from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Supplier, Product, PurchaseRequest, PurchaseRequestItem, PurchaseOrder, OrderItem, WorkshopStock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'contact_person', 'email']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'sku', 'quantity', 'min_quantity', 'price', 'supplier', 'needs_reorder_indicator']
    list_filter = ['category', 'supplier']
    search_fields = ['name', 'sku']
    
    def needs_reorder_indicator(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color: red;">⚠️ Требуется заказ</span>')
        return format_html('<span style="color: green;">✓ В норме</span>')
    needs_reorder_indicator.short_description = 'Статус запаса'


@admin.register(WorkshopStock)
class WorkshopStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'location', 'responsible_person', 'min_quantity', 'status', 'last_updated', 'needs_replenishment_indicator']
    list_filter = ['status', 'location']
    search_fields = ['product__name', 'product__sku']
    readonly_fields = ['last_updated', 'status']
    
    def needs_replenishment_indicator(self, obj):
        if obj.needs_replenishment:
            return format_html('<span style="color: red;">⚠️ Требуется пополнение</span>')
        return format_html('<span style="color: green;">✓ В норме</span>')
    needs_replenishment_indicator.short_description = 'Статус запаса'


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'requester', 'created_at']
    search_fields = ['request_number', 'requester__username']
    readonly_fields = ['request_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('request_number', 'requester')
        }),
        ('Описание товаров', {
            'fields': ('items_description',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseRequestItem)
class PurchaseRequestItemAdmin(admin.ModelAdmin):
    list_display = ['request', 'product', 'quantity_requested', 'quantity_approved']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'status', 'total_amount', 'created_at', 'created_by']
    list_filter = ['status', 'supplier', 'created_at']
    search_fields = ['order_number', 'supplier__name']
    readonly_fields = ['order_number', 'total_amount', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'supplier', 'status', 'request')
        }),
        ('Сумма', {
            'fields': ('total_amount',)
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_by')
        }),
        ('Даты', {
            'fields': ('created_at', 'sent_at', 'received_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity_ordered', 'quantity_received', 'unit_price', 'subtotal']
    list_filter = ['order__status']
