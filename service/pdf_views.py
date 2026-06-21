#PDF-генерация для заявок и отчётов
import io
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import os

from service.models import RepairRequest
from service.utils import get_role

#кириллический шрифт
def _register_font():
    #DejaVuSans из папки проекта
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled      = os.path.join(base, "static", "fonts", "DejaVuSans.ttf")
    bundled_bold = os.path.join(base, "static", "fonts", "DejaVuSans-Bold.ttf")
    if os.path.exists(bundled):
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", bundled))
            if os.path.exists(bundled_bold):
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bundled_bold))
            return "DejaVuSans", "DejaVuSans-Bold"
        except Exception:
            pass
    #cистемные пути как запасной вариант
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "Arial"),
        ("/Library/Fonts/Arial.ttf", "Arial"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name, name
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"

FONT_NAME, FONT_BOLD = _register_font()


def _styles():
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "cyrillic_normal",
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
    )
    title = ParagraphStyle(
        "cyrillic_title",
        fontName=FONT_BOLD,
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    heading = ParagraphStyle(
        "cyrillic_heading",
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        spaceBefore=10,
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "cyrillic_small",
        fontName=FONT_NAME,
        fontSize=8,
        leading=12,
        textColor=colors.grey,
    )
    return normal, title, heading, small


def _status_label(status):
    return dict(RepairRequest.STATUS_CHOICES).get(status, status)


@login_required
def repair_request_pdf(request, pk):
    obj = get_object_or_404(
        RepairRequest.objects.select_related("assigned_master", "created_by"),
        pk=pk
    )
    role = get_role(request.user)
    if role == "client" and obj.created_by_id != request.user.id:
        raise PermissionDenied()
    if role == "master" and obj.assigned_master_id != request.user.id:
        raise PermissionDenied()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    normal, title_style, heading_style, small_style = _styles()
    elements = []

    # Заголовок
    elements.append(Paragraph(f"Наряд-заказ № {obj.id}", title_style))
    elements.append(Paragraph(
        f"Создан: {obj.created_at.strftime('%d.%m.%Y %H:%M')}  |  Статус: {_status_label(obj.status)}",
        small_style
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 0.3 * cm))

    # Данные клиента
    elements.append(Paragraph("Клиент", heading_style))
    client_data = [
        ["Имя:", obj.client_name or "—"],
        ["Телефон:", obj.client_phone or "—"],
        ["Email:", obj.client_email or "—"],
    ]
    t = Table(client_data, colWidths=[4 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)

    # Оборудование
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("Оборудование", heading_style))
    eq_data = [
        ["Тип:", obj.equipment_type or "—"],
        ["Серийный №:", obj.serial_number or "—"],
        ["Расположение:", obj.office_location or "—"],
    ]
    t2 = Table(eq_data, colWidths=[4 * cm, 13 * cm])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t2)

    # Проблема
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("Описание проблемы", heading_style))
    elements.append(Paragraph(obj.problem_description or "—", normal))

    # Назначенный мастер
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("Исполнитель", heading_style))
    master_name = obj.assigned_master.get_full_name() or obj.assigned_master.username if obj.assigned_master else "—"
    elements.append(Paragraph(master_name, normal))

    # Журнал работ
    work_logs = list(obj.work_logs.select_related("master").order_by("work_date"))
    if work_logs:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Журнал выполненных работ", heading_style))
        wl_data = [["Дата", "Мастер", "Часов", "Описание"]]
        for wl in work_logs:
            wl_data.append([
                wl.work_date.strftime("%d.%m.%Y"),
                wl.master.get_full_name() or wl.master.username,
                str(int(round(float(wl.hours)))),
                wl.description[:100],
            ])
        total_hours = sum(float(wl.hours) for wl in work_logs)
        wl_data.append(["", "Итого:", str(int(round(total_hours))), ""])
        tw = Table(wl_data, colWidths=[2.5 * cm, 4 * cm, 2 * cm, 8.5 * cm])
        tw.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(tw)

    # Использованные запчасти
    usages = list(obj.part_usages.select_related("part").order_by("used_at"))
    if usages:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Использованные запчасти", heading_style))
        pu_data = [["Артикул", "Название", "Кол-во", "Цена за ед.", "Сумма"]]
        total_cost = 0
        for pu in usages:
            line = float(pu.quantity) * float(pu.part.unit_cost)
            total_cost += line
            pu_data.append([
                pu.part.sku,
                pu.part.name,
                str(pu.quantity),
                f"{pu.part.unit_cost:.2f} ₽",
                f"{line:.2f} ₽",
            ])
        pu_data.append(["", "", "", "Итого:", f"{total_cost:.2f} ₽"])
        tp = Table(pu_data, colWidths=[3 * cm, 6 * cm, 2 * cm, 3 * cm, 3 * cm])
        tp.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(tp)

    # Подпись
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.3 * cm))
    sig_data = [
        ["Клиент: ___________________________", "Мастер: ___________________________"],
        ["Дата выдачи: __________________", "Подпись: ___________________________"],
    ]
    ts = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    ts.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(ts)

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename=f"repair_{obj.id}.pdf", content_type="application/pdf")


