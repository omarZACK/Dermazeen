import os
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from rest_framework import status, generics, serializers
from rest_framework.response import Response
from ai_models.melasma_model import MelasmaDetector
from apps.shared.permissions import IsAuthenticatedUser
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Assessment
from apps.analysis.models import SkinAnalysis
from apps.shared.expert_system.services import KbsEngineService
from .serializers import (
    AssessmentSerializer,
    AnswerSerializer,
    AnalysisResultSerializer, StartAssessmentSerializer
)
from ..shared.enums import AssessmentStatusChoices



User = get_user_model()


class StartAssessmentView(generics.GenericAPIView):
    """Start skin assessment with optional AI image analysis"""

    permission_classes = [IsAuthenticatedUser]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = StartAssessmentSerializer
    queryset = Assessment.objects.all()

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        # Initialize the AI model (make sure the path is correct)
        model_path = os.path.join(settings.BASE_DIR, 'ai_models', 'melasma_detector.pkl')
        try:
            self.melasma_detector = MelasmaDetector(model_path)
            print("✅ Melasma AI model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading AI model: {e}")
            self.melasma_detector = None

    def create_assessment(self):
        """Create new assessment with analysis"""
        analysis = SkinAnalysis.objects.create(user=self.request.user)
        assessment = Assessment.objects.create(user=self.request.user, analysis=analysis)
        return assessment

    def process_image_with_ai(self, image_file):
        """Process uploaded image with AI model"""
        try:
            if not self.melasma_detector:
                return {
                    'error': 'AI model not available',
                    'prediction': None,
                    'confidence': 0.0
                }

            # Reset file pointer if it was read before
            image_file.seek(0)

            # Read image from uploaded file
            image_data = image_file.read()

            # Convert to OpenCV format
            image = Image.open(BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert PIL to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            # Get AI prediction
            prediction_result = self.melasma_detector.predict(opencv_image)

            print(f"🤖 AI Prediction: {prediction_result['prediction']} "
                  f"(confidence: {prediction_result['confidence']:.3f})")

            return {
                'success': True,
                'prediction': prediction_result['prediction'],
                'confidence': prediction_result['confidence'],
                'melasma_probability': prediction_result['melasma_probability'],
                'normal_probability': prediction_result['normal_probability']
            }

        except Exception as e:
            print(f"❌ AI processing failed: {str(e)}")
            return {
                'error': f'AI processing failed: {str(e)}',
                'prediction': None,
                'confidence': 0.0
            }

    @staticmethod
    def save_image_and_update_analysis(assessment, image_file, ai_result):
        """Save uploaded image and update analysis with AI results"""
        try:
            # Reset file pointer
            image_file.seek(0)

            # Create unique filename
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"skin_analysis_{assessment.user.id}_{timestamp}_{image_file.name}"

            # Save image file
            file_path = default_storage.save(
                f'skin_images/{filename}',
                ContentFile(image_file.read())
            )
            image_url = default_storage.url(file_path)

            # Update SkinAnalysis with image and AI results
            assessment.analysis.image_url = image_url
            assessment.analysis.image_metadata = {
                'filename': filename,
                'size': image_file.size,
                'content_type': getattr(image_file, 'content_type', 'unknown'),
                'uploaded_at': timezone.now().isoformat()
            }
            assessment.analysis.confidence_score = ai_result.get('confidence', 0.0)
            assessment.analysis.analyzed_at = timezone.now()

            # Store AI results in analysis
            assessment.analysis.results_data = {
                'ai_prediction': ai_result,
                'image_processed': True,
                'processing_timestamp': timezone.now().isoformat()
            }
            assessment.analysis.save()

            print(f"💾 Image saved: {filename}")
            return True, image_url

        except Exception as e:
            print(f"❌ Failed to save image: {str(e)}")
            return False, str(e)

    @staticmethod
    def convert_ai_prediction_to_screening_choices(ai_result):
        """Convert AI prediction to screening question format"""
        if ai_result.get('error'):
            # If AI failed, return "Other" to let user specify manually
            return [9]  # "Other" option

        prediction = ai_result.get('prediction', '').lower()
        confidence = ai_result.get('confidence', 0.0)
        melasma_probability = ai_result.get('melasma_probability', 0.0)

        # High confidence melasma detection
        if prediction == 'melasma' and confidence > 0.7:
            return [8]  # "Melasma" option

        # Medium confidence melasma detection
        elif prediction == 'melasma' and confidence > 0.5:
            return [8]  # "Melasma" option

        # Low melasma probability but some uncertainty
        elif melasma_probability > 0.3:
            return [1, 8]  # "No specific problems suspected" + "Melasma" to be safe

        # Normal skin with high confidence
        elif prediction == 'normal' and confidence > 0.8:
            return [1]  # "No specific problems suspected"

        # Uncertain cases
        else:
            return [1, 9]  # "No specific problems suspected" + "Other"

    def inject_ai_screening_answer(self, service, ai_result):
        """Inject AI prediction as screening question answer using proper service method"""
        try:
            # Convert AI prediction to screening choices
            screening_choices = self.convert_ai_prediction_to_screening_choices(ai_result)

            # Use the service's submit_answer method to properly handle the screening answer
            # This ensures all the proper facts are declared and the engine state is updated
            result = service.submit_answer("screening_main", screening_choices)

            if result.get("status") == "error":
                return False, result.get('message')
            return True, screening_choices

        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def post(self, request):
        """Start a new skin assessment with optional image upload"""
        # Validate input data first
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get validated image (if provided)
            image_file = serializer.validated_data.get('image')
            ai_result = None
            ai_choices_injected = None

            # Create assessment
            assessment = self.create_assessment()
            print(f"📝 Created assessment {assessment.id} for user {assessment.user.id}")

            # Process image if provided
            if image_file:
                print(f"📸 Processing uploaded image: {image_file.name}")

                # Process with AI
                ai_result = self.process_image_with_ai(image_file)

                # Save image and update analysis
                image_saved, image_info = self.save_image_and_update_analysis(
                    assessment, image_file, ai_result
                )

                if not image_saved:
                    return Response({
                        'error': f'Failed to save image: {image_info}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Initialize the KBS service
            service = KbsEngineService(assessment)

            # Start the analysis first (this sets up the engine and asks first question)
            print("🚀 Starting KBS analysis...")
            state = service.start_analysis()

            # If we have successful AI results, inject them as an answer to the screening question
            if ai_result and not ai_result.get('error'):
                print("🤖 AI analysis successful, injecting screening answer...")

                injection_success, ai_choices_injected = self.inject_ai_screening_answer(service, ai_result)

                if injection_success:
                    # Get updated state after AI injection
                    state = service._get_current_state()
                    print(f"🎯 Updated state after AI injection: {state.get('status')}")

                    # Log current question if there is one
                    if state.get('current_question'):
                        question = state['current_question']
                        print(f"❓ Next question: {question.get('name')} - {question.get('text')}")
                    elif state.get('status') == 'complete':
                        print("✅ Assessment completed after AI injection!")
                else:
                    print(f"⚠️  AI injection failed: {ai_choices_injected}")

            # Prepare response data
            assessment_serializer = AssessmentSerializer(assessment)
            result_serializer = AnalysisResultSerializer(state)

            response_data = {
                'success': True,
                'assessment': assessment_serializer.data,
                'state': result_serializer.data
            }

            # Add AI results to response if available
            if ai_result:
                response_data['ai_analysis'] = {
                    'processed': not ai_result.get('error'),
                    'prediction': ai_result.get('prediction'),
                    'confidence': ai_result.get('confidence'),
                    'melasma_probability': ai_result.get('melasma_probability'),
                    'normal_probability': ai_result.get('normal_probability'),
                    'injected_successfully': ai_choices_injected is not None,
                    'injected_choices': ai_choices_injected,
                    'error': ai_result.get('error')
                }

            # Add image info if uploaded
            if image_file:
                response_data['image_uploaded'] = True
                response_data['image_url'] = getattr(assessment.analysis, 'image_url', None)

            print(f"✅ Assessment {assessment.id} started successfully")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except serializers.ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            print(f"❌ Assessment creation failed: {str(e)}")
            return Response({
                'error': f'Assessment creation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitAnswerView(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedUser]
    serializer_class = AnswerSerializer

    def post(self, request, assessment_id):
        """Submit an answer to the current question using option indices starting from 1"""
        assessment = get_object_or_404(Assessment, id=assessment_id, is_active=True)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        value = serializer.validated_data['value']

        value = [int(v) for v in value if v >= 1]

        service = KbsEngineService(assessment)
        state = service.submit_answer(
            serializer.validated_data['question_id'],
            value
        )

        if state.get('status') == 'error':
            return Response(state, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            "status": assessment.get_assessment_status_display(),
            "phase": assessment.get_current_phase_display(),
            "current_question": state.get("current_question") or "No more questions",
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CurrentQuestionView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedUser]
    queryset = Assessment.objects.all()
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        """Get the current question if assessment is in progress"""
        try:
            assessment = self.get_object()

            # Check if assessment is already complete
            if assessment.assessment_status == AssessmentStatusChoices.COMPLETED:
                return Response({
                    'status': 'complete',
                    'message': 'Assessment is already complete'
                }, status=status.HTTP_200_OK)

            service = KbsEngineService(assessment)

            # Ensure the engine is initialized
            service._ensure_engine_initialized()

            # Get the current state
            state = service._get_current_state()

            if state.get('status') == 'complete':
                return Response({
                    'status': 'complete',
                    'message': 'Assessment is complete'
                }, status=status.HTTP_200_OK)
            elif state.get('status') == 'in_progress':
                return Response({
                    'status': 'in_progress',
                    'question': state.get('current_question')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'not_started',
                    'message': 'Assessment not started'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'Failed to get current question: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssessmentDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedUser]
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    lookup_field = 'id'

class UserAssessmentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedUser]
    queryset = Assessment.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = AssessmentSerializer