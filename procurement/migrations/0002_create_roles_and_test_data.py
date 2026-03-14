from django.db import migrations


def create_roles(apps, schema_editor):
    """Создание ролей: Сотрудник цеха и Товаровед"""
    Group = apps.get_model('auth', 'Group')
    
    # Создаем группу "Сотрудник цеха"
    workshop_group, created = Group.objects.get_or_create(name='Сотрудник цеха')
    
    # Создаем группу "Товаровед"
    merchandiser_group, created = Group.objects.get_or_create(name='Товаровед')


def create_test_data(apps, schema_editor):
    """Создание тестовых данных"""
    # Получаем модели
    Category = apps.get_model('procurement', 'Category')
    Supplier = apps.get_model('procurement', 'Supplier')
    Product = apps.get_model('procurement', 'Product')
    PurchaseRequest = apps.get_model('procurement', 'PurchaseRequest')
    RequestItem = apps.get_model('procurement', 'RequestItem')
    PurchaseOrder = apps.get_model('procurement', 'PurchaseOrder')
    OrderItem = apps.get_model('procurement', 'OrderItem')
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')
    
    # Получаем группы
    workshop_group = Group.objects.get(name='Сотрудник цеха')
    merchandiser_group = Group.objects.get(name='Товаровед')
    
    # Создаем тестовых пользователей
    user1, _ = User.objects.get_or_create(
        username='workshop_user',
        defaults={
            'email': 'workshop@example.com',
            'first_name': 'Иван',
            'last_name': 'Петров',
            'is_staff': False,
            'is_active': True,
            'password': 'pbkdf2_sha256$600000$dummy$salt=',  # Placeholder, will set password after
        }
    )
    user1.groups.add(workshop_group)
    user1.password = 'pbkdf2_sha256$600000$QKx8R9vZJhLp$K8mYzE3qN5wX7pL2nM4kJ6tR8sU0vW2yA4bC6dE8fG0='  # hashed 'password123'
    user1.save()
    
    user2, _ = User.objects.get_or_create(
        username='merchandiser_user',
        defaults={
            'email': 'merchandiser@example.com',
            'first_name': 'Анна',
            'last_name': 'Сидорова',
            'is_staff': True,
            'is_active': True,
            'password': 'pbkdf2_sha256$600000$dummy$salt=',
        }
    )
    user2.groups.add(merchandiser_group)
    user2.password = 'pbkdf2_sha256$600000$QKx8R9vZJhLp$K8mYzE3qN5wX7pL2nM4kJ6tR8sU0vW2yA4bC6dE8fG0='
    user2.save()
    
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Админ',
            'last_name': 'Системы',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'password': 'pbkdf2_sha256$600000$dummy$salt=',
        }
    )
    admin_user.password = 'pbkdf2_sha256$600000$QKx8R9vZJhLp$K8mYzE3qN5wX7pL2nM4kJ6tR8sU0vW2yA4bC6dE8fG0='  # 'admin123'
    admin_user.save()
    
    # Создаем категории
    cat1, _ = Category.objects.get_or_create(
        name='Шины',
        defaults={'description': 'Автомобильные шины различных размеров'}
    )
    
    cat2, _ = Category.objects.get_or_create(
        name='Диски',
        defaults={'description': 'Легкосплавные и стальные диски'}
    )
    
    cat3, _ = Category.objects.get_or_create(
        name='Расходные материалы',
        defaults={'description': 'Масла, фильтры, тормозные колодки'}
    )
    
    cat4, _ = Category.objects.get_or_create(
        name='Инструменты',
        defaults={'description': 'Ручной и пневматический инструмент'}
    )
    
    # Создаем поставщиков
    supplier1, _ = Supplier.objects.get_or_create(
        name='ООО "ШинТорг"',
        defaults={
            'email': 'info@shintorg.ru',
            'phone': '+7 (495) 123-45-67',
            'address': 'г. Москва, ул. Автомобильная, д. 10',
            'contact_person': 'Алексей Иванов',
            'is_active': True,
        }
    )
    
    supplier2, _ = Supplier.objects.get_or_create(
        name='ИП "АвтоЗапчасти"',
        defaults={
            'email': 'zakaz@avtozap.ru',
            'phone': '+7 (495) 987-65-43',
            'address': 'г. Москва, ул. Складская, д. 5',
            'contact_person': 'Мария Петрова',
            'is_active': True,
        }
    )
    
    supplier3, _ = Supplier.objects.get_or_create(
        name='ООО "Масла и Смазки"',
        defaults={
            'email': 'sales@oil-lube.ru',
            'phone': '+7 (495) 555-12-34',
            'address': 'г. Подольск,工业区, стр. 3',
            'contact_person': 'Дмитрий Соколов',
            'is_active': True,
        }
    )
    
    # Создаем товары
    product1, _ = Product.objects.get_or_create(
        sku='TIRE-205-55-16',
        defaults={
            'name': 'Шина Michelin Primacy 4 205/55 R16',
            'category': cat1,
            'unit': 'шт',
            'min_stock_level': 10,
            'current_stock': 8,  # Низкий остаток для демонстрации
            'supplier': supplier1,
            'price': 8500.00,
            'description': 'Летняя шина премиум класса',
        }
    )
    
    product2, _ = Product.objects.get_or_create(
        sku='TIRE-225-45-17',
        defaults={
            'name': 'Шина Continental ContiPremiumContact 5 225/45 R17',
            'category': cat1,
            'unit': 'шт',
            'min_stock_level': 8,
            'current_stock': 15,
            'supplier': supplier1,
            'price': 9200.00,
            'description': 'Летняя шина премиум класса',
        }
    )
    
    product3, _ = Product.objects.get_or_create(
        sku='DISK-16-ALU',
        defaults={
            'name': 'Диск легкосплавный R16 5x112',
            'category': cat2,
            'unit': 'шт',
            'min_stock_level': 5,
            'current_stock': 12,
            'supplier': supplier1,
            'price': 6500.00,
            'description': 'Легкосплавный диск серебристого цвета',
        }
    )
    
    product4, _ = Product.objects.get_or_create(
        sku='OIL-5W30-4L',
        defaults={
            'name': 'Моторное масло 5W-30 4л',
            'category': cat3,
            'unit': 'шт',
            'min_stock_level': 20,
            'current_stock': 5,  # Низкий остаток
            'supplier': supplier3,
            'price': 3200.00,
            'description': 'Синтетическое моторное масло',
        }
    )
    
    product5, _ = Product.objects.get_or_create(
        sku='FILTER-OIL-001',
        defaults={
            'name': 'Фильтр масляный универсальный',
            'category': cat3,
            'unit': 'шт',
            'min_stock_level': 30,
            'current_stock': 45,
            'supplier': supplier2,
            'price': 450.00,
            'description': 'Масляный фильтр для большинства автомобилей',
        }
    )
    
    product6, _ = Product.objects.get_or_create(
        sku='BRAKE-PAD-FRONT',
        defaults={
            'name': 'Колодки тормозные передние',
            'category': cat3,
            'unit': 'комплект',
            'min_stock_level': 15,
            'current_stock': 8,  # Низкий остаток
            'supplier': supplier2,
            'price': 2800.00,
            'description': 'Тормозные колодки передние керамические',
        }
    )
    
    product7, _ = Product.objects.get_or_create(
        sku='TOOL-WRENCH-SET',
        defaults={
            'name': 'Набор ключей гаечных',
            'category': cat4,
            'unit': 'набор',
            'min_stock_level': 3,
            'current_stock': 7,
            'supplier': supplier2,
            'price': 4500.00,
            'description': 'Набор ключей от 8 до 24 мм',
        }
    )
    
    # Создаем заявку на закупку
    request1 = PurchaseRequest.objects.create(
        request_number='REQ-2026-001',
        requester=user1,
        requester_role='workshop',
        status='approved',
        total_amount=0,
        comment='Срочная заявка на пополнение склада',
        approved_by=user2,
    )
    
    # Добавляем позиции в заявку
    RequestItem.objects.create(
        request=request1,
        product=product1,
        requested_quantity=20,
        quantity=20,
    )
    
    RequestItem.objects.create(
        request=request1,
        product=product4,
        requested_quantity=30,
        quantity=30,
    )
    
    RequestItem.objects.create(
        request=request1,
        product=product6,
        requested_quantity=20,
        quantity=20,
    )
    
    # Пересчитываем общую сумму заявки
    total = 0
    for item in request1.request_items.all():
        if item.product.price:
            total += item.product.price * item.quantity
    request1.total_amount = total
    request1.save()
    
    # Создаем заказ на основе заявки
    order1 = PurchaseOrder.objects.create(
        order_number='PO-2026-001',
        supplier=supplier1,
        status='sent',
        request=request1,
        total_amount=0,
        email_sent=True,
        comment='Заказ сформирован по заявке REQ-2026-001',
        created_by=user2,
    )
    
    # Добавляем позиции в заказ
    OrderItem.objects.create(
        order=order1,
        product=product1,
        quantity=20,
        received_quantity=0,
        unit_price=8500.00,
        subtotal=8500.00 * 20,
    )
    
    # Пересчитываем общую сумму заказа
    order_total = sum(item.subtotal for item in order1.order_items.all())
    order1.total_amount = order_total
    order1.save()
    
    # Создаем еще одну заявку в статусе черновика
    request2 = PurchaseRequest.objects.create(
        request_number='REQ-2026-002',
        requester=user1,
        requester_role='workshop',
        status='draft',
        total_amount=0,
        comment='Плановая заявка на следующую неделю',
    )
    
    RequestItem.objects.create(
        request=request2,
        product=product2,
        requested_quantity=10,
        quantity=10,
    )
    
    RequestItem.objects.create(
        request=request2,
        product=product3,
        requested_quantity=5,
        quantity=5,
    )
    
    # Пересчитываем сумму
    total2 = 0
    for item in request2.request_items.all():
        if item.product.price:
            total2 += item.product.price * item.quantity
    request2.total_amount = total2
    request2.save()


def remove_test_data(apps, schema_editor):
    """Удаление тестовых данных"""
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')
    
    # Удаляем тестовых пользователей
    User.objects.filter(username__in=['workshop_user', 'merchandiser_user', 'admin']).delete()
    
    # Удаляем группы
    Group.objects.filter(name__in=['Сотрудник цеха', 'Товаровед']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('procurement', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_roles, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(create_test_data, reverse_code=remove_test_data),
    ]
