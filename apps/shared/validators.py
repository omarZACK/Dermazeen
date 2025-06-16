from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_phone_number(phone):
    """
    Validate phone number format
    """
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, phone):
        raise ValidationError(_('Enter a valid phone number.'))


def validate_license_number(license_number):
    """
    Validate medical license number format
    """
    if len(license_number) < 5:
        raise ValidationError(_('License number must be at least 5 characters long.'))


def validate_age_range(min_age, max_age):
    """
    Validate age range
    """
    if (min_age and max_age) and min_age > max_age:
        raise ValidationError({
            'min_age': _('Minimum age cannot be greater than maximum age.'),
            'max_age': _('Maximum age must be greater than or equal to minimum age.'),
        })


def validate_proportion(value):
    """
    Validate proportion value (0-1)
    """
    if not 0 <= value <= 1:
        raise ValidationError(_('Proportion must be between 0 and 1.'))


def validate_confidence_score(value):
    """
    Validate confidence score (0-1)
    """
    if not 0.00 <= value <= 1.00:
        raise ValidationError(_('Confidence score must be between 0 and 1.'))


def validate_mood_rating(value):
    """
    Validate mood rating (1-10)
    """
    if not 1 <= value <= 10:
        raise ValidationError(_('Mood rating must be between 1 and 10.'))

def validate_adherence_rate(value):
    """
    Validate adherence rate (0-1)
    """
    if not 0 <= value <= 1:
        raise ValidationError(_('Adherence rate must be between 0 and 1.'))