from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404

from crm.forms import ClientForm, EquipmentForm
from crm.models import Client, Equipment
from service.models import RepairRequest
from service.utils import get_role


@login_required
def client_list(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    q = request.GET.get("q", "").strip()
    clients = Client.objects.all()
    if q:
        clients = clients.filter(name__icontains=q) | clients.filter(phone__icontains=q)
    return render(request, "crm/client_list.html", {"clients": clients, "role": role, "q": q})


@login_required
def client_create(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    form = ClientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        client = form.save()
        return redirect("client_detail", pk=client.pk)
    return render(request, "crm/client_form.html", {"form": form, "title": "Добавить клиента"})


@login_required
def client_detail(request, pk):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    client = get_object_or_404(Client, pk=pk)
    #заявки с email или именем клиента
    repair_history = RepairRequest.objects.filter(
        client_email=client.email
    ).order_by("-created_at") if client.email else RepairRequest.objects.none()
    if not client.email:
        repair_history = RepairRequest.objects.filter(
            client_name=client.name
        ).order_by("-created_at")
    return render(request, "crm/client_detail.html", {
        "client": client,
        "repair_history": repair_history,
        "role": role,
    })


@login_required
def client_edit(request, pk):
    role = get_role(request.user)
    if role not in ("manager",):
        raise PermissionDenied()
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("client_detail", pk=client.pk)
    return render(request, "crm/client_form.html", {"form": form, "title": f"Редактировать: {client.name}"})


@login_required
def equipment_list(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    q = request.GET.get("q", "").strip()
    equipment = Equipment.objects.select_related("client").all()
    if q:
        equipment = equipment.filter(equipment_type__icontains=q) | equipment.filter(serial_number__icontains=q) | equipment.filter(brand__icontains=q)
    return render(request, "crm/equipment_list.html", {"equipment": equipment, "role": role, "q": q})


@login_required
def equipment_create(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    form = EquipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        eq = form.save()
        return redirect("equipment_detail", pk=eq.pk)
    return render(request, "crm/equipment_form.html", {"form": form, "title": "Добавить оборудование"})


@login_required
def equipment_detail(request, pk):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    eq = get_object_or_404(Equipment.objects.select_related("client"), pk=pk)
    repair_history = RepairRequest.objects.filter(
        serial_number=eq.serial_number
    ).order_by("-created_at") if eq.serial_number else RepairRequest.objects.none()
    return render(request, "crm/equipment_detail.html", {
        "eq": eq,
        "repair_history": repair_history,
        "role": role,
    })


@login_required
def equipment_edit(request, pk):
    role = get_role(request.user)
    if role not in ("manager",):
        raise PermissionDenied()
    eq = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=eq)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("equipment_detail", pk=eq.pk)
    return render(request, "crm/equipment_form.html", {"form": form, "title": f"Редактировать оборудование"})
