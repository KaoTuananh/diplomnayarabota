from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

class Part(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_stock_level = models.PositiveIntegerField(default=0, help_text="Минимальный остаток. 0 = без ограничений")
    reserved_quantity = models.PositiveIntegerField(default=0, help_text="Зарезервировано под заявки")

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        return self.min_stock_level > 0 and self.quantity <= self.min_stock_level

class RepairRequest(models.Model):
    STATUS_NEW = "new"
    STATUS_IN_WORK = "in_work"
    STATUS_WAIT_PART = "wait_part"
    STATUS_DONE = "done"

    STATUS_CHOICES = [
        (STATUS_NEW, "Новая"),
        (STATUS_IN_WORK, "В работе"),
        (STATUS_WAIT_PART, "Ожидает запчасть"),
        (STATUS_DONE, "Завершена"),
    ]

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_requests")
    assigned_master = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="assigned_requests")

    client_name = models.CharField(max_length=200)
    client_phone = models.CharField(max_length=30, blank=True)
    client_email = models.EmailField(blank=True)

    equipment_type = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=200, blank=True)
    office_location = models.CharField(max_length=200, blank=True)

    problem_description = models.TextField()
    photo = models.ImageField(upload_to="request_photos/", blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Заявка #{self.id} - {self.client_name} - {self.get_status_display()}"

class StatusHistory(models.Model):
    request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"#{self.request_id}: {self.old_status} -> {self.new_status}"

class WorkLog(models.Model):
    request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name="work_logs")
    master = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="work_logs")
    work_date = models.DateField(default=timezone.now)
    hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    description = models.TextField()

    def __str__(self):
        return f"Работа по #{self.request_id} ({self.master.username})"

class PartUsage(models.Model):
    request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name="part_usages")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="usages")
    quantity = models.PositiveIntegerField()
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_usages")
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Списание {self.part.sku} x{self.quantity} по #{self.request_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            part = Part.objects.select_for_update().get(pk=self.part_id)
            if self.quantity == 0:
                raise ValueError("Количество не может быть 0")
            if part.quantity < self.quantity:
                raise ValueError("Недостаточно запчастей на складе")
            part.quantity -= self.quantity
            part.save(update_fields=["quantity"])
            super().save(*args, **kwargs)


class PartReservation(models.Model):
    request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name="reservations")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="reservations")
    quantity = models.PositiveIntegerField()
    reserved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations")
    reserved_at = models.DateTimeField(auto_now_add=True)
    released = models.BooleanField(default=False)

    def __str__(self):
        return f"Резерв {self.part.sku} x{self.quantity} для #{self.request_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            super().save(*args, **kwargs)
            return
        with transaction.atomic():
            part = Part.objects.select_for_update().get(pk=self.part_id)
            if part.available_quantity < self.quantity:
                raise ValueError("Недостаточно доступных запчастей для резервирования")
            part.reserved_quantity += self.quantity
            part.save(update_fields=["reserved_quantity"])
            super().save(*args, **kwargs)

    def release(self):
        if self.released:
            return
        with transaction.atomic():
            Part.objects.filter(pk=self.part_id).update(
                reserved_quantity=models.F("reserved_quantity") - self.quantity
            )
            self.released = True
            self.save(update_fields=["released"])


class Notification(models.Model):
    KIND_STATUS = "status"
    KIND_ASSIGN = "assign"
    KIND_NEW = "new"
    KIND_STOCK = "stock"
    KIND_PART = "part"
    KIND_WORK = "work"
    KIND_OTHER = "other"

    KIND_CHOICES = [
        (KIND_STATUS, "Смена статуса"),
        (KIND_ASSIGN, "Назначение мастера"),
        (KIND_NEW, "Новая заявка"),
        (KIND_STOCK, "Склад"),
        (KIND_PART, "Запчасти"),
        (KIND_WORK, "Работы"),
        (KIND_OTHER, "Прочее"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_OTHER)
    text = models.TextField()
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications", null=True, blank=True,
        help_text="Кому адресовано. NULL = системное событие (видят менеджеры)"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    repair_request = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.kind}] {self.text[:60]}"
