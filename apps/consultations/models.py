from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from apps.accounts.models import Doctor
from apps.shared.enums import (
    ConsultationStatusChoices,
    TestCategoryChoices,
    UrgencyLevelChoices
)
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.analysis.models import SkinAnalysis

# Create your models here

User = get_user_model()

class Consultation(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patient_consultations',
        help_text=_("Patient requesting the consultation.")
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='doctor_consultations',
        help_text=_("Doctor assigned to this consultation.")
    )
    analysis = models.OneToOneField(
        SkinAnalysis,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text=_("Skin analysis that prompted this consultation.")
    )
    requested_at = models.DateTimeField(
        help_text=_("Timestamp when the consultation was requested.")
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Scheduled date and time for the consultation.")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when the consultation was completed.")
    )
    consultation_status = models.CharField(
        max_length=15,
        choices=ConsultationStatusChoices.choices,
        default=ConsultationStatusChoices.REQUESTED,
        help_text=_("Current status of the consultation.")
    )
    user_message = models.TextField(
        help_text=_("Message from the patient describing their concerns.")
    )
    doctor_response = models.TextField(
        null=True,
        blank=True,
        help_text=_("Doctor's response and recommendations.")
    )

    def __str__(self):
        return f"Consultation #{self.pk} - {self.user.username} with Dr. {self.doctor.username}"

    class Meta:
        verbose_name = _("Consultation")
        verbose_name_plural = _("Consultations")
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['doctor']),
            models.Index(fields=['analysis']),
            models.Index(fields=['consultation_status']),
            models.Index(fields=['requested_at']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['completed_at']),
        ]


class MedicalTest(ActiveModel, TimeStampedModel, SoftDeleteModel):
    test_name = models.CharField(
        max_length=200,
        unique=True,
        help_text=_("Unique name of the medical test (e.g., 'Hormone Panel', 'CBC').")
    )
    description = models.TextField(
        help_text=_("Description of what the test is and why it's used.")
    )
    test_category = models.CharField(
        max_length=15,
        choices=TestCategoryChoices.choices,
        help_text=_("Category of the medical test.")
    )
    preparation_instructions = models.TextField(
        null=True,
        blank=True,
        help_text=_("Instructions for test preparation (fasting, medications to stop, etc.).")
    )
    requires_lab = models.BooleanField(
        default=True,
        help_text=_("Whether this test requires a laboratory visit.")
    )

    def __str__(self):
        return self.test_name

    class Meta:
        verbose_name = _("Medical Test")
        verbose_name_plural = _("Medical Tests")
        ordering = ['test_name']
        indexes = [
            models.Index(fields=['test_category']),
            models.Index(fields=['requires_lab']),
        ]


class RecommendedTest(ActiveModel, TimeStampedModel, SoftDeleteModel):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='recommended_tests',
        help_text=_("Consultation where this test was recommended.")
    )
    test = models.ForeignKey(
        MedicalTest,
        on_delete=models.CASCADE,
        help_text=_("Medical test that was recommended.")
    )
    doctor_notes = models.TextField(
        help_text=_("Doctor's notes explaining why this test was suggested.")
    )
    urgency_level = models.CharField(
        max_length=15,
        choices=UrgencyLevelChoices.choices,
        default=UrgencyLevelChoices.LOW,
        help_text=_("Urgency level of this test recommendation.")
    )
    is_completed = models.BooleanField(
        default=False,
        help_text=_("Whether this test has been completed by the patient.")
    )
    recommended_at = models.DateTimeField(
        help_text=_("Timestamp when this test was recommended.")
    )

    def __str__(self):
        return f"{self.test.test_name} recommended for Consultation #{self.consultation.pk}"

    class Meta:
        verbose_name = _("Recommended Test")
        verbose_name_plural = _("Recommended Tests")
        ordering = ['-recommended_at']
        unique_together = ('consultation', 'test')
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['test']),
            models.Index(fields=['urgency_level']),
            models.Index(fields=['is_completed']),
            models.Index(fields=['recommended_at']),
        ]