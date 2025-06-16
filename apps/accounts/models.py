from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator
from .managers import UserManager
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.shared.enums import (
    GenderChoices, UserTypeChoices, SkinTypeChoices,
    ApprovalStatusChoices, AdminRoleChoices
)
from apps.shared.validators import validate_phone_number, validate_license_number
from apps.shared.utils import generate_upload_path


class User(AbstractUser, TimeStampedModel, ActiveModel, SoftDeleteModel):
    """
    Custom User model extending AbstractUser
    """
    # Remove username field and use email as unique identifier
    username = None

    # Core fields
    email = models.EmailField(
        _('Email Address'),
        unique=True,
        validators=[EmailValidator()],
        error_messages={'unique': _('A user with this email already exists.')}
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
    birth_date = models.DateField(_('Birth Date'), null=True, blank=True)
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
        default=UserTypeChoices.PATIENT
    )
    email_verified = models.BooleanField(_('Email Verified'), default=False)
    phone_verified = models.BooleanField(_('Phone Verified'), default=False)

    # Profile image
    profile_image = models.ImageField(
        _('Profile Image'),
        upload_to=generate_upload_path,
        null=True,
        blank=True
    )
    is_staff = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

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


class Admin(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin')
    admin_role = models.CharField(max_length=20, choices=AdminRoleChoices.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.admin_role}"


class PatientProfile(TimeStampedModel):
    """
    Extended profile information for patient users
    """
    user = models.OneToOneField(
        User,
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

    # Lifestyle factors stored as JSON
    lifestyle_factors = models.JSONField(
        _('Lifestyle Factors'),
        default=dict,
        blank=True,
        help_text=_('JSON object containing lifestyle information')
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

        # Check lifestyle factors
        if self.lifestyle_factors:
            completed_fields += 1
        total_fields += 1

        percentage = int((completed_fields / total_fields) * 100)
        self.completion_percentage = percentage
        self.profile_completed = percentage >= 80
        return percentage

    def update_lifestyle_factor(self, key, value):
        """Update a specific lifestyle factor"""
        if not self.lifestyle_factors:
            self.lifestyle_factors = {}
        self.lifestyle_factors[key] = value
        self.save()

    def get_lifestyle_factor(self, key, default=None):
        """Get a specific lifestyle factor"""
        return self.lifestyle_factors.get(key, default) if self.lifestyle_factors else default


class Doctor(TimeStampedModel, ActiveModel):
    """
    Doctor profile for medical professionals
    """
    user = models.OneToOneField(
        User,
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
        limit_choices_to={'user_type': UserTypeChoices.ADMIN}
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
        blank=True
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
