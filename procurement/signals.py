from django.db.models.signals import post_save
from django.dispatch import receiver
from procurement.models import WorkshopStock

@receiver(post_save, sender=WorkshopStock)
def update_stock_status(sender, instance, **kwargs):
    """
    Автоматически обновляет статус запаса при изменении количества товароведом.
    Если текущее количество меньше минимального -> статус 'low', иначе 'normal'.
    """
    old_instance = None
    # Проверяем, было ли изменение именно в количестве, если нужно оптимизировать,
    # но для надежности просто пересчитываем статус при любом сохранении
    
    needs_update = False
    if instance.quantity < instance.min_quantity:
        if instance.status != 'low':
            instance.status = 'low'
            needs_update = True
    else:
        if instance.status != 'normal':
            instance.status = 'normal'
            needs_update = True
    
    if needs_update:
        # Отключаем сигнал временно, чтобы избежать бесконечного цикла, если бы он был сложнее,
        # но здесь мы просто сохраняем поле status, что вызовет сигнал снова.
        # Чтобы избежать рекурсии, можно проверить, изменилось ли значение реально перед сохранением.
        # В данном простом случае Django обработает это корректно, так как значение уже присвоено.
        # Но чтобы не вызывать лишний save(), лучше обновлять через update() внутри сигнала, 
        # если мы хотим изменить только статус без триггера других логик.
        
        # Используем update для избежания рекурсивного вызова этого же сигнала
        WorkshopStock.objects.filter(pk=instance.pk).update(status=instance.status)
