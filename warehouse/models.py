from django.conf import settings
from django.db import models, transaction


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    contact_name = models.CharField(max_length=200, blank=True, verbose_name="Контактное лицо")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Адрес")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ORDERED = "ordered"
    STATUS_RECEIVED = "received"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Черновик"),
        (STATUS_ORDERED, "Заказано"),
        (STATUS_RECEIVED, "Получено"),
        (STATUS_CANCELLED, "Отменено"),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="orders", verbose_name="Поставщик"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="Статус"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ordered_at = models.DateTimeField(blank=True, null=True)
    received_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, verbose_name="Примечания")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Закупка"
        verbose_name_plural = "Закупки"

    def __str__(self):
        return f"Закупка #{self.id} от {self.supplier}"

    def get_total(self):
        return sum(item.get_line_total() for item in self.items.all())

    def receive(self, user):
        #Принять закупку пополнить склад по каждой позиции
        from django.utils import timezone
        from service.models import Part
        if self.status != self.STATUS_ORDERED:
            raise ValueError("Только заказ со статусом 'Заказано' можно принять")
        with transaction.atomic():
            for item in self.items.select_related("part").all():
                Part.objects.filter(pk=item.part_id).update(
                    quantity=models.F("quantity") + item.quantity
                )
            self.status = self.STATUS_RECEIVED
            self.received_at = timezone.now()
            self.save(update_fields=["status", "received_at"])


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items", verbose_name="Закупка"
    )
    part = models.ForeignKey(
        "service.Part", on_delete=models.PROTECT, related_name="purchase_items", verbose_name="Запчасть"
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Цена за ед.")

    def get_line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.part} x{self.quantity}"


class InventoryAdjustment(models.Model):
    REASON_INVENTORY = "inventory"
    REASON_DAMAGE = "damage"
    REASON_RETURN = "return"
    REASON_OTHER = "other"

    REASON_CHOICES = [
        (REASON_INVENTORY, "Инвентаризация"),
        (REASON_DAMAGE, "Брак/Повреждение"),
        (REASON_RETURN, "Возврат"),
        (REASON_OTHER, "Прочее"),
    ]

    part = models.ForeignKey(
        "service.Part", on_delete=models.PROTECT, related_name="adjustments", verbose_name="Запчасть"
    )
    delta = models.IntegerField(verbose_name="Изменение (+ добавить, - убрать)")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default=REASON_OTHER, verbose_name="Причина")
    comment = models.CharField(max_length=300, blank=True, verbose_name="Комментарий")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="adjustments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    quantity_before = models.IntegerField(verbose_name="Остаток до")
    quantity_after = models.IntegerField(verbose_name="Остаток после")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Корректировка склада"
        verbose_name_plural = "Корректировки склада"

    def __str__(self):
        sign = "+" if self.delta >= 0 else ""
        return f"{self.part.sku}: {sign}{self.delta} ({self.get_reason_display()})"
