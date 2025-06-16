from django.db.models import TextChoices as TChoices
from django.utils.translation import gettext_lazy as _

# --------------------------------------------------------------
# Accounts
# --------------------------------------------------------------

class GenderChoices(TChoices):
    """Gender choices for users"""
    MALE = 'M', _('Male')
    FEMALE = 'F', _('Female')

class UserTypeChoices(TChoices):
    """User type choices"""
    PATIENT = 'patient', _('Patient')
    DOCTOR = 'doctor', _('Doctor')
    ADMIN = 'admin', _('Admin')


class SkinTypeChoices(TChoices):
    """Skin type choices"""
    DRY = 'dry', _('Dry')
    OILY = 'oily', _('Oily')
    SENSITIVE = 'sensitive', _('Sensitive')
    NORMAL = 'normal', _('Normal')
    COMBINATION = 'combination', _('Combination')

class ApprovalStatusChoices(TChoices):
    """Approval status for doctors"""
    PENDING = 'pending', _('Pending Review')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    SUSPENDED = 'suspended', _('Suspended')

class AdminRoleChoices(TChoices):
    """Admin role choices"""
    SUPER_ADMIN = 'super', _('Super Admin')
    CONTENT_ADMIN = 'content', _('Content Admin')
    DOCTOR_ADMIN = 'doctor', _('Doctor Admin')
    AUDIT_ADMIN = 'audit', _('Audit Admin')

# --------------------------------------------------------------
# Analysis
# --------------------------------------------------------------

class AnalysisStatusChoices(TChoices):
    """Status choices for skin analysis"""
    PENDING = 'pending', _('Pending')
    PROCESSING = 'processing', _('Processing')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')

class ConditionCategoryChoices(TChoices):
    """Categories for skin conditions"""
    ACNE = 'acne', _('Acne')
    PIGMENTATION = 'pigmentation', _('Pigmentation')
    AGING = 'aging', _('Aging Signs')
    SENSITIVITY = 'sensitivity', _('Sensitivity')
    INFLAMMATION = 'inflammation', _('Inflammation')
    BARRIER_DAMAGE = 'barrier_damage', _('Barrier Damage')
    HORMONAL = 'hormonal', _('Hormonal')
    LIFESTYLE = 'lifestyle', _('Lifestyle Related')
    CHRONIC = 'chronic', _('Chronic Conditions')
    GENETIC ='genetic', _('Genetic Related')

class SeverityLevelChoices(TChoices):
    """Severity level for detected conditions"""
    NONE = 'none', _('No Problem')
    MILD = 'mild', _('Mild')
    MODERATE = 'moderate', _('Moderate')
    SEVERE = 'severe', _('Severe')

# --------------------------------------------------------------
# Assessment
# --------------------------------------------------------------

class AssessmentStatusChoices(TChoices):
    """Status choices for assessments"""
    STARTED = 'started', _('Started')
    IN_PROGRESS = 'in_progress', _('In Progress')
    COMPLETED = 'completed', _('Completed')
    ABANDONED = 'abandoned', _('Abandoned')

class QuestionTypeChoices(TChoices):
    """Question type choices"""
    SINGLE_CHOICE = 'single', _('Single Choice')
    MULTIPLE_CHOICE = 'multiple', _('Multiple Choice')
    TEXT = 'text', _('Text Input')
    BOOLEAN = 'boolean', _('Yes/No')
    SCALE = 'scale', _('Rating Scale')


# --------------------------------------------------------------
# Recommendation
# --------------------------------------------------------------

class RecommendationTypeChoices(TChoices):
    """Recommendation type choices"""
    ROUTINE = 'routine', _('Skincare Routine')
    LIFESTYLE = 'lifestyle', _('Lifestyle Advice')
    MEDICAL_REFERRAL = 'medical', _('Medical Referral')

