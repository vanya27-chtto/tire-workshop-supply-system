from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from procurement.models import PurchaseRequest, Product, PurchaseOrder, WorkshopStock, OrderItem, RequestItem
from core.models import WorkshopWarehouse, Supplier


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
    
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def suppliers(request):
    """Страница поставщиков - управление поставщиками"""
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id')
        
        try:
            if supplier_id:
                # Редактирование существующего поставщика
                supplier = get_object_or_404(Supplier, id=supplier_id)
                supplier.name = request.POST.get('name', '')
                supplier.contact_person = request.POST.get('contact_person', '')
                supplier.phone = request.POST.get('phone', '')
                supplier.email = request.POST.get('email', '')
                supplier.address = request.POST.get('address', '')
                supplier.is_active = request.POST.get('is_active') == 'true'
                supplier.save()
                messages.success(request, f'Поставщик "{supplier.name}" успешно обновлён!')
            else:
                # Добавление нового поставщика
                supplier = Supplier.objects.create(
                    name=request.POST.get('name', ''),
                    contact_person=request.POST.get('contact_person', ''),
                    phone=request.POST.get('phone', ''),
                    email=request.POST.get('email', ''),
                    address=request.POST.get('address', ''),
                    is_active=request.POST.get('is_active') == 'true'
                )
                messages.success(request, f'Поставщик "{supplier.name}" успешно добавлен!')
            
            return redirect('suppliers')
            
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    suppliers_list = Supplier.objects.all().order_by('name')
    
    context = {
        'suppliers': suppliers_list,
        'user': request.user,
    }
    
    return render(request, 'procurement/suppliers.html', context)


@login_required
def warehouse(request):
    """Страница склада - управление товарными запасами"""
    products = Product.objects.all().select_related('category')
    workshop_stocks = WorkshopStock.objects.all().select_related('product', 'updated_by')
    workshop_warehouses = WorkshopWarehouse.objects.all().select_related('product', 'responsible_person')
    
    context = {
        'products': products,
        'workshop_stocks': workshop_stocks,
        'workshop_warehouses': workshop_warehouses,
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
def requests_view(request):
    """Страница заявок от сотрудников цеха"""
    requests_list = PurchaseRequest.objects.all().select_related('requester').order_by('-created_at')
    
    context = {
        'requests': requests_list,
        'user': request.user,
    }
    
    return render(request, 'procurement/requests.html', context)


@login_required
def create_request(request):
    """Создание новой заявки от сотрудника цеха"""
    if request.method == 'POST':
        items_description = request.POST.get('items_description', '')
        product_ids = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        notes_list = request.POST.getlist('notes[]')
        
        try:
            # Создаем заявку
            purchase_request = PurchaseRequest.objects.create(
                requester=request.user,
                items_description=items_description
            )
            
            # Добавляем позиции заявки
            for i, product_id in enumerate(product_ids):
                if product_id and quantities[i]:
                    product = get_object_or_404(Product, id=product_id)
                    quantity = int(quantities[i])
                    notes = notes_list[i] if i < len(notes_list) else ''
                    
                    PurchaseRequestItem.objects.create(
                        request=purchase_request,
                        product=product,
                        quantity_requested=quantity,
                        notes=notes
                    )
            
            messages.success(request, f'Заявка {purchase_request.request_number} создана!')
            return redirect('requests')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявки: {str(e)}')
    
    products_list = Product.objects.all().order_by('name')
    
    context = {
        'products': products_list,
        'user': request.user,
    }
    
    return render(request, 'procurement/create_request.html', context)


@login_required
def orders(request):
    """Страница заказов поставщикам"""
    orders_list = PurchaseOrder.objects.all().select_related('supplier', 'created_by').order_by('-created_at')
    suppliers_list = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'orders': orders_list,
        'suppliers': suppliers_list,
        'user': request.user,
    }
    
    return render(request, 'procurement/orders.html', context)


