import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from apps.shared.models import TimeStampedModel


class EmailVerificationCode(TimeStampedModel):
    """
    Email verification model with both UUID token (for URLs) and verification code (for user entry)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='email_verifications'
    )
    token = models.UUIDField(
        _('URL Token'),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_('UUID token used in verification URLs')
    )
    verification_code = models.CharField(
        _('Verification Code'),
        max_length=6,
        unique=True,
        help_text=_('6-digit code that user enters for verification')
    )
    expires_at = models.DateTimeField(
        _('Expires At'),
        null=True,
        blank=True
    )
    is_used = models.BooleanField(
        _('Is Used'),
        default=False
    )

    def save(self, *args, **kwargs):
        """Generate tokens and set expiration date."""
        if not self.token:
            self.token = uuid.uuid4()
        if not self.verification_code:
            self.verification_code = self.generate_unique_code()

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_code():
        """Generate a unique 6-digit verification code"""
        while True:
            code = get_random_string(length=6,allowed_chars="1234567890ZXCVBNMASDFGHJKLQWERTYUIOP")

            # Check if code already exists
            if not EmailVerificationCode.objects.filter(
                    verification_code=code,
                    is_used=False,
                    expires_at__gt=timezone.now()
            ).exists():
                return code

    def is_expired(self):
        """Check if verification token is expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if verification token is valid"""
        return not self.is_expired() and not self.is_used and not self.user.is_active

    class Meta:
        verbose_name = _('Email Verification')
        verbose_name_plural = _('Email Verifications')
        db_table = 'verification_code'
        indexes = [
            models.Index(fields=['user', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Verification for {self.user.email} - Code: {self.verification_code} - {'Used' if self.is_used else 'Active'}"