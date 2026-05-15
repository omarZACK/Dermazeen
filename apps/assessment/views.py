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
from ai_models import MelasmaDetector, RosaceaDetector,predict_single_image_exact_training_method,FaceAcneDetector
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
    """Start skin assessment with triple AI model image analysis"""

    permission_classes = [IsAuthenticatedUser]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = StartAssessmentSerializer
    queryset = Assessment.objects.all()

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

        # Initialize all AI models
        self.melasma_detector = None
        self.rosacea_detector = None
        self.acne_detector = None

        # Load melasma model
        melasma_model_path = os.path.join(settings.BASE_DIR, 'ai_models', 'melasma_detector.pkl')
        try:
            self.melasma_detector = MelasmaDetector(melasma_model_path)
            print("✅ Melasma detector loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load melasma detector: {e}")

        # Load rosacea model
        rosacea_model_path = os.path.join(settings.BASE_DIR, 'ai_models', 'rosacea_model.pkl')
        try:
            self.rosacea_detector = RosaceaDetector(rosacea_model_path)
            print("✅ Rosacea detector loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load rosacea detector: {e}")

        # Load acne model
        try:
            self.acne_detector = FaceAcneDetector()
            print("✅ Acne detector loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load acne detector: {e}")

    # ----------------------------
    # Helper: convert to safe JSON
    # ----------------------------
    @staticmethod
    def _make_serializable(obj):
        """Convert NumPy / bytes objects to JSON-serializable Python types."""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, (bytes, bytearray)):
            return obj.decode('utf-8', errors='ignore')
        elif isinstance(obj, dict):
            return {k: StartAssessmentView._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [StartAssessmentView._make_serializable(v) for v in obj]
        return obj

    def create_assessment(self):
        """Create new assessment with analysis"""
        analysis = SkinAnalysis.objects.create(user=self.request.user)
        assessment = Assessment.objects.create(user=self.request.user, analysis=analysis)
        return assessment

    def process_image_with_ai(self, image_file):
        """Process uploaded image with all AI models"""
        try:
            if not any([self.melasma_detector, self.rosacea_detector, self.acne_detector]):
                return {
                    'error': 'No AI models available',
                    'melasma_result': None,
                    'rosacea_result': None,
                    'acne_result': None
                }

            image_file.seek(0)
            image_data = image_file.read()

            # Convert to OpenCV image
            image = Image.open(BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            results = {
                'success': True,
                'melasma_result': None,
                'rosacea_result': None,
                'acne_result': None,
                'errors': []
            }

            # Melasma
            if self.melasma_detector:
                try:
                    melasma_prediction = self.melasma_detector.predict(opencv_image)
                    results['melasma_result'] = self._make_serializable(melasma_prediction)
                    print(f"🔬 Melasma prediction: {melasma_prediction}")
                except Exception as e:
                    msg = f"Melasma prediction failed: {e}"
                    results['errors'].append(msg)
                    print(f"❌ {msg}")

            # Rosacea
            if self.rosacea_detector:
                try:
                    rosacea_prediction = self.rosacea_detector.predict(opencv_image)
                    results['rosacea_result'] = self._make_serializable(rosacea_prediction)
                    print(f"🔬 Rosacea prediction: {rosacea_prediction}")
                except Exception as e:
                    msg = f"Rosacea prediction failed: {e}"
                    results['errors'].append(msg)
                    print(f"❌ {msg}")

            # Acne
            if self.acne_detector:
                try:
                    temp_image_path = os.path.join(settings.BASE_DIR, 'temp_image.jpg')
                    cv2.imwrite(temp_image_path, opencv_image)

                    acne_prediction = predict_single_image_exact_training_method(
                        os.path.join(settings.BASE_DIR, 'ai_models', 'final_enhanced_dual_input_acne_classifier.pth'),
                        temp_image_path,
                        self.acne_detector
                    )

                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)

                    results['acne_result'] = self._make_serializable(acne_prediction)
                    print(f"🔬 Acne prediction: {acne_prediction}")
                except Exception as e:
                    msg = f"Acne prediction failed: {e}"
                    results['errors'].append(msg)
                    print(f"❌ {msg}")

            if not any([results['melasma_result'], results['rosacea_result'], results['acne_result']]):
                return {
                    'error': 'All AI models failed',
                    'errors': results['errors']
                }

            return results

        except Exception as e:
            return {
                'error': f'Image processing failed: {str(e)}',
                'melasma_result': None,
                'rosacea_result': None,
                'acne_result': None
            }

    @staticmethod
    def save_image_and_update_analysis(assessment, image_file, ai_result):
        """Save uploaded image and update analysis with AI results"""
        try:
            image_file.seek(0)
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"skin_analysis_{assessment.user.id}_{timestamp}_{image_file.name}"

            file_path = default_storage.save(
                f'skin_images/{filename}',
                ContentFile(image_file.read())
            )
            image_url = default_storage.url(file_path)

            confidences = []
            if ai_result.get('melasma_result'):
                confidences.append(ai_result['melasma_result'].get('confidence', 0.0))
            if ai_result.get('rosacea_result'):
                confidences.append(ai_result['rosacea_result'].get('confidence', 0.0))
            if ai_result.get('acne_result'):
                confidences.append(ai_result['acne_result'].get('confidence', 0.0))

            overall_confidence = np.mean(confidences) if confidences else 0.0

            # Ensure JSON-safe AI results
            serializable_result = StartAssessmentView._make_serializable(ai_result)

            assessment.analysis.image_url = image_url
            assessment.analysis.image_metadata = {
                'filename': filename,
                'size': image_file.size,
                'content_type': getattr(image_file, 'content_type', 'unknown'),
                'uploaded_at': timezone.now().isoformat()
            }
            assessment.analysis.confidence_score = overall_confidence
            assessment.analysis.analyzed_at = timezone.now()
            assessment.analysis.results_data = {
                'ai_prediction': serializable_result,
                'image_processed': True,
                'processing_timestamp': timezone.now().isoformat()
            }
            assessment.analysis.save()

            return True, image_url

        except Exception as e:
            return False, str(e)


    @staticmethod
    def convert_ai_prediction_to_screening_choices(ai_result):
        """Convert AI predictions to screening question format"""
        if ai_result.get('error'):
            # If AI failed, return "Other" to let user specify manually
            return [9]  # "Other" option

        melasma_result = ai_result.get('melasma_result')
        rosacea_result = ai_result.get('rosacea_result')
        acne_result = ai_result.get('acne_result')

        detected_conditions = []
        high_confidence_conditions = []

        # Analyze melasma results
        if melasma_result:
            melasma_pred = melasma_result.get('prediction', '').lower()
            melasma_conf = melasma_result.get('confidence', 0.0)
            melasma_prob = melasma_result.get('melasma_probability', 0.0)

            print(f"🔍 Melasma - Pred: {melasma_pred}, Conf: {melasma_conf:.3f}, Prob: {melasma_prob:.3f}")

            if melasma_pred == 'melasma':
                detected_conditions.append(8)  # "Melasma"
                if melasma_conf > 0.7:
                    high_confidence_conditions.append(8)
            elif melasma_prob > 0.4:  # Moderate melasma probability even if not predicted
                detected_conditions.append(8)

        # Analyze rosacea results
        if rosacea_result:
            rosacea_pred = rosacea_result.get('prediction', '').lower()
            rosacea_conf = rosacea_result.get('confidence', 0.0)
            rosacea_prob = rosacea_result.get('rosacea_probability', 0.0)

            print(f"🔍 Rosacea - Pred: {rosacea_pred}, Conf: {rosacea_conf:.3f}, Prob: {rosacea_prob:.3f}")

            if rosacea_pred == 'rosacea':
                detected_conditions.append(3)  # "Rosacea"
                if rosacea_conf > 0.7:
                    high_confidence_conditions.append(3)
            elif rosacea_prob > 0.4:  # Moderate rosacea probability even if not predicted
                detected_conditions.append(3)

        # Analyze acne results
        if acne_result:
            acne_pred = acne_result.get('predicted_class_name', '').lower()
            acne_conf = acne_result.get('confidence', 0.0)
            acne_level = acne_pred.replace('level_', '') if 'level' in acne_pred else '0'

            print(f"🔍 Acne - Pred: {acne_pred}, Conf: {acne_conf:.3f}, Level: {acne_level}")

            if 'level' in acne_pred and acne_level != '0':
                detected_conditions.append(2)  # "Acne"
                if acne_conf > 0.7:
                    high_confidence_conditions.append(2)
            elif acne_conf > 0.4:  # Moderate acne probability even if not predicted as level
                detected_conditions.append(2)

        # Decision logic for screening choices
        if high_confidence_conditions:
            # High confidence detections - return those conditions
            choices = list(set(high_confidence_conditions))
            print(f"🎯 High confidence conditions detected: {choices}")
            return choices

        elif detected_conditions:
            # Medium confidence detections - include detected conditions
            choices = list(set(detected_conditions))
            print(f"🎯 Medium confidence conditions detected: {choices}")
            return choices

        else:
            # No conditions detected or low confidence
            # Check if models agree on "normal"
            melasma_normal = melasma_result and melasma_result.get('prediction', '').lower() == 'normal'
            rosacea_normal = rosacea_result and rosacea_result.get('prediction', '').lower() == 'normal'
            acne_normal = acne_result and ('normal' in acne_result.get('predicted_class_name', '').lower() or
                                           'level_0' in acne_result.get('predicted_class_name', '').lower())

            # Get overall confidence for normal predictions
            normal_confidences = []
            if melasma_normal:
                normal_confidences.append(melasma_result.get('confidence', 0.0))
            if rosacea_normal:
                normal_confidences.append(rosacea_result.get('confidence', 0.0))
            if acne_normal:
                normal_confidences.append(acne_result.get('confidence', 0.0))

            avg_normal_confidence = np.mean(normal_confidences) if normal_confidences else 0.0

            if avg_normal_confidence > 0.6:
                print(f"🎯 Normal skin detected with confidence: {avg_normal_confidence:.3f}")
                return [1]  # "No specific problems suspected"
            else:
                print(f"🎯 Uncertain results, defaulting to no problems + other")
                return [1, 9]  # "No specific problems suspected" + "Other"

    def inject_ai_screening_answer(self, service, ai_result):
        """Inject AI prediction as screening question answer"""
        try:
            # Convert AI predictions to screening choices
            screening_choices = self.convert_ai_prediction_to_screening_choices(ai_result)

            print(f"🤖 AI screening injection - Choices: {screening_choices}")

            # Use the service's submit_answer method to properly handle the screening answer
            result = service.submit_answer("screening_main", screening_choices)

            if result.get("status") == "error":
                return False, result.get('message')

            print(f"✅ AI screening answer injected successfully: {screening_choices}")
            return True, screening_choices

        except Exception as e:
            print(f"❌ AI screening injection failed: {e}")
            return False, str(e)

    @transaction.atomic
    def post(self, request):
        """Start a new skin assessment with AI model image analysis"""
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

            # Process image if provided
            if image_file:
                print("🖼️  Processing image with AI models...")

                # Process with AI models
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
            state = service.start_analysis()

            # If we have successful AI results, inject them as an answer to the screening question
            if ai_result and not ai_result.get('error'):
                print("🧠 Injecting AI results into screening question...")

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
                    'melasma_prediction': ai_result.get('melasma_result'),
                    'rosacea_prediction': ai_result.get('rosacea_result'),
                    'acne_prediction': ai_result.get('acne_result'),
                    'injected_successfully': ai_choices_injected is not None,
                    'injected_choices': ai_choices_injected,
                    'errors': ai_result.get('errors', []),
                    'error': ai_result.get('error')
                }

            # Add image info if uploaded
            if image_file:
                response_data['image_uploaded'] = True
                response_data['image_url'] = getattr(assessment.analysis, 'image_url', None)

            return Response(response_data, status=status.HTTP_201_CREATED)

        except serializers.ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            print(f"❌ Assessment creation failed: {e}")
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