@login_required
def create_order(request):
    """Создание нового заказа поставщику"""
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        product_ids = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        prices = request.POST.getlist('prices[]')
        notes = request.POST.get('notes', '')
        send_email = request.POST.get('send_email') == 'on'
        
        try:
            supplier = get_object_or_404(Supplier, id=supplier_id)
            
            # Определяем начальный статус заказа
            # Если выбрана отправка по email и у поставщика есть email - статус 'sent', иначе 'draft'
            initial_status = PurchaseOrder.Status.SENT if (send_email and supplier.email) else PurchaseOrder.Status.DRAFT
            
            # Создаем заказ
            order = PurchaseOrder.objects.create(
                supplier=supplier,
                status=initial_status,
                notes=notes,
                created_by=request.user
            )
            
            # Если заказ сразу отправлен, устанавливаем дату отправки
            if initial_status == PurchaseOrder.Status.SENT:
                from django.utils import timezone
                order.sent_at = timezone.now()
                order.save()
            
            # Добавляем позиции заказа
            total = 0
            order_items_data = []
            for i, product_id in enumerate(product_ids):
                if product_id and quantities[i]:
                    product = get_object_or_404(Product, id=product_id)
                    quantity = int(quantities[i])
                    price = float(prices[i]) if prices[i] else product.price
                    
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity_ordered=quantity,
                        unit_price=price,
                        subtotal=quantity * price
                    )
                    order_items_data.append({
                        'product': product.name,
                        'quantity': quantity,
                        'unit_price': price,
                        'subtotal': quantity * price
                    })
                    total += quantity * price
            
            # Обновляем общую сумму
            order.total_amount = total
            order.save()
            
            # Отправляем email поставщику (если не был отправлен автоматически при создании)
            if send_email and supplier.email and initial_status != PurchaseOrder.Status.SENT:
                send_order_email(order, order_items_data, total)
                messages.success(request, f'Заказ {order.order_number} создан и отправлен поставщику {supplier.name}!')
            elif initial_status == PurchaseOrder.Status.SENT:
                send_order_email(order, order_items_data, total)
                messages.success(request, f'Заказ {order.order_number} создан и отправлен поставщику {supplier.name}!')
            else:
                messages.success(request, f'Заказ {order.order_number} создан!')
            
            return redirect('orders')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заказа: {str(e)}')
    
    suppliers_list = Supplier.objects.filter(is_active=True).order_by('name')
    products_list = Product.objects.all().order_by('name')
    
    context = {
        'suppliers': suppliers_list,
        'products': products_list,
        'user': request.user,
    }
    
    return render(request, 'procurement/create_order.html', context)


@login_required
def send_order(request, order_id):
    """Отправка заказа поставщику по email"""
    order = get_object_or_404(PurchaseOrder, id=order_id)
    
    if not order.supplier.email:
        messages.error(request, 'У поставщика не указан email!')
        return redirect('orders')
    
    # Получаем позиции заказа
    order_items_data = []
    for item in order.items.all():
        order_items_data.append({
            'product': item.product.name,
            'quantity': item.quantity_ordered,
            'unit_price': float(item.unit_price),
            'subtotal': float(item.subtotal)
        })
    
    if send_order_email(order, order_items_data, float(order.total_amount)):
        order.status = PurchaseOrder.Status.SENT
        from django.utils import timezone
        order.sent_at = timezone.now()
        order.save()
        messages.success(request, f'Заказ {order.order_number} отправлен поставщику {order.supplier.name}!')
    else:
        messages.error(request, 'Ошибка при отправке email. Проверьте настройки SMTP.')
    
    return redirect('orders')


