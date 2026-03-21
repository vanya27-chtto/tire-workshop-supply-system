from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Product, PurchaseRequest, PurchaseOrder, Supplier, WorkshopStock, WorkshopWarehouse
from django.db.models import Sum, F
from datetime import datetime


@login_required
def dashboard(request):
    """Главная страница/dashboard с виджетами в зависимости от роли пользователя"""
    
    user = request.user
    user_groups = user.groups.all()
    
    # Определяем роль пользователя
    is_merchandiser = user_groups.filter(name='Товаровед').exists() or user.username == 'merchandiser_user'
    is_workshop = user_groups.filter(name='Сотрудник цеха').exists() or user.username == 'workshop_user'
    is_admin = user.is_superuser
    
    context = {
        'current_time': datetime.now(),
        'is_merchandiser': is_merchandiser,
        'is_workshop': is_workshop,
        'is_admin': is_admin,
    }
    
    # Данные для товароведа
    if is_merchandiser or is_admin:
        # Уведомления о заявках на согласование
        pending_requests = PurchaseRequest.objects.filter(
            status='pending'
        ).select_related('requester')
        
        # Уведомления о низком запасе на складе (из таблицы Product)
        low_stock_warehouse = Product.objects.filter(
            quantity__lte=F('min_quantity'),
        ).order_by('quantity')[:10]
        
        # Уведомления о низком запасе в цеху (из таблицы WorkshopStock)
        low_stock_workshop = WorkshopStock.objects.filter(
            quantity__lte=F('min_quantity')
        ).select_related('product').order_by('quantity')[:10]
        
        # Статистика по заказам
        total_orders = PurchaseOrder.objects.count()
        pending_orders = PurchaseOrder.objects.filter(status='draft').count()
        sent_orders = PurchaseOrder.objects.filter(status='sent').count()
        
        # Недавние заявки
        recent_requests = PurchaseRequest.objects.all().order_by('-created_at')[:5]
        
        context.update({
            'pending_requests': pending_requests,
            'low_stock_warehouse': low_stock_warehouse,
            'low_stock_workshop': low_stock_workshop,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'sent_orders': sent_orders,
            'recent_requests': recent_requests,
        })
    
    # Данные для сотрудника цеха
    if is_workshop or is_admin:
        # Материалы в цеху (из таблицы WorkshopStock) - показываем все записи
        workshop_materials = WorkshopStock.objects.select_related('product').order_by('product__category', 'product__name')
        
        # Общая стоимость материалов в цеху
        total_workshop_value = workshop_materials.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        # Склад цеха (из таблицы WorkshopWarehouse) - показываем все записи
        workshop_warehouse_items = WorkshopWarehouse.objects.select_related('product').order_by('product__category', 'product__name')
        
        # Общий объем на складе цеха
        total_workshop_warehouse_value = workshop_warehouse_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        context.update({
            'workshop_materials': workshop_materials,
            'total_workshop_value': total_workshop_value,
            'workshop_warehouse_items': workshop_warehouse_items,
            'total_workshop_warehouse_value': total_workshop_warehouse_value,
        })
    
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def use_material(request):
    """Обработка использования материала сотрудником цеха"""
    if request.method == 'POST':
        stock_id = request.POST.get('stock_id')
        quantity = int(request.POST.get('quantity', 0))
        
        try:
            workshop_stock = WorkshopStock.objects.get(id=stock_id)
            
            if quantity <= 0:
                messages.error(request, 'Количество должно быть больше 0')
            elif quantity > workshop_stock.quantity:
                messages.error(request, f'Недостаточно материала в цеху. Доступно: {workshop_stock.quantity}')
            else:
                # Списываем материал из цеха
                workshop_stock.quantity -= quantity
                
                # Статус автоматически обновится при сохранении благодаря методу save() в модели
                
                workshop_stock.save()
                
                messages.success(
                    request, 
                    f'Материал "{workshop_stock.product.name}" использован в количестве {quantity} {workshop_stock.product.unit}'
                )
        except WorkshopStock.DoesNotExist:
            messages.error(request, 'Запись о материале не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('dashboard')
