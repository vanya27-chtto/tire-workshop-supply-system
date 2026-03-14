from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import F
from procurement.models import PurchaseRequest, Product, PurchaseOrder


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
    
    # Материалы в цеху (для работников цеха)
    workshop_materials = Product.objects.all()[:10]
    
    context = {
        'notifications': notifications,
        'workshop_materials': workshop_materials,
        'user': request.user,
    }
    
    return render(request, 'dashboard.html', context)

# Create your views here.
