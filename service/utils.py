import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from service.models import StatusHistory, RepairRequest, Notification

logger = logging.getLogger(__name__)


def get_role(user):
    if not user.is_authenticated:
        return None
    if hasattr(user, "profile"):
        return user.profile.role
    return None


def notify(kind, text, target_user=None, repair_request=None):
    #Сохранить уведомление в БД и залогировать
    logger.info(f"[NOTIFY:{kind}] {text}")
    try:
        Notification.objects.create(
            kind=kind.lower() if kind.lower() in dict(Notification.KIND_CHOICES) else Notification.KIND_OTHER,
            text=text,
            target_user=target_user,
            repair_request=repair_request,
        )
    except Exception as e:
        logger.warning(f"Не удалось сохранить уведомление: {e}")


def send_status_email(repair_request, new_status):
   #отправка email клиенту при смене статуса,если указан email
    if not repair_request.client_email:
        return
    status_labels = {
        RepairRequest.STATUS_NEW: "Новая",
        RepairRequest.STATUS_IN_WORK: "Взята в работу",
        RepairRequest.STATUS_WAIT_PART: "Ожидает запчасть",
        RepairRequest.STATUS_DONE: "Завершена",
    }
    label = status_labels.get(new_status, new_status)
    subject = f"Статус вашей заявки #{repair_request.id} изменён"
    message = (
        f"Здравствуйте, {repair_request.client_name}!\n\n"
        f"Статус вашей заявки #{repair_request.id} изменён на: {label}\n"
        f"Оборудование: {repair_request.equipment_type}\n\n"
        f"С уважением,\nRepairDesk"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@repairdesk.local"),
            recipient_list=[repair_request.client_email],
            fail_silently=True,
        )
        logger.info(f"Email отправлен клиенту {repair_request.client_email} по заявке #{repair_request.id}")
    except Exception as e:
        logger.warning(f"Не удалось отправить email: {e}")


def change_status(request_obj: RepairRequest, new_status: str, changed_by, note: str = ""):
    old = request_obj.status
    if old == new_status:
        return

    request_obj.status = new_status

    if new_status == RepairRequest.STATUS_IN_WORK and request_obj.started_at is None:
        request_obj.started_at = timezone.now()

    if new_status == RepairRequest.STATUS_DONE and request_obj.completed_at is None:
        request_obj.completed_at = timezone.now()

    request_obj.save()

    StatusHistory.objects.create(
        request=request_obj,
        old_status=old,
        new_status=new_status,
        changed_by=changed_by,
        note=note or "",
    )

    status_labels = dict(RepairRequest.STATUS_CHOICES)
    text = (
        f"Заявка #{request_obj.id} ({request_obj.client_name}): "
        f"статус изменён с «{status_labels.get(old, old)}» на «{status_labels.get(new_status, new_status)}»"
    )
    notify(Notification.KIND_STATUS, text, repair_request=request_obj)

    #Уведомление мастеру
    if request_obj.assigned_master:
        notify(
            Notification.KIND_STATUS,
            text,
            target_user=request_obj.assigned_master,
            repair_request=request_obj,
        )

    #Email клиенту
    send_status_email(request_obj, new_status)


def assign_master(request_obj: RepairRequest, master_user, changed_by):
    old_master = request_obj.assigned_master.username if request_obj.assigned_master else "—"
    new_master = master_user.username if master_user else "—"
    request_obj.assigned_master = master_user
    request_obj.save(update_fields=["assigned_master", "updated_at"])

    text = f"Заявка #{request_obj.id}: мастер изменён с {old_master} на {new_master}"
    notify(Notification.KIND_ASSIGN, text, repair_request=request_obj)

    if master_user:
        notify(
            Notification.KIND_ASSIGN,
            f"Вам назначена заявка #{request_obj.id} ({request_obj.equipment_type}, {request_obj.client_name})",
            target_user=master_user,
            repair_request=request_obj,
        )
