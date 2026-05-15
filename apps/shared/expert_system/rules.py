from typing import Any, Dict, List, Optional, Tuple
from experta import *
from apps.shared.enums import QuestionPhase
from apps.assessment.models import QuestionTemplate
from .models import *
from .scoring import ConditionScorer, SeverityAnalyzer, SkinProfileAnalyzer
from .recommendations import RecommendationGenerator

class SkinAnalysisEngine(KnowledgeEngine):
    """Enhanced rule-based expert system with confidence factors, medical referral logic, melasma detection, and multi-choice support"""
    def __init__(self):
        super().__init__()
        self.analysis_result = None
        self.condition_scorer = ConditionScorer()
        self.recommendation_generator = RecommendationGenerator()

        self.user_responses: Dict[str, Any] = {}
        self.asked_questions: set[str] = set()
        self.skin_profile: Dict[str, Any] = {}
        self.condition_scores: Dict[str, Dict[str, float]] = {}
        self.recommendations: List[Tuple[str, Any]] = []
        self.severity_level = None
        self.condition_classification: Optional[str] = None
        self.primary_condition: Optional[str] = None
        self.medical_referral_required: bool = False
        self.confidence_factors: Dict[str, float] = {}
        self.pending_question: Optional[Dict[str, Any]] = None
        self.messages: List[Dict[str, str]] = []

    def start_assessment(self, phase: QuestionPhase = QuestionPhase.SCREENING) -> None:
        """Initialize the engine and ask the first question (halts)."""
        self.reset()
        self.declare(CurrentPhase(phase=phase))
        self.run()

    def feed_answer(self, question_id: str, value: Any) -> None:
        """Inject a user's answer and continue until next pending question or completion."""
        self.pending_question = None
        if isinstance(value, (list, tuple)):
            for v in value:
                self.declare(UserResponse(question_id=question_id, value=v))
                self.user_responses[question_id] = v
        else:
            self.declare(UserResponse(question_id=question_id, value=value))
            self.user_responses[question_id] = value

        self.run()

    def get_summary(self) -> Dict[str, Any]:
        phase = None
        for f in self.facts.values():
            if isinstance(f, CurrentPhase):
                phase = f["phase"]
                break

        summary = {
            "phase": phase.name if phase else None,
            "pending_question": self.pending_question,
            "asked_questions": sorted(list(self.asked_questions)),
            "user_responses": self.user_responses,
            "condition_scores": self.condition_scores,
            "skin_profile": self.skin_profile,
            "severity_level": getattr(self.severity_level, "value", None),
            "condition_classification": self.condition_classification,
            "primary_condition": self.primary_condition,
            "medical_referral_required": self.medical_referral_required,
            "messages": self.messages,
        }

        if hasattr(self, 'analysis_result'):
            summary["analysis_result"] = self.analysis_result

        return summary

    def _ask(self, question_key: str) -> None:
        """Ask a question and halt the engine until answered."""
        if question_key in self.asked_questions:
            return
        try:
            question = QuestionTemplate.objects.get(question_name=question_key)
            self.pending_question = {
                "name": question.question_name,
                "text": question.question_text,
                "type": question.get_question_type_display(),
                "options": question.options,
            }
            self.declare(QuestionAsked(question_id=question_key))
            self.asked_questions.add(question_key)
            self.halt()
        except QuestionTemplate.DoesNotExist:
            self._log_message(f"Question {question_key} not found in database", level="error")

    def _declare_cf(self, rule_name: str, cf: float = 1.0):
        """Declare a confidence factor when a rule fires"""
        self.declare(ConfidenceFactor(rule=rule_name, cf=cf))

    def _log_message(self, text: str, level: str = "info"):
        """Store a message to be returned via API"""
        self.messages.append({"level": level, "text": text})

    # =============================================================================
    # PHASE 1: SCREENING RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.SCREENING),
          NOT(QuestionAsked(question_id="screening_main")),
          salience=100)
    def ask_screening_question(self):
        """Rule: Ask initial screening question [CF: 1.0]"""
        self._declare_cf("screening_main", 1.0)
        self._ask("screening_main")

    @Rule(UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: not _static_has_choice(
              _static_normalize_choice_value(choice), 1)),  # Not "No specific problems"
          NOT(QuestionAsked(question_id="condition_duration")),
          salience=90)
    def ask_condition_duration(self):
        """Rule: Ask condition duration if problem suspected [CF: 0.9]"""
        self._declare_cf("condition_duration", 0.9)
        self._ask("condition_duration")

    @Rule(UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: not _static_has_choice(
              _static_normalize_choice_value(choice), 1)),
          NOT(QuestionAsked(question_id="condition_severity")),
          salience=90)
    def ask_condition_severity(self):
        """Rule: Ask condition severity [CF: 0.9]"""
        self._declare_cf("condition_severity", 0.9)
        self._ask("condition_severity")

    @Rule(UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: not _static_has_choice(
              _static_normalize_choice_value(choice), 1)),
          NOT(QuestionAsked(question_id="previous_treatments")),
          salience=85)
    def ask_previous_treatments(self):
        """Rule: Ask previous treatments [CF: 0.8]"""
        self._declare_cf("previous_treatments", 0.8)
        self._ask("previous_treatments")

    @Rule(CurrentPhase(phase=QuestionPhase.SCREENING),
          QuestionAsked(question_id="screening_main"),
          OR(UserResponse(question_id="screening_main", value=MATCH.choice) &
             TEST(lambda choice: _static_has_choice(
                 _static_normalize_choice_value(choice), 1)),
             AND(QuestionAsked(question_id="condition_duration"),
                 QuestionAsked(question_id="condition_severity"),
                 QuestionAsked(question_id="previous_treatments"))),
          salience=80)
    def move_to_basic_info(self):
        """Rule: Transition to basic information phase [CF: 0.95]"""
        self._change_phase(QuestionPhase.BASIC_INFO)
        self._declare_cf("phase_transition_basic", 0.95)

    # =============================================================================
    # PHASE 2: BASIC INFORMATION RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.BASIC_INFO),
          NOT(QuestionAsked(question_id="age")),
          salience=75)
    def ask_age(self):
        """Rule: Ask user's age [CF: 1.0]"""
        self._declare_cf("ask_age", 1.0)
        self._ask("age")

    @Rule(CurrentPhase(phase=QuestionPhase.BASIC_INFO),
          NOT(QuestionAsked(question_id="gender")),
          salience=75)
    def ask_gender(self):
        """Rule: Ask user's gender [CF: 1.0]"""
        self._declare_cf("ask_gender", 1.0)
        self._ask("gender")

    @Rule(CurrentPhase(phase=QuestionPhase.BASIC_INFO),
          NOT(QuestionAsked(question_id="skin_tone")),
          salience=70)
    def ask_skin_tone(self):
        """Rule: Ask about natural skin tone [CF: 0.8]"""
        self._declare_cf("ask_skin_tone", 0.8)
        self._ask("skin_tone")

    @Rule(CurrentPhase(phase=QuestionPhase.BASIC_INFO),
          NOT(QuestionAsked(question_id="family_history")),
          salience=85)
    def ask_family_history(self):
        """Rule: Ask about family history [CF: 0.9]"""
        self._declare_cf("ask_family_history", 0.9)
        self._ask("family_history")

    @Rule(CurrentPhase(phase=QuestionPhase.BASIC_INFO),
          QuestionAsked(question_id="age"),
          QuestionAsked(question_id="gender"),
          QuestionAsked(question_id="skin_tone"),
          QuestionAsked(question_id="family_history"),
          salience=70)
    def move_to_specific_conditions(self):
        """Rule: Transition to specific condition assessment [CF: 0.95]"""
        self._change_phase(QuestionPhase.SPECIFIC_CONDITION)
        self._declare_cf("phase_transition_specific", 0.95)

    # =============================================================================
    # PHASE 3: SPECIFIC CONDITION RULES
    # =============================================================================

    # VITILIGO DETECTION RULES
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: _static_has_choice(
              _static_normalize_choice_value(choice), 2)),  # Vitiligo selected
          NOT(QuestionAsked(question_id="vitiligo_spots")),
          salience=95)
    def ask_vitiligo_spots_from_screening(self):
        """Rule: Ask about vitiligo spots when vitiligo suspected"""
        self._declare_cf("vitiligo_spots", 0.9)
        self._ask("vitiligo_spots")

    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="family_history", value=MATCH.history),
          TEST(lambda history: _static_has_choice(
              _static_normalize_choice_value(history), 2)),  # Vitiligo in family history
          NOT(QuestionAsked(question_id="vitiligo_spots")),
          salience=90)
    def ask_vitiligo_spots_from_family(self):
        """Rule: Ask about vitiligo spots when family history present"""
        self._declare_cf("vitiligo_spots_family", 0.8)
        self._ask("vitiligo_spots")

    @Rule(UserResponse(question_id="vitiligo_spots", value=MATCH.spots),
          TEST(lambda spots: _static_get_single_value(spots) > 1),
          NOT(QuestionAsked(question_id="vitiligo_location")),
          salience=90)
    def ask_vitiligo_location(self):
        """Rule: Ask where vitiligo spots appear"""
        self._declare_cf("vitiligo_location", 0.85)
        self._ask("vitiligo_location")

    # VITILIGO MEDICAL REFERRAL RULES
    @Rule(UserResponse(question_id="vitiligo_location", value=MATCH.location),
          TEST(lambda location: _static_has_any_choice(
              _static_normalize_choice_value(location), [1, 5])),  # Face or around eyes
          salience=100)
    def detect_vitiligo_facial_involvement(self):
        """Rule: Detect vitiligo facial involvement requiring medical referral"""
        self._log_message("⚠️ Facial vitiligo detected - medical referral recommended", level="warning")
        self.declare(MedicalReferralRequired(condition="vitiligo", reason="facial_involvement"))
        self._declare_cf("vitiligo_facial_referral", 0.95)

    # ROSACEA DETECTION RULES
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: _static_has_choice(
              _static_normalize_choice_value(choice), 3)),  # Rosacea selected
          NOT(QuestionAsked(question_id="rosacea_redness")),
          salience=90)
    def ask_rosacea_redness_from_screening(self):
        """Rule: Ask about rosacea redness when rosacea suspected"""
        self._declare_cf("rosacea_redness", 0.85)
        self._ask("rosacea_redness")

    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="family_history", value=MATCH.history),
          TEST(lambda history: _static_has_choice(
              _static_normalize_choice_value(history), 3)),  # Rosacea in family history
          NOT(QuestionAsked(question_id="rosacea_redness")),
          salience=85)
    def ask_rosacea_redness_from_family(self):
        """Rule: Ask about rosacea redness when family history present"""
        self._declare_cf("rosacea_redness_family", 0.75)
        self._ask("rosacea_redness")

    @Rule(UserResponse(question_id="rosacea_redness", value=MATCH.redness),
          TEST(lambda redness: _static_get_single_value(redness) > 1),
          NOT(QuestionAsked(question_id="rosacea_triggers")),
          salience=85)
    def ask_rosacea_triggers(self):
        """Rule: Ask about rosacea triggers"""
        self._declare_cf("rosacea_triggers", 0.8)
        self._ask("rosacea_triggers")

    # ECZEMA DETECTION RULES
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: _static_has_choice(
              _static_normalize_choice_value(choice), 4)),  # Eczema selected
          NOT(QuestionAsked(question_id="eczema_itching")),
          salience=90)
    def ask_eczema_itching_from_screening(self):
        """Rule: Ask about eczema itching when eczema suspected"""
        self._declare_cf("eczema_itching", 0.85)
        self._ask("eczema_itching")

    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="family_history", value=MATCH.history),
          TEST(lambda history: _static_has_choice(
              _static_normalize_choice_value(history), 4)),  # Eczema in family history
          NOT(QuestionAsked(question_id="eczema_itching")),
          salience=85)
    def ask_eczema_itching_from_family(self):
        """Rule: Ask about eczema itching when family history present"""
        self._declare_cf("eczema_itching_family", 0.75)
        self._ask("eczema_itching")

    @Rule(UserResponse(question_id="eczema_itching", value=MATCH.itching),
          TEST(lambda itching: _static_get_single_value(itching) > 1),
          NOT(QuestionAsked(question_id="eczema_location")),
          salience=88)
    def ask_eczema_location(self):
        """Rule: Ask where eczema appears"""
        self._declare_cf("eczema_location", 0.8)
        self._ask("eczema_location")

    @Rule(UserResponse(question_id="eczema_itching", value=MATCH.itching),
          TEST(lambda itching: _static_get_single_value(itching) > 1),
          NOT(QuestionAsked(question_id="eczema_triggers")),
          salience=82)
    def ask_eczema_triggers(self):
        """Rule: Ask about eczema triggers"""
        self._ask("eczema_triggers")
        self._declare_cf("eczema_triggers", 0.75)

    # ECZEMA MEDICAL REFERRAL RULES
    @Rule(UserResponse(question_id="eczema_location", value=MATCH.location),
          TEST(lambda location: _static_has_choice(
              _static_normalize_choice_value(location), 1)),  # Face
          salience=100)
    def detect_eczema_facial_involvement(self):
        """Rule: Detect eczema facial involvement requiring medical referral"""
        self._log_message("⚠️ Facial eczema detected - medical referral recommended", level="warning")
        self.declare(MedicalReferralRequired(condition="eczema", reason="facial_involvement"))
        self._declare_cf("eczema_facial_referral", 0.9)

    @Rule(UserResponse(question_id="eczema_itching", value=MATCH.itching),
          TEST(lambda itching: _static_get_single_value(itching) >= 4),
          salience=95)
    def detect_severe_eczema_itching(self):
        """Rule: Detect severe eczema itching requiring medical referral"""
        self._log_message("⚠️ Severe eczema itching detected - medical referral recommended", level="warning")
        self.declare(MedicalReferralRequired(condition="eczema", reason="severe_symptoms"))
        self._declare_cf("eczema_severe_itching", 0.85)

    # MELASMA DETECTION RULES
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="screening_main", value=MATCH.screening),
          TEST(lambda screening: _static_has_choice(_static_normalize_choice_value(screening), 8)),
          NOT(QuestionAsked(question_id="melasma_patches")),
          salience=90)
    def ask_melasma_patches_from_screening(self):
        """Rule: Ask about melasma patches when melasma suspected"""
        self._ask("melasma_patches")
        self._declare_cf("melasma_patches", 0.9)

    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="gender", value=MATCH.gender),
          TEST(lambda gender: _static_has_exact_value(gender, 2)),
          UserResponse(question_id="age", value=MATCH.age),
          TEST(lambda age: _static_get_single_value(age) >= 2),
          UserResponse(question_id="screening_main", value=MATCH.screening),
          TEST(lambda screening: not _static_has_exact_value(screening, 1)),
          NOT(QuestionAsked(question_id="melasma_patches")),
          salience=85)
    def ask_melasma_patches_female_adult(self):
        """Rule: Ask about melasma patches for adult females"""
        self._ask("melasma_patches")
        self._declare_cf("melasma_patches_female", 0.75)

    @Rule(UserResponse(question_id="melasma_patches", value=MATCH.patches),
          TEST(lambda patches: _static_get_single_value(patches) > 1),
          NOT(QuestionAsked(question_id="melasma_location")),
          salience=88)
    def ask_melasma_location(self):
        """Rule: Ask where melasma patches appear"""
        self._ask("melasma_location")
        self._declare_cf("melasma_location", 0.85)

    @Rule(UserResponse(question_id="melasma_patches", value=MATCH.patches),
          TEST(lambda patches: _static_get_single_value(patches) > 1),
          NOT(QuestionAsked(question_id="melasma_triggers")),
          salience=85)
    def ask_melasma_triggers(self):
        """Rule: Ask about melasma triggers with gender filtering"""
        self._ask("melasma_triggers")
        self._declare_cf("melasma_triggers", 0.8)

    @Rule(UserResponse(question_id="melasma_patches", value=MATCH.patches),
          TEST(lambda patches: _static_get_single_value(patches) > 1),
          UserResponse(question_id="gender", value=2),
          NOT(QuestionAsked(question_id="melasma_pregnancy_hormones")),
          salience=82)
    def ask_melasma_pregnancy_hormones(self):
        """Rule: Ask about pregnancy/hormonal factors for melasma"""
        self._ask("melasma_pregnancy_hormones")
        self._declare_cf("melasma_hormones", 0.8)

    # ACNE DETECTION RULES FOR FEMALES
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          UserResponse(question_id="screening_main", value=MATCH.choice),
          TEST(lambda choice: _static_has_choice(
              _static_normalize_choice_value(choice), 6)),  # Severe Acne selected
          UserResponse(question_id="gender", value=2),
          NOT(QuestionAsked(question_id="menstrual_cycle_acne")),
          salience=85)
    def ask_menstrual_cycle_acne_from_screening(self):
        """Rule: Ask about menstrual cycle impact when severe acne suspected"""
        self._ask("menstrual_cycle_acne")
        self._declare_cf("menstrual_acne", 0.8)

    @Rule(UserResponse(question_id="menstrual_cycle_acne", value=MATCH.cycle),
          TEST(lambda cycle: _static_get_single_value(cycle) > 1),
          NOT(QuestionAsked(question_id="hormonal_birth_control")),
          salience=80)
    def ask_hormonal_birth_control(self):
        """Rule: Ask about hormonal birth control use"""
        self._ask("hormonal_birth_control")
        self._declare_cf("hormonal_birth_control", 0.7)

    # PHASE TRANSITION RULE
    @Rule(CurrentPhase(phase=QuestionPhase.SPECIFIC_CONDITION),
          salience=50)
    def move_to_oiliness_assessment(self):
        """Rule: Move to oiliness assessment phase"""
        self._change_phase(QuestionPhase.OILINESS_ASSESSMENT)
        self._declare_cf("phase_transition_oiliness", cf=0.9)

    # =============================================================================
    # PHASE 4: OILINESS ASSESSMENT RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.OILINESS_ASSESSMENT),
          NOT(QuestionAsked(question_id="t_zone_oiliness")),
          salience=75)
    def ask_t_zone_oiliness(self):
        """Rule: Ask about T-zone oiliness"""
        self._ask("t_zone_oiliness")
        self._declare_cf("t_zone_oiliness", 0.85)

    @Rule(CurrentPhase(phase=QuestionPhase.OILINESS_ASSESSMENT),
          NOT(QuestionAsked(question_id="cheek_oiliness")),
          salience=75)
    def ask_cheek_oiliness(self):
        """Rule: Ask about cheek oiliness"""
        self._ask("cheek_oiliness")
        self._declare_cf("cheek_oiliness", 0.85)

    @Rule(CurrentPhase(phase=QuestionPhase.OILINESS_ASSESSMENT),
          NOT(QuestionAsked(question_id="pore_size")),
          salience=70)
    def ask_pore_size(self):
        """Rule: Ask about pore size"""
        self._ask("pore_size")
        self._declare_cf("pore_size", 0.8)

    @Rule(UserResponse(question_id="t_zone_oiliness", value=MATCH.oil),
          TEST(lambda oil: _static_get_single_value(oil) >= 4),
          UserResponse(question_id="gender", value=2),
          NOT(QuestionAsked(question_id="menstrual_cycle_acne")),
          salience=85)
    def ask_menstrual_cycle_acne_from_oiliness(self):
        """Rule: Ask about menstrual cycle impact when high oiliness detected"""
        self._ask("menstrual_cycle_acne")
        self._declare_cf("menstrual_cycle_acne", 0.75)

    @Rule(CurrentPhase(phase=QuestionPhase.OILINESS_ASSESSMENT),
          QuestionAsked(question_id="t_zone_oiliness"),
          QuestionAsked(question_id="cheek_oiliness"),
          QuestionAsked(question_id="pore_size"),
          salience=65)
    def move_to_sensitivity_assessment(self):
        """Rule: Transition to sensitivity assessment"""
        self._change_phase(QuestionPhase.SENSITIVITY_ASSESSMENT)
        self._declare_cf("phase_transition_sensitivity", 0.9)

    # =============================================================================
    # PHASE 5: SENSITIVITY ASSESSMENT RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          NOT(QuestionAsked(question_id="product_sensitivity")),
          salience=80)
    def ask_product_sensitivity(self):
        """Rule: Ask about sensitivity to new products"""
        self._ask("product_sensitivity")
        self._declare_cf("product_sensitivity", 0.85)

    @Rule(UserResponse(question_id="product_sensitivity", value=MATCH.sens),
          TEST(lambda sens: _static_get_single_value(sens) > 1),
          NOT(QuestionAsked(question_id="environmental_sensitivity")),
          salience=75)
    def ask_environmental_sensitivity(self):
        """Rule: Ask about environmental sensitivity"""
        self._ask("environmental_sensitivity")
        self._declare_cf("environmental_sensitivity", 0.8)

    # DETAILED ALLERGEN SENSITIVITY QUESTIONS
    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          UserResponse(question_id="product_sensitivity", value=MATCH.sens),
          TEST(lambda sens: _static_get_single_value(sens) >= 3),
          NOT(QuestionAsked(question_id="fragrance_sensitivity")),
          salience=75)
    def ask_fragrance_sensitivity_detailed(self):
        """Rule: Ask about fragrance sensitivity for sensitive skin"""
        self._ask("fragrance_sensitivity")
        self._declare_cf("fragrance_sensitivity", 0.8)

    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          QuestionAsked(question_id="fragrance_sensitivity"),
          NOT(QuestionAsked(question_id="preservative_sensitivity")),
          salience=70)
    def ask_preservative_sensitivity_detailed(self):
        """Rule: Ask about preservative sensitivity"""
        self._ask("preservative_sensitivity")
        self._declare_cf("preservative_sensitivity", 0.75)

    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          QuestionAsked(question_id="preservative_sensitivity"),
          NOT(QuestionAsked(question_id="metal_sensitivity")),
          salience=70)
    def ask_metal_sensitivity_detailed(self):
        """Rule: Ask about metal sensitivity"""
        self._ask("metal_sensitivity")
        self._declare_cf("metal_sensitivity", 0.75)

    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          QuestionAsked(question_id="metal_sensitivity"),
          NOT(QuestionAsked(question_id="botanical_sensitivity")),
          salience=70)
    def ask_botanical_sensitivity_detailed(self):
        """Rule: Ask about botanical sensitivity"""
        self._ask("botanical_sensitivity")
        self._declare_cf("botanical_sensitivity", 0.7)

    @Rule(CurrentPhase(phase=QuestionPhase.SENSITIVITY_ASSESSMENT),
          UserResponse(question_id="product_sensitivity", value=MATCH.v),
          TEST(lambda v: _static_has_exact_value(v, 1)),  # Updated
          OR(UserResponse(question_id="product_sensitivity", value=MATCH.v2) &
             TEST(lambda v2: _static_has_exact_value(v2, 1)),
             AND(UserResponse(question_id="product_sensitivity", value=MATCH.v3) &
                 TEST(lambda v3: _static_has_exact_value(v3, 2)),
                 NOT(QuestionAsked(question_id="fragrance_sensitivity"))),
             QuestionAsked(question_id="botanical_sensitivity")),
          salience=60)
    def move_to_hydration_assessment(self):
        """Rule: Transition to hydration assessment"""
        self._change_phase(QuestionPhase.HYDRATION_ASSESSMENT)
        self._declare_cf("phase_transition_hydration", 0.9)

    # =============================================================================
    # PHASE 6: HYDRATION ASSESSMENT RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.HYDRATION_ASSESSMENT),
          NOT(QuestionAsked(question_id="dryness_feeling")),
          salience=75)
    def ask_dryness_feeling(self):
        """Rule: Ask about feelings of dryness or tightness"""
        self._ask("dryness_feeling")
        self._declare_cf("dryness_feeling", 0.85)

    @Rule(UserResponse(question_id="dryness_feeling", value=MATCH.dry),
          TEST(lambda dry: _static_get_single_value(dry) > 1),
          NOT(QuestionAsked(question_id="moisturizer_response")),
          salience=70)
    def ask_moisturizer_response(self):
        """Rule: Ask how skin responds to moisturizers"""
        self._ask("moisturizer_response")
        self._declare_cf("moisturizer_response", 0.8)

    @Rule(CurrentPhase(phase=QuestionPhase.HYDRATION_ASSESSMENT),
          QuestionAsked(question_id="dryness_feeling"),
          OR(UserResponse(question_id="dryness_feeling", value=1),
             QuestionAsked(question_id="moisturizer_response")),
          salience=65)
    def move_to_lifestyle_assessment(self):
        """Rule: Transition to lifestyle assessment"""
        self._change_phase(QuestionPhase.LIFESTYLE)
        self._declare_cf("phase_transition_lifestyle", 0.9)

    # =============================================================================
    # PHASE 7: LIFESTYLE ASSESSMENT RULES (SIMPLIFIED)
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.LIFESTYLE),
          NOT(LifestyleDataProcessed()),
          salience=100)
    def process_lifestyle_data(self):
        """Rule: Process lifestyle data and immediately move to analysis"""
        self.declare(LifestyleDataProcessed())

        lifestyle_questions = ["sun_exposure", "stress_level", "sleep_quality"]
        for question_id in lifestyle_questions:
            if question_id not in self.asked_questions:
                self.declare(QuestionAsked(question_id=question_id))
                self.asked_questions.add(question_id)
                self._declare_cf(question_id, 0.8)

        self._log_message("Moving to analysis phase...")

        self._change_phase(QuestionPhase.ANALYSIS)
        self._declare_cf("phase_transition_analysis", 0.95)

    # =============================================================================
    # PHASE 8: ANALYSIS RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.ANALYSIS),
          NOT(ConditionScore()),
          salience=90)
    def calculate_condition_scores(self):
        """Rule: Calculate scores for different conditions with CF"""
        # Extract responses from facts
        for _fact in self.facts.values():
            if isinstance(_fact, UserResponse):
                self.user_responses[_fact['question_id']] = _fact['value']

        self.condition_scores = self.condition_scorer.calculate_all_scores(self.user_responses)

        for condition, data in self.condition_scores.items():
            self.declare(ConditionScore(condition=condition, score=data['score'], cf=data['cf']))

        self.declare(ConfidenceFactor(rule="calculate_scores", cf=0.9))

    @Rule(CurrentPhase(phase=QuestionPhase.ANALYSIS),
          ConditionScore(),
          NOT(SkinProfile()),
          salience=85)
    def determine_skin_profile(self):
        """Rule: Determine overall skin profile"""
        self.skin_profile = SkinProfileAnalyzer.determine_skin_profile(self.user_responses)

        self.declare(SkinProfile(
            skin_type=self.skin_profile['type'],
            sensitivity=self.skin_profile['sensitivity'],
            hydration=self.skin_profile['hydration']
        ))
        self.declare(ConfidenceFactor(rule="skin_profile", cf=0.85))

    @Rule(CurrentPhase(phase=QuestionPhase.ANALYSIS),
          ConditionScore(),
          SkinProfile(),
          NOT(RecommendationGenerated()),
          salience=80)
    def generate_recommendations(self):
        """Rule: Generate personalized recommendations with medical referral handling"""
        medical_referral_required = False
        for _fact in self.facts.values():
            if isinstance(_fact, MedicalReferralRequired):
                medical_referral_required = True
                break

        severity_level, condition_classification, primary_condition, auto_referral = \
            SeverityAnalyzer.determine_severity_level(self.condition_scores, self.user_responses)

        if auto_referral:
            medical_referral_required = True

        self.severity_level = severity_level
        self.condition_classification = condition_classification
        self.primary_condition = primary_condition
        self.medical_referral_required = medical_referral_required

        self.recommendations = self.recommendation_generator.generate_all_recommendations(
            condition_classification, self.skin_profile, primary_condition,
            self.user_responses, self.condition_scores, medical_referral_required
        )

        self.declare(RecommendationGenerated())
        self.declare(ConfidenceFactor(rule="generate_recommendations", cf=0.9))
        print("✅ Recommendations generated!")

    @Rule(CurrentPhase(phase=QuestionPhase.ANALYSIS),
          RecommendationGenerated(),
          salience=75)
    def move_to_complete(self):
        """Rule: Transition to completion phase"""
        print("\n🏁 Moving to completion phase...")
        self._change_phase(QuestionPhase.COMPLETE)
        self._declare_cf("phase_transition_complete", 1.0)

    # =============================================================================
    # PHASE 9: COMPLETION RULES
    # =============================================================================

    @Rule(CurrentPhase(phase=QuestionPhase.COMPLETE),
          salience=100)
    def display_results(self):
        """Rule: Store final analysis and recommendations"""
        self.analysis_result = self._display_complete_analysis()
        self._declare_cf("display_results", 1.0)
        self.halt()

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def _change_phase(self, new_phase):
        """Utility to change the current phase"""
        for f in list(self.facts.values()):
            if isinstance(f, CurrentPhase):
                self.retract(f)
        self.declare(CurrentPhase(phase=new_phase))

    def _display_complete_analysis(self):
        """Generate comprehensive analysis results as structured data for API"""
        from datetime import datetime

        analysis_result = {
            'medical_referral': {
                'required': self.medical_referral_required,
                'message': None,
                'reasons': []
            },
            'overall_assessment': {
                'severity_level': getattr(self.severity_level, "value", "UNKNOWN"),
                'condition_classification': self.condition_classification,
                'primary_condition': self.primary_condition,
                'status_message': None
            },
            'condition_analysis': {
                'conditions': [],
                'weighted_scores': {}
            },
            'skin_profile': {
                'type': self.skin_profile.get('type', 'Unknown'),
                'sensitivity': self.skin_profile.get('sensitivity', 'Unknown'),
                'hydration': self.skin_profile.get('hydration', 'Unknown')
            },
            'allergen_sensitivities': {
                'has_sensitivities': False,
                'high_risk_allergens': [],
                'avoid_ingredients': []
            },
            'hormonal_factors': {
                'is_female': False,
                'has_hormonal_acne': False,
                'cycle_severity': None,
                'birth_control_use': False
            },
            'recommendations': {
                'medical_referral': None,
                'skincare_routine': None,
                'lifestyle': []
            },
            'confidence_metrics': {
                'average_cf': 0.0,
                'total_rules_fired': 0
            },
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'engine_version': '2.0',
                'disclaimers': [
                    "This analysis is educational only, not a medical diagnosis.",
                    "Consult healthcare professionals for medical concerns."
                ]
            }
        }

        try:
            # Medical referral status
            if self.medical_referral_required:
                analysis_result['medical_referral']['message'] = "MEDICAL REFERRAL REQUIRED"
                for rec_type, rec_data in self.recommendations:
                    if rec_type == "Medical Referral":
                        analysis_result['medical_referral']['reasons'] = rec_data.get('reasons', [])
                        analysis_result['recommendations']['medical_referral'] = rec_data
                        break

            all_scores_low = True
            max_weighted_score = 0

            if self.condition_scores:
                for condition, data in self.condition_scores.items():
                    weighted_score = data['score'] * data['cf']
                    if weighted_score > max_weighted_score:
                        max_weighted_score = weighted_score
                    if weighted_score >= 10:  # Threshold for considering a condition significant
                        all_scores_low = False

            # Overall assessment status
            if all_scores_low and max_weighted_score < 10:
                analysis_result['overall_assessment'][
                    'status_message'] = "HEALTHY - No significant skin conditions detected"
                analysis_result['overall_assessment']['condition_classification'] = "HEALTHY"
                analysis_result['overall_assessment']['primary_condition'] = "none"
            elif self.condition_classification == "SEVERE" or self.medical_referral_required:
                analysis_result['overall_assessment']['status_message'] = "PROFESSIONAL MEDICAL ATTENTION REQUIRED"
            elif self.condition_classification == "MODERATE":
                analysis_result['overall_assessment'][
                    'status_message'] = "MODERATE CONDITION DETECTED - Monitor closely"
            else:
                analysis_result['overall_assessment'][
                    'status_message'] = "MILD CONDITION DETECTED - Manageable with proper care"

            if self.condition_scores:
                sorted_conditions = sorted(
                    self.condition_scores.items(),
                    key=lambda x: x[1]['score'] * x[1]['cf'],
                    reverse=True
                )

                for condition, data in sorted_conditions:
                    if data['score'] > 0:
                        condition_name = condition.replace('_', ' ').title()
                        score = data['score']
                        cf = data['cf']
                        weighted_score = score * cf

                        if weighted_score >= 70:
                            risk_level = "High likelihood"
                            risk_color = "red"
                        elif weighted_score >= 40:
                            risk_level = "Moderate likelihood"
                            risk_color = "yellow"
                        elif weighted_score >= 20:
                            risk_level = "Low-moderate likelihood"
                            risk_color = "orange"
                        elif weighted_score >= 10:
                            risk_level = "Low likelihood"
                            risk_color = "green"
                        else:
                            continue

                        condition_info = {
                            'name': condition_name,
                            'raw_score': score,
                            'confidence_factor': cf,
                            'weighted_score': round(weighted_score, 1),
                            'risk_level': risk_level,
                            'risk_color': risk_color
                        }

                        analysis_result['condition_analysis']['conditions'].append(condition_info)
                        analysis_result['condition_analysis']['weighted_scores'][condition] = weighted_score

            allergen_profile = self.skin_profile.get('allergen_profile', {})
            if allergen_profile.get('high_risk_allergens'):
                analysis_result['allergen_sensitivities']['has_sensitivities'] = True
                analysis_result['allergen_sensitivities']['high_risk_allergens'] = allergen_profile[
                    'high_risk_allergens']
                analysis_result['allergen_sensitivities']['avoid_ingredients'] = allergen_profile.get(
                    'avoid_ingredients', [])

            is_female = self.user_responses.get("gender") == 2
            has_cycle_acne = self.user_responses.get("menstrual_cycle_acne", 1) > 1

            analysis_result['hormonal_factors']['is_female'] = is_female
            analysis_result['hormonal_factors']['has_hormonal_acne'] = is_female and has_cycle_acne

            if is_female and has_cycle_acne:
                cycle_severity = self.user_responses.get("menstrual_cycle_acne", 1)
                analysis_result['hormonal_factors']['cycle_severity'] = cycle_severity
                analysis_result['hormonal_factors']['birth_control_use'] = self.user_responses.get(
                    "hormonal_birth_control", 1) > 1

            for rec_type, rec_data in self.recommendations:
                if rec_type == "Skincare Routine":
                    analysis_result['recommendations']['skincare_routine'] = rec_data
                elif rec_type == "Lifestyle Recommendations":
                    analysis_result['recommendations']['lifestyle'] = rec_data
            total_cf = sum(f.get('cf', 0) for f in self.facts.values() if hasattr(f, 'get') and 'cf' in f)
            cf_count = sum(1 for f in self.facts.values() if hasattr(f, 'get') and 'cf' in f)

            if cf_count > 0:
                analysis_result['confidence_metrics']['average_cf'] = round(total_cf / cf_count, 2)
                analysis_result['confidence_metrics']['total_rules_fired'] = cf_count

        except Exception as e:
            pass
        self.analysis_result = analysis_result

        level = analysis_result['overall_assessment']['severity_level']
        self._log_message(f"Analysis completed: {level} condition detected", level="info")
        if self.medical_referral_required:
            self._log_message("Medical referral required", level="warning")

        return analysis_result
def _static_choice_count(choices: List[int]) -> int:
    """Static version of choice_count for use in lambda functions."""
    return len(choices)

def _static_has_all_choices(choices: List[int], target_choices: List[int]) -> bool:
    """Static version of has_all_choices for use in lambda functions."""
    return all(choice in choices for choice in target_choices)


def _static_has_any_choice(choices: List[int], target_choices: List[int]) -> bool:
    """Static version of has_any_choice for use in lambda functions."""
    return any(choice in choices for choice in target_choices)


def _static_has_choice(choices: List[int], target_choice: int) -> bool:
    """Static version of has_choice for use in lambda functions."""
    return target_choice in choices
def _static_normalize_choice_value(value: Any) -> List[int]:
    """Static version of normalize_choice_value for use in lambda functions."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value if v is not None]
    return [int(value)]

def _static_get_single_value(value: Any) -> Optional[int]:
    """Get single value from either single value or list."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return int(value[0]) if value else None
    return int(value)

def _static_has_exact_value(value: Any, target: int) -> bool:
    """Check if value exactly matches target, handling both single values and lists."""
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return len(value) == 1 and value[0] == target
    return value == target