class SafetyLevelChoices(TChoices):
    """Safety level for products and ingredients"""
    SAFE = 'safe', _('Safe')
    CAUTION = 'caution', _('Use with Caution')
    PRESCRIPTION_ONLY = 'prescription', _('Prescription Only')
    NOT_RECOMMENDED = 'not_recommended', _('Not Recommended')

class UsageFrequencyChoices(TChoices):
    """Product usage frequency"""
    DAILY_MORNING = 'daily_am', _('Daily Morning')
    DAILY_EVENING = 'daily_pm', _('Daily Evening')
    TWICE_DAILY = 'twice_daily', _('Twice Daily')
    WEEKLY = 'weekly', _('Weekly')
    AS_NEEDED = 'as_needed', _('As Needed')

# --------------------------------------------------------------
# Consultation
# --------------------------------------------------------------

class ConsultationStatusChoices(TChoices):
    """Consultation status choices"""
    REQUESTED = 'requested', _('Requested')
    SCHEDULED = 'scheduled', _('Scheduled')
    IN_PROGRESS = 'in_progress', _('In Progress')
    COMPLETED = 'completed', _('Completed')
    CANCELLED = 'cancelled', _('Cancelled')

class TestCategoryChoices(TChoices):
    """Medical test categories"""
    BLOOD_TEST = 'blood', _('Blood Test')
    HORMONE_TEST = 'hormone', _('Hormone Test')
    ALLERGY_TEST = 'allergy', _('Allergy Test')
    DERMATOLOGY = 'dermatology', _('Dermatological Test')
    IMAGING = 'imaging', _('Imaging Test')

class UrgencyLevelChoices(TChoices):
    """Test urgency levels"""
    LOW = 'low', _('Low Priority')
    MEDIUM = 'medium', _('Medium Priority')
    HIGH = 'high', _('High Priority')
    URGENT = 'urgent', _('Urgent')

# --------------------------------------------------------------
# Follow-up
# --------------------------------------------------------------

class RoutineStatusChoices(TChoices):
    """User routine status"""
    ACTIVE = 'active', _('Active')
    PAUSED = 'paused', _('Paused')
    COMPLETED = 'completed', _('Completed')
    ABANDONED = 'abandoned', _('Abandoned')

class CompletionStatusChoices(TChoices):
    """Completion status for routine activities"""
    NOT_DONE = 'not_done', _('Not Done')
    COMPLETED = 'completed', _('Completed')
    PARTIALLY_DONE = 'partial', _('Partially Done')
    SKIPPED = 'skipped', _('Skipped')

class ReminderTypeChoices(TChoices):
    """Reminder type choices"""
    ROUTINE = 'routine', _('Routine Reminder')
    HYDRATION = 'hydration', _('Hydration Reminder')
    PROGRESS_PHOTO = 'progress_photo', _('Progress Photo')
    CONSULTATION = 'consultation', _('Consultation Reminder')

class PhotoTypeChoices(TChoices):
    """Progress photo types"""
    BASELINE = 'baseline', _('Baseline Photo')
    WEEKLY = 'weekly', _('Weekly Progress')
    MONTHLY = 'monthly', _('Monthly Progress')
    FINAL = 'final', _('Final Result')

# --------------------------------------------------------------
# System Audit
# --------------------------------------------------------------

class ActionTypeChoices(TChoices):
    """System log action types"""
    CREATE = 'create', _('Create')
    UPDATE = 'update', _('Update')
    DELETE = 'delete', _('Delete')
    LOGIN = 'login', _('Login')
    LOGOUT = 'logout', _('Logout')
    ANALYSIS = 'analysis', _('Skin Analysis')
    RECOMMENDATION = 'recommendation', _('Recommendation Generated')

class AuditStatusChoices(TChoices):
    """Audit status for recommendations"""
    PENDING = 'pending', _('Pending Review')
    APPROVED = 'approved', _('Approved')
    FLAGGED = 'flagged', _('Safety Flagged')
    REQUIRES_REVISION = 'revision', _('Requires Revision')

