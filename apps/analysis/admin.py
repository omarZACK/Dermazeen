from django.contrib import admin
from apps.analysis.models import SkinCondition, SkinAnalysis


# Register your models here.

class SkinConditionCategoryInline(admin.TabularInline):
    model = SkinCondition.categories.through  # Use the auto-created through table
    extra = 1  # Number of empty forms to show


@admin.register(SkinCondition)
class SkinConditionAdmin(admin.ModelAdmin):
    list_display = ("id", "condition_name", "is_chronic", "requires_medical_attention")
    search_fields = ("condition_name",)
    list_filter = ("categories", "is_chronic")
    filter_vertical = ("categories",)
    readonly_fields = ("categories",)

@admin.register(SkinAnalysis)
class SkinAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id',)