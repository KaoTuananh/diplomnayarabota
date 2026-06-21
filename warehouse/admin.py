from django.contrib import admin
from warehouse.models import Supplier, PurchaseOrder, PurchaseOrderItem, InventoryAdjustment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "contact_name", "phone", "email"]
    search_fields = ["name", "email"]


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "supplier", "status", "created_at", "ordered_at", "received_at"]
    list_filter = ["status"]
    inlines = [PurchaseOrderItemInline]
    raw_id_fields = ["created_by"]


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["id", "part", "delta", "reason", "quantity_before", "quantity_after", "created_by", "created_at"]
    list_filter = ["reason"]
    raw_id_fields = ["part", "created_by"]
