from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from procurement.models import Product, PurchaseRequest, PurchaseOrder, Supplier
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
            status='pending_approval'
        ).select_related('requester')
        
        # Уведомления о низком запасе на складе
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=F('min_stock_level'),
            is_active=True
        ).order_by('stock_quantity')
        
        # Статистика по заказам
        total_orders = PurchaseOrder.objects.count()
        pending_orders = PurchaseOrder.objects.filter(status='draft').count()
        sent_orders = PurchaseOrder.objects.filter(status='sent').count()
        
        # Недавние заявки
        recent_requests = PurchaseRequest.objects.all().order_by('-created_at')[:5]
        
        context.update({
            'pending_requests': pending_requests,
            'low_stock_products': low_stock_products,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'sent_orders': sent_orders,
            'recent_requests': recent_requests,
        })
    
    # Данные для сотрудника цеха
    if is_workshop or is_admin:
        # Материалы в цеху (товары с остатками)
        workshop_materials = Product.objects.filter(
            is_active=True
        ).order_by('category', 'name')[:20]  # Показываем первые 20
        
        # Общая стоимость материалов в цеху
        total_workshop_value = workshop_materials.aggregate(
            total=Sum('stock_quantity')
        )['total'] or 0
        
        context.update({
            'workshop_materials': workshop_materials,
            'total_workshop_value': total_workshop_value,
        })
    
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def use_material(request):
    """Обработка использования материала сотрудником цеха"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 0))
        
        try:
            product = Product.objects.get(id=product_id)
            
            if quantity <= 0:
                messages.error(request, 'Количество должно быть больше 0')
            elif quantity > product.stock_quantity:
                messages.error(request, f'Недостаточно материала на складе. Доступно: {product.stock_quantity}')
            else:
                # Списываем материал со склада
                product.stock_quantity -= quantity
                product.save()
                
                messages.success(
                    request, 
                    f'Материал "{product.name}" использован в количестве {quantity} {product.unit}'
                )
        except Product.DoesNotExist:
            messages.error(request, 'Товар не найден')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('dashboard')
