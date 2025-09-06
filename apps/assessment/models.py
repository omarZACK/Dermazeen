from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from apps.shared.enums import (
    AssessmentStatusChoices,
    QuestionTypeChoices, QuestionPhase
)
from apps.shared.mixins import OrderedMixin
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.analysis.models import SkinAnalysis, SkinCondition

# Create your models here.

User = get_user_model()

class Assessment(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User taking the assessment.")
    )
    analysis = models.OneToOneField(
        SkinAnalysis,
        on_delete=models.CASCADE,
        help_text=_("Associated skin analysis record.")
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the assessment was started.")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when the assessment was completed.")
    )
    current_phase = models.CharField(
        max_length=30,
        choices=QuestionPhase.choices,
        default=QuestionPhase.SCREENING
    )
    assessment_status = models.CharField(
        max_length=20,
        choices=AssessmentStatusChoices.choices,
        default=AssessmentStatusChoices.STARTED,
        help_text=_("Current status of the assessment.")
    )

    def __str__(self):
        return f"Assessment #{self.pk} for User {self.user.get_full_name}"

    class Meta:
        verbose_name = _("Assessment")
        verbose_name_plural = _("Assessments")
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['analysis']),
            models.Index(fields=['assessment_status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]

class QuestionTemplate(ActiveModel, TimeStampedModel, SoftDeleteModel, OrderedMixin):
    question_name = models.CharField(
        max_length=40,
        null=False,
        blank=False,
        unique=True,
        help_text=_("Question title.")
    )
    question_text = models.TextField(
        help_text=_("The text of the question to be displayed.")
    )
    question_type = models.CharField(
        max_length=20,
        choices=QuestionTypeChoices.choices,
        help_text=_("Type of question (single choice, multiple choice, etc.).")
    )
    options = models.JSONField(
        null=True,
        blank=True,
        help_text=_("JSON array of choices or parameters for UI rendering.")
    )

    condition_triggers = models.ManyToManyField(
        SkinCondition,
        related_name="condition_triggers",
        help_text=_("Conditions that trigger this question (e.g. acne -> hormonal questions).")
    )

    def __str__(self):
        return f"Question {self.pk}: {self.question_text[:50]}..."

    class Meta:
        verbose_name = _("Question Template")
        verbose_name_plural = _("Question Templates")
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['question_type']),
            models.Index(fields=['display_order']),
            models.Index(fields=['is_active']),
        ]

class AssessmentResponse(ActiveModel, TimeStampedModel, SoftDeleteModel):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_("Assessment this response belongs to.")
    )
    question = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.CASCADE,
        help_text=_("Question that was answered.")
    )
    answer_value = models.TextField(
        help_text=_("The user's answer to the question.")
    )
    answered_at = models.DateTimeField(
        help_text=_("Timestamp when the question was answered.")
    )

    def __str__(self):
        return f"Response to Question {self.question.pk} in Assessment {self.assessment.pk}"

    class Meta:
        verbose_name = _("Assessment Response")
        verbose_name_plural = _("Assessment Responses")
        ordering = ['-answered_at']
        unique_together = ('assessment', 'question')
        indexes = [
            models.Index(fields=['assessment']),
            models.Index(fields=['question']),
            models.Index(fields=['answered_at']),
            models.Index(fields=['assessment', 'question']),
        ]