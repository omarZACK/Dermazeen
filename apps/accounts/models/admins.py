from django.db import models
from apps.shared.enums import AdminRoleChoices
from apps.shared.models import TimeStampedModel
from django.conf import settings

class Admin(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin')
    admin_role = models.CharField(max_length=20, choices=AdminRoleChoices.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.admin_role}"