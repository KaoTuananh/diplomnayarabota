from django import forms
from crm.models import Client, Equipment


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "phone", "email", "address", "notes"]
        labels = {
            "name": "Имя / Организация",
            "phone": "Телефон",
            "email": "Email",
            "address": "Адрес",
            "notes": "Примечания",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ["client", "equipment_type", "brand", "model_name", "serial_number",
                  "purchase_date", "warranty_until", "notes"]
        labels = {
            "client": "Клиент",
            "equipment_type": "Тип оборудования",
            "brand": "Производитель",
            "model_name": "Модель",
            "serial_number": "Серийный номер",
            "purchase_date": "Дата покупки",
            "warranty_until": "Гарантия до",
            "notes": "Примечания",
        }
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "warranty_until": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
