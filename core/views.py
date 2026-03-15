from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from procurement.models import PurchaseRequest, Product, PurchaseOrder, WorkshopStock


@login_required
def dashboard(request):
    """Главная страница после авторизации"""
    
    # Уведомления для товароведа
    notifications = []
    
    # Уведомления о запросах от работников цеха
    pending_requests = PurchaseRequest.objects.filter(
        requester__isnull=False
    ).order_by('-created_at')[:5]
    
    for req in pending_requests:
        notifications.append({
            'type': 'request',
            'title': f'Новая заявка {req.request_number}',
            'description': f'Заявка от {req.requester.username if req.requester else "Неизвестно"}',
            'date': req.created_at,
            'icon': '📋',
            'priority': 'normal'
        })
    
    # Уведомления о низком запасе на складе
    low_stock_products = Product.objects.filter(current_stock__lte=F('min_stock_level'))
    for product in low_stock_products:
        notifications.append({
            'type': 'low_stock',
            'title': f'Низкий запас: {product.name}',
            'description': f'Осталось: {product.current_stock} {product.unit} (минимум: {product.min_stock_level})',
            'date': product.updated_at,
            'icon': '⚠️',
            'priority': 'high'
        })
    
    # Материалы в цеху (для работников цеха) - данные из модели WorkshopStock
    workshop_materials = WorkshopStock.objects.all().select_related('product')[:10]
    
    context = {
        'notifications': notifications,
        'workshop_materials': workshop_materials,
        'user': request.user,
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def warehouse(request):
    """Страница склада - управление товарными запасами"""
    products = Product.objects.all().select_related('category')
    
    context = {
        'products': products,
        'user': request.user,
    }
    
    return render(request, 'procurement/warehouse.html', context)


@login_required
def update_product_stock(request, product_id):
    """Обновление остатков товара товароведом"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            current_stock = int(request.POST.get('current_stock', 0))
            min_stock_level = int(request.POST.get('min_stock_level', 0))
            
            # Обновляем значения
            product.current_stock = current_stock
            product.min_stock_level = min_stock_level
            product.save()
            
            messages.success(
                request, 
                f'Запасы товара "{product.name}" обновлены: текущий={current_stock}, минимальный={min_stock_level}'
            )
        except Product.DoesNotExist:
            messages.error(request, 'Товар не найден')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')


@login_required
def workshop_stock(request):
    """Страница запасов цеха"""
    workshop_stocks = WorkshopStock.objects.all().select_related('product', 'updated_by')
    
    context = {
        'workshop_stocks': workshop_stocks,
        'user': request.user,
    }
    
    return render(request, 'procurement/workshop_stock.html', context)


@login_required
def update_workshop_stock(request, stock_id):
    """Обновление запасов цеха товароведом"""
    if request.method == 'POST':
        try:
            workshop_stock = WorkshopStock.objects.get(id=stock_id)
            quantity = int(request.POST.get('quantity', 0))
            min_quantity = int(request.POST.get('min_quantity', 0))
            location = request.POST.get('location', '')
            
            # Обновляем значения
            workshop_stock.quantity = quantity
            workshop_stock.min_quantity = min_quantity
            workshop_stock.location = location
            workshop_stock.updated_by = request.user
            # Статус обновится автоматически в методе save() модели
            workshop_stock.save()
            
            messages.success(
                request, 
                f'Запасы "{workshop_stock.product.name}" в цеху обновлены: количество={quantity}, мин. запас={min_quantity}'
            )
        except WorkshopStock.DoesNotExist:
            messages.error(request, 'Запись о запасах не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('workshop_stock')
