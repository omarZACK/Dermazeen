from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from apps.shared.enums import (
    AnalysisStatusChoices,
    ConditionCategoryChoices,
    SeverityLevelChoices
)
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.shared.validators import validate_confidence_score

User = get_user_model()

# Create your models here.

class SkinAnalysis(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User who submitted the image for analysis.")
    )
    image_url = models.URLField(
        help_text=_("URL of the uploaded skin image.")
    )
    image_metadata = models.JSONField(
        help_text=_("JSON data containing image resolution, lighting, etc.")
    )
    analyzed_at = models.DateTimeField(
        help_text=_("Timestamp when the analysis was performed.")
    )
    analysis_status = models.CharField(
        max_length=10,
        choices=AnalysisStatusChoices.choices,
        help_text=_("Status of the analysis process.")
    )
    confidence_score = models.FloatField(
        validators=[validate_confidence_score],
        help_text=_("Overall confidence score for the analysis.")
    )

    def __str__(self):
        return f"Analysis #{self.pk} for User {self.user_id}"

    class Meta:
        verbose_name = _("Skin Analysis")
        verbose_name_plural = _("Skin Analyses")
        ordering = ['-analyzed_at']
        unique_together = ('user', 'image_url')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['analysis_status']),
            models.Index(fields=['analyzed_at']),
            models.Index(fields=['confidence_score']),
        ]


class SkinCondition(ActiveModel, TimeStampedModel, SoftDeleteModel):
    condition_name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique name of the skin condition.")
    )
    description = models.TextField(
        help_text=_("Detailed description of the skin condition.")
    )
    category = models.CharField(
        max_length=20,
        choices=ConditionCategoryChoices.choices,
        help_text=_("Category under which this condition falls.")
    )
    is_chronic = models.BooleanField(
        default=False,
        help_text=_("Whether this condition is chronic.")
    )
    requires_medical_attention = models.BooleanField(
        default=False,
        help_text=_("Whether this condition requires medical attention.")
    )

    def __str__(self):
        return self.condition_name

    class Meta:
        verbose_name = _("Skin Condition")
        verbose_name_plural = _("Skin Conditions")
        ordering = ['condition_name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_chronic']),
            models.Index(fields=['requires_medical_attention']),
        ]


class DetectedCondition(ActiveModel, TimeStampedModel, SoftDeleteModel):
    analysis = models.ForeignKey(
        SkinAnalysis,
        on_delete=models.CASCADE,
        help_text=_("Associated skin analysis record.")
    )
    condition = models.ForeignKey(
        SkinCondition,
        on_delete=models.CASCADE,
        help_text=_("Detected skin condition.")
    )
    severity_level = models.CharField(
        max_length=10,
        choices=SeverityLevelChoices.choices,
        help_text=_("Severity level of the detected condition.")
    )
    confidence_score = models.FloatField(
        validators=[validate_confidence_score],
        help_text=_("Confidence score for the condition detection.")
    )
    detected_areas = models.TextField(
        help_text=_("Textual representation of affected areas (e.g., coordinates or labels).")
    )
    notes = models.TextField(
        help_text=_("AI-generated notes about this detection.")
    )

    def __str__(self):
        return f"{self.condition} in Analysis #{self.analysis.pk}"

    class Meta:
        verbose_name = _("Detected Condition")
        verbose_name_plural = _("Detected Conditions")
        ordering = ['-created_at']
        unique_together = ('analysis', 'condition')
        indexes = [
            models.Index(fields=['severity_level']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['analysis', 'condition']),
        ]