def send_order_email(order, items, total):
    """Отправка email с заказом поставщику"""
    if not order.supplier.email:
        return False
    
    subject = f'Заказ {order.order_number} от {order.created_at.strftime("%d.%m.%Y")}'
    
    # Формируем HTML тело письма
    html_message = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .total {{ font-weight: bold; font-size: 1.2em; }}
        </style>
    </head>
    <body>
        <h2>Новый заказ {order.order_number}</h2>
        <p><strong>Дата:</strong> {order.created_at.strftime("%d.%m.%Y %H:%M")}</p>
        <p><strong>Поставщик:</strong> {order.supplier.name}</p>
        {f'<p><strong>Контактное лицо:</strong> {order.supplier.contact_person}</p>' if order.supplier.contact_person else ''}
        
        <h3>Позиции заказа:</h3>
        <table>
            <thead>
                <tr>
                    <th>№</th>
                    <th>Товар</th>
                    <th>Количество</th>
                    <th>Цена за ед.</th>
                    <th>Сумма</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, item in enumerate(items, 1):
        html_message += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item['product']}</td>
                    <td>{item['quantity']}</td>
                    <td>{item['unit_price']:.2f} руб.</td>
                    <td>{item['subtotal']:.2f} руб.</td>
                </tr>
        """
    
    html_message += f"""
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="4" style="text-align: right;"><strong>Итого:</strong></td>
                    <td class="total">{total:.2f} руб.</td>
                </tr>
            </tfoot>
        </table>
        
        <h3>Дополнительная информация:</h3>
        <p>{order.notes if order.notes else 'Нет дополнительных примечаний.'}</p>
        
        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            Это письмо было отправлено автоматически системой управления снабжением.<br>
            Пожалуйста, подтвердите получение и сроки выполнения заказа.
        </p>
    </body>
    </html>
    """
    
    # Текстовая версия для клиентов без HTML
    text_message = f"""
Заказ {order.order_number} от {order.created_at.strftime("%d.%m.%Y")}

Поставщик: {order.supplier.name}
{f'Контактное лицо: {order.supplier.contact_person}' if order.supplier.contact_person else ''}

Позиции заказа:
"""
    for i, item in enumerate(items, 1):
        text_message += f"{i}. {item['product']} - {item['quantity']} шт. x {item['unit_price']:.2f} руб. = {item['subtotal']:.2f} руб.\n"
    
    text_message += f"\nИтого: {total:.2f} руб.\n\n"
    text_message += f"Примечание: {order.notes if order.notes else 'Нет дополнительных примечаний.'}\n\n"
    text_message += "Это письмо было отправлено автоматически системой управления снабжением.\n"
    text_message += "Пожалуйста, подтвердите получение и сроки выполнения заказа."
    
    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.supplier.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


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


@login_required
def replenish_workshop_warehouse(request, warehouse_id):
    """Пополнение запаса склада цеха со основного склада"""
    if request.method == 'POST':
        try:
            from core.models import WorkshopWarehouse
            warehouse = WorkshopWarehouse.objects.get(id=warehouse_id)
            quantity_to_add = int(request.POST.get('quantity_to_add', 0))
            
            if quantity_to_add > 0:
                # Проверяем, достаточно ли товара на основном складе
                product = warehouse.product
                if product.current_stock >= quantity_to_add:
                    # Списываем с основного склада
                    product.current_stock -= quantity_to_add
                    product.save()
                    
                    # Добавляем в склад цеха
                    warehouse.quantity += quantity_to_add
                    warehouse.responsible_person = request.user
                    warehouse.save()
                    
                    messages.success(
                        request,
                        f'Склад цеха пополнен: "{product.name}" добавлено {quantity_to_add} {product.unit}'
                    )
                else:
                    messages.error(
                        request,
                        f'Недостаточно товара на складе. Доступно: {product.current_stock} {product.unit}'
                    )
            else:
                messages.error(request, 'Количество должно быть больше нуля')
        except WorkshopWarehouse.DoesNotExist:
            messages.error(request, 'Запись склада не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')


@login_required
def replenish_product(request, product_id):
    """Пополнение товара на складе (добавление нового товара)"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            quantity_to_add = int(request.POST.get('quantity_to_add', 0))
            
            if quantity_to_add > 0:
                product.current_stock += quantity_to_add
                product.save()
                
                messages.success(
                    request,
                    f'Товар "{product.name}" пополнен на {quantity_to_add} {product.unit}. Текущий остаток: {product.current_stock}'
                )
            else:
                messages.error(request, 'Количество должно быть больше нуля')
        except Product.DoesNotExist:
            messages.error(request, 'Товар не найден')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')
