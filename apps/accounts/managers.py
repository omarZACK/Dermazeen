from django.contrib.auth.models import BaseUserManager
from django.db import transaction

from apps.shared.enums import UserTypeChoices, AdminRoleChoices


class UserManager(BaseUserManager):
    def create_user(self, email, phone=None, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)

        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone=None, password=None, **extra_fields):
        with transaction.atomic():
            from apps.admin.models import Admin
            extra_fields.setdefault('is_active', True)
            extra_fields.setdefault('user_type', UserTypeChoices.ADMIN)
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_superuser', True)

            if not extra_fields.get('is_staff'):
                raise ValueError('Superuser must have is_staff=True.')
            if not extra_fields.get('is_superuser'):
                raise ValueError('Superuser must have is_superuser=True.')

            user = self.create_user(email, phone, password, **extra_fields)
            Admin.objects.create(user=user, admin_role=AdminRoleChoices.SUPER_ADMIN)
            return user
