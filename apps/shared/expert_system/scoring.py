"""
Enhanced scoring logic with Confidence Factors and Melasma Detection - FIXED VERSION with NULL handling
"""

from apps.shared.enums import SeverityLevelChoices
from apps.analysis.models import SkinCondition

class ConditionScorer:
    """Enhanced scoring with confidence factors and melasma detection - all bugs fixed including null handling"""

    def __init__(self):
        self.condition_scores = {
            condition.condition_name: {'score': 0, 'cf': 0.0}
            for condition in SkinCondition.objects.all()
        }

    def _safe_get(self, responses, key, default=1):
        """Safely get a value from responses, handling None values and lists"""
        value = responses.get(key, default)
        if value is None:
            return default

        # Handle both single values and lists
        if isinstance(value, (list, tuple)):
            # For multi-choice questions, return the first value for numeric comparisons
            return value[0] if value else default
        return value

    def calculate_all_scores(self, user_responses):
        """Calculate scores with confidence factors for all conditions"""
        self._calculate_vitiligo_score(user_responses)
        self._calculate_rosacea_score(user_responses)
        self._calculate_eczema_score(user_responses)
        self._calculate_psoriasis_score(user_responses)
        self._calculate_acne_score(user_responses)
        self._calculate_melasma_score(user_responses)
        return self.condition_scores

    def _update_condition_score(self, condition, points, confidence):
        """Update condition score with confidence factor"""
        current = self.condition_scores.get(condition, {'score': 0, 'cf': 0.0})

        # Combine scores using confidence-weighted approach
        new_score = current['score'] + points

        # Combine confidence factors (modified Dempster-Shafer approach)
        if current['cf'] == 0:
            new_cf = confidence
        else:
            new_cf = current['cf'] + confidence * (1 - current['cf'])

        self.condition_scores[condition] = {
            'score': min(new_score, 100),  # Cap at 100
            'cf': min(new_cf, 1.0)  # Cap at 1.0
        }

    def _calculate_vitiligo_score(self, responses):
        """Calculate vitiligo score with confidence factors"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 2:
            self._update_condition_score("vitiligo", 30, 0.9)

        family_history = self._safe_get(responses, "family_history", [])
        if isinstance(family_history, (list, tuple)):
            if 2 in family_history:  # Vitiligo in family
                self._update_condition_score("vitiligo", 20, 0.7)
        elif family_history == 2:
            self._update_condition_score("vitiligo", 20, 0.7)

        vitiligo_spots = self._safe_get(responses, "vitiligo_spots", 1)
        if vitiligo_spots > 1:
            confidence = 0.8 if vitiligo_spots >= 4 else 0.6
            points = 25 + (vitiligo_spots - 2) * 5
            self._update_condition_score("vitiligo", points, confidence)

        # Check for multiple locations
        vitiligo_location = self._safe_get(responses, "vitiligo_location", [])
        if isinstance(vitiligo_location, (list, tuple)) and len(vitiligo_location) > 1:
            points = len(vitiligo_location) * 3
            self._update_condition_score("vitiligo", points, 0.7)

    def _calculate_rosacea_score(self, responses):
        """Calculate rosacea score with confidence factors"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 3:
            self._update_condition_score("rosacea", 30, 0.9)

        family_history = self._safe_get(responses, "family_history", [])
        if isinstance(family_history, (list, tuple)):
            if 3 in family_history:  # Rosacea in family
                self._update_condition_score("rosacea", 15, 0.6)
        elif family_history == 3:
            self._update_condition_score("rosacea", 15, 0.6)

        redness = self._safe_get(responses, "rosacea_redness", 1)
        if redness > 1:
            points = redness * 6
            confidence = 0.9 if redness >= 4 else 0.7
            self._update_condition_score("rosacea", points, confidence)

        # Check for multiple triggers
        triggers = self._safe_get(responses, "rosacea_triggers", [])
        if isinstance(triggers, (list, tuple)) and len(triggers) > 2:
            points = len(triggers) * 3
            self._update_condition_score("rosacea", points, 0.8)

    def _calculate_eczema_score(self, responses):
        """Calculate eczema score with confidence factors"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 4:
            self._update_condition_score("eczema", 30, 0.9)

        family_history = responses.get("family_history", []) or []
        if isinstance(family_history, (list, tuple)):
            if 4 in family_history:  # Eczema in family
                self._update_condition_score("eczema", 15, 0.7)
        elif family_history == 4:
            self._update_condition_score("eczema", 15, 0.7)

        itching = self._safe_get(responses, "eczema_itching", 1)
        if itching > 1:
            points = itching * 6
            confidence = 0.9 if itching >= 4 else 0.7
            self._update_condition_score("eczema", points, confidence)

        sensitivity = self._safe_get(responses, "product_sensitivity", 1)
        if sensitivity >= 4:
            self._update_condition_score("eczema", 15, 0.6)

        # Check for multiple triggers
        triggers = responses.get("eczema_triggers", []) or []
        if isinstance(triggers, (list, tuple)) and len(triggers) > 2:
            points = len(triggers) * 2
            self._update_condition_score("eczema", points, 0.7)

    def _calculate_psoriasis_score(self, responses):
        """Calculate psoriasis score with confidence factors"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 5:
            self._update_condition_score("psoriasis", 30, 0.9)

        family_history = self._safe_get(responses, "family_history", [])
        if isinstance(family_history, (list, tuple)):
            if 5 in family_history:  # Psoriasis in family
                self._update_condition_score("psoriasis", 20, 0.8)
        elif family_history == 5:
            self._update_condition_score("psoriasis", 20, 0.8)

    def _calculate_acne_score(self, responses):
        """Calculate acne score with confidence factors"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 6:
            self._update_condition_score("severe_acne", 30, 0.9)

        t_zone = self._safe_get(responses, "t_zone_oiliness", 1)
        if t_zone >= 4:
            points = (t_zone - 3) * 10
            confidence = 0.8 if t_zone == 5 else 0.6
            self._update_condition_score("severe_acne", points, confidence)

        pore_size = self._safe_get(responses, "pore_size", 1)
        if pore_size >= 4:
            self._update_condition_score("severe_acne", 15, 0.7)

        stress = self._safe_get(responses, "stress_level", 1)
        if stress >= 4:
            self._update_condition_score("severe_acne", 10, 0.5)

        # Hormonal factors for females
        gender = self._safe_get(responses, "gender", 1)
        if gender == 2:
            menstrual_impact = self._safe_get(responses, "menstrual_cycle_acne", 1)
            if menstrual_impact >= 4:
                self._update_condition_score("severe_acne", 20, 0.8)
            elif menstrual_impact >= 3:
                self._update_condition_score("severe_acne", 15, 0.7)
            elif menstrual_impact >= 2:
                self._update_condition_score("severe_acne", 10, 0.6)

            birth_control = self._safe_get(responses, "hormonal_birth_control", 1)
            if birth_control >= 2:
                self._update_condition_score("severe_acne", 5, 0.4)

    def _calculate_melasma_score(self, responses):
        """Calculate melasma score with confidence factors - VERY CONSERVATIVE for pregnancy"""
        screening_main = self._safe_get(responses, "screening_main", 1)
        if screening_main == 8:
            self._update_condition_score("melasma", 20, 0.8)  # Further reduced from 25

        melasma_patches = self._safe_get(responses, "melasma_patches", 1)
        if melasma_patches > 1:
            # Very conservative scoring based on patch size
            if melasma_patches == 2:  # Small patches
                points = 8  # Reduced from 10
                confidence = 0.6
            elif melasma_patches == 3:  # Medium patches
                points = 15  # Reduced from 20
                confidence = 0.7
            elif melasma_patches == 4:  # Large patches
                points = 25  # Reduced from 30
                confidence = 0.8
            else:  # Widespread
                points = 35  # Reduced from 40
                confidence = 0.9
            self._update_condition_score("melasma", points, confidence)

        # Check melasma location - facial involvement is VERY COMMON for melasma
        melasma_location = self._safe_get(responses, "melasma_location", [])
        if isinstance(melasma_location, (list, tuple)):
            if 1 in melasma_location:  # Face - very common location, minimal points
                self._update_condition_score("melasma", 5, 0.6)  # Further reduced from 8
            if len(melasma_location) > 1:  # Multiple locations - more concerning
                points = len(melasma_location) * 3  # Reduced multiplier
                self._update_condition_score("melasma", points, 0.7)
        elif isinstance(melasma_location, int) and melasma_location == 1:  # Face (single choice)
            self._update_condition_score("melasma", 5, 0.6)  # Further reduced from 8

        # Check triggers - VERY CONSERVATIVE for common causes
        triggers = self._safe_get(responses, "melasma_triggers", [])
        if isinstance(triggers, (list, tuple)):
            # Sun exposure is major trigger but common
            if 1 in triggers:  # Sun exposure
                self._update_condition_score("melasma", 8, 0.7)  # Reduced from 12
            # Hormonal triggers - pregnancy is EXTREMELY common, minimal points
            if 2 in triggers:  # Pregnancy - extremely common cause
                self._update_condition_score("melasma", 3, 0.5)  # Much further reduced
            elif 3 in triggers:  # Other hormonal changes
                self._update_condition_score("melasma", 6, 0.6)  # Reduced from 8
            # Multiple triggers - only if really multiple
            if len(triggers) > 3:  # More than 3 triggers is concerning
                points = (len(triggers) - 3) * 2
                self._update_condition_score("melasma", points, 0.6)
        elif isinstance(triggers, int):  # Single value (backward compatibility)
            if triggers == 1:  # Sun exposure
                self._update_condition_score("melasma", 8, 0.7)
            elif triggers == 2:  # Pregnancy
                self._update_condition_score("melasma", 3, 0.5)
            elif triggers == 3:  # Other hormonal changes
                self._update_condition_score("melasma", 6, 0.6)

        # Pregnancy/hormonal factors for females ONLY - EXTREMELY CONSERVATIVE
        gender = self._safe_get(responses, "gender", 1)
        if gender == 2:  # Only for females
            pregnancy_hormones = self._safe_get(responses, "melasma_pregnancy_hormones", [])
            if isinstance(pregnancy_hormones, (list, tuple)):
                if len(pregnancy_hormones) > 0 and 1 not in pregnancy_hormones:  # Not "No hormonal changes"
                    # Extremely conservative scoring for hormonal causes
                    if 2 in pregnancy_hormones:  # Currently pregnant
                        points = 5  # Very minimal - pregnancy melasma is normal
                        confidence = 0.6
                        self._update_condition_score("melasma", points, confidence)
                    elif 3 in pregnancy_hormones:  # Recently pregnant
                        points = 7  # Still minimal - common postpartum
                        confidence = 0.6
                        self._update_condition_score("melasma", points, confidence)
                    elif 4 in pregnancy_hormones:  # Started birth control
                        points = 4  # Very minimal - common side effect
                        confidence = 0.5
                        self._update_condition_score("melasma", points, confidence)
                    else:
                        # Other hormonal factors - more concerning
                        points = len(pregnancy_hormones) * 4  # Further reduced multiplier
                        confidence = 0.5
                        self._update_condition_score("melasma", points, confidence)
            elif isinstance(pregnancy_hormones, int) and pregnancy_hormones > 1:  # Handle single value
                if pregnancy_hormones == 2:  # Currently pregnant
                    points = 5
                    confidence = 0.6
                elif pregnancy_hormones == 4:  # Birth control
                    points = 4
                    confidence = 0.5
                else:
                    points = pregnancy_hormones * 4
                    confidence = 0.5
                self._update_condition_score("melasma", points, confidence)

        # Gender and age factors - MINIMAL
        if gender == 2:  # Female
            self._update_condition_score("melasma", 3, 0.4)  # Further reduced from 5

            # Age factor - melasma more common in reproductive age
            age = self._safe_get(responses, "age", 1)
            if 2 <= age <= 4:  # Ages 18-45
                self._update_condition_score("melasma", 2, 0.3)  # Further reduced from 3
        elif gender == 1:  # Male - melasma is rare
            # For males, reduce base confidence and don't add hormonal factors
            self._update_condition_score("melasma", -3, 0.3)  # Less penalty

        # Sun exposure factor - CONSERVATIVE
        sun_exposure = self._safe_get(responses, "sun_exposure", 1)
        if sun_exposure >= 4:
            self._update_condition_score("melasma", 8, 0.7)  # Reduced from 10
        elif sun_exposure >= 3:
            self._update_condition_score("melasma", 5, 0.6)  # Reduced from 6


class SeverityAnalyzer:
    """Enhanced severity analysis with confidence factors"""

    @staticmethod
    def determine_severity_level(condition_scores, user_responses):
        """Determine severity with confidence-adjusted scoring"""
        # Find highest confidence-weighted score
        max_weighted_score = 0
        max_condition = "none"

        for condition, data in condition_scores.items():
            weighted_score = data['score'] * data['cf']
            if weighted_score > max_weighted_score:
                max_weighted_score = weighted_score
                max_condition = condition

        # Check for medical referral conditions
        medical_referral_required = SeverityAnalyzer._check_medical_referral_conditions(
            condition_scores, user_responses
        )

        if medical_referral_required:
            return SeverityLevelChoices.SEVERE, "SEVERE", max_condition, True

        # Safe get with default values
        condition_duration = user_responses.get("condition_duration", 1) or 1
        if isinstance(condition_duration, (list, tuple)):
            condition_duration = condition_duration[0] if condition_duration else 1

        condition_severity = user_responses.get("condition_severity", 1) or 1
        if isinstance(condition_severity, (list, tuple)):
            condition_severity = condition_severity[0] if condition_severity else 1

        previous_treatments = user_responses.get("previous_treatments", []) or []

        # Calculate severity multiplier
        severity_multiplier = 1.0

        if condition_duration >= 5:
            severity_multiplier += 0.3
        elif condition_duration >= 4:
            severity_multiplier += 0.2
        elif condition_duration >= 3:
            severity_multiplier += 0.1

        if condition_severity >= 4:
            severity_multiplier += 0.4
        elif condition_severity >= 3:
            severity_multiplier += 0.2
        elif condition_severity >= 2:
            severity_multiplier += 0.1

        # Handle previous treatments (handle both list and single value)
        treatment_multiplier = 0.0
        if isinstance(previous_treatments, (list, tuple)):
            # For multi-select treatments
            if len(previous_treatments) >= 3 or 4 in previous_treatments or 5 in previous_treatments:
                treatment_multiplier = 0.3
            elif len(previous_treatments) >= 2 or 3 in previous_treatments:
                treatment_multiplier = 0.2
            elif 2 in previous_treatments:
                treatment_multiplier = 0.1
        else:
            # For single value treatments (backward compatibility)
            if previous_treatments >= 4:
                treatment_multiplier = 0.3
            elif previous_treatments >= 3:
                treatment_multiplier = 0.2
            elif previous_treatments >= 2:
                treatment_multiplier = 0.1

        severity_multiplier += treatment_multiplier

        adjusted_score = max_weighted_score * severity_multiplier

        # Determine classification with PREGNANCY-SPECIFIC logic
        # Special handling for pregnancy melasma (very common and often mild)
        is_pregnancy_related = False
        pregnancy_hormones = user_responses.get("melasma_pregnancy_hormones", []) or []
        triggers = user_responses.get("melasma_triggers", []) or []

        if isinstance(pregnancy_hormones, (list, tuple)):
            is_pregnancy_related = 2 in pregnancy_hormones  # Currently pregnant
        elif isinstance(triggers, (list, tuple)):
            is_pregnancy_related = 2 in triggers  # Pregnancy trigger

        # For pregnancy melasma, use more lenient thresholds
        if is_pregnancy_related and condition_severity <= 2:
            severe_conditions = (
                adjusted_score >= 90 or  # Much higher threshold for pregnancy
                condition_severity >= 4 or
                condition_duration >= 5  # Only if very long duration
            )

            moderate_conditions = (
                adjusted_score >= 70 or  # Higher threshold for pregnancy
                condition_severity >= 3 or
                (condition_duration >= 4 and max_weighted_score >= 50)
            )
        else:
            # Normal thresholds for non-pregnancy melasma
            severe_conditions = (
                adjusted_score >= 80 or
                condition_severity >= 4 or
                (max_weighted_score >= 70 and treatment_multiplier >= 0.3) or
                (condition_duration >= 5 and condition_severity >= 3)
            )

            moderate_conditions = (
                adjusted_score >= 50 or
                condition_severity >= 3 or
                max_weighted_score >= 60 or
                (condition_duration >= 4 and max_weighted_score >= 40)
            )

        if severe_conditions:
            severity_level = SeverityLevelChoices.SEVERE
            condition_classification = "SEVERE"
        elif moderate_conditions:
            severity_level = SeverityLevelChoices.MODERATE
            condition_classification = "MODERATE"
        else:
            severity_level = SeverityLevelChoices.MILD
            condition_classification = "MILD"

        primary_condition = max_condition if max_weighted_score > 20 else "none"

        return severity_level, condition_classification, primary_condition, False

    @staticmethod
    def _check_medical_referral_conditions(condition_scores, user_responses):
        """Check for specific conditions requiring immediate medical referral"""
        # Vitiligo facial involvement
        vitiligo_score = condition_scores.get("vitiligo", {}).get('score', 0)
        if vitiligo_score > 30:  # Likely vitiligo
            vitiligo_location = user_responses.get("vitiligo_location", []) or []
            if isinstance(vitiligo_location, (list, tuple)):
                if 1 in vitiligo_location or 5 in vitiligo_location:  # Face or around eyes
                    return True
            elif vitiligo_location == 1:  # Face (single choice)
                return True

        # Eczema facial involvement or severe symptoms
        eczema_score = condition_scores.get("eczema", {}).get('score', 0)
        if eczema_score > 30:  # Likely eczema
            # Check location
            eczema_location = user_responses.get("eczema_location", []) or []
            if isinstance(eczema_location, (list, tuple)):
                if 1 in eczema_location:  # Face
                    return True
            elif eczema_location == 1:  # Face (single choice)
                return True

            # Check for severe itching
            eczema_itching = user_responses.get("eczema_itching", 1) or 1
            if eczema_itching >= 4:  # Severe itching
                return True

        return False


class SkinProfileAnalyzer:
    """Enhanced skin profile analysis"""

    @staticmethod
    def determine_skin_profile(user_responses):
        """Determine skin profile with enhanced allergen analysis"""

        # Helper function to safely extract single values from responses
        def get_single_value(key, default=1):
            value = user_responses.get(key, default) or default
            if isinstance(value, (list, tuple)):
                return value[0] if value else default
            return value

        # Skin type determination
        t_zone = get_single_value("t_zone_oiliness", 3)
        cheeks = get_single_value("cheek_oiliness", 3)

        if t_zone <= 2 and cheeks <= 2:
            skin_type = "Dry"
        elif t_zone >= 4 and cheeks >= 4:
            skin_type = "Oily"
        elif t_zone >= 4 and cheeks <= 3:
            skin_type = "Combination"
        else:
            skin_type = "Normal"

        # Sensitivity determination
        sensitivity_level = get_single_value("product_sensitivity", 1)
        if sensitivity_level <= 2:
            sensitivity = "Low"
        elif sensitivity_level <= 3:
            sensitivity = "Moderate"
        else:
            sensitivity = "High"

        # Hydration determination
        dryness = get_single_value("dryness_feeling", 1)
        if dryness <= 2:
            hydration = "Well-hydrated"
        elif dryness <= 3:
            hydration = "Moderate hydration needs"
        else:
            hydration = "High hydration needs"

        # Enhanced allergen analysis
        allergen_profile = SkinProfileAnalyzer._analyze_allergen_sensitivity(user_responses)

        return {
            'type': skin_type,
            'sensitivity': sensitivity,
            'hydration': hydration,
            'allergen_profile': allergen_profile
        }

    @staticmethod
    def _analyze_allergen_sensitivity(responses):
        """Enhanced allergen sensitivity analysis with null handling"""
        allergen_profile = {
            'fragrance_sensitivity': responses.get("fragrance_sensitivity", 1) or 1,
            'preservative_sensitivity': responses.get("preservative_sensitivity", 1) or 1,
            'metal_sensitivity': responses.get("metal_sensitivity", 1) or 1,
            'botanical_sensitivity': responses.get("botanical_sensitivity", 1) or 1,
            'high_risk_allergens': [],
            'avoid_ingredients': []
        }
        
        # Identify high-risk allergens with confidence factors
        if allergen_profile['fragrance_sensitivity'] >= 4:
            allergen_profile['high_risk_allergens'].append('fragrances')
            allergen_profile['avoid_ingredients'].extend([
                'parfum', 'fragrance', 'essential oils', 'citrus oils'
            ])
            
        if allergen_profile['preservative_sensitivity'] >= 3:
            allergen_profile['high_risk_allergens'].append('preservatives')
            allergen_profile['avoid_ingredients'].extend([
                'parabens', 'formaldehyde releasers', 'methylisothiazolinone'
            ])
            
        if allergen_profile['metal_sensitivity'] >= 3:
            allergen_profile['high_risk_allergens'].append('metals')
            allergen_profile['avoid_ingredients'].extend([
                'nickel', 'chromium', 'titanium dioxide (in some formulations)'
            ])
            
        if allergen_profile['botanical_sensitivity'] >= 4:
            allergen_profile['high_risk_allergens'].append('botanicals')
            allergen_profile['avoid_ingredients'].extend([
                'tea tree oil', 'lavender oil', 'chamomile', 'arnica'
            ])
        return allergen_profile