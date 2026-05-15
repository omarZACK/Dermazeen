from django.contrib import admin
from apps.assessment.models import QuestionTemplate, Assessment,AssessmentResponse


# Register your models here.

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id","user","current_phase","started_at","completed_at")

@admin.register(QuestionTemplate)
class QuestionTemplateAdmin(admin.ModelAdmin):
    list_display = ("id","question_name", "question_text", "question_type","options")
    search_fields = ("question_name","question_text", "question_type")
    list_filter = ("question_type","condition_triggers")
    ordering = ("id",)
    filter_vertical = ("condition_triggers",)
    readonly_fields = ("condition_triggers",)

@admin.register(AssessmentResponse)
class AssessmentResponseAdmin(admin.ModelAdmin):
    list_display = ["id","assessment","question","answer_value"]
    readonly_fields = ("assessment","question","answer_value",)