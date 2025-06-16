from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import PatientProfile
from apps.analysis.models import SkinCondition
from apps.shared.enums import SeverityLevelChoices
from apps.shared.models import TimeStampedModel,ActiveModel

User = get_user_model()

class Allergy(TimeStampedModel):
    """
    Model representing different types of allergies/allergens
    """
    allergy_id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(2)],
        help_text=_("Name of the allergy/allergen")
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_("Optional description of the allergy")
    )

    class Meta:
        db_table = 'allergy'
        verbose_name = _('Allergy')
        verbose_name_plural = _('Allergies')
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """Custom validation"""
        if self.name:
            self.name = self.name.strip().title()


class UserAllergy(TimeStampedModel,ActiveModel):
    """
    Model representing user's specific allergies
    Links users to their allergies with additional notes
    """
    profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='user_allergies',
        help_text=_("Patient profile this allergy belongs to")
    )
    allergy = models.ForeignKey(
        'Allergy',
        on_delete=models.CASCADE,
        related_name='user_allergies',
        help_text=_("The allergy/allergen")
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_("Additional notes about this specific allergy")
    )
    severity_level = models.CharField(
        max_length=20,
        choices=SeverityLevelChoices.choices,
        default=SeverityLevelChoices.MILD,
        help_text=_("Severity level of the allergic reaction")
    )
    diagnosed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When this allergy was diagnosed")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this allergy is active"),
        verbose_name=_("Is Active")
    )

    class Meta:
        db_table = 'user_allergy'
        verbose_name = _('User Allergy')
        verbose_name_plural = _('User Allergies')
        unique_together = ['profile', 'allergy']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.profile.user.get_full_name} - {self.allergy.name}"

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency"""
        super().save(*args, **kwargs)

class MedicalHistory(TimeStampedModel,ActiveModel):
    """
    Model representing user's medical history related to skin conditions
    """

    history_id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='medical_histories',
        help_text=_("Patient profile this medical history belongs to")
    )
    condition = models.ForeignKey(
        SkinCondition,
        on_delete=models.CASCADE,
        related_name='medical_histories',
        help_text=_("The skin condition")
    )
    is_chronic = models.BooleanField(
        default=False,
        help_text=_("Whether this condition is chronic for this user")
    )
    diagnosed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When this condition was diagnosed")
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_("Additional notes about this medical history")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this medical history record is active"),
        verbose_name=_("Is Active")
    )

    class Meta:
        db_table = 'medical_history'
        verbose_name = _('Medical History')
        verbose_name_plural = _('Medical Histories')
        unique_together = ['profile', 'condition']
        ordering = ['-diagnosed_at', '-created_at']

    def __str__(self):
        return f"{self.profile.user.get_full_name} - {self.condition.condition_name}"

    def clean(self):
        """Custom validation"""
        from django.core.exceptions import ValidationError

        # If condition is chronic, the user's record should also be chronic
        if self.condition.is_chronic and not self.is_chronic:
            raise ValidationError(_("This condition is inherently chronic."))

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency"""
        self.full_clean()
        super().save(*args, **kwargs)