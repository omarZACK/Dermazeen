from django.urls import path
from .views import (
    StartAssessmentView,
    SubmitAnswerView,
    CurrentQuestionView,
    AssessmentDetailView,
    UserAssessmentsView
)

urlpatterns = [
    path('start/', StartAssessmentView.as_view(), name='assessment_start'),
    path('list/', UserAssessmentsView.as_view(), name='user_assessments'),
    path('<int:id>/', AssessmentDetailView.as_view(), name='assessment_detail'),
    path('<int:assessment_id>/answer/', SubmitAnswerView.as_view(), name='assessment_submit_answer'),
    path('<int:id>/current-question/', CurrentQuestionView.as_view(), name='assessment_current_question'),
]