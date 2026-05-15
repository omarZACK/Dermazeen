from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from apps.shared.enums import (
    RecommendationTypeChoices,
    SafetyLevelChoices,
    UsageFrequencyChoices
)
from apps.shared.mixins import OrderedMixin
from apps.shared.models import TimeStampedModel, ActiveModel, SoftDeleteModel
from apps.assessment.models import Assessment
from apps.shared.utils import validate_age_range,validate_proportion

# Create your models here.

User = get_user_model()

class Recommendation(TimeStampedModel, ActiveModel, SoftDeleteModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User receiving the recommendation.")
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        help_text=_("Assessment this recommendation is based on.")
    )
    generated_at = models.DateTimeField(
        help_text=_("Timestamp when the recommendation was generated.")
    )
    recommendation_type = models.CharField(
        max_length=20,
        choices=RecommendationTypeChoices.choices,
        help_text=_("Type of recommendation (routine, lifestyle, medical referral).")
    )
    routine_morning = models.TextField(
        null=True,
        blank=True,
        help_text=_("Morning skincare routine recommendations.")
    )
    routine_evening = models.TextField(
        null=True,
        blank=True,
        help_text=_("Evening skincare routine recommendations.")
    )
    lifestyle_advice = models.TextField(
        null=True,
        blank=True,
        help_text=_("Lifestyle advice and general recommendations.")
    )
    safety_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_("Important safety notes and warnings.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this recommendation is currently active.")
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this recommendation expires.")
    )

    def __str__(self):
        return f"Recommendation #{self.pk} for {self.user.get_full_name}"

    class Meta:
        verbose_name = _("Recommendation")
        verbose_name_plural = _("Recommendations")
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['assessment']),
            models.Index(fields=['recommendation_type']),
            models.Index(fields=['generated_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]

class ProductCategory(ActiveModel, TimeStampedModel, SoftDeleteModel, OrderedMixin):
    category_name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique name of the product category.")
    )
    description = models.TextField(
        help_text=_("Description of the product category.")
    )
    is_topical_only = models.BooleanField(
        default=True,
        help_text=_("Whether this category contains only topical products.")
    )

    def __str__(self):
        return self.category_name

    class Meta:
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['display_order']),
            models.Index(fields=['is_topical_only']),
        ]

class Ingredient(ActiveModel, TimeStampedModel, SoftDeleteModel):
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text=_("Unique name of the ingredient.")
    )
    description = models.TextField(
        help_text=_("Description of the ingredient and its properties.")
    )
    is_allergen = models.BooleanField(
        default=False,
        help_text=_("Whether this ingredient is a common allergen.")
    )
    pregnancy_safe = models.BooleanField(
        default=True,
        help_text=_("Whether this ingredient is safe during pregnancy.")
    )
    safety_level = models.CharField(
        max_length=15,
        choices=SafetyLevelChoices.choices,
        default=SafetyLevelChoices.SAFE,
        help_text=_("General safety level of this ingredient.")
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Ingredient")
        verbose_name_plural = _("Ingredients")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_allergen']),
            models.Index(fields=['pregnancy_safe']),
            models.Index(fields=['safety_level']),
        ]


class Product(ActiveModel, TimeStampedModel, SoftDeleteModel):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        help_text=_("Category this product belongs to.")
    )
    product_name = models.CharField(
        max_length=200,
        help_text=_("Name of the product.")
    )
    description = models.TextField(
        help_text=_("Detailed description of the product.")
    )
    usage_instructions = models.TextField(
        help_text=_("Instructions on how to use this product.")
    )
    safety_level = models.CharField(
        max_length=15,
        choices=SafetyLevelChoices.choices,
        default=SafetyLevelChoices.SAFE,
        help_text=_("Safety level of this product.")
    )
    pregnancy_safe = models.BooleanField(
        default=True,
        help_text=_("Whether this product is safe during pregnancy.")
    )
    min_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Minimum recommended age for using this product.")
    )
    max_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum recommended age for using this product.")
    )

    def __str__(self):
        return self.product_name

    def clean(self):
        super().clean()
        validate_age_range(self.min_age, self.max_age)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['product_name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['safety_level']),
            models.Index(fields=['pregnancy_safe']),
            models.Index(fields=['is_active']),
            models.Index(fields=['min_age']),
            models.Index(fields=['max_age']),
        ]


class ProductIngredient(ActiveModel, TimeStampedModel, SoftDeleteModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ingredients',
        help_text=_("Product containing this ingredient.")
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='products',
        help_text=_("Ingredient in this product.")
    )
    proportion = models.FloatField(
        validators=[validate_proportion],
        help_text=_("Percentage proportion of this ingredient (0.0 - 1.0).")
    )
    notes = models.TextField(
        null=True,
        blank=True,
        help_text=_("Additional notes about this ingredient in this product.")
    )

    def __str__(self):
        return f"{self.ingredient.name} in {self.product.product_name} ({self.proportion}%)"

    class Meta:
        verbose_name = _("Product Ingredient")
        verbose_name_plural = _("Product Ingredients")
        ordering = ['-proportion']
        unique_together = ('product', 'ingredient')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['ingredient']),
            models.Index(fields=['proportion']),
        ]


class RecommendedProduct(ActiveModel, TimeStampedModel, SoftDeleteModel):
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE,
        related_name='recommended_products',
        help_text=_("Recommendation this product belongs to.")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        help_text=_("Product being recommended.")
    )
    usage_frequency = models.CharField(
        max_length=15,
        choices=UsageFrequencyChoices.choices,
        help_text=_("How frequently this product should be used.")
    )
    specific_instructions = models.TextField(
        null=True,
        blank=True,
        help_text=_("Specific instructions for using this product.")
    )
    priority_order = models.PositiveIntegerField(
        help_text=_("Priority order of this product in the recommendation.")
    )

    def __str__(self):
        return f"{self.product.product_name} for Recommendation #{self.recommendation.pk}"

    class Meta:
        verbose_name = _("Recommended Product")
        verbose_name_plural = _("Recommended Products")
        ordering = ['priority_order']
        unique_together = ('recommendation', 'product')
        indexes = [
            models.Index(fields=['recommendation']),
            models.Index(fields=['product']),
            models.Index(fields=['usage_frequency']),
            models.Index(fields=['priority_order']),
        ]
