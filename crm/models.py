from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Имя/Организация")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.CharField(max_length=300, blank=True, verbose_name="Адрес")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    def __str__(self):
        return self.name


class Equipment(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="equipment", verbose_name="Клиент"
    )
    equipment_type = models.CharField(max_length=200, verbose_name="Тип оборудования")
    brand = models.CharField(max_length=100, blank=True, verbose_name="Производитель")
    model_name = models.CharField(max_length=200, blank=True, verbose_name="Модель")
    serial_number = models.CharField(max_length=200, blank=True, verbose_name="Серийный номер")
    purchase_date = models.DateField(blank=True, null=True, verbose_name="Дата покупки")
    warranty_until = models.DateField(blank=True, null=True, verbose_name="Гарантия до")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["equipment_type", "brand"]
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"

    def __str__(self):
        parts = [self.equipment_type]
        if self.brand:
            parts.append(self.brand)
        if self.model_name:
            parts.append(self.model_name)
        if self.serial_number:
            parts.append(f"({self.serial_number})")
        return " ".join(parts)

    @property
    def is_warranty_active(self):
        if not self.warranty_until:
            return None
        from django.utils import timezone
        return self.warranty_until >= timezone.now().date()
