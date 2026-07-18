"""
@cross-cutting
@module nutrition.food_seed
@tags @xc:bindings

nut-2 seeds — FoodItems + NutrientContent for the first foods, including
the sweet-basil that GROWS in the aquaponics self-watering pot (aqp-1/4/
8), so a real grow run yields real meal nutrients. Values per 100 g
edible are USDA FDC priors (flagged). Idempotent-by-name.

@consumers
  - polariServer seed_pairs (foods before contents)
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-2 + Appendix A
"""

import json

SEED_FOOD_ITEMS = [
    {
        'name': 'basil-leaf', 'display_name': 'Fresh basil leaves',
        'plant_name': 'sweet-basil',
        'edible_parts_json': json.dumps(['sweet-basil-leaf']),
        'preparation': 'raw', 'moisture_loss_fraction': 0.0,
        'provenance_id': 'nut-2 (grows in the aqp self-watering pot)',
    },
    {
        'name': 'kale-leaf', 'display_name': 'Fresh kale leaves',
        'plant_name': 'kale',
        'edible_parts_json': json.dumps(['kale-leaf']),
        'preparation': 'raw', 'moisture_loss_fraction': 0.0,
        'provenance_id': 'nut-2',
    },
]

# Per 100 g edible (USDA FDC priors). Only the headline nutrients each
# food is a notable source of (Appendix A) — extend freely.
_CONTENT = {
    'basil-leaf': {
        'vitamin-k': ('ug', 414.8), 'vitamin-a': ('ug', 264.0),
        'vitamin-c': ('mg', 18.0), 'calcium': ('mg', 177.0),
        'iron': ('mg', 3.17), 'magnesium': ('mg', 64.0),
        'manganese': ('mg', 1.15), 'potassium': ('mg', 295.0),
    },
    'kale-leaf': {
        'vitamin-k': ('ug', 389.6), 'vitamin-a': ('ug', 241.0),
        'vitamin-c': ('mg', 93.4), 'calcium': ('mg', 254.0),
        'iron': ('mg', 1.6), 'potassium': ('mg', 348.0),
        'manganese': ('mg', 0.92),
    },
}

SEED_NUTRIENT_CONTENTS = [
    {'name': f'{food}-{nutrient}', 'food_name': food,
     'nutrient_name': nutrient, 'amount_per_100g': amount, 'unit': unit,
     'is_prior': True, 'source': 'USDA FDC', 'provenance_id': 'nut-2'}
    for food, table in _CONTENT.items()
    for nutrient, (unit, amount) in table.items()
]
