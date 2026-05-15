from django.urls import path
from .views import RecommendationView
urlpatterns = [
    path("<int:id>/results/",RecommendationView.as_view(), name="assessment_results"),
]