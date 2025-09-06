from django.core.management.base import BaseCommand

from apps.analysis.models import SkinCondition
from apps.assessment.models import QuestionTemplate, QuestionTypeChoices


QUESTIONS_DICT = {
    "screening_main": {
        "text": "Do you suspect you have any of these skin conditions?",
        "multi_select": False,
        "condition_triggers": [],
        "options": [
            "No specific problems suspected",
            "Vitiligo",
            "Rosacea",
            "Eczema",
            "Psoriasis",
            "Severe Acne",
            "Contact dermatitis",
            "Melasma",
            "Other"
        ]
    },
    "condition_duration": {
        "text": "How long have you been dealing with this problem?",
        "multi_select": False,
        "condition_triggers": ["Vitiligo", "Rosacea", "Eczema", "Psoriasis", "Acne", "Contact dermatitis", "Melasma",
                               "Other"],
        "options": [
            "Less than a month",
            "1-3 months",
            "3-6 months",
            "6-12 months",
            "More than a year"
        ]
    },
    "condition_severity": {
        "text": "How would you rate the severity of the problem?",
        "multi_select": False,
        "condition_triggers": ["Vitiligo", "Rosacea", "Eczema", "Psoriasis", "Acne", "Contact dermatitis", "Melasma", "Other"],
        "options": [
            "Mild",
            "Moderate",
            "Severe",
            "Very severe"
        ]

    },
    "previous_treatments": {
        "text": "Have you tried any treatments before?",
        "multi_select": True,  # Allow multiple treatment types
        "condition_triggers": ["Vitiligo", "Rosacea", "Eczema", "Psoriasis", "Acne", "Contact dermatitis", "Melasma", "Other"],
        "options": [
            "Haven't tried any treatments",
            "Home remedies",
            "Over-the-counter products",
            "Medical treatments",
            "Multiple types"
        ]
    },

    # Basic Info Questions
    "age": {
        "text": "What is your age group?",
        "multi_select": False,
        "condition_triggers": ["Vitiligo", "Rosacea", "Eczema", "Psoriasis", "Acne", "Melasma", "Other"],
        "options": [
            "Under 18",
            "18-25",
            "26-35",
            "36-45",
            "Over 45"
        ]
    },
    "gender": {
        "text": "What is your gender?",
        "multi_select": False,
        "condition_triggers": ["Rosacea", "Acne", "Melasma", "Other"],  # some are gender/hormone related
        "options": [
            "Male",
            "Female",
            "Prefer not to answer"
        ]
    },
    "skin_tone": {
        "text": "What is your natural skin tone?",
        "multi_select": False,
        "condition_triggers": ["Melasma", "Vitiligo", "Other"],
        "options": [
            "Very light",
            "Light",
            "Medium",
            "Dark",
            "Very dark"
        ]
    },
    "family_history": {
        "text": "Is there a family history of skin problems? (Select all that apply)",
        "multi_select": True,  # Multiple family conditions possible
        "condition_triggers": ["Vitiligo", "Rosacea", "Eczema", "Psoriasis", "Other"],
        "options": [
            "None",
            "Vitiligo",
            "Rosacea",
            "Eczema",
            "Psoriasis",
            "Skin sensitivity",
            "Multiple conditions"
        ]
    },

    # Enhanced Specific Condition Questions
    "vitiligo_spots": {
        "text": "Have you noticed white spots appearing on your skin?",
        "multi_select": False,
        "condition_triggers": ["Vitiligo"],
        "options": [
            "No",
            "Yes, small spots",
            "Yes, medium spots",
            "Yes, large spots",
            "Yes, widespread"
        ]
    },
    "vitiligo_location": {
        "text": "Where do these spots appear? (Select all that apply)",
        "multi_select": True,  # Multiple locations possible
        "condition_triggers": ["Vitiligo"],
        "options": [
            "Face",
            "Hands",
            "Feet",
            "Neck",
            "Around eyes",
            "Arms/legs",
            "Torso",
            "Multiple areas"
        ]
    },
    "eczema_location": {
        "text": "Where does the eczema appear? (Select all that apply)",
        "multi_select": True,  # Multiple locations possible
        "condition_triggers": ["Eczema"],
            "options": [
            "Face",
            "Hands",
            "Arms",
            "Legs",
            "Neck",
            "Behind ears",
            "Torso",
            "Multiple areas"
        ]
    },
    "rosacea_redness": {
        "text": "Do you experience persistent redness in your face?",
        "multi_select": False,
        "condition_triggers": ["Rosacea"],
        "options": [
            "No",
            "Mild redness",
            "Moderate redness",
            "Severe redness",
            "Redness with burning sensation"
        ]
    },
    "rosacea_triggers": {
        "text": "What triggers the redness? (Select all that apply)",
        "multi_select": True,  # Multiple triggers possible
        "condition_triggers": ["Rosacea"],
        "options": [
            "Sun exposure",
            "Spicy food",
            "Alcohol",
            "Stress",
            "Heat",
            "Cold",
            "Exercise",
            "Certain products"
        ]
    },
    "eczema_itching": {
        "text": "Do you experience persistent itching on your skin?",
        "multi_select": False,
        "condition_triggers": ["Eczema"],
        "options": [
            "No",
            "Mild itching",
            "Moderate itching",
            "Severe itching",
            "Unbearable itching"
        ]
    },
    "eczema_triggers": {
        "text": "What triggers the eczema? (Select all that apply)",
        "multi_select": True,  # Multiple triggers possible
        "condition_triggers": ["Eczema"],
        "options": [
            "Harsh soaps",
            "Fragrances",
            "Certain fabrics",
            "Stress",
            "Weather",
            "Food",
            "Dust/allergens",
            "Not identified"
        ]
    },

    # NEW MELASMA QUESTIONS
    "melasma_patches": {
        "text": "Have you noticed brown or dark patches on your skin?",
        "multi_select": False,
        "condition_triggers": ["Melasma"],
        "options": [
            "No",
            "Yes, small patches",
            "Yes, medium patches",
            "Yes, large patches",
            "Yes, widespread patches"
        ]
    },
    "melasma_location": {
        "text": "Where do these dark patches appear? (Select all that apply)",
        "multi_select": True,
        "condition_triggers": ["Melasma"],
        "options": [
            "Face (cheeks, forehead, nose)",
            "Upper lip area",
            "Neck",
            "Arms",
            "Shoulders",
            "Chest",
            "Other sun-exposed areas"
        ]
    },
    "melasma_triggers": {
        "text": "What seems to trigger or worsen these patches? (Select all that apply)",
        "multi_select": True,
        "condition_triggers": ["Melasma"],
        "options": [
            "Sun exposure",
            "Pregnancy",
            "Hormonal changes",
            "Birth control pills",
            "Hormone replacement therapy",
            "Certain medications",
            "Not sure"
        ]
    },
    "melasma_pregnancy_hormones": {
        "text": "Have you experienced hormonal changes that might be related? (Select all that apply)",
        "multi_select": True,
        "condition_triggers": ["Melasma"],
        "options": [
            "No hormonal changes",
            "Currently pregnant",
            "Recently pregnant",
            "Started birth control",
            "Menopause/perimenopause",
            "Hormone replacement therapy",
            "Other hormonal medications"
        ]
    },

    # Remaining questions (keeping existing structure)...
    "t_zone_oiliness": {
        "text": "How would you describe the oiliness in your T-zone (forehead, nose, chin) 4-6 hours after washing?",
        "multi_select": False,
        "condition_triggers": ["Acne"],
        "options": [
            "Completely dry",
            "Slightly dry",
            "Normal",
            "Slightly oily",
            "Very oily with visible shine"
        ]
    },
    "cheek_oiliness": {
        "text": "How would you describe your cheeks 30 minutes after washing?",
        "multi_select": False,
        "condition_triggers": ["Acne"],
        "options": [
            "Dry and tight",
            "Slightly dry",
            "Normal and comfortable",
            "Slightly oily",
            "Very oily"
        ]
    },
    "pore_size": {
        "text": "How would you describe the size of your pores?",
        "multi_select": False,
        "condition_triggers": ["Acne"],
        "options": [
            "Invisible or very small",
            "Small",
            "Medium",
            "Large in T-zone only",
            "Large all over face"
        ]
    },
    "product_sensitivity": {
        "text": "How does your skin react to new skincare products?",
        "multi_select": False,
        "condition_triggers": ["Eczema", "Rosacea", "barrier_damage"],
        "options": [
            "Never reacts",
            "Rarely reacts",
            "Sometimes reacts",
            "Often reacts",
            "Always reacts with severe sensitivity"
        ]
    },
    "environmental_sensitivity": {
        "text": "How does your skin react to environmental factors (wind, cold, heat)?",
        "multi_select": False,
        "condition_triggers": ["Rosacea", "Eczema"],
        "options": [
            "Not affected",
            "Slightly affected",
            "Moderately affected",
            "Severely affected",
            "Severely affected with inflammation"
        ]
    },
    "dryness_feeling": {
        "text": "Do you feel dryness or tightness in your skin throughout the day?",
        "multi_select": False,
        "condition_triggers": ["Eczema",],
        "options": [
            "Never",
            "Rarely",
            "Sometimes",
            "Often",
            "Always and painful"
        ]
    },
    "moisturizer_response": {
        "text": "How does your skin respond to moisturizers?",
        "multi_select": False,
        "condition_triggers": [],
        "options": [
            "Becomes oily quickly",
            "Comfortable for short time",
            "Comfortable for long time",
            "Needs strong moisturizer",
            "Needs multiple moisturizers daily"
        ]
    },
    "menstrual_cycle_acne": {
        "text": "Do you notice acne changes related to your menstrual cycle?",
        "multi_select": False,
        "condition_triggers": ["Acne"],
        "options": [
            "No changes",
            "Slight worsening before period",
            "Moderate worsening before period",
            "Severe worsening before period",
            "Constant flare-ups throughout cycle"
        ]
    },
    "hormonal_birth_control": {
        "text": "Are you currently using hormonal birth control?",
        "multi_select": False,
        "condition_triggers": ["Acne", "Melasma"],
        "options": [
            "No",
            "Birth control pills",
            "IUD (hormonal)",
            "Contraceptive shot/injection",
            "Other hormonal methods"
        ]
    },
    "fragrance_sensitivity": {
        "text": "How does your skin react to fragrances in products?",
        "multi_select": False,
        "condition_triggers": ["Eczema", "Rosacea", "Contact dermatitis"],
        "options": [
            "No reaction",
            "Mild irritation occasionally",
            "Moderate irritation",
            "Severe irritation/redness",
            "Immediate allergic reaction"
        ]
    },
    "preservative_sensitivity": {
        "text": "Have you experienced reactions to preservatives (parabens, formaldehyde releasers)?",
        "multi_select": False,
        "condition_triggers": ["Contact dermatitis", "Eczema"],
        "options": [
            "No known reactions",
            "Suspected mild reactions",
            "Confirmed mild reactions",
            "Confirmed moderate reactions",
            "Severe allergic reactions"
        ]
    },
    "metal_sensitivity": {
        "text": "Do you have sensitivity to metals (nickel, jewelry)?",
        "multi_select": False,
        "condition_triggers": ["Contact dermatitis"],
        "options": [
            "No sensitivity",
            "Mild skin discoloration",
            "Moderate rash/redness",
            "Severe allergic contact dermatitis",
            "Multiple metal allergies"
        ]
    },
    "botanical_sensitivity": {
        "text": "How does your skin react to natural/botanical ingredients?",
        "multi_select": False,
        "condition_triggers": ["Eczema", "Rosacea", "Contact dermatitis"],
        "options": [
            "Generally well-tolerated",
            "Occasional mild reactions",
            "Frequent mild reactions",
            "Severe reactions to most botanicals",
            "Allergic to specific plants (specify which)"
        ]
    },
    "sun_exposure": {
        "text": "How much sun exposure do you get daily?",
        "multi_select": False,
        "condition_triggers": ["Melasma", "Rosacea", "Vitiligo", "Other"],
        "options": [
            "Minimal (indoor most of day)",
            "Light (short outdoor periods)",
            "Moderate (regular outdoor activities)",
            "High (work/spend lots of time outdoors)",
            "Very high (beach, sports, etc.)"
        ]
    },
    "stress_level": {
        "text": "How would you rate your stress levels?",
        "multi_select": False,
        "condition_triggers": ["Eczema", "Psoriasis", "Acne", "Rosacea"],
        "options": [
            "Very low",
            "Low",
            "Moderate",
            "High",
            "Very high"
        ]
    },
    "sleep_quality": {
        "text": "How would you rate your sleep quality?",
        "multi_select": False,
        "condition_triggers": ["Acne", "Eczema", "Psoriasis", "Rosacea"],
        "options": [
            "Excellent (7-9 hours, good quality)",
            "Good (6-8 hours, decent quality)",
            "Fair (5-7 hours, some issues)",
            "Poor (less than 6 hours or poor quality)",
            "Very poor (chronic sleep issues)"
        ]
    }
}

class Command(BaseCommand):
    help = "Load predefined survey questions into the database"

    def handle(self, *args, **kwargs):
        created_count, skipped_count = 0, 0
        # print(len(QUESTIONS_DICT.keys()))
        for idx, (key, q) in enumerate(QUESTIONS_DICT.items(), start=1):
            question_type = (
                QuestionTypeChoices.MULTIPLE_CHOICE
                if q["multi_select"] else
                QuestionTypeChoices.SINGLE_CHOICE
            )

            condition_names = q.pop("condition_triggers")
            condition_objs = SkinCondition.objects.filter(condition_name__in=condition_names)

            obj, created = QuestionTemplate.objects.get_or_create(
                question_name=key,
                question_text=q["text"],
                defaults={
                    "question_type": question_type,
                    "options": q["options"],
                }
            )

            obj.condition_triggers.set(condition_objs)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Created: {obj} (triggers={condition_names})")
                )
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(
                    f"⚠️ Skipped (already exists): {obj}")
                )

        self.stdout.write(
            self.style.SUCCESS(
            f"\nDone! Created {created_count}, skipped {skipped_count}.")
        )