@login_required
def reports_pdf(request):
    role = get_role(request.user)
    if role != "manager":
        raise PermissionDenied()

    from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
    from django.contrib.auth.models import User

    by_status = list(RepairRequest.objects.values("status").annotate(count=Count("id")).order_by("status"))
    duration_expr = ExpressionWrapper(F("completed_at") - F("created_at"), output_field=DurationField())
    avg_duration = (
        RepairRequest.objects.filter(status=RepairRequest.STATUS_DONE, completed_at__isnull=False)
        .annotate(d=duration_expr)
        .aggregate(avg=Avg("d"))
        .get("avg")
    )
    avg_hours = round(avg_duration.total_seconds() / 3600, 2) if avg_duration else None

    # По оборудованию
    by_eq = list(
        RepairRequest.objects.values("equipment_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # KPI мастеров
    from django.db.models import Sum
    from service.models import WorkLog
    master_kpi = list(
        WorkLog.objects.values("master__username", "master__first_name", "master__last_name")
        .annotate(total_hours=Sum("hours"), jobs=Count("request_id", distinct=True))
        .order_by("-total_hours")[:10]
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    normal, title_style, heading_style, small_style = _styles()
    elements = []

    elements.append(Paragraph("Отчёт руководителя", title_style))
    elements.append(Paragraph(
        f"Сформирован: {timezone.now().strftime('%d.%m.%Y %H:%M')}",
        small_style
    ))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))

    # Статусы
    elements.append(Paragraph("Заявки по статусам", heading_style))
    status_data = [["Статус", "Количество"]]
    total_req = 0
    for row in by_status:
        status_data.append([_status_label(row["status"]), str(row["count"])])
        total_req += row["count"]
    status_data.append(["Всего:", str(total_req)])
    t1 = Table(status_data, colWidths=[10*cm, 7*cm])
    t1.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t1)

    if avg_hours:
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f"Среднее время ремонта: {avg_hours} ч.", normal))

    # Топ оборудования
    if by_eq:
        elements.append(Paragraph("Топ типов оборудования", heading_style))
        eq_data = [["Тип оборудования", "Заявок"]]
        for row in by_eq:
            eq_data.append([row["equipment_type"], str(row["count"])])
        t2 = Table(eq_data, colWidths=[12*cm, 5*cm])
        t2.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t2)

    # KPI мастеров
    if master_kpi:
        elements.append(Paragraph("KPI мастеров", heading_style))
        kpi_data = [["Мастер", "Заявок", "Часов"]]
        for row in master_kpi:
            name = f"{row['master__first_name']} {row['master__last_name']}".strip() or row["master__username"]
            kpi_data.append([name, str(row["jobs"]), str(int(round(float(row["total_hours"] or 0))))])
        t3 = Table(kpi_data, colWidths=[9*cm, 3.5*cm, 4.5*cm])
        t3.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t3)

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename="reports.pdf", content_type="application/pdf")
