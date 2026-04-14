from django.db import models
from django.contrib.auth.models import User


class WorkshopStock(models.Model):
    """Запасы материалов в цеху"""
    STATUS_CHOICES = [
        ('normal', 'В норме'),
        ('low', 'Низкий запас'),
    ]
    
    product = models.ForeignKey(
        'procurement.Product',
        on_delete=models.CASCADE,
        related_name='workshop_stocks',
        verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество в цеху"
    )
    min_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Минимальное количество"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='normal',
        verbose_name="Статус"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Место хранения"
    )
    responsible_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workshop_stocks_managed',
        verbose_name="Ответственный"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Запас в цеху"
        verbose_name_plural = "Запасы в цеху"
        ordering = ['product__name']
        unique_together = ['product']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit}"

    @property
    def is_low_stock(self):
        """Проверка необходимости пополнения"""
        return self.quantity <= self.min_quantity
    
    def save(self, *args, **kwargs):
        """Автоматическое обновление статуса при сохранении"""
        if self.quantity < self.min_quantity:
            self.status = 'low'
        else:
            self.status = 'normal'
        super().save(*args, **kwargs)


class Category(models.Model):
    """Категория товаров (например: Шины, Диски, Расходные материалы)"""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик товаров"""
    name = models.CharField(max_length=200, verbose_name="Название поставщика")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    address = models.TextField(blank=True, verbose_name="Адрес")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="Контактное лицо")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар/Материал на складе"""
    name = models.CharField(max_length=200, verbose_name="Наименование")
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products',
        verbose_name="Категория"
    )
    sku = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    unit = models.CharField(max_length=20, default='шт', verbose_name="Единица измерения")
    min_stock_level = models.PositiveIntegerField(
        default=0, 
        verbose_name="Минимальный остаток"
    )
    current_stock = models.PositiveIntegerField(
        default=0, 
        verbose_name="Текущий остаток"
    )
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products',
        verbose_name="Основной поставщик"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Цена за единицу"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        """Проверка необходимости пополнения"""
        return self.current_stock <= self.min_stock_level


class PurchaseRequest(models.Model):
    """Заявка на закупку от сотрудника цеха"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending', 'На согласовании'),
        ('approved', 'Согласована'),
        ('rejected', 'Отклонена'),
        ('ordered', 'Заказана'),
    ]

    ROLE_CHOICES = [
        ('workshop', 'Сотрудник цеха'),
        ('warehouse', 'Кладовщик'),
    ]

    request_number = models.CharField(max_length=20, unique=True, verbose_name="Номер заявки")
    requester = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='requests',
        verbose_name="Заявитель"
    )
    requester_role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        default='workshop',
        verbose_name="Роль заявителя"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Статус"
    )
    items = models.ManyToManyField('Product', through='RequestItem', verbose_name="Товары")
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Общая сумма"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_requests',
        verbose_name="Кто согласовал"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата согласования")
    items_description = models.TextField(blank=True, verbose_name="Описание товаров", help_text="Описание товаров, необходимых для заявки")

    class Meta:
        verbose_name = "Заявка на закупку"
        verbose_name_plural = "Заявки на закупку"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка {self.request_number} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Автогенерация номера заявки при создании"""
        if not self.request_number and not self.pk:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            last_request = PurchaseRequest.objects.filter(
                created_at__date=datetime.now().date()
            ).order_by('-pk').first()
            seq = (last_request.pk % 1000 + 1) if last_request else 1
            self.request_number = f"PR-{date_str}-{seq:04d}"
        super().save(*args, **kwargs)


class RequestItem(models.Model):
    """Позиция заявки на закупку"""
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='request_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    requested_quantity = models.PositiveIntegerField(verbose_name="Запрошенное количество")
    notes = models.TextField(blank=True, verbose_name="Примечание")

    class Meta:
        verbose_name = "Позиция заявки"
        verbose_name_plural = "Позиции заявок"

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit}"


class PurchaseOrder(models.Model):
    """Заказ поставщику"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('sent', 'Отправлен'),
        ('confirmed', 'Подтвержден'),
        ('partial', 'Частично исполнен'),
        ('completed', 'Исполнен'),
        ('cancelled', 'Отменен'),
    ]

    order_number = models.CharField(max_length=20, unique=True, verbose_name="Номер заказа")
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Поставщик"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Статус"
    )
    request = models.ForeignKey(
        PurchaseRequest, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='orders',
        verbose_name="Заявка-основание"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Общая сумма"
    )
    email_sent = models.BooleanField(default=False, verbose_name="Отправлен по email")
    email_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки email")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='procurement_created_orders',
        verbose_name="Создал"
    )

    class Meta:
        verbose_name = "Заказ поставщику"
        verbose_name_plural = "Заказы поставщикам"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ {self.order_number} - {self.supplier.name}"


class OrderItem(models.Model):
    """Позиция заказа поставщику"""
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    received_quantity = models.PositiveIntegerField(default=0, verbose_name="Получено")
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Цена за единицу"
    )
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Сумма"
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit}"

    def save(self, *args, **kwargs):
        if self.unit_price and self.quantity:
            self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
