from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

class UserStampedMixin(models.Model):
    """
    Mixin to add created_by and updated_by fields
    """
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name=_('Created By')
    )
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name=_('Updated By')
    )

    class Meta:
        abstract = True


class OrderedMixin(models.Model):
    """
    Mixin to add ordering capability
    """
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Display Order'),
        help_text=_('Order in which items should be displayed')
    )

    class Meta:
        abstract = True
        ordering = ['display_order']