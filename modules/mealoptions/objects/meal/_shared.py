"""@module mealoptions.objects.meal._shared — what the meal row classes share (constants, seeds, helpers); split from meal_basis.py (sap-2c)."""

MEAL_SLOTS = ('breakfast', 'lunch', 'dinner', 'brunch', 'linner',
              'snack', 'snack-2')
SEED_MEAL_TEMPLATES = [
    {'name': 'chicken-bowl-dinner',
     'display_name': 'Chicken rice bowl dinner',
     'description': 'The chicken-rice-bowl recipe as a dinner meal.',
     'recipe_names_json': '["chicken-rice-bowl"]',
     'slots_json': '["dinner", "lunch", "linner"]',
     'dish_base': 'bowl',
     'is_prior': True, 'provenance_id': 'nmp-4'},
    {'name': 'omelet-breakfast', 'display_name': 'Omelet breakfast',
     'description': 'The spinach omelet as a breakfast.',
     'recipe_names_json': '["spinach-omelet"]',
     'slots_json': '["breakfast", "brunch"]',
     'dish_base': 'omelet',
     'is_prior': True, 'provenance_id': 'nmp-4'},
]
SEED_VARIATIONS = [
    {'name': 'chicken-bowl-dinner-base', 'display_name': 'As written',
     'template_name': 'chicken-bowl-dinner', 'swaps_json': '[]',
     'scale_min': 0.8, 'scale_max': 1.2, 'is_prior': True,
     'provenance_id': 'nmp-4'},
    # calcium-set tofu is calcium-DENSE — the gate sizes the swap
    # (120 g keeps the meal under the per-meal calcium cap at max
    # scale; the chicken's R6 code does not carry over).
    {'name': 'chicken-bowl-dinner-tofu', 'display_name': 'Tofu swap',
     'template_name': 'chicken-bowl-dinner',
     'swaps_json':
         '[{"from_food": "chicken-breast-raw", "to_food": '
         '"tofu-firm", "grams": 120}]',
     'scale_min': 0.8, 'scale_max': 1.2, 'is_prior': True,
     'provenance_id': 'nmp-4'},
    {'name': 'omelet-breakfast-base', 'display_name': 'As written',
     'template_name': 'omelet-breakfast', 'swaps_json': '[]',
     'scale_min': 0.8, 'scale_max': 1.5, 'is_prior': True,
     'provenance_id': 'nmp-4'},
]
