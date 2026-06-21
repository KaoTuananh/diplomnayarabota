from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from service.forms import (
    RepairRequestCreateForm,
    RepairRequestEditForm,
    AssignMasterForm,
    StatusChangeForm,
    WorkLogForm,
    PartForm,
    PartUsageForm,
)
from service.models import RepairRequest, Part, PartUsage, PartReservation, Notification, WorkLog
from service.utils import get_role, change_status, assign_master, notify

def masters_queryset():
    return User.objects.filter(profile__role="master").order_by("username")

def can_view_request(user, req: RepairRequest):
    role = get_role(user)
    if role == "manager":
        return True
    if role == "master":
        return req.assigned_master_id == user.id
    return req.created_by_id == user.id

def can_edit_request(user, req: RepairRequest):
    role = get_role(user)
    if role == "manager":
        return True
    if role == "master":
        return req.assigned_master_id == user.id
    return req.created_by_id == user.id and req.status == RepairRequest.STATUS_NEW

@login_required
def dashboard(request):
    role = get_role(request.user)
    qs = RepairRequest.objects.all().select_related("assigned_master", "created_by").order_by("-created_at")

    status = request.GET.get("status") or ""
    if status:
        qs = qs.filter(status=status)

    if role == "client":
        qs = qs.filter(created_by=request.user)
    elif role == "master":
        qs = qs.filter(assigned_master=request.user)

    counts = RepairRequest.objects.values("status").annotate(c=Count("id")).order_by("status")
    return render(request, "service/dashboard.html", {"requests": qs, "counts": counts, "role": role, "status_filter": status})

@login_required
def request_create(request):
    form = RepairRequestCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        notify("NEW", f"Создана заявка #{obj.id}. Пользователь: {request.user.username}")
        return redirect("request_detail", pk=obj.id)
    return render(request, "service/request_form.html", {"form": form, "title": "Создание заявки"})

@login_required
def request_detail(request, pk: int):
    obj = get_object_or_404(RepairRequest.objects.select_related("assigned_master", "created_by"), pk=pk)
    if not can_view_request(request.user, obj):
        raise PermissionDenied()

    role = get_role(request.user)
    return render(
        request,
        "service/request_detail.html",
        {
            "obj": obj,
            "role": role,
            "history": obj.status_history.select_related("changed_by").order_by("-changed_at"),
            "work_logs": obj.work_logs.select_related("master").order_by("-work_date", "-id"),
            "part_usages": obj.part_usages.select_related("part", "used_by").order_by("-used_at"),
        },
    )

@login_required
def request_edit(request, pk: int):
    obj = get_object_or_404(RepairRequest, pk=pk)
    if not can_edit_request(request.user, obj):
        raise PermissionDenied()

    form = RepairRequestEditForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        notify("EDIT", f"Изменена заявка #{obj.id}. Пользователь: {request.user.username}")
        return redirect("request_detail", pk=obj.id)

    return render(request, "service/request_form.html", {"form": form, "title": f"Редактирование заявки #{obj.id}"})

@login_required
def request_assign_master(request, pk: int):
    role = get_role(request.user)
    if role != "manager":
        raise PermissionDenied()

    obj = get_object_or_404(RepairRequest, pk=pk)
    form = AssignMasterForm(request.POST or None, masters=masters_queryset())
    if request.method == "POST" and form.is_valid():
        master = form.cleaned_data["assigned_master"]
        assign_master(obj, master, request.user)
        return redirect("request_detail", pk=obj.id)
    return render(request, "service/request_assign.html", {"form": form, "obj": obj})

@login_required
def request_change_status(request, pk: int):
    obj = get_object_or_404(RepairRequest, pk=pk)
    role = get_role(request.user)

    if role == "client":
        raise PermissionDenied()

    if role == "master" and obj.assigned_master_id != request.user.id:
        raise PermissionDenied()

    form = StatusChangeForm(request.POST or None, initial={"status": obj.status})
    if request.method == "POST" and form.is_valid():
        new_status = form.cleaned_data["status"]
        note = form.cleaned_data["note"]
        change_status(obj, new_status, request.user, note=note)
        return redirect("request_detail", pk=obj.id)
    return render(request, "service/request_status.html", {"form": form, "obj": obj})

