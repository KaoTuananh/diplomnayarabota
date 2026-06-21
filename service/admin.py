from django.contrib import admin
from service.models import RepairRequest, StatusHistory, WorkLog, Part, PartUsage, PartReservation, Notification

@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "client_name", "equipment_type", "status", "assigned_master", "created_at")
    list_filter = ("status",)
    search_fields = ("client_name", "equipment_type", "serial_number")

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("request", "old_status", "new_status", "changed_by", "changed_at")
    list_filter = ("new_status",)

@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("request", "master", "work_date", "hours")

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "quantity", "unit_cost")
    search_fields = ("name", "sku")

@admin.register(PartUsage)
class PartUsageAdmin(admin.ModelAdmin):
    list_display = ("request", "part", "quantity", "used_by", "used_at")

@admin.register(PartReservation)
class PartReservationAdmin(admin.ModelAdmin):
    list_display = ("request", "part", "quantity", "reserved_by", "reserved_at", "released")
    list_filter = ("released",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("kind", "text", "target_user", "is_read", "created_at")
    list_filter = ("kind", "is_read")
    search_fields = ("text",)
