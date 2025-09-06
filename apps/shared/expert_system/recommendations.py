"""
Enhanced recommendation generation with medical referral handling and Melasma Treatment
"""


class RecommendationGenerator:
    """Enhanced recommendation generator with medical referral support and melasma treatment"""
    
    def __init__(self):
        self.recommendations = []
    
    def generate_all_recommendations(self, condition_classification, skin_profile, 
                                   primary_condition, user_responses, condition_scores=None,
                                   medical_referral_required=False):
        """Generate recommendations with medical referral handling"""
        self.recommendations = []
        
        if medical_referral_required or condition_classification == "SEVERE":
            self._generate_medical_referral(condition_classification, primary_condition, 
                                          medical_referral_required)
        else:
            self._generate_skincare_routine(condition_classification, skin_profile, 
                                          primary_condition, user_responses)
        
        self._generate_lifestyle_recommendations(skin_profile, user_responses, condition_scores)
        return self.recommendations
    
    def _generate_medical_referral(self, condition_classification, primary_condition, 
                                 facial_involvement=False):
        """Generate medical referral recommendations"""
        referral_reasons = []
        
        if facial_involvement:
            if primary_condition == "vitiligo":
                referral_reasons.append("Vitiligo affecting facial area detected")
                referral_reasons.append("Facial vitiligo requires specialized treatment")
            elif primary_condition == "eczema":
                referral_reasons.append("Eczema affecting facial area detected")
                referral_reasons.append("Facial eczema can be complex and requires professional care")
        
        if condition_classification == "SEVERE":
            referral_reasons.append("Severe skin condition detected")
        
        self.recommendations.append(("Medical Referral", {
            'message': "⚠️ MEDICAL ATTENTION REQUIRED",
            'reasons': referral_reasons,
            'instructions': [
                "Schedule an appointment with a dermatologist as soon as possible",
                "Bring this analysis report to your appointment",
                "Document symptoms with photos if possible",
                "List all current medications and treatments tried",
                "Do not attempt self-treatment until seen by a doctor"
            ],
            'urgency_signs': [
                "Rapid spreading of symptoms",
                "Severe pain or discomfort", 
                "Signs of infection (pus, fever, red streaking)",
                "Difficulty sleeping due to symptoms",
                "Significant impact on daily activities"
            ],
            'specialist_notes': [
                "Dermatologist consultation recommended within 1-2 weeks",
                "Consider patch testing for allergen identification",
                "Discuss treatment options and prognosis",
                "Regular follow-up appointments may be needed"
            ]
        }))
    
    def _generate_skincare_routine(self, condition_classification, skin_profile, 
                                 primary_condition, user_responses):
        """Generate skincare routine for mild/moderate conditions"""
        skin_type = skin_profile['type']
        sensitivity = skin_profile['sensitivity']
        hydration = skin_profile['hydration']
        
        routine = {
            'morning': [],
            'evening': [],
            'weekly': [],
            'notes': []
        }

        # Add condition-specific note
        if condition_classification == "MODERATE":
            routine['notes'].append("⚠️ MODERATE CONDITION: Monitor symptoms closely. If no improvement in 4-6 weeks, consult a dermatologist.")
        else:
            routine['notes'].append("✅ MILD CONDITION: This routine should help manage your symptoms effectively.")

        # Basic cleansing recommendations
        self._add_cleansing_recommendations(routine, skin_type, condition_classification)
        
        # Moisturizer recommendations
        self._add_moisturizer_recommendations(routine, skin_type, hydration)
        
        # Sun protection
        routine['morning'].append("Broad-spectrum SPF 30+ sunscreen (reapply every 2 hours)")

        # Sensitivity considerations
        if sensitivity == "High":
            routine['notes'].append("🔍 HIGH SENSITIVITY: Choose fragrance-free, hypoallergenic products only")
            routine['notes'].append("🧪 PATCH TEST: Test all new products on a small skin area first")

        # Condition-specific treatments
        self._add_condition_specific_treatments(routine, primary_condition, condition_classification, user_responses)

        # Allergen-specific recommendations
        self._add_allergen_specific_recommendations(routine, skin_profile)

        # General care instructions
        routine['notes'].append("💧 HYDRATION: Drink 8+ glasses of water daily")
        routine['notes'].append("🛁 BATHING: Use lukewarm water, limit to 10-15 minutes")
        routine['notes'].append("👕 CLOTHING: Choose soft, breathable fabrics")

        self.recommendations.append(("Skincare Routine", routine))
    
    @staticmethod
    def _add_cleansing_recommendations(routine, skin_type, condition_classification):
        """Add cleansing recommendations based on skin type"""
        if skin_type == "Dry":
            routine['morning'].append("Gentle cream cleanser (fragrance-free)")
            routine['evening'].append("Gentle cream cleanser (fragrance-free)")
        elif skin_type == "Oily":
            if condition_classification == "MODERATE":
                routine['morning'].append("Gentle foaming cleanser (avoid harsh ingredients)")
                routine['evening'].append("Mild salicylic acid cleanser (2-3 times per week)")
            else:
                routine['morning'].append("Foaming cleanser with salicylic acid")
                routine['evening'].append("Deep cleansing gel")
        elif skin_type == "Combination":
            routine['morning'].append("Gentle foaming cleanser")
            routine['evening'].append("Balancing gel cleanser")
        else:  # Normal
            routine['morning'].append("Mild foaming cleanser")
            routine['evening'].append("Gentle cleansing gel")
    
    @staticmethod
    def _add_moisturizer_recommendations(routine, skin_type, hydration):
        """Add moisturizer recommendations based on hydration needs"""
        if hydration == "High hydration needs":
            if skin_type == "Oily":
                routine['morning'].append("Lightweight hyaluronic acid moisturizer")
                routine['evening'].append("Hydrating gel cream with ceramides")
            else:
                routine['morning'].append("Rich moisturizing cream with ceramides")
                routine['evening'].append("Intensive repair cream")
        elif hydration == "Moderate hydration needs":
            routine['morning'].append("Daily moisturizer with SPF 30+")
            routine['evening'].append("Hydrating night moisturizer")
        else:  # Well-hydrated
            routine['morning'].append("Light daily moisturizer with SPF 30+")
            routine['evening'].append("Light night moisturizer")
            
    @staticmethod
    def _add_condition_specific_treatments(routine, primary_condition, condition_classification, user_responses):
        """Add condition-specific treatments including melasma"""
        if primary_condition == "vitiligo" and condition_classification != "SEVERE":
            if condition_classification == "MODERATE":
                routine['morning'].append("Topical corticosteroid (mild strength - consult pharmacist)")
                routine['evening'].append("Vitamin D analog cream (consult pharmacist)")
                routine['weekly'].append("Limited sun exposure with protection (consult dermatologist)")
            else:  # MILD
                routine['morning'].append("Vitamin E oil or cream")
                routine['evening'].append("Zinc oxide-based products")
                routine['weekly'].append("Gentle sun exposure (10-15 minutes with SPF)")
                
        elif primary_condition == "rosacea" and condition_classification != "SEVERE":
            if condition_classification == "MODERATE":
                routine['morning'].append("Green-tinted primer or makeup")
                routine['evening'].append("Azelaic acid cream (consult pharmacist)")
                routine['weekly'].append("Gentle exfoliation (once per week max)")
            else:  # MILD
                routine['morning'].append("Green-tinted moisturizer")
                routine['evening'].append("Niacinamide serum (5%)")
                routine['weekly'].append("Cool compress for redness (5-10 minutes)")
            
            # Handle multiple triggers
            triggers = user_responses.get("rosacea_triggers")
            if isinstance(triggers, (list, tuple)) and triggers:
                avoid_list = []
                trigger_map = {1: "sun exposure", 2: "spicy foods", 3: "alcohol", 
                             4: "stress", 5: "heat", 6: "cold", 7: "exercise", 8: "certain products"}
                for trigger in triggers:
                    if trigger in trigger_map:
                        avoid_list.append(trigger_map[trigger])
                if avoid_list:
                    routine['notes'].append(f"🚫 AVOID TRIGGERS: {', '.join(avoid_list)}")
            
        elif primary_condition == "eczema" and condition_classification != "SEVERE":
            if condition_classification == "MODERATE":
                routine['morning'].append("Ceramide-rich moisturizer (thick application)")
                routine['evening'].append("Hydrocortisone cream 1% (short-term use)")
                routine['weekly'].append("Oatmeal bath (2-3 times per week)")
            else:  # MILD
                routine['morning'].append("Colloidal oatmeal moisturizer")
                routine['evening'].append("Petrolatum-based healing ointment")
                routine['weekly'].append("Gentle oatmeal bath (once per week)")
            
            # Handle multiple triggers
            triggers = user_responses.get("eczema_triggers")
            if isinstance(triggers, (list, tuple)) and triggers:
                avoid_list = []
                trigger_map = {1: "harsh soaps", 2: "fragrances", 3: "certain fabrics", 
                             4: "stress", 5: "weather changes", 6: "food allergens", 
                             7: "dust/allergens"}
                for trigger in triggers:
                    if trigger in trigger_map:
                        avoid_list.append(trigger_map[trigger])
                if avoid_list:
                    routine['notes'].append(f"🚫 AVOID TRIGGERS: {', '.join(avoid_list)}")
            
        elif primary_condition == "severe_acne" and condition_classification != "SEVERE":
            # Check if it's hormonal acne
            is_hormonal_acne = (user_responses.get("gender") == 2 and
                                user_responses.get("menstrual_cycle_acne") > 1)
            
            if condition_classification == "MODERATE":
                if is_hormonal_acne:
                    routine['morning'].append("Gentle salicylic acid cleanser")
                    routine['morning'].append("Niacinamide serum 5-10%")
                    routine['evening'].append("Retinol 0.25% (start 2x/week)")
                    routine['evening'].append("Spot treatment with benzoyl peroxide 2.5%")
                    routine['weekly'].append("Clay mask (1-2 times per week)")
                    routine['notes'].append("⚠️ HORMONAL ACNE: Consider consulting gynecologist about hormonal balance")
                    
                    birth_control = user_responses.get("hormonal_birth_control")
                    if birth_control > 1:
                        routine['notes'].append("💊 Review birth control with doctor - some can worsen acne")
                else:
                    routine['morning'].append("Benzoyl peroxide 2.5% (start every other day)")
                    routine['evening'].append("Salicylic acid serum 0.5-1%")
                    routine['weekly'].append("Clay mask (once per week)")
            else:  # MILD
                if is_hormonal_acne:
                    routine['morning'].append("Gentle foaming cleanser")
                    routine['morning'].append("Niacinamide serum 3-5%")
                    routine['evening'].append("Salicylic acid cleanser (3x/week)")
                    routine['evening'].append("Tea tree oil spot treatment (diluted)")
                    routine['weekly'].append("Gentle clay mask (once per week)")
                    routine['notes'].append("🔄 Track symptoms with menstrual cycle")
                else:
                    routine['morning'].append("Salicylic acid cleanser (2-3 times per week)")
                    routine['evening'].append("Tea tree oil spot treatment (diluted)")
                    routine['weekly'].append("Gentle exfoliation (once per week)")
            
            routine['notes'].append("🚫 AVOID: Over-washing, picking at skin, heavy makeup")
            
            if is_hormonal_acne:
                routine['notes'].append("🍃 Consider spearmint tea (may help with hormonal balance)")
                routine['notes'].append("⚖️ Maintain stable blood sugar levels")
                routine['notes'].append("😴 Prioritize sleep quality (affects hormones)")
        
        elif primary_condition == "melasma" and condition_classification != "SEVERE":
            # MELASMA TREATMENT RECOMMENDATIONS
            if condition_classification == "MODERATE":
                routine['morning'].append("Vitamin C serum 15-20% (antioxidant protection)")
                routine['morning'].append("Broad-spectrum SPF 50+ with zinc oxide")
                routine['evening'].append("Hydroquinone 2% (OTC bleaching agent)")
                routine['evening'].append("Tretinoin 0.025% (start 2x/week - may need prescription)")
                routine['weekly'].append("Gentle chemical peel with glycolic acid (1-2x/week)")
                routine['notes'].append("⚠️ MODERATE MELASMA: Progress may be slow, be patient with treatment")
            else:  # MILD
                routine['morning'].append("Vitamin C serum 10-15%")
                routine['morning'].append("Broad-spectrum SPF 50+ (reapply every 2 hours)")
                routine['evening'].append("Kojic acid or arbutin serum (natural lightening)")
                routine['evening'].append("Niacinamide 5% (helps with pigmentation)")
                routine['weekly'].append("Gentle AHA exfoliation (glycolic or lactic acid)")
                routine['notes'].append("✅ MILD MELASMA: Consistent treatment should show improvement in 2-3 months")
            
            # Melasma-specific precautions
            routine['notes'].append("☀️ CRITICAL: Strict sun protection is essential - melasma worsens with UV exposure")
            routine['notes'].append("🕶️ Wear wide-brimmed hat and sunglasses when outdoors")
            routine['notes'].append("🚫 AVOID: Waxing on affected areas (can worsen pigmentation)")
            
            # Handle melasma triggers (check gender first)
            triggers = user_responses.get("melasma_triggers")
            if isinstance(triggers, (list, tuple)) and triggers:
                trigger_notes = []
                # Only check hormonal triggers for females
                if user_responses.get("gender") == 2:  # Female
                    if 2 in triggers or 3 in triggers:  # Pregnancy or hormonal changes
                        trigger_notes.append("hormonal factors")
                    if 4 in triggers or 5 in triggers:  # Birth control or HRT
                        trigger_notes.append("hormonal medications")
                    if trigger_notes:
                        routine['notes'].append(f"💊 HORMONAL TRIGGERS DETECTED: Discuss {', '.join(trigger_notes)} with doctor")
            
            # Pregnancy considerations (females only)
            if user_responses.get("gender") == 2:  # Female
                pregnancy_hormones = user_responses.get("melasma_pregnancy_hormones")
                if isinstance(pregnancy_hormones, (list, tuple)):
                    if 2 in pregnancy_hormones:  # Currently pregnant
                        routine['notes'].append("🤰 PREGNANCY: Avoid retinoids and hydroquinone - use vitamin C and sunscreen only")
                    elif 4 in pregnancy_hormones:  # Started birth control
                        routine['notes'].append("💊 BIRTH CONTROL: Consider discussing alternatives with gynecologist")
            else:  # Male
                routine['notes'].append("👨 MALE MELASMA: This condition is rare in men - consider underlying medical causes")

    @staticmethod
    def _add_allergen_specific_recommendations(routine, skin_profile):
        """Add recommendations based on specific allergen sensitivities"""
        allergen_profile = skin_profile.get('allergen_profile')
        if not allergen_profile:
            return
            
        high_risk_allergens = allergen_profile.get('high_risk_allergens')
        avoid_ingredients = allergen_profile.get('avoid_ingredients')
        
        if high_risk_allergens:
            routine['notes'].append("⚠️ ALLERGEN SENSITIVITIES DETECTED:")
            
            for allergen in high_risk_allergens:
                if allergen == 'fragrances':
                    routine['notes'].append("  🌸 FRAGRANCE-FREE products only")
                    routine['notes'].append("  📖 Always read ingredient lists carefully")
                elif allergen == 'preservatives':
                    routine['notes'].append("  🧪 Choose preservative-free or low-preservative products")
                    routine['notes'].append("  📦 Consider single-use packets or airless pumps")
                elif allergen == 'metals':
                    routine['notes'].append("  ⚗️ Avoid products with metallic applicators")
                    routine['notes'].append("  💍 Remove jewelry before applying skincare")
                elif allergen == 'botanicals':
                    routine['notes'].append("  🌿 Avoid natural/botanical ingredients")
                    routine['notes'].append("  🔬 Stick to synthetic, proven ingredients")
                    
            if avoid_ingredients:
                routine['notes'].append("🚫 INGREDIENTS TO AVOID:")
                for ingredient in avoid_ingredients[:5]:
                    routine['notes'].append(f"  • {ingredient}")
                if len(avoid_ingredients) > 5:
                    routine['notes'].append(f"  • ...and {len(avoid_ingredients) - 5} more")
                    
            routine['notes'].append("✅ SAFER INGREDIENT OPTIONS:")
            routine['notes'].append("  • Ceramides, hyaluronic acid, squalane")
            routine['notes'].append("  • Mineral sunscreens (zinc oxide, titanium dioxide)")
            routine['notes'].append("  • Simple formulations with fewer ingredients")

    def _generate_lifestyle_recommendations(self, skin_profile, user_responses, condition_scores=None):
        """Generate enhanced lifestyle recommendations"""
        lifestyle_tips = []

        # Sun exposure recommendations
        sun_exposure = user_responses.get("sun_exposure")
        if sun_exposure >= 4:
            lifestyle_tips.append("⚠️ High sun exposure detected - wear protective clothing and reapply sunscreen every 2 hours")
        elif sun_exposure >= 3:
            lifestyle_tips.append("☀️ Moderate sun exposure - ensure daily SPF application")

        # Stress management
        stress_level = user_responses.get("stress_level")
        if stress_level >= 4:
            lifestyle_tips.append("🧘 High stress levels can worsen skin conditions - consider meditation, yoga, or stress counseling")
        elif stress_level >= 3:
            lifestyle_tips.append("😌 Moderate stress detected - try regular exercise and relaxation techniques")

        # Sleep recommendations
        sleep_quality = user_responses.get("sleep_quality")
        if sleep_quality >= 4:
            lifestyle_tips.append("😴 Poor sleep affects skin healing - aim for 7-9 hours of quality sleep")
        elif sleep_quality >= 3:
            lifestyle_tips.append("🛏️ Improve sleep hygiene for better skin health")

        # Hydration
        if skin_profile.get('hydration') == "High hydration needs":
            lifestyle_tips.append("💧 Drink at least 8 glasses of water daily for skin hydration")

        # Hormonal acne specific recommendations
        is_female = user_responses.get("gender") == 2
        has_cycle_acne = user_responses.get("menstrual_cycle_acne", 1) > 1
        
        if is_female and has_cycle_acne:
            lifestyle_tips.append("🔄 Track your skin changes with menstrual cycle to identify patterns")
            lifestyle_tips.append("🍃 Consider spearmint tea (may help balance androgens naturally)")
            lifestyle_tips.append("🥗 Eat anti-inflammatory foods: omega-3 rich fish, leafy greens, berries")
            lifestyle_tips.append("⚖️ Maintain stable blood sugar - avoid high glycemic foods")
            lifestyle_tips.append("🏃‍♀️ Regular exercise helps balance hormones (but shower immediately after)")
            
            birth_control = user_responses.get("hormonal_birth_control", 1)
            if birth_control > 1:
                lifestyle_tips.append("💊 Discuss your acne with gynecologist - birth control type matters")

        # Allergen avoidance lifestyle tips
        if skin_profile.get('allergen_profile'):
            allergen_profile = skin_profile['allergen_profile']
            if allergen_profile.get('high_risk_allergens', []):
                lifestyle_tips.append("🏠 Use fragrance-free household products (detergents, fabric softeners)")
                lifestyle_tips.append("👕 Choose natural fiber clothing and wash new clothes before wearing")
                lifestyle_tips.append("🧴 Always patch test new products on inner wrist 24-48 hours before use")
                
                if 'metals' in allergen_profile['high_risk_allergens']:
                    lifestyle_tips.append("💍 Avoid nickel jewelry; choose surgical steel, titanium, or gold")
                    
                if 'fragrances' in allergen_profile['high_risk_allergens']:
                    lifestyle_tips.append("🌸 Avoid scented candles, air fresheners, and perfumed environments")

        # Diet recommendations based on primary condition
        if condition_scores:
            max_condition = max(condition_scores, key=lambda x: condition_scores[x]['score']) if condition_scores else None
            max_score = condition_scores.get(max_condition, {}).get('score', 0) if condition_scores else 0
            
            if max_score >= 40:
                if max_condition == "rosacea":
                    lifestyle_tips.append("🌶️ Avoid spicy foods, alcohol, and hot beverages that may trigger rosacea")
                elif max_condition == "eczema":
                    lifestyle_tips.append("🥗 Consider elimination diet to identify food triggers")
                elif max_condition == "severe_acne":
                    lifestyle_tips.append("🥛 Limit dairy and high-glycemic foods that may worsen acne")
                elif max_condition == "melasma":
                    lifestyle_tips.append("🍊 Eat antioxidant-rich foods (vitamin C, E) to support skin healing")
                    lifestyle_tips.append("☀️ CRITICAL: Avoid peak sun hours (10 AM - 4 PM) when possible")
                    lifestyle_tips.append("🕶️ Always wear UV-protective clothing and wide-brimmed hats")

        lifestyle_tips.append("🥗 Consider a balanced diet rich in antioxidants for overall skin health")

        self.recommendations.append(("Lifestyle Recommendations", lifestyle_tips))