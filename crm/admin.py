from django.contrib import admin
from crm.models import Client, Equipment


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "email", "created_at"]
    search_fields = ["name", "phone", "email"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["id", "equipment_type", "brand", "model_name", "serial_number", "client"]
    search_fields = ["equipment_type", "serial_number", "brand"]
    list_filter = ["equipment_type"]
    raw_id_fields = ["client"]
