# serializers.py
from rest_framework import serializers

class RecommendationsSerializer(serializers.Serializer):
    # This serializer is mainly for documentation purposes
    # since the response structure is complex and dynamic
    status = serializers.CharField()
    assessment_id = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    condition_analysis = serializers.DictField()
    skin_profile = serializers.DictField()
    recommendations = serializers.DictField()
    medical_referral_required = serializers.BooleanField()
    severity_level = serializers.CharField(required=False)
    primary_condition = serializers.CharField(required=False)