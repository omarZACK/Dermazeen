from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.admin.models import Admin
from apps.shared.models import TimeStampedModel
from apps.shared.utils import validate_license_number
from django.conf import settings
from apps.shared.enums import (
    UserTypeChoices,
    ApprovalStatusChoices
)

class Doctor(TimeStampedModel):
    """
    Doctor profile for medical professionals
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor'
    )

    # Professional information
    license_number = models.CharField(
        _('Medical License Number'),
        max_length=50,
        unique=True,
        validators=[validate_license_number]
    )
    specialization = models.CharField(
        _('Specialization'),
        max_length=100,
        help_text=_('Primary medical specialization')
    )
    qualifications = models.TextField(
        _('Qualifications'),
        help_text=_('Medical qualifications and certifications')
    )

    # Verification and approval
    approval_status = models.CharField(
        _('Approval Status'),
        max_length=15,
        choices=ApprovalStatusChoices.choices,
        default=ApprovalStatusChoices.PENDING
    )
    approved_at = models.DateTimeField(
        _('Approved At'),
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_doctors',
        limit_choices_to={'user__user_type': UserTypeChoices.ADMIN}
    )
    rejection_reason = models.TextField(
        _('Rejection Reason'),
        blank=True,
        help_text=_('Reason for rejection if status is rejected')
    )

    # Availability
    is_available = models.BooleanField(
        _('Available for Consultations'),
        default=True
    )

    # Statistics
    consultation_count = models.PositiveIntegerField(
        _('Total Consultations'),
        default=0
    )
    rating = models.DecimalField(
        _('Average Rating'),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )

    class Meta:
        verbose_name = _('Doctor')
        verbose_name_plural = _('Doctors')
        db_table = 'doctors'
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['specialization']),
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name} - {self.specialization}"
