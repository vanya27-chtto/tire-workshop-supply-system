from django.contrib import admin
from .models import WorkshopStock, Category, Supplier, Product, PurchaseRequest, RequestItem, PurchaseOrder, OrderItem


@admin.register(WorkshopStock)
class WorkshopStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'min_quantity', 'status', 'location', 'updated_at', 'updated_by')
    list_filter = ('status', 'location')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('updated_at', 'updated_by', 'status')
    
    def save_model(self, request, obj, form, change):
        # Автоматически устанавливаем пользователя, который обновил запись
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'contact_person', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'email', 'phone')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'unit', 'current_stock', 'min_stock_level', 'supplier', 'price')
    list_filter = ('category', 'supplier')
    search_fields = ('name', 'sku')


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'requester', 'requester_role', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'requester_role')
    search_fields = ('request_number', 'requester__username')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'supplier', 'status', 'total_amount', 'created_at', 'created_by')
    list_filter = ('status', 'supplier')
    search_fields = ('order_number', 'supplier__name')
