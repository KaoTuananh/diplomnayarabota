from django import forms
from warehouse.models import Supplier, PurchaseOrder, PurchaseOrderItem, InventoryAdjustment


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_name", "phone", "email", "address", "notes"]
        labels = {
            "name": "Название",
            "contact_name": "Контактное лицо",
            "phone": "Телефон",
            "email": "Email",
            "address": "Адрес",
            "notes": "Примечания",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "notes"]
        labels = {
            "supplier": "Поставщик",
            "notes": "Примечания",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["part", "quantity", "unit_price"]
        labels = {
            "part": "Запчасть",
            "quantity": "Количество",
            "unit_price": "Цена за ед.",
        }


class InventoryAdjustmentForm(forms.ModelForm):
    class Meta:
        model = InventoryAdjustment
        fields = ["part", "delta", "reason", "comment"]
        labels = {
            "part": "Запчасть",
            "delta": "Изменение (положительное = добавить, отрицательное = убрать)",
            "reason": "Причина",
            "comment": "Комментарий",
        }
