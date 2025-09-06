
import json
from typing import Dict, Any, Optional, List, Tuple
from django.utils import timezone
from django.db import transaction
from apps.shared.expert_system import Engine
from apps.assessment.models import Assessment, AssessmentResponse, QuestionTemplate
from apps.shared.enums import QuestionPhase, AssessmentStatusChoices
from apps.shared.expert_system.models import UserResponse, CurrentPhase, QuestionAsked, ConditionExcluded
from apps.analysis.models import SkinAnalysis as Analysis
from apps.recommendations.models import Recommendation

class KbsEngineService:
    def __init__(self, assessment: Assessment):
        self.assessment = assessment
        self.engine = None
        self._engine_initialized = False

    def start_analysis(self) -> Dict[str, Any]:
        """Start a new skin analysis and return the first question (or final results if it completes immediately)."""
        try:
            # Update assessment status/phase
            self.assessment.assessment_status = AssessmentStatusChoices.IN_PROGRESS
            self.assessment.current_phase = QuestionPhase.SCREENING.name
            self.assessment.save()

            # Fresh engine
            self.engine = Engine()
            self._engine_initialized = True

            # IMPORTANT: start the engine (this calls reset() internally)
            self.engine.start_assessment()

            # Inject user-sourced data AFTER reset/start (so they persist)
            self._inject_user_profile_data()
            self._inject_lifestyle_data()

            # Return current state
            return self._get_current_state()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to start analysis: {str(e)}",
            }

    def submit_answer(self, question_id: str, answer_value: Any) -> Dict[str, Any]:
        """Submit an answer and return next question or final results."""
        try:
            self._ensure_engine_initialized()

            if hasattr(self.engine, "pending_question"):
                self.engine.pending_question = None

            self.engine.feed_answer(question_id, answer_value)

            if not self._save_response_to_db(question_id, answer_value):
                return {"status": "error", "message": f"Question {question_id} not found in database"}

            return self._get_current_state()

        except Exception as e:
            return {"status": "error", "message": f"Error processing answer: {str(e)}"}

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Return the currently pending question (if analysis is in progress)."""
        if self.assessment.assessment_status != AssessmentStatusChoices.IN_PROGRESS:
            return None
        try:
            self._ensure_engine_initialized()
            summary = self.engine.get_summary()
            return summary.get("pending_question")
        except Exception as e:
            return None

    def get_final_results(self) -> Dict[str, Any]:
        """
        Get the final analysis results if assessment is completed.
        Returns structured data from the database.
        """
        if self.assessment.assessment_status != AssessmentStatusChoices.COMPLETED:
            return {
                "status": "error",
                "message": "Assessment is not completed yet"
            }

        try:
            self._ensure_engine_initialized()
            self._ensure_completion()
            if hasattr(self.assessment, 'analysis') and self.assessment.analysis.results_data:
                analysis_result = self.assessment.analysis.results_data
            elif hasattr(self.engine, 'analysis_result') and self.engine.analysis_result:
                analysis_result = self.engine.analysis_result
            else:
                analysis_result = self._build_analysis_result_manually()
            return {
                "status": "success",
                "assessment_id": self.assessment.id,
                "completed_at": self.assessment.completed_at.isoformat() if self.assessment.completed_at else None,
                "analysis": analysis_result
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving final results: {str(e)}"
            }

    def _build_final_results_fallback(self) -> Dict[str, Any]:
        """Fallback method to build final results from engine state."""
        try:
            if hasattr(self.engine, 'analysis_result') and self.engine.analysis_result:
                analysis_result = self.engine.analysis_result
            else:
                analysis_result = {
                    "medical_referral": {
                        "required": getattr(self.engine, "medical_referral_required", False),
                        "message": "Medical referral required" if getattr(self.engine, "medical_referral_required",
                                                                          False) else None,
                        "reasons": []
                    },
                    "overall_assessment": {
                        "severity_level": self._enum_to_str(getattr(self.engine, "severity_level", None)),
                        "condition_classification": getattr(self.engine, "condition_classification", "UNKNOWN"),
                        "primary_condition": getattr(self.engine, "primary_condition", None),
                        "status_message": self._get_status_message()
                    },
                    "condition_analysis": self._get_condition_analysis(),
                    "skin_profile": self._get_skin_profile(),
                    "recommendations": self._format_recommendations(),
                    "confidence_metrics": self._get_confidence_metrics(),
                    "metadata": {
                        "analysis_timestamp": timezone.now().isoformat(),
                        "engine_version": "2.0",
                        "disclaimers": [
                            "This analysis is educational only, not a medical diagnosis.",
                            "Consult healthcare professionals for medical concerns."
                        ]
                    }
                }

            return {
                "status": "success",
                "assessment_id": self.assessment.id,
                "completed_at": self.assessment.completed_at.isoformat() if self.assessment.completed_at else None,
                "analysis": analysis_result
            }
        except Exception as e:
            print(f"Error in fallback results builder: {e}")
            return {
                "status": "error",
                "message": f"Error building final results: {str(e)}"
            }
    def _ensure_engine_initialized(self):
        """
        Initialize engine and rebuild state from DB, profile, lifestyle if needed.
        Updated to include screening exclusions.
        """
        if self._engine_initialized and self.engine is not None:
            return

        self.engine = Engine()
        self._engine_initialized = True
        self._restore_current_phase()
        self._inject_user_profile_data()
        self._inject_lifestyle_data()
        self._load_previous_responses()
        self._inject_screening_exclusions()
        self.engine.run()

    def _restore_current_phase(self):
        """Restore current phase from DB onto the engine."""
        try:
            for fact in list(self.engine.facts.values()):
                if hasattr(fact, "__class__") and "CurrentPhase" in fact.__class__.__name__:
                    self.engine.retract(fact)

            phase_name = (self.assessment.current_phase or "SCREENING").upper()
            phase = None
            for p in QuestionPhase:
                if p.name.upper() == phase_name:
                    phase = p
                    break
            if phase is None:
                phase = QuestionPhase.SCREENING

            self.engine.declare(CurrentPhase(phase=phase))
        except Exception:
            self.engine.declare(CurrentPhase(phase=QuestionPhase.SCREENING))

    def _load_previous_responses(self):
        """Replay all previous user answers as UserResponse facts."""
        responses = (
            AssessmentResponse.objects.filter(assessment=self.assessment, is_active=True)
            .select_related("question")
            .order_by("answered_at")
        )
        for resp in responses:
            try:
                value = json.loads(resp.answer_value)
                qid = resp.question.question_name

                if isinstance(value, (list, tuple)):
                    for v in value:
                        self.engine.declare(UserResponse(question_id=qid, value=v))
                else:
                    self.engine.declare(UserResponse(question_id=qid, value=value))

                self.engine.declare(QuestionAsked(question_id=qid))
                self.engine.asked_questions.add(qid)

                self.engine.user_responses[qid] = value

            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Error loading response {resp.id}: {e}")

    def _get_current_state(self) -> Dict[str, Any]:
        if not self._engine_initialized or self.engine is None:
            return {"status": "not_started"}

        try:
            summary = self.engine.get_summary()
        except Exception as e:
            return {"status": "error", "message": f"Error getting engine summary: {str(e)}"}

        self._update_assessment_phase(summary)

        if self._is_analysis_complete(summary):
            self._ensure_completion()
            return self._handle_completion(summary)

        phase = summary.get("phase")
        self._phase_to_name(phase)
        if not summary.get("pending_question"):
            self._force_continuation_if_stalled()
            summary = self.engine.get_summary()
            self._update_assessment_phase(summary)

            if self._is_analysis_complete(summary):
                self._ensure_completion()
                return self._handle_completion(summary)

        return {
            "status": "in_progress",
            "current_question": summary.get("pending_question"),
        }

    def _handle_completion(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize assessment in DB and return a normalized final payload."""
        try:
            self.assessment.assessment_status = AssessmentStatusChoices.COMPLETED
            self.assessment.completed_at = timezone.now()
            self.assessment.save()
            if hasattr(self.engine, '_display_complete_analysis'):
                analysis_result = self.engine._display_complete_analysis()
            else:
                analysis_result = self._build_analysis_result_manually()

            final = {
                "status": "success",
                "assessment_id": self.assessment.id,
                "completed_at": timezone.now().isoformat(),
                "analysis": analysis_result
            }

            self._persist_results(final)
            return {"status": "complete", "results": final}
        except Exception as e:
            return {"status": "error", "message": f"Error completing analysis: {str(e)}"}

    def _build_analysis_result_manually(self) -> Dict[str, Any]:
        """
        Manual fallback to build analysis result structure.
        Updated to use the new condition analysis format.
        """
        try:
            condition_analysis = self._get_condition_analysis()
            skin_profile = self._get_skin_profile()
            recommendations = self._format_recommendations()

            hormonal_factors = self._get_hormonal_factors()

            allergen_sensitivities = self._get_allergen_sensitivities()

            return {
                "metadata": {
                    "analysis_timestamp": timezone.now().isoformat(),
                    "engine_version": "2.0",
                    "disclaimers": [
                        "This analysis is educational only, not a medical diagnosis.",
                        "Consult healthcare professionals for medical concerns."
                    ]
                },
                "skin_profile": {
                    "type": skin_profile.get("skin_type", "Normal"),
                    "hydration": skin_profile.get("hydration_status", "Well-hydrated"),
                    "sensitivity": skin_profile.get("sensitivity_level", "Low")
                },
                "recommendations": recommendations,
                "hormonal_factors": hormonal_factors,
                "medical_referral": {
                    "required": getattr(self.engine, "medical_referral_required", False),
                    "message": None,
                    "reasons": []
                },
                "condition_analysis": condition_analysis,
                "confidence_metrics": self._get_confidence_metrics(),
                "overall_assessment": {
                    "severity_level": "mild",
                    "status_message": self._get_status_message(),
                    "primary_condition": getattr(self.engine, "primary_condition", "none"),
                    "condition_classification": "MILD"
                },
                "allergen_sensitivities": allergen_sensitivities
            }

        except Exception as e:
            return {
                "metadata": {
                    "analysis_timestamp": timezone.now().isoformat(),
                    "engine_version": "2.0",
                    "disclaimers": [
                        "This analysis is educational only, not a medical diagnosis.",
                        "Consult healthcare professionals for medical concerns."
                    ]
                },
                "skin_profile": {"type": "Normal", "hydration": "Well-hydrated", "sensitivity": "Low"},
                "recommendations": {},
                "hormonal_factors": {"is_female": True, "has_hormonal_acne": False},
                "medical_referral": {"required": False, "message": None, "reasons": []},
                "condition_analysis": {"conditions": [], "weighted_scores": {}},
                "confidence_metrics": {"average_cf": 0.0, "total_rules_fired": 0},
                "overall_assessment": {
                    "severity_level": "mild",
                    "status_message": "MILD CONDITION DETECTED - Manageable with proper care",
                    "primary_condition": "none",
                    "condition_classification": "MILD"
                },
                "allergen_sensitivities": {"has_sensitivities": False, "avoid_ingredients": []}
            }

    def _get_hormonal_factors(self) -> Dict[str, Any]:
        """Build hormonal factors from user data and responses."""
        try:
            user = self.assessment.user
            gender = getattr(user, "gender", "F")

            return {
                "is_female": gender == "F",
                "cycle_severity": None,
                "birth_control_use": False,
                "has_hormonal_acne": False
            }
        except Exception:
            return {
                "is_female": True,
                "cycle_severity": None,
                "birth_control_use": False,
                "has_hormonal_acne": False
            }

    def _get_allergen_sensitivities(self) -> Dict[str, Any]:
        """Build allergen sensitivities from skin profile and responses."""
        try:
            skin_profile = getattr(self.engine, "skin_profile", {})
            allergen_profile = skin_profile.get("allergen_profile", {})
            return {
                "has_sensitivities": bool(allergen_profile.get("avoid_ingredients")),
                "avoid_ingredients": allergen_profile.get("avoid_ingredients", []),
                "high_risk_allergens": allergen_profile.get("high_risk_allergens", [])
            }
        except Exception as e:
            return {
                "has_sensitivities": False,
                "avoid_ingredients": [],
                "high_risk_allergens": []
            }

    def _persist_results(self, final_payload: Dict[str, Any]) -> None:
        """Persist final analysis to the related analysis model and save recommendations."""
        try:
            analysis, created = Analysis.objects.get_or_create(
                assessment=self.assessment,
                defaults={'results_data': final_payload['analysis']}
            )

            if not created:
                analysis.results_data = final_payload['analysis']
                analysis.save()
            self._save_recommendations_to_db(final_payload['analysis'])

        except Exception as e:
            print(f"Error persisting results: {e}")

    def _ensure_completion(self):
        """Ensure the engine completes the analysis even if it gets stuck."""
        try:
            if self.assessment.current_phase == QuestionPhase.ANALYSIS.name:
                for _ in range(10):  # Limit to 10 iterations to prevent infinite loop
                    if hasattr(self.engine, 'analysis_result') and self.engine.analysis_result:
                        break
                    self.engine.run()
            if (self.assessment.current_phase == QuestionPhase.COMPLETE.name and
                    not hasattr(self.engine, 'analysis_result')):
                self.engine.analysis_result = self.engine._display_complete_analysis()

        except Exception as e:
            pass
    def _save_recommendations_to_db(self, analysis_result: Dict[str, Any]) -> None:
        """Save recommendations to the Recommendation model."""
        try:
            recommendations_data = analysis_result.get("recommendations", {})
            skincare_routine = recommendations_data.get('skincare_routine', {})
            lifestyle_data = recommendations_data.get('lifestyle', [])
            medical_referral = recommendations_data.get('medical_referral', {})
            morning_routine = ""
            evening_routine = ""

            if isinstance(skincare_routine, dict):
                if 'morning' in skincare_routine:
                    morning_routine = str(skincare_routine['morning'])
                if 'evening' in skincare_routine:
                    evening_routine = str(skincare_routine['evening'])

                if not morning_routine and not evening_routine and skincare_routine:
                    routine_str = str(skincare_routine)
                    morning_routine = routine_str
                    evening_routine = routine_str
            elif skincare_routine:
                routine_str = str(skincare_routine)
                morning_routine = routine_str
                evening_routine = routine_str

            lifestyle_advice = ""
            if isinstance(lifestyle_data, list):
                lifestyle_advice = "\n".join(str(item) for item in lifestyle_data)
            elif lifestyle_data:
                lifestyle_advice = str(lifestyle_data)

            safety_notes = ""
            if isinstance(medical_referral, dict):
                if 'message' in medical_referral:
                    safety_notes = str(medical_referral['message'])
                elif 'reasons' in medical_referral:
                    reasons = medical_referral['reasons']
                    if isinstance(reasons, list):
                        safety_notes = "\n".join(str(reason) for reason in reasons)
                    else:
                        safety_notes = str(reasons)
            elif medical_referral:
                safety_notes = str(medical_referral)

            recommendation_type = "routine"  # Default
            if analysis_result.get('medical_referral', {}).get('required', False):
                recommendation_type = "medical_referral"
            elif lifestyle_advice and not (morning_routine or evening_routine):
                recommendation_type = "lifestyle"

            recommendation, created = Recommendation.objects.update_or_create(
                assessment=self.assessment,
                defaults={
                    'user': self.assessment.user,
                    'generated_at': timezone.now(),
                    'recommendation_type': recommendation_type,
                    'routine_morning': morning_routine[:1000] if morning_routine else None,  # Limit length if needed
                    'routine_evening': evening_routine[:1000] if evening_routine else None,  # Limit length if needed
                    'lifestyle_advice': lifestyle_advice[:2000] if lifestyle_advice else None,  # Limit length if needed
                    'safety_notes': safety_notes[:1000] if safety_notes else None,  # Limit length if needed
                    'is_active': True,
                    'expires_at': None,
                }
            )

        except Exception:
            pass

    def _update_assessment_phase(self, summary: Dict[str, Any]):
        """Keep assessment.current_phase in sync with engine."""
        try:
            phase = summary.get("phase")
            if not phase:
                return
            # Prefer enum name; fall back to lowercase string
            if hasattr(phase, "name"):
                self.assessment.current_phase = phase.name
            elif hasattr(phase, "value"):
                self.assessment.current_phase = str(phase.value).upper()
            else:
                self.assessment.current_phase = str(phase).upper()
            self.assessment.save()
        except Exception as e:
            pass
    def _is_analysis_complete(self, summary: Dict[str, Any]) -> bool:
        """Check if the analysis is complete based on phase."""
        try:
            phase = summary.get("phase")
            phase_name = self._phase_to_name(phase)
            return phase_name == "COMPLETE"
        except Exception:
            return False

    def _get_status_message(self) -> str:
        """Get status message based on condition classification and medical referral."""
        classification = getattr(self.engine, "condition_classification", "UNKNOWN")
        medical_referral = getattr(self.engine, "medical_referral_required", False)

        if classification == "SEVERE" or medical_referral:
            return "PROFESSIONAL MEDICAL ATTENTION REQUIRED"
        elif classification == "MODERATE":
            return "MODERATE CONDITION DETECTED - Monitor closely"
        else:
            return "MILD CONDITION DETECTED - Manageable with proper care"

    def _get_confidence_metrics(self) -> Dict[str, Any]:
        """Get confidence metrics from engine facts."""
        try:
            total_cf = sum(f.get('cf', 0) for f in self.engine.facts.values() if hasattr(f, 'get') and 'cf' in f)
            cf_count = sum(1 for f in self.engine.facts.values() if hasattr(f, 'get') and 'cf' in f)

            return {
                "average_cf": round(total_cf / cf_count, 2) if cf_count > 0 else 0.0,
                "total_rules_fired": cf_count
            }
        except Exception as e:
            return {"average_cf": 0.0, "total_rules_fired": 0}

    def _get_condition_analysis(self) -> Dict[str, Any]:
        """
        Build a sorted, weighted condition analysis list.
        Respects screening responses to exclude conditions user said they don't have.
        """
        try:
            condition_scores: Dict[str, Dict[str, float]] = getattr(self.engine, "condition_scores", {}) or {}

            screening_response = self.engine.user_responses.get("screening_main", [])
            excluded_conditions = set()

            if isinstance(screening_response, list) and 1 in screening_response:
                excluded_conditions.update([
                    "melasma", "vitiligo", "rosacea", "eczema", "psoriasis",
                    "severe_acne", "contact_dermatitis", "acne"
                ])
            elif screening_response == 1:
                excluded_conditions.update([
                    "melasma", "vitiligo", "rosacea", "eczema", "psoriasis",
                    "severe_acne", "contact_dermatitis", "acne"
                ])

            if isinstance(screening_response, list) and len(screening_response) > 0 and 1 not in screening_response:
                all_conditions = {
                    "vitiligo", "rosacea", "eczema", "psoriasis",
                    "severe_acne", "contact_dermatitis", "melasma"
                }
                selected_conditions = set()
                for value in screening_response:
                    if value == 2:
                        selected_conditions.add("vitiligo")
                    elif value == 3:
                        selected_conditions.add("rosacea")
                    elif value == 4:
                        selected_conditions.add("eczema")
                    elif value == 5:
                        selected_conditions.add("psoriasis")
                    elif value == 6:
                        selected_conditions.add("severe_acne")
                    elif value == 7:
                        selected_conditions.add("contact_dermatitis")
                    elif value == 8:
                        selected_conditions.add("melasma")
                excluded_conditions = all_conditions - selected_conditions

            items: List[Dict[str, Any]] = []
            weighted_scores = {}

            for cond_key, data in condition_scores.items():
                if cond_key.lower() in excluded_conditions:
                    continue

                score = float(data.get("score", 0))
                cf = float(data.get("cf", 0))

                if score <= 0 or score < 5:
                    continue

                weighted = score * cf

                if weighted < 5.0:
                    continue

                risk_level, risk_color = self._determine_risk_level_and_color(weighted)

                condition_name = cond_key.replace("_", " ").title()

                items.append({
                    "name": condition_name,
                    "raw_score": score,
                    "confidence_factor": round(cf, 2),
                    "weighted_score": round(weighted, 1),
                    "risk_level": risk_level,
                    "risk_color": risk_color
                })

                weighted_scores[cond_key] = round(weighted, 1)

            items.sort(key=lambda x: x["weighted_score"], reverse=True)

            classification = getattr(self.engine, "condition_classification", "UNKNOWN") or "UNKNOWN"

            return {
                "conditions": items,
                "weighted_scores": weighted_scores,
                "classification": classification
            }

        except Exception:
            return {
                "conditions": [],
                "weighted_scores": {},
                "classification": "UNKNOWN"
            }

    @staticmethod
    def _determine_risk_level_and_color(weighted_score: float) -> tuple[str, str]:
        """
        Determine risk level and corresponding color based on weighted score.
        Returns tuple of (risk_level, risk_color).
        """
        if weighted_score >= 70:
            return "High likelihood", "red"
        elif weighted_score >= 40:
            return "Moderate likelihood", "orange"
        elif weighted_score >= 20:
            return "Low-moderate likelihood", "yellow"
        else:
            return "Low likelihood", "green"

    def _get_skin_profile(self) -> Dict[str, Any]:
        """Expose the skin profile in a stable API shape."""
        try:
            profile = getattr(self.engine, "skin_profile", {}) or {}
            return {
                "skin_type": profile.get("type", "Unknown"),
                "sensitivity_level": profile.get("sensitivity", "Unknown"),
                "hydration_status": profile.get("hydration", "Unknown"),
                "allergen_profile": profile.get("allergen_profile", {}),
            }
        except Exception:
            return {
                "skin_type": "Unknown",
                "sensitivity_level": "Unknown",
                "hydration_status": "Unknown",
                "allergen_profile": {},
            }

    def _format_recommendations(self) -> Dict[str, Any]:
        """Normalize engine.recommendations (list of (type, payload)) into a dict."""
        try:
            engine_recs: List[Tuple[str, Any]] = getattr(self.engine, "recommendations", []) or []
            out: Dict[str, Any] = {}
            for rec_type, payload in engine_recs:
                key = rec_type.lower().replace(" ", "_")
                out[key] = payload
            return out
        except Exception as e:
            return {}

    def _save_response_to_db(self, question_id: str, answer_value: Any) -> bool:
        """Persist a single answer."""
        try:
            with transaction.atomic():
                question = QuestionTemplate.objects.get(question_name=question_id)
                AssessmentResponse.objects.create(
                    assessment=self.assessment,
                    question=question,
                    answer_value=json.dumps(answer_value),
                    answered_at=timezone.now(),
                )
            return True
        except QuestionTemplate.DoesNotExist:
            return False
        except Exception as e:
            return False

    # ------------------------------------------------------------------------------
    # Data injection
    # ------------------------------------------------------------------------------

    def _inject_user_profile_data(self):
        """
        Inject profile answers (gender, age-range) as if the user had answered them.
        Must be called AFTER engine.reset/start.
        """
        try:
            user = self.assessment.user
            gender_mapping = {"M": 1, "F": 2}
            gender_value = gender_mapping.get(getattr(user, "gender", None), 1)
            age_value = self._get_age_range(getattr(user, "age", None))

            if "gender" not in getattr(self.engine, "asked_questions", set()):
                self.engine.declare(UserResponse(question_id="gender", value=gender_value))
                self.engine.declare(QuestionAsked(question_id="gender"))
                self.engine.user_responses["gender"] = gender_value
                self.engine.asked_questions.add("gender")

            if "age" not in getattr(self.engine, "asked_questions", set()):
                self.engine.declare(UserResponse(question_id="age", value=age_value))
                self.engine.declare(QuestionAsked(question_id="age"))
                self.engine.user_responses["age"] = age_value
                self.engine.asked_questions.add("age")

        except Exception as e:
            pass

    def _inject_lifestyle_data(self):
        """
        Inject lifestyle answers (sun_exposure, stress_level, sleep_quality) from PatientProfile.
        Must be called AFTER engine.reset/start.
        """
        try:
            patient_profile = getattr(self.assessment.user, "patient_profile", None)
            if not patient_profile:
                return

            # Sun exposure
            sun_map = {
                "minimal": 1,
                "light": 2,
                "moderate": 3,
                "high": 4,
                "very_high": 5,
            }
            sun_value = sun_map.get(getattr(patient_profile, "sun_exposure", ""), 1)

            # Stress
            stress_map = {
                "very_low": 1,
                "low": 2,
                "moderate": 3,
                "high": 4,
                "very_high": 5,
            }
            stress_value = stress_map.get(getattr(patient_profile, "stress_level", ""), 1)

            # Sleep → quality (reversed scale in your system)
            sleep_hours = getattr(patient_profile, "sleep_hours", None)
            sleep_quality = self._convert_sleep_hours_to_quality(sleep_hours)

            if "sun_exposure" not in self.engine.asked_questions:
                self.engine.declare(UserResponse(question_id="sun_exposure", value=sun_value))
                self.engine.declare(QuestionAsked(question_id="sun_exposure"))
                self.engine.user_responses["sun_exposure"] = sun_value
                self.engine.asked_questions.add("sun_exposure")

            if "stress_level" not in self.engine.asked_questions:
                self.engine.declare(UserResponse(question_id="stress_level", value=stress_value))
                self.engine.declare(QuestionAsked(question_id="stress_level"))
                self.engine.user_responses["stress_level"] = stress_value
                self.engine.asked_questions.add("stress_level")

            if "sleep_quality" not in self.engine.asked_questions and sleep_quality is not None:
                self.engine.declare(UserResponse(question_id="sleep_quality", value=sleep_quality))
                self.engine.declare(QuestionAsked(question_id="sleep_quality"))
                self.engine.user_responses["sleep_quality"] = sleep_quality
                self.engine.asked_questions.add("sleep_quality")

        except Exception:
            pass
    def _inject_screening_exclusions(self):
        """
        Inject screening-based exclusions into the engine after user answers screening questions.
        This ensures that conditions explicitly ruled out by the user are not evaluated.
        """
        try:
            screening_response = self.engine.user_responses.get("screening_main")
            if not screening_response:
                return

            # If user said "No specific problems suspected"
            if (isinstance(screening_response, list) and 1 in screening_response) or screening_response == 1:
                conditions_to_exclude = [
                    "melasma", "vitiligo", "rosacea", "eczema", "psoriasis",
                    "severe_acne", "contact_dermatitis"
                ]

                for condition in conditions_to_exclude:
                    self.engine.declare(ConditionExcluded(condition=condition))

            # If user selected specific conditions, exclude the others
            elif isinstance(screening_response, list) and len(screening_response) > 0:
                all_conditions = {
                    "vitiligo": 2, "rosacea": 3, "eczema": 4, "psoriasis": 5,
                    "severe_acne": 6, "contact_dermatitis": 7, "melasma": 8
                }

                # Find conditions that weren't selected
                selected_values = set(screening_response)
                for condition, value in all_conditions.items():
                    if value not in selected_values:
                        self.engine.declare(ConditionExcluded(condition=condition))

        except Exception as e:
            pass

    def _force_continuation_if_stalled(self):
        """
        If engine is in a non-terminal phase without a pending question, nudge it forward
        a few times to allow phase-transition rules to fire.
        """
        try:
            attempts = 0
            while attempts < 3:
                summary = self.engine.get_summary()
                phase_name = self._phase_to_name(summary.get("phase"))
                pending = summary.get("pending_question")

                if phase_name == "COMPLETE":
                    break
                if pending:
                    break

                # Clear pending (safety), run again
                if hasattr(self.engine, "pending_question"):
                    self.engine.pending_question = None
                self.engine.run()
                attempts += 1
        except Exception as e:
            pass

    @staticmethod
    def _get_age_range(age: Optional[int]) -> int:
        """Map chronological age to the engine's age bucket."""
        if age is None:
            return 1
        if age < 18:
            return 1
        if 18 <= age <= 25:
            return 2
        if 26 <= age <= 35:
            return 3
        if 36 <= age <= 45:
            return 4
        return 5

    @staticmethod
    def _convert_sleep_hours_to_quality(sleep_hours: Optional[int]) -> Optional[int]:
        """Convert sleep hours to reversed quality scale used by the engine."""
        if sleep_hours is None:
            return None
        if sleep_hours <= 4:
            return 5  # Very poor
        if sleep_hours == 5:
            return 4  # Poor
        if sleep_hours == 6:
            return 3  # Fair
        if 7 <= sleep_hours <= 8:
            return 2  # Good
        if sleep_hours >= 9:
            return 1  # Excellent
        return None

    @staticmethod
    def _determine_risk_level(weighted_score: float) -> str:
        if weighted_score >= 70:
            return "High"
        if weighted_score >= 40:
            return "Moderate"
        if weighted_score >= 20:
            return "Low-Moderate"
        return "Low"

    @staticmethod
    def _phase_to_name(phase_obj: Any) -> str:
        if hasattr(phase_obj, "name"):
            return phase_obj.name
        if hasattr(phase_obj, "value"):
            return str(phase_obj.value).upper()
        return str(phase_obj or "").upper()

    @staticmethod
    def _enum_to_str(enum_val: Any) -> Optional[str]:
        """Return enum.name if Enum, else the raw string/None."""
        try:
            if hasattr(enum_val, "name"):
                return enum_val.name
            if hasattr(enum_val, "value") and isinstance(enum_val.value, str):
                return enum_val.value
            return enum_val if isinstance(enum_val, str) else None
        except Exception:
            return None

    def debug_engine_state(self) -> Dict[str, Any]:
        """Inspect internal engine state (safe for logs)."""
        if not self._engine_initialized or not self.engine:
            return {"error": "Engine not initialized"}
        try:
            return {
                "initialized": self._engine_initialized,
                "facts_count": len(self.engine.facts),
                "user_responses": dict(getattr(self.engine, "user_responses", {})),
                "asked_questions": list(getattr(self.engine, "asked_questions", [])),
                "pending_question": getattr(self.engine, "pending_question", None),
                "current_phase": self.assessment.current_phase,
                "assessment_status": self.assessment.assessment_status,
            }
        except Exception as e:
            return {"error": str(e)}

    def force_continue(self) -> Dict[str, Any]:
        """Manually nudge the engine forward (debug)."""
        try:
            self._ensure_engine_initialized()
            if hasattr(self.engine, "pending_question"):
                self.engine.pending_question = None
            self.engine.run()
            return self._get_current_state()
        except Exception as e:
            return {"status": "error", "message": f"Error forcing continuation: {str(e)}"}