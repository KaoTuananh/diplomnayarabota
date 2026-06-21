from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from service.models import Part
from service.utils import get_role
from warehouse.forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemForm, InventoryAdjustmentForm
from warehouse.models import Supplier, PurchaseOrder, PurchaseOrderItem, InventoryAdjustment


def _require_manager(user):
    if get_role(user) != "manager":
        raise PermissionDenied()


#Поставщики

@login_required
def supplier_list(request):
    _require_manager(request.user)
    suppliers = Supplier.objects.all()
    return render(request, "warehouse/supplier_list.html", {"suppliers": suppliers})


@login_required
def supplier_create(request):
    _require_manager(request.user)
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("supplier_list")
    return render(request, "warehouse/supplier_form.html", {"form": form, "title": "Добавить поставщика"})


@login_required
def supplier_edit(request, pk):
    _require_manager(request.user)
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("supplier_list")
    return render(request, "warehouse/supplier_form.html", {"form": form, "title": f"Редактировать: {supplier.name}"})


#Закупки

@login_required
def purchase_list(request):
    _require_manager(request.user)
    orders = PurchaseOrder.objects.select_related("supplier", "created_by").all()
    return render(request, "warehouse/purchase_list.html", {"orders": orders})


@login_required
def purchase_create(request):
    _require_manager(request.user)
    form = PurchaseOrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order.created_by = request.user
        order.save()
        return redirect("purchase_detail", pk=order.pk)
    return render(request, "warehouse/purchase_form.html", {"form": form, "title": "Создать закупку"})


@login_required
def purchase_detail(request, pk):
    _require_manager(request.user)
    order = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    items = order.items.select_related("part").all()
    item_form = PurchaseOrderItemForm(request.POST or None)

    if request.method == "POST" and "add_item" in request.POST and item_form.is_valid():
        item = item_form.save(commit=False)
        item.order = order
        item.save()
        return redirect("purchase_detail", pk=order.pk)

    return render(request, "warehouse/purchase_detail.html", {
        "order": order,
        "items": items,
        "item_form": item_form,
        "total": order.get_total(),
    })


@login_required
def purchase_send(request, pk):
    #Перевести закупку в статус Заказано
    _require_manager(request.user)
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status == PurchaseOrder.STATUS_DRAFT:
        order.status = PurchaseOrder.STATUS_ORDERED
        order.ordered_at = timezone.now()
        order.save(update_fields=["status", "ordered_at"])
    return redirect("purchase_detail", pk=order.pk)


@login_required
def purchase_receive(request, pk):
    #Принять закупку пополнить склад
    _require_manager(request.user)
    order = get_object_or_404(PurchaseOrder, pk=pk)
    error = ""
    try:
        order.receive(request.user)
    except ValueError as e:
        error = str(e)
    if error:
        items = order.items.select_related("part").all()
        return render(request, "warehouse/purchase_detail.html", {
            "order": order, "items": items, "error": error, "total": order.get_total(),
        })
    return redirect("purchase_detail", pk=order.pk)


#Инвентаризация корректировки

@login_required
def adjustment_list(request):
    _require_manager(request.user)
    adjustments = InventoryAdjustment.objects.select_related("part", "created_by").all()[:100]
    return render(request, "warehouse/adjustment_list.html", {"adjustments": adjustments})


@login_required
def adjustment_create(request):
    _require_manager(request.user)
    form = InventoryAdjustmentForm(request.POST or None)
    error = ""
    if request.method == "POST" and form.is_valid():
        delta = form.cleaned_data["delta"]
        part = form.cleaned_data["part"]
        try:
            with transaction.atomic():
                part_obj = Part.objects.select_for_update().get(pk=part.pk)
                new_qty = part_obj.quantity + delta
                if new_qty < 0:
                    raise ValueError("Количество не может стать отрицательным")
                InventoryAdjustment.objects.create(
                    part=part_obj,
                    delta=delta,
                    reason=form.cleaned_data["reason"],
                    comment=form.cleaned_data["comment"],
                    created_by=request.user,
                    quantity_before=part_obj.quantity,
                    quantity_after=new_qty,
                )
                part_obj.quantity = new_qty
                part_obj.save(update_fields=["quantity"])
            return redirect("adjustment_list")
        except ValueError as e:
            error = str(e)

    return render(request, "warehouse/adjustment_form.html", {"form": form, "error": error, "title": "Корректировка склада"})


#Сигналы низкого остатка

@login_required
def low_stock_list(request):
    _require_manager(request.user)
    from django.db.models import F
    low_parts = Part.objects.filter(
        min_stock_level__gt=0,
        quantity__lte=F("min_stock_level")
    ).order_by("quantity")
    return render(request, "warehouse/low_stock.html", {"parts": low_parts})
