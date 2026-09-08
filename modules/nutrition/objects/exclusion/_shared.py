"""@module nutrition.objects.exclusion._shared — what the exclusion row classes share (constants, seeds, helpers); split from exclusion_basis.py (sap-2c)."""

ALLERGEN_CLASSES = (
    'milk', 'egg', 'fish', 'crustacean-shellfish', 'tree-nut',
    'peanut', 'wheat', 'soybean', 'sesame',
)
EXCLUSION_SEVERITIES = ('allergy-hard', 'intolerance-hard',
                        'preference-soft')
_PROV = ('mpb-1 (MEAL_PLANNING_APP_PLAN §3b); allergen class = '
         'food IDENTITY under the FDA major-9 vocabulary '
         '(FASTER Act 2021) — not a lab analysis')
def _flag(food, allergen, basis):
    return {'name': f'{food}-{allergen}', 'food_name': food,
            'allergen_class': allergen, 'basis': basis,
            'is_prior': True, 'provenance_id': _PROV, 'notes': ''}
SEED_FOOD_ALLERGEN_FLAGS = [
    _flag('milk-whole', 'milk', 'is milk'),
    _flag('yogurt-plain-whole', 'milk', 'cultured milk product'),
    _flag('butter-unsalted', 'milk', 'milk-fat product'),
    _flag('cheese-cheddar', 'milk', 'milk product'),
    _flag('egg-whole-raw', 'egg', 'is egg'),
    _flag('cod-raw', 'fish', 'is finfish'),
    _flag('salmon-atlantic-raw', 'fish', 'is finfish'),
    _flag('tilapia-raw', 'fish', 'is finfish'),
    _flag('almonds-raw', 'tree-nut', 'is a tree nut'),
    _flag('walnuts-raw', 'tree-nut', 'is a tree nut'),
    _flag('flour-all-purpose', 'wheat', 'wheat flour'),
    _flag('flour-whole-wheat', 'wheat', 'wheat flour'),
    _flag('pasta-dry', 'wheat', 'durum-wheat product'),
    _flag('tofu-firm', 'soybean', 'soybean curd'),
]
SEED_PERSON_EXCLUSIONS = [
    {'name': 'demo-alex-tree-nut', 'person_name': 'demo-alex',
     'allergen_class': 'tree-nut', 'food_name': '',
     'severity': 'allergy-hard',
     'stated_reason': 'demo row — declared tree-nut allergy',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo — replace with real declarations'},
]
