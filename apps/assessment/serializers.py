from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Assessment, AssessmentResponse, QuestionTemplate
from apps.analysis.models import SkinAnalysis

User = get_user_model()


class StartAssessmentSerializer(serializers.Serializer):
    """Serializer for starting assessment with optional image"""
    image = serializers.ImageField(
        required=False,
        help_text="Optional skin image for AI analysis"
    )

    def validate_image(self, value):
        """Validate uploaded image"""
        if value:
            # Validate file size (10MB limit)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Image file too large (> 10MB)")

            # Validate file format
            allowed_content_types = [
                'image/jpeg', 'image/jpg', 'image/png',
                'image/bmp', 'image/tiff', 'image/webp'
            ]
            if value.content_type.lower() not in allowed_content_types:
                raise serializers.ValidationError(
                    f"Unsupported image format. Allowed: JPEG, PNG, BMP, TIFF, WebP"
                )

        return value
class QuestionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionTemplate
        fields = ['id', 'question_name', 'question_text', 'question_type', 'options']
        read_only_fields = ['id', 'question_name', 'question_text', 'question_type', 'options']

class AssessmentResponseSerializer(serializers.ModelSerializer):
    question = QuestionTemplateSerializer(read_only=True)

    class Meta:
        model = AssessmentResponse
        fields = ['id', 'assessment', 'question', 'answer_value', 'answered_at']
        read_only_fields = ['id', 'assessment', 'question', 'answered_at']

class SkinAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkinAnalysis
        fields = ['id', 'user', 'image_url', 'analysis_status', 'confidence_score', 'results_data', 'created_at']
        read_only_fields = ['id', 'user', 'analysis_status', 'confidence_score', 'results_data', 'created_at']

class AssessmentSerializer(serializers.ModelSerializer):
    responses = AssessmentResponseSerializer(many=True, read_only=True)
    analysis = SkinAnalysisSerializer(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id', 'user', 'analysis', 'started_at', 'completed_at',
            'current_phase', 'assessment_status', 'responses'
        ]
        read_only_fields = [
            'id', 'user', 'analysis', 'started_at',
            'completed_at', 'current_phase','assessment_status'
        ]

class AnswerSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    value = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )

class AnalysisResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    current_question = serializers.DictField(required=False)
    progress = serializers.IntegerField(required=False, min_value=0, max_value=100)
    results = serializers.DictField(required=False)