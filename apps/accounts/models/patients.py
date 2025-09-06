from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.shared.enums import SkinTypeChoices, GenderChoices,SunExposureChoices,StressLevelChoices
from apps.shared.models import TimeStampedModel
from django.conf import settings

class PatientProfile(TimeStampedModel):
    """
    Extended profile information for patient users
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='patient_profile'
    )

    # Skin information
    skin_type = models.CharField(
        _('Skin Type'),
        max_length=15,
        choices=SkinTypeChoices.choices,
        null=True,
        blank=True
    )

    # Health information
    is_pregnant = models.BooleanField(
        _('Currently Pregnant'),
        default=False,
        help_text=_('Important for product safety recommendations')
    )

    sun_exposure = models.CharField(
        _('Sun Exposure'),
        max_length=20,
        choices=SunExposureChoices.choices,
        default=SunExposureChoices.MINIMAL
    )

    stress_level = models.CharField(
        _('Stress Level'),
        max_length=20,
        choices=StressLevelChoices.choices,
        default=StressLevelChoices.VERY_LOW
    )

    sleep_hours = models.PositiveSmallIntegerField(
        _('Sleep Hours'),
        help_text=_('Average daily sleep hours (0–24)'),
        default=6
    )

    # Profile completion tracking
    profile_completed = models.BooleanField(
        _('Profile Completed'),
        default=False
    )
    completion_percentage = models.PositiveSmallIntegerField(
        _('Completion Percentage'),
        default=0
    )

    class Meta:
        verbose_name = _('Patient Profile')
        verbose_name_plural = _('Patient Profiles')
        db_table = 'patient_profiles'

    def __str__(self):
        return f"Profile of {self.user.get_full_name}"

    def calculate_completion_percentage(self):
        """Calculate profile completion percentage"""
        fields_to_check = [
            'skin_type', 'is_pregnant', 'user.birth_date',
            'user.gender', 'user.phone'
        ]
        if self.user.gender == GenderChoices.MALE:
            fields_to_check.remove('is_pregnant')
        completed_fields = 0
        total_fields = len(fields_to_check)

        for field in fields_to_check:
            if '.' in field:
                # Handle nested field access
                obj = self
                for attr in field.split('.'):
                    obj = getattr(obj, attr, None)
                    if obj is None:
                        break
                if obj:
                    completed_fields += 1
            else:
                if getattr(self, field):
                    completed_fields += 1
        total_fields += 1

        percentage = int((completed_fields / total_fields) * 100)
        self.completion_percentage = percentage
        self.profile_completed = percentage >= 80
        return percentage