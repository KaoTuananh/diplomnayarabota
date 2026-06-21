from django import forms
from django.contrib.auth.models import User
from service.models import RepairRequest, WorkLog, Part, PartUsage

class RepairRequestCreateForm(forms.ModelForm):
    class Meta:
        model = RepairRequest
        fields = [
            "client_name",
            "client_phone",
            "client_email",
            "equipment_type",
            "serial_number",
            "office_location",
            "problem_description",
            "photo",
        ]

class RepairRequestEditForm(forms.ModelForm):
    class Meta:
        model = RepairRequest
        fields = [
            "client_name",
            "client_phone",
            "client_email",
            "equipment_type",
            "serial_number",
            "office_location",
            "problem_description",
            "photo",
        ]

class AssignMasterForm(forms.Form):
    assigned_master = forms.ModelChoiceField(queryset=User.objects.none(), label="Мастер", required=False)

    def __init__(self, *args, **kwargs):
        masters = kwargs.pop("masters", User.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["assigned_master"].queryset = masters

class StatusChangeForm(forms.Form):
    status = forms.ChoiceField(choices=RepairRequest.STATUS_CHOICES, label="Статус")
    note = forms.CharField(label="Комментарий", required=False)

class WorkLogForm(forms.ModelForm):
    class Meta:
        model = WorkLog
        fields = ["work_date", "hours", "description"]

class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ["name", "sku", "quantity", "unit_cost", "min_stock_level"]
        labels = {
            "name": "Название",
            "sku": "Артикул (SKU)",
            "quantity": "Количество",
            "unit_cost": "Цена за единицу",
            "min_stock_level": "Минимальный остаток",
        }

class PartUsageForm(forms.ModelForm):
    class Meta:
        model = PartUsage
        fields = ["part", "quantity"]
