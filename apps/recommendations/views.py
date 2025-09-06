from rest_framework import generics, status
from rest_framework.response import Response
from apps.assessment.models import Assessment
from apps.shared.expert_system import KbsEngineService
from apps.shared.permissions import IsAuthenticatedUser


class RecommendationView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedUser]
    queryset = Assessment.objects.all()
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        assessment = self.get_object()
        service = KbsEngineService(assessment=assessment)

        # Get the complete analysis results
        result = service.get_final_results()

        if result.get('status') == 'error':
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)