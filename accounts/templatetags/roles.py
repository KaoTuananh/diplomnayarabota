from django import template

register = template.Library()

@register.simple_tag
def user_role(user):
    if not user or not user.is_authenticated:
        return ""
    if hasattr(user, "profile"):
        return user.profile.role or ""
    return ""
