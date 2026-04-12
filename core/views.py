from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from procurement.models import PurchaseRequest, PurchaseOrder, OrderItem, RequestItem, Product as ProcurementProduct
from core.models import WorkshopWarehouse, Supplier, WorkshopStock, Product as CoreProduct


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
    low_stock_products = CoreProduct.objects.filter(quantity__lte=F('min_quantity'))
    for product in low_stock_products:
        notifications.append({
            'type': 'low_stock',
            'title': f'Низкий запас: {product.name}',
            'description': f'Осталось: {product.quantity} {product.unit} (минимум: {product.min_quantity})',
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
    """Страница склада - управление материалами цеха"""
    # Все материалы (шины, грузики, вентили и т.д.)
    products = CoreProduct.objects.all().select_related('category')
    workshop_stocks = WorkshopStock.objects.all().select_related('product', 'responsible_person')
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
            product = CoreProduct.objects.get(id=product_id)
            quantity = int(request.POST.get('quantity', 0))
            min_quantity = int(request.POST.get('min_quantity', 0))
            
            # Обновляем значения (используем правильные имена полей из core.models.Product)
            product.quantity = quantity
            product.min_quantity = min_quantity
            product.save()
            
            messages.success(
                request, 
                f'Запасы товара "{product.name}" обновлены: текущий={quantity}, минимальный={min_quantity}'
            )
        except CoreProduct.DoesNotExist:
            messages.error(request, 'Товар не найден')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')


@login_required
def workshop_stock(request):
    """Страница запасов цеха"""
    workshop_stocks = WorkshopStock.objects.all().select_related('product', 'responsible_person')
    
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
def view_request(request, request_id):
    """Просмотр деталей заявки"""
    request_obj = get_object_or_404(PurchaseRequest, id=request_id)
    items = RequestItem.objects.filter(request=request_obj).select_related('product')
    
    context = {
        'request_obj': request_obj,
        'items': items,
        'user': request.user,
    }
    
    return render(request, 'procurement/view_request.html', context)


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
                    # Получаем CoreProduct из WorkshopWarehouse
                    warehouse_item = get_object_or_404(WorkshopWarehouse, id=product_id)
                    product = warehouse_item.product  # Это CoreProduct
                    
                    # Создаем или получаем соответствующий ProcurementProduct
                    proc_product, created = ProcurementProduct.objects.get_or_create(
                        name=product.name,
                        defaults={
                            'sku': product.sku,
                            'unit': product.unit,
                            'category': product.category,
                            'price': product.price,
                        }
                    )
                    
                    quantity = int(quantities[i])
                    notes = notes_list[i] if i < len(notes_list) else ''
                    
                    RequestItem.objects.create(
                        request=purchase_request,
                        product=proc_product,
                        quantity=quantity,
                        requested_quantity=quantity
                    )
            
            messages.success(request, f'Заявка {purchase_request.request_number} создана!')
            return redirect('requests')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявки: {str(e)}')
    
    # Получаем только материалы со склада цеха (WorkshopWarehouse)
    workshop_stocks = WorkshopWarehouse.objects.select_related('product').order_by('product__name')
    
    context = {
        'workshop_stocks': workshop_stocks,
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
            
            # Создаем заказ
            order = PurchaseOrder.objects.create(
                supplier=supplier,
                status=PurchaseOrder.Status.SENT if send_email else PurchaseOrder.Status.DRAFT,
                notes=notes,
                created_by=request.user
            )
            
            # Добавляем позиции заказа
            total = 0
            order_items_data = []
            for i, product_id in enumerate(product_ids):
                if product_id and quantities[i]:
                    product = get_object_or_404(ProcurementProduct, id=product_id)
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
            
            # Отправляем email поставщику
            if send_email and supplier.email:
                from django.utils import timezone
                order.sent_at = timezone.now()
                order.save()
                send_order_email(order, order_items_data, total)
                messages.success(request, f'Заказ {order.order_number} создан и отправлен поставщику {supplier.name}!')
            else:
                messages.success(request, f'Заказ {order.order_number} создан!')
            
            return redirect('orders')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заказа: {str(e)}')
    
    suppliers_list = Supplier.objects.filter(is_active=True).order_by('name')
    products_list = ProcurementProduct.objects.all().order_by('name')
    
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
            workshop_stock_item = WorkshopStock.objects.get(id=stock_id)
            quantity_str = request.POST.get('quantity', '0')
            min_quantity_str = request.POST.get('min_quantity', '0')
            location = request.POST.get('location', '')
            
            # Проверка на пустые значения
            if not quantity_str or quantity_str.strip() == '':
                messages.error(request, 'Количество должно быть указано')
                return redirect('workshop_stock')
            if not min_quantity_str or min_quantity_str.strip() == '':
                messages.error(request, 'Минимальное количество должно быть указано')
                return redirect('workshop_stock')
                
            quantity = int(quantity_str)
            min_quantity = int(min_quantity_str)
            
            # Обновляем значения
            workshop_stock_item.quantity = quantity
            workshop_stock_item.min_quantity = min_quantity
            workshop_stock_item.location = location
            # Не пытаемся установить updated_by, так как это property без setter
            # responsible_person обновляется отдельно если нужно
            workshop_stock_item.responsible_person = request.user
            # Статус обновится автоматически в методе save() модели
            workshop_stock_item.save()
            
            messages.success(
                request, 
                f'Запасы "{workshop_stock_item.product.name}" в цеху обновлены: количество={quantity}, мин. запас={min_quantity}'
            )
        except WorkshopStock.DoesNotExist:
            messages.error(request, 'Запись о запасах не найдена')
        except ValueError:
            messages.error(request, 'Некорректное значение количества')
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
            quantity_to_add_str = request.POST.get('quantity_to_add', '0')
            
            # Проверка на пустое значение
            if not quantity_to_add_str or quantity_to_add_str.strip() == '':
                messages.error(request, 'Количество должно быть указано')
                return redirect('warehouse')
                
            quantity_to_add = int(quantity_to_add_str)
            
            if quantity_to_add > 0:
                # Проверяем, достаточно ли товара на основном складе
                product = warehouse.product
                if product.quantity >= quantity_to_add:
                    # Списываем с основного склада
                    product.quantity -= quantity_to_add
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
                        f'Недостаточно товара на складе. Доступно: {product.quantity} {product.unit}'
                    )
            else:
                messages.error(request, 'Количество должно быть больше нуля')
        except WorkshopWarehouse.DoesNotExist:
            messages.error(request, 'Запись склада не найдена')
        except ValueError:
            messages.error(request, 'Некорректное значение количества')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')


@login_required
def close_request(request, request_id):
    """Закрытие заявки"""
    request_obj = get_object_or_404(PurchaseRequest, id=request_id)
    
    if request.method == 'POST':
        try:
            # Обновляем статус заявки на "completed" или другой финальный статус
            request_obj.status = 'ordered'  # или можно добавить новый статус 'closed'
            request_obj.save()
            messages.success(request, f'Заявка {request_obj.request_number} успешно закрыта!')
        except Exception as e:
            messages.error(request, f'Ошибка при закрытии заявки: {str(e)}')
    
    return redirect('requests')


@login_required
def replenish_product(request, product_id):
    """Пополнение товара на складе (добавление нового товара)"""
    if request.method == 'POST':
        try:
            product = CoreProduct.objects.get(id=product_id)
            quantity_to_add_str = request.POST.get('quantity_to_add', '0')
            
            # Проверка на пустое значение
            if not quantity_to_add_str or quantity_to_add_str.strip() == '':
                messages.error(request, 'Количество должно быть указано')
                return redirect('warehouse')
                
            quantity_to_add = int(quantity_to_add_str)
            
            if quantity_to_add > 0:
                product.quantity += quantity_to_add
                product.save()
                
                messages.success(
                    request,
                    f'Товар "{product.name}" пополнен на {quantity_to_add} {product.unit}. Текущий остаток: {product.quantity}'
                )
            else:
                messages.error(request, 'Количество должно быть больше нуля')
        except CoreProduct.DoesNotExist:
            messages.error(request, 'Товар не найден')
        except ValueError:
            messages.error(request, 'Некорректное значение количества')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('warehouse')
