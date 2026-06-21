from django import template

register = template.Library()

STATUS_MAP = {
    "new": "Новая",
    "in_work": "В работе",
    "wait_part": "Ожидает запчасть",
    "done": "Завершена",
}

@register.filter
def status_ru(value):
    if value is None:
        return ""
    return STATUS_MAP.get(str(value), str(value))
