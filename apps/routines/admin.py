from django.contrib import admin

from apps.recommendations.models import Recommendation


# Register your models here.

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Recommendation._meta.fields]