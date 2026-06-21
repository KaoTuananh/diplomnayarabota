from django.conf import settings
from django.db import models

class Profile(models.Model):
    ROLE_CLIENT = "client"
    ROLE_MASTER = "master"
    ROLE_MANAGER = "manager"

    ROLE_CHOICES = [
        (ROLE_CLIENT, "Клиент"),
        (ROLE_MASTER, "Мастер"),
        (ROLE_MANAGER, "Менеджер"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