@login_required
def worklog_add(request, pk: int):
    obj = get_object_or_404(RepairRequest, pk=pk)
    role = get_role(request.user)

    if role == "client":
        raise PermissionDenied()
    if role == "master" and obj.assigned_master_id != request.user.id:
        raise PermissionDenied()

    form = WorkLogForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        wl = form.save(commit=False)
        wl.request = obj
        wl.master = request.user
        wl.save()
        notify("WORK", f"Добавлена запись работ по заявке #{obj.id}. Мастер: {request.user.username}")
        return redirect("request_detail", pk=obj.id)

    return render(request, "service/worklog_form.html", {"form": form, "obj": obj})

@login_required
def parts_list(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()
    parts = Part.objects.all().order_by("name")
    return render(request, "service/parts_list.html", {"parts": parts, "role": role})

@login_required
def part_create(request):
    role = get_role(request.user)
    if role != "manager":
        raise PermissionDenied()
    form = PartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        notify("PART", f"Добавлена запчасть. Пользователь: {request.user.username}")
        return redirect("parts_list")
    return render(request, "service/part_form.html", {"form": form, "title": "Добавить запчасть"})

@login_required
def part_edit(request, part_id: int):
    role = get_role(request.user)
    if role != "manager":
        raise PermissionDenied()
    obj = get_object_or_404(Part, pk=part_id)
    form = PartForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        notify("PART", f"Изменена запчасть {obj.sku}. Пользователь: {request.user.username}")
        return redirect("parts_list")
    return render(request, "service/part_form.html", {"form": form, "title": f"Редактировать: {obj.sku}"})

@login_required
def part_usage_add(request, pk: int):
    obj = get_object_or_404(RepairRequest, pk=pk)
    role = get_role(request.user)

    if role == "client":
        raise PermissionDenied()
    if role == "master" and obj.assigned_master_id != request.user.id:
        raise PermissionDenied()

    form = PartUsageForm(request.POST or None)
    error = ""
    if request.method == "POST" and form.is_valid():
        usage = form.save(commit=False)
        usage.request = obj
        usage.used_by = request.user
        try:
            usage.save()
            notify("STOCK", f"Списание по заявке #{obj.id}: {usage.part.sku} x{usage.quantity}. Пользователь: {request.user.username}")
            return redirect("request_detail", pk=obj.id)
        except Exception as e:
            error = str(e)

    return render(request, "service/usage_form.html", {"form": form, "obj": obj, "error": error})

@login_required
def part_reserve_add(request, pk: int):
    obj = get_object_or_404(RepairRequest, pk=pk)
    role = get_role(request.user)
    if role == "client":
        raise PermissionDenied()
    if role == "master" and obj.assigned_master_id != request.user.id:
        raise PermissionDenied()

    from django import forms as dj_forms
    class ReserveForm(dj_forms.Form):
        part = dj_forms.ModelChoiceField(queryset=Part.objects.all(), label="Запчасть")
        quantity = dj_forms.IntegerField(min_value=1, label="Количество")

    error = ""
    form = ReserveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            PartReservation.objects.create(
                request=obj,
                part=form.cleaned_data["part"],
                quantity=form.cleaned_data["quantity"],
                reserved_by=request.user,
            )
            return redirect("request_detail", pk=obj.id)
        except Exception as e:
            error = str(e)
    return render(request, "service/reserve_form.html", {"form": form, "obj": obj, "error": error})


@login_required
def reports(request):
    role = get_role(request.user)
    if role != "manager":
        raise PermissionDenied()

    by_status = list(RepairRequest.objects.values("status").annotate(count=Count("id")).order_by("status"))

    duration_expr = ExpressionWrapper(F("completed_at") - F("created_at"), output_field=DurationField())
    avg_duration = (
        RepairRequest.objects.filter(status=RepairRequest.STATUS_DONE, completed_at__isnull=False)
        .annotate(d=duration_expr)
        .aggregate(avg=Avg("d"))
        .get("avg")
    )

    avg_hours = None
    if avg_duration:
        avg_hours = round(avg_duration.total_seconds() / 3600, 2)

    #По типам оборудования
    by_equipment = list(
        RepairRequest.objects.values("equipment_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    #KPI мастеров
    master_kpi = list(
        WorkLog.objects.values("master__username", "master__first_name", "master__last_name")
        .annotate(total_hours=Sum("hours"), jobs=Count("request_id", distinct=True))
        .order_by("-total_hours")
    )

    #Воронка
    funnel = {
        "new": 0, "in_work": 0, "wait_part": 0, "done": 0,
    }
    for row in by_status:
        funnel[row["status"]] = row["count"]

    #ABC-анализ запчастей по сумме списаний
    abc_parts = list(
        PartUsage.objects.values("part__sku", "part__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:10]
    )

    #Данные для Chart.js
    import json
    chart_status = {
        "labels": [dict(RepairRequest.STATUS_CHOICES).get(row["status"], row["status"]) for row in by_status],
        "data": [row["count"] for row in by_status],
    }
    chart_eq = {
        "labels": [row["equipment_type"] for row in by_equipment],
        "data": [row["count"] for row in by_equipment],
    }

    return render(
        request,
        "service/reports.html",
        {
            "by_status": by_status,
            "avg_hours": avg_hours,
            "by_equipment": by_equipment,
            "master_kpi": master_kpi,
            "funnel": funnel,
            "abc_parts": abc_parts,
            "chart_status_json": json.dumps(chart_status),
            "chart_eq_json": json.dumps(chart_eq),
        },
    )


@login_required
def notifications_list(request):
    user = request.user
    role = get_role(user)
    if role == "manager":
        # Менеджер видит системные без target_user + свои
        notifs = Notification.objects.filter(target_user__isnull=True) | Notification.objects.filter(target_user=user)
        notifs = notifs.distinct().order_by("-created_at")[:100]
    else:
        notifs = Notification.objects.filter(target_user=user).order_by("-created_at")[:50]
    return render(request, "service/notifications.html", {"notifications": notifs, "role": role})


@login_required
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    if notif.target_user_id and notif.target_user_id != request.user.id:
        raise PermissionDenied()
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return redirect("notifications_list")


@login_required
def notifications_read_all(request):
    if request.method == "POST":
        Notification.objects.filter(target_user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications_list")


@login_required
def master_calendar(request):
    role = get_role(request.user)
    if role not in ("manager", "master"):
        raise PermissionDenied()

    import json
    from datetime import timedelta, date

    #Диапазон текущая неделя
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    days = [start_of_week + timedelta(days=i) for i in range(7)]

    #Активные заявки с назначенным мастером
    if role == "master":
        active_reqs = RepairRequest.objects.filter(
            assigned_master=request.user,
            status__in=[RepairRequest.STATUS_NEW, RepairRequest.STATUS_IN_WORK, RepairRequest.STATUS_WAIT_PART]
        ).select_related("assigned_master")
    else:
        active_reqs = RepairRequest.objects.filter(
            assigned_master__isnull=False,
            status__in=[RepairRequest.STATUS_NEW, RepairRequest.STATUS_IN_WORK, RepairRequest.STATUS_WAIT_PART]
        ).select_related("assigned_master")

    #Агрегация по мастерам
    masters_load = {}
    for req in active_reqs:
        m = req.assigned_master
        key = m.username
        if key not in masters_load:
            masters_load[key] = {
                "name": m.get_full_name() or m.username,
                "count": 0,
                "requests": [],
            }
        masters_load[key]["count"] += 1
        masters_load[key]["requests"].append({
            "id": req.id,
            "client": req.client_name,
            "equipment": req.equipment_type,
            "status": req.get_status_display(),
            "created": req.created_at.strftime("%d.%m"),
        })

    return render(request, "service/calendar.html", {
        "days": days,
        "today": today,
        "masters_load": masters_load,
        "active_reqs": active_reqs,
        "role": role,
    })
