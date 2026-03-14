from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Категория товаров"""
    name = models.CharField(_('Название категории'), max_length=100)
    description = models.TextField(_('Описание'), blank=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик товаров"""
    name = models.CharField(_('Название поставщика'), max_length=200)
    contact_person = models.CharField(_('Контактное лицо'), max_length=100, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Телефон'), max_length=50, blank=True)
    address = models.TextField(_('Адрес'), blank=True)
    created_at = models.DateTimeField(_('Дата добавления'), auto_now_add=True)
    is_active = models.BooleanField(_('Активен'), default=True)

    class Meta:
        verbose_name = _('Поставщик')
        verbose_name_plural = _('Поставщики')
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар на складе"""
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='products',
        verbose_name=_('Категория')
    )
    name = models.CharField(_('Название товара'), max_length=200)
    sku = models.CharField(_('Артикул'), max_length=50, unique=True, blank=True)
    unit = models.CharField(_('Единица измерения'), max_length=20, default='шт.')
    quantity = models.PositiveIntegerField(_('Количество на складе'), default=0)
    min_quantity = models.PositiveIntegerField(
        _('Минимальный уровень запаса'), 
        default=10,
        help_text=_('При достижении этого уровня требуется заказ')
    )
    price = models.DecimalField(_('Цена за единицу'), max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_('Основной поставщик')
    )
    created_at = models.DateTimeField(_('Дата добавления'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Товар')
        verbose_name_plural = _('Товары')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def needs_reorder(self):
        """Проверка необходимости заказа"""
        return self.quantity <= self.min_quantity


class PurchaseRequest(models.Model):
    """Заявка от сотрудника цеха"""

    request_number = models.CharField(_('Номер заявки'), max_length=20, unique=True, editable=False)
    requester = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchase_requests',
        verbose_name=_('Заявитель')
    )
    items_description = models.TextField(_('Описание товаров'), blank=True, help_text=_('Описание товаров, необходимых для заявки'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Заявка')
        verbose_name_plural = _('Заявки')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_number} - {self.requester.username if self.requester else 'Unknown'}"

    def save(self, *args, **kwargs):
        if not self.request_number and not self.pk:
            # Генерация номера заявки
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            last_request = PurchaseRequest.objects.filter(
                created_at__date=datetime.now().date()
            ).order_by('-pk').first()
            seq = (last_request.pk % 1000 + 1) if last_request else 1
            self.request_number = f"PR-{date_str}-{seq:04d}"
        super().save(*args, **kwargs)


class PurchaseRequestItem(models.Model):
    """Позиция заявки"""
    request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заявка')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='request_items',
        verbose_name=_('Товар')
    )
    quantity_requested = models.PositiveIntegerField(_('Запрашиваемое количество'))
    quantity_approved = models.PositiveIntegerField(_('Одобренное количество'), null=True, blank=True)
    notes = models.TextField(_('Примечание'), blank=True)

    class Meta:
        verbose_name = _('Позиция заявки')
        verbose_name_plural = _('Позиции заявок')

    def __str__(self):
        return f"{self.product.name} - {self.quantity_requested}"


class PurchaseOrder(models.Model):
    """Заказ поставщику"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        SENT = 'sent', _('Отправлен')
        CONFIRMED = 'confirmed', _('Подтвержден')
        PARTIAL = 'partial', _('Частично выполнен')
        COMPLETED = 'completed', _('Выполнен')
        CANCELLED = 'cancelled', _('Отменен')

    STATUS_CHOICES = Status.choices

    order_number = models.CharField(_('Номер заказа'), max_length=20, unique=True, editable=False)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_('Поставщик')
    )
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=Status.DRAFT
    )
    request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_('На основе заявки')
    )
    total_amount = models.DecimalField(_('Общая сумма'), max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(_('Примечание'), blank=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    sent_at = models.DateTimeField(_('Дата отправки'), null=True, blank=True)
    received_at = models.DateTimeField(_('Дата получения'), null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='core_created_orders',
        verbose_name=_('Создал')
    )

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.order_number and not self.pk:
            # Генерация номера заказа
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            last_order = PurchaseOrder.objects.filter(
                created_at__date=datetime.now().date()
            ).order_by('-pk').first()
            seq = (last_order.pk % 1000 + 1) if last_order else 1
            self.order_number = f"PO-{date_str}-{seq:04d}"
        super().save(*args, **kwargs)

    def calculate_total(self):
        """Пересчет общей суммы"""
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.save()


class OrderItem(models.Model):
    """Позиция заказа"""
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заказ')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name=_('Товар')
    )
    quantity_ordered = models.PositiveIntegerField(_('Заказано'))
    quantity_received = models.PositiveIntegerField(_('Получено'), default=0)
    unit_price = models.DecimalField(_('Цена за единицу'), max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(_('Подытог'), max_digits=12, decimal_places=2, editable=False)

    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказов')

    def __str__(self):
        return f"{self.product.name} x {self.quantity_ordered}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)
