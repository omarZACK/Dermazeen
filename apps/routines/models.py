from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from apps.shared.enums import (
    RoutineStatusChoices,
    CompletionStatusChoices,
    PhotoTypeChoices,
    ReminderTypeChoices
)
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.recommendations.models import Recommendation
from apps.shared.utils import validate_mood_rating, validate_adherence_rate

User = get_user_model()


class UserRoutine(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User following this routine.")
    )
    recommendation = models.OneToOneField(
        Recommendation,
        on_delete=models.CASCADE,
        help_text=_("Recommendation this routine is based on.")
    )
    started_at = models.DateTimeField(
        help_text=_("Timestamp when the routine was started.")
    )
    routine_status = models.CharField(
        max_length=15,
        choices=RoutineStatusChoices.choices,
        default=RoutineStatusChoices.ACTIVE,
        help_text=_("Current status of the routine.")
    )
    total_days = models.PositiveIntegerField(
        help_text=_("Total number of days in the routine.")
    )
    completed_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of days completed so far.")
    )
    adherence_rate = models.FloatField(
        validators=[validate_adherence_rate],
        default=0.0,
        help_text=_("Adherence rate as a percentage (0.0 - 100.0).")
    )

    def __str__(self):
        return f"Routine #{self.pk} for {self.user.username} ({self.completed_days}/{self.total_days} days)"

    def calculate_adherence_rate(self):
        """Calculate and update adherence rate based on completed days."""
        if self.total_days > 0:
            self.adherence_rate = (self.completed_days / self.total_days)
        else:
            self.adherence_rate = 0.0
        return self.adherence_rate

    class Meta:
        verbose_name = _("User Routine")
        verbose_name_plural = _("User Routines")
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['recommendation']),
            models.Index(fields=['routine_status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['adherence_rate']),
        ]


class RoutineLog(ActiveModel, TimeStampedModel, SoftDeleteModel):
    routine = models.ForeignKey(
        UserRoutine,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text=_("Routine this log entry belongs to.")
    )
    log_date = models.DateField(
        help_text=_("Date for this log entry.")
    )
    morning_completed = models.CharField(
        max_length=15,
        choices=CompletionStatusChoices.choices,
        default=CompletionStatusChoices.NOT_DONE,
        help_text=_("Status of morning routine completion.")
    )
    evening_completed = models.CharField(
        max_length=15,
        choices=CompletionStatusChoices.choices,
        default=CompletionStatusChoices.NOT_DONE,
        help_text=_("Status of evening routine completion.")
    )
    user_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_("User's notes about their routine for this day.")
    )
    mood_rating = models.PositiveIntegerField(
        validators=[validate_mood_rating],
        null=True,
        blank=True,
        help_text=_("User's mood rating for the day (1-10 scale).")
    )
    side_effects = models.TextField(
        null=True,
        blank=True,
        help_text=_("Any side effects experienced during the routine.")
    )
    logged_at = models.DateTimeField(
        help_text=_("Timestamp when this log entry was created.")
    )

    def __str__(self):
        return f"Log for {self.routine.user.username} on {self.log_date}"

    class Meta:
        verbose_name = _("Routine Log")
        verbose_name_plural = _("Routine Logs")
        ordering = ['-log_date']
        unique_together = ('routine', 'log_date')
        indexes = [
            models.Index(fields=['routine']),
            models.Index(fields=['log_date']),
            models.Index(fields=['morning_completed']),
            models.Index(fields=['evening_completed']),
            models.Index(fields=['mood_rating']),
            models.Index(fields=['logged_at']),
        ]


class ProgressPhoto(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User who took this progress photo.")
    )
    routine = models.ForeignKey(
        UserRoutine,
        on_delete=models.CASCADE,
        related_name='progress_photos',
        help_text=_("Routine this progress photo is associated with.")
    )
    image_url = models.URLField(
        help_text=_("URL of the progress photo.")
    )
    notes = models.TextField(
        null=True,
        blank=True,
        help_text=_("User's notes about this progress photo.")
    )
    taken_at = models.DateTimeField(
        help_text=_("Timestamp when the photo was taken.")
    )
    photo_type = models.CharField(
        max_length=15,
        choices=PhotoTypeChoices.choices,
        help_text=_("Type of progress photo (before, during, after).")
    )

    def __str__(self):
        return f"Progress photo for {self.user.username} - {self.photo_type} ({self.taken_at.date()})"

    class Meta:
        verbose_name = _("Progress Photo")
        verbose_name_plural = _("Progress Photos")
        ordering = ['-taken_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['routine']),
            models.Index(fields=['photo_type']),
            models.Index(fields=['taken_at']),
        ]


class Reminder(ActiveModel, TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User receiving this reminder.")
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=ReminderTypeChoices.choices,
        help_text=_("Type of reminder (routine, photo, checkup).")
    )
    message = models.TextField(
        help_text=_("Message content for the reminder.")
    )
    scheduled_time = models.TimeField(
        help_text=_("Time of day when the reminder should be sent.")
    )
    days_of_week = models.JSONField(
        default=list,
        help_text=_("List of weekday numbers when reminder should be sent (0=Monday, 6=Sunday). Example: [0, 2, 4] for Mon, Wed, Fri.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this reminder is currently active.")
    )
    last_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when this reminder was last sent.")
    )
    send_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times this reminder has been sent.")
    )

    def __str__(self):
        return f"Reminder for {self.user.username} - {self.reminder_type} at {self.scheduled_time}"

    class Meta:
        verbose_name = _("Reminder")
        verbose_name_plural = _("Reminders")
        ordering = ['scheduled_time']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['reminder_type']),
            models.Index(fields=['scheduled_time']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_sent']),
        ]