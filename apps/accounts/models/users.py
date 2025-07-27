from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from apps.accounts.managers import UserManager
from apps.shared.models import TimeStampedModel, SoftDeleteModel
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.shared.validators import validate_phone_number
from apps.shared.enums import (
    GenderChoices, UserTypeChoices
)
from apps.shared.utils import generate_upload_path

class User(AbstractUser, TimeStampedModel, SoftDeleteModel):
    """
    Custom User model extending AbstractUser
    """
    username = None
    # Core fields
    email = models.EmailField(
        _('Email Address'),
        unique=True,
        validators=[EmailValidator()],
        error_messages={'unique': _('A user with this email already exists.')},
        null=False,
        blank=False
    )
    phone = models.CharField(
        _('Phone Number'),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_phone_number]
    )

    # Personal information
    first_name = models.CharField(_('First Name'), max_length=150)
    last_name = models.CharField(_('Last Name'), max_length=150)
    birth_date = models.DateField(_('Birth Date'), null=False, blank=False)
    gender = models.CharField(
        _('Gender'),
        max_length=1,
        choices=GenderChoices.choices,
        null=False,
        blank=False,
    )

    # User type and verification
    user_type = models.CharField(
        _('User Type'),
        max_length=10,
        choices=UserTypeChoices.choices,
        null=True,
        blank=True,
    )
    phone_verified = models.BooleanField(_('Phone Verified'), default=False)

    # Profile image
    profile_image = models.ImageField(
        _('Profile Image'),
        upload_to=generate_upload_path,
        null=True,
        blank=True
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name','birth_date']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['user_type']),
        ]

    @property
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip()
    def get_short_name(self):
        """Return full name"""
        return f"{self.first_name}".strip()

    def __str__(self):
        return f"{self.get_full_name} ({self.email})"

    @property
    def age(self):
        """Calculate user age"""
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def can_receive_recommendations(self):
        """Check if user can receive AI recommendations"""
        return self.user_type == UserTypeChoices.PATIENT and self.is_active

    def is_doctor(self):
        """Check if user is a doctor"""
        return self.user_type == UserTypeChoices.DOCTOR

    def is_admin_user(self):
        """Check if user is an admin"""
        return self.user_type == UserTypeChoices.ADMIN

