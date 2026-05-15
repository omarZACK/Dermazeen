from django.core.management.base import BaseCommand
from apps.analysis.models import SkinCondition,ConditionCategory


categories = {
    "acne": "Conditions primarily involving pimples, blackheads, whiteheads, or cysts.",
    "pigmentation": "Conditions affecting skin color, including dark or light patches.",
    "aging": "Signs of aging on the skin, such as wrinkles, fine lines, and age spots.",
    "sensitivity": "Conditions where the skin is easily irritated or reactive to external factors.",
    "inflammation": "Conditions that cause redness, swelling, or immune-related skin reactions.",
    "barrier_damage": "Conditions related to weakened or compromised skin barrier, leading to dryness or irritation.",
    "hormonal": "Conditions influenced by hormonal changes, such as during puberty, pregnancy, or menstrual cycles.",
    "lifestyle": "Conditions affected by lifestyle factors like diet, stress, sun exposure, or sleep.",
    "chronic": "Long-term or recurring skin conditions that often require ongoing management.",
    "genetic": "Conditions with a hereditary or genetic component that may run in families.",
    "other": "A general placeholder category for skin conditions that do not fit into the predefined categories."
}

CONDITIONS_DICT = {
    "Vitiligo": {
        "description": "A long-term skin condition characterized by patches of the skin losing their pigment, resulting in white spots. It occurs when melanocytes (pigment-producing cells) are destroyed.",
        "is_chronic": True,
        "requires_medical_attention": True,
        "categories": ["chronic", "genetic", "pigmentation"]
    },
    "Rosacea": {
        "description": "A chronic inflammatory skin condition that primarily affects the face, causing redness, visible blood vessels, and sometimes acne-like bumps.",
        "is_chronic": True,
        "requires_medical_attention": True,
        "categories": ["chronic", "inflammation", "sensitivity"]
    },
    "Eczema": {
        "description": "Also known as atopic dermatitis, eczema is a condition that makes the skin red, itchy, and inflamed. It often appears in patches and can flare up periodically.",
        "is_chronic": True,
        "requires_medical_attention": True,
        "categories": ["chronic", "inflammation", "barrier_damage", "sensitivity"]
    },
    "Psoriasis": {
        "description": "An autoimmune condition that speeds up the life cycle of skin cells, causing thick, red, scaly patches, usually on elbows, knees, and scalp.",
        "is_chronic": True,
        "requires_medical_attention": True,
        "categories": ["chronic", "inflammation", "genetic"]
    },
    "Acne": {
        "description": "A skin condition marked by frequent or intense outbreaks of pimples, blackheads, whiteheads, or cysts. Severe acne may cause scarring if untreated.",
        "is_chronic": False,
        "requires_medical_attention": True,
        "categories": ["acne", "hormonal", "inflammation"]
    },
    "Contact dermatitis": {
        "description": "An inflammatory skin reaction caused by direct contact with irritants or allergens, leading to red, itchy, and sometimes blistered skin.",
        "is_chronic": False,
        "requires_medical_attention": False,
        "categories": ["sensitivity", "inflammation", "barrier_damage"]
    },
    "Melasma": {
        "description": "A common skin condition causing brown or gray-brown patches, usually on the face, often triggered by sun exposure, hormonal changes, or pregnancy.",
        "is_chronic": True,
        "requires_medical_attention": True,
        "categories": ["pigmentation", "hormonal", "chronic", "lifestyle"]
    },
    "Other": {
        "description": "A placeholder category for any skin condition not listed above.",
        "is_chronic": False,
        "requires_medical_attention": False,
        "categories": ["other"]
    }
}


class Command(BaseCommand):
    help = "Load predefined survey questions into the database"

    def handle(self, *args, **kwargs):
        created_count, skipped_count = 0, 0
        print("Creating Categories")
        for idx, (key, q) in enumerate(categories.items(), start=1):
            obj, created = ConditionCategory.objects.get_or_create(
                name=key,
                description=q,
            )
            if created:
                created_count += 1
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created category: {obj}"))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"⚠️ Skipped category (exists): {obj}"))
        print("Creating Conditions")
        for idx, (key, q) in enumerate(CONDITIONS_DICT.items(), start=1):
            created_count, skipped_count = 0, 0
            category_names = q.pop("categories")
            category_objs = ConditionCategory.objects.filter(name__in=category_names)
            obj, created = SkinCondition.objects.get_or_create(
                condition_name=key,
                defaults=q,
            )
            obj.categories.set(category_objs)

            if created:
                created_count += 1
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created condition: {obj}"))

            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"⚠️ Skipped condition (exists): {obj}"))