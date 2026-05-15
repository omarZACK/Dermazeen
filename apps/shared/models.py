from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    Abstract base class for models that need created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    Manager for soft delete functionality
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Abstract base class for models that support soft delete
    """
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is Deleted'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Deleted At'))

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the object"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class ActiveModel(models.Model):
    """
    Abstract base class for models that have active/inactive status
    """
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        abstract = True