from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Admin
from apps.recommendations.models import Recommendation
from apps.shared.enums import (
    ActionTypeChoices,
    AuditStatusChoices
)
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel

User = get_user_model()


class SystemLog(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User who performed the action (null for system actions).")
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionTypeChoices.choices,
        help_text=_("Type of action performed (CREATE, UPDATE, DELETE, LOGIN, etc.).")
    )
    table_affected = models.CharField(
        max_length=100,
        help_text=_("Name of the database table/model that was affected.")
    )
    record_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("ID of the specific record that was affected.")
    )
    old_values = models.JSONField(
        null=True,
        blank=True,
        help_text=_("JSON representation of the record's values before the change.")
    )
    new_values = models.JSONField(
        null=True,
        blank=True,
        help_text=_("JSON representation of the record's values after the change.")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the action was performed.")
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address from which the action was performed.")
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text=_("User agent string from the request.")
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text=_("Session key for tracking user sessions.")
    )
    additional_data = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Additional context data for the action.")
    )

    def __str__(self):
        user_info = self.user.username if self.user else "System"
        return f"{self.action_type} on {self.table_affected} by {user_info} at {self.timestamp}"

    class Meta:
        verbose_name = _("System Log")
        verbose_name_plural = _("System Logs")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action_type']),
            models.Index(fields=['table_affected']),
            models.Index(fields=['record_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['table_affected', 'record_id']),
        ]


class RecommendationAudit(ActiveModel, TimeStampedModel, SoftDeleteModel):
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE,
        related_name='audits',
        help_text=_("Recommendation being audited.")
    )
    reviewed_by = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        help_text=_("Staff member who reviewed this recommendation.")
    )
    reviewed_at = models.DateTimeField(
        help_text=_("Timestamp when the review was conducted.")
    )
    audit_status = models.CharField(
        max_length=15,
        choices=AuditStatusChoices.choices,
        help_text=_("Status of the audit review.")
    )
    reviewer_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_("Reviewer's notes about the recommendation quality and appropriateness.")
    )
    safety_flags = models.TextField(
        null=True,
        blank=True,
        help_text=_("Any safety concerns or flags identified during review.")
    )
    compliance_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Compliance score assigned during audit (1-100).")
    )
    follow_up_required = models.BooleanField(
        default=False,
        help_text=_("Whether this recommendation requires follow-up review.")
    )
    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date when follow-up review should be conducted.")
    )

    def __str__(self):
        reviewer = self.reviewed_by.user.get_full_name if self.reviewed_by else "Unknown"
        return f"Audit of Recommendation #{self.recommendation.pk} by {reviewer}"

    class Meta:
        verbose_name = _("Recommendation Audit")
        verbose_name_plural = _("Recommendation Audits")
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['recommendation']),
            models.Index(fields=['reviewed_by']),
            models.Index(fields=['audit_status']),
            models.Index(fields=['reviewed_at']),
            models.Index(fields=['follow_up_required']),
            models.Index(fields=['follow_up_date']),
            models.Index(fields=['compliance_score']),
        ]


class AuditTrail(ActiveModel, TimeStampedModel, SoftDeleteModel):
    """
    Generic audit trail model for tracking changes across multiple models.
    This can be used as a base for automatic audit logging.
    """
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        help_text=_("Content type of the model being audited.")
    )
    object_id = models.PositiveIntegerField(
        help_text=_("ID of the object being audited.")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User who made the change.")
    )
    action = models.CharField(
        max_length=20,
        choices=ActionTypeChoices.choices,
        help_text=_("Action performed on the object.")
    )
    changes = models.JSONField(
        help_text=_("JSON representation of the changes made.")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the change was made.")
    )

    def __str__(self):
        return f"{self.action} on {self.content_type.model} #{self.object_id}"

    class Meta:
        verbose_name = _("Audit Trail")
        verbose_name_plural = _("Audit Trails")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
        ]