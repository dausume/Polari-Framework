"""
@cross-cutting
@module nutrition.nutrient_seed
@tags @xc:bindings

nut-1 seeds — the full dietary-nutrient vocabulary (Dustin's canonical
list; do NOT drop any) + adult RDA/AI reference rows (NIH DRI, adult
19–50; sex-specific where they differ, else 'any'). Idempotent-by-name.

Values are literature priors — flagged. Calories carry no flat RDA
(computed from BMR/TDEE in nut-3); protein scales per-kg body mass.

@consumers
  - polariServer seed_pairs (nutrients before references)
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-1 + Appendix A
"""

# (name, display, category, unit, role, plant_availability, alt_source)
_NUTRIENTS = [
    ('calories', 'Calories (energy)', 'macro', 'kcal',
     'Energy from carbohydrate + fat + protein', 'common', ''),
    ('carbohydrate', 'Carbohydrate', 'macro', 'g',
     'Primary energy source', 'common', ''),
    ('protein', 'Protein', 'macro', 'g',
     'Essential amino acids — tissue + enzymes', 'common', ''),
    ('healthy-fat', 'Healthy fat', 'macro', 'g',
     'Energy, hormones, fat-soluble vitamin uptake', 'common', ''),
    ('vitamin-a', 'Vitamin A', 'vitamin', 'ug',
     'Eye & skin health', 'common', ''),
    ('vitamin-b1', 'Vitamin B1 (thiamin)', 'vitamin', 'mg',
     'Energy metabolism', 'common', ''),
    ('vitamin-b2', 'Vitamin B2 (riboflavin)', 'vitamin', 'mg',
     'Energy metabolism', 'common', ''),
    ('vitamin-b3', 'Vitamin B3 (niacin)', 'vitamin', 'mg',
     'Energy metabolism, skin', 'common', ''),
    ('vitamin-b5', 'Vitamin B5 (pantothenic acid)', 'vitamin', 'mg',
     'Coenzyme A / fatty-acid metabolism', 'common', ''),
    ('vitamin-b6', 'Vitamin B6', 'vitamin', 'mg',
     'Amino-acid metabolism, neurotransmitters', 'common', ''),
    ('vitamin-b7', 'Vitamin B7 (biotin)', 'vitamin', 'ug',
     'Fat/carb metabolism, hair & nails', 'common', ''),
    ('vitamin-b9', 'Vitamin B9 (folate)', 'vitamin', 'ug',
     'DNA synthesis, red blood cells', 'common', ''),
    ('vitamin-b12', 'Vitamin B12', 'vitamin', 'ug',
     'Nerve function, red blood cells', 'none',
     'Fermentation of plant foods, or animal/algae sources'),
    ('vitamin-c', 'Vitamin C', 'vitamin', 'mg',
     'Immunity & collagen (hair/skin)', 'common', ''),
    ('vitamin-d', 'Vitamin D', 'vitamin', 'ug',
     'Immunity & bone growth', 'hard',
     'Sun-exposed mushrooms (Shiitake/Oyster); sunlight'),
    ('vitamin-e', 'Vitamin E', 'vitamin', 'mg',
     'Protects cells from oxidative damage', 'common', ''),
    ('vitamin-k', 'Vitamin K', 'vitamin', 'ug',
     'Blood clotting, bone health', 'common', ''),
    ('iron', 'Iron', 'mineral', 'mg',
     'Blood health, oxygen transport', 'common', ''),
    ('calcium', 'Calcium', 'mineral', 'mg',
     'Bone & muscle function', 'common', ''),
    ('magnesium', 'Magnesium', 'mineral', 'mg',
     'Muscle & nerve health', 'common', ''),
    ('omega-3', 'Omega-3 fatty acids', 'fatty-acid', 'g',
     'Brain & heart health', 'common', ''),
    ('potassium', 'Potassium', 'electrolyte', 'mg',
     'Blood pressure, muscle & nerve signaling', 'common', ''),
    ('sodium', 'Sodium', 'electrolyte', 'mg',
     'Fluid balance, nerve & muscle function', 'none',
     'Saltwater seaweed (Dulse/Kelp/Sea Lettuce/Red Ogo)'),
    ('chloride', 'Chloride', 'electrolyte', 'mg',
     'Fluid balance, digestion', 'none',
     'Saltwater seaweed (Dulse/Kelp/Sea Lettuce/Red Ogo)'),
    ('zinc', 'Zinc', 'trace', 'mg',
     'Immunity, wound healing, DNA synthesis', 'common', ''),
    ('selenium', 'Selenium', 'trace', 'ug',
     'Antioxidant, thyroid, immunity', 'common', ''),
    ('copper', 'Copper', 'trace', 'ug',
     'Red blood cells, iron metabolism, immunity', 'common', ''),
    ('manganese', 'Manganese', 'trace', 'mg',
     'Metabolism, bone formation, antioxidant', 'common', ''),
    ('iodine', 'Iodine', 'trace', 'ug',
     'Thyroid hormone production, metabolism', 'none',
     'Saltwater seaweed (Dulse/Kelp/Sea Lettuce/Red Ogo)'),
    ('chromium', 'Chromium', 'trace', 'ug',
     'Blood-sugar regulation (insulin)', 'common', ''),
    ('molybdenum', 'Molybdenum', 'trace', 'ug',
     'Enzyme function, detoxification', 'common', ''),
    ('boron', 'Boron', 'trace', 'mg',
     'Bone density, Ca/Mg metabolism', 'common', ''),
    ('silicon', 'Silicon', 'trace', 'mg',
     'Connective tissue, collagen formation', 'common', ''),
]

SEED_DIETARY_NUTRIENTS = [
    {'name': n, 'display_name': d, 'category': c, 'unit': u, 'role': r,
     'plant_availability': pa, 'alternate_source': alt,
     'provenance_id': 'nut-1'}
    for (n, d, c, u, r, pa, alt) in _NUTRIENTS
]

# References. Entry forms:
#   (nutrient, rda_any)                          -> one 'any' row
#   (nutrient, rda_male, rda_female)             -> two sex rows
#   (nutrient, rda_male, rda_female, upper)      -> + upper limit
# per-kg + prior handled separately below.
_REF_ANY = [
    ('carbohydrate', 130.0, 0.0),
    ('calcium', 1000.0, 2500.0),
    ('vitamin-b1', 1.2, 0.0), ('vitamin-b2', 1.3, 0.0),
    ('vitamin-b6', 1.3, 100.0), ('vitamin-b9', 400.0, 1000.0),
    ('vitamin-b12', 2.4, 0.0), ('vitamin-d', 15.0, 100.0),
    ('vitamin-e', 15.0, 1000.0), ('selenium', 55.0, 400.0),
    ('copper', 900.0, 10000.0), ('iodine', 150.0, 1100.0),
    ('molybdenum', 45.0, 2000.0),
]
_REF_SEX = [
    # (nutrient, male, female, upper)
    ('vitamin-a', 900.0, 700.0, 3000.0),
    ('vitamin-b3', 16.0, 14.0, 35.0),
    ('vitamin-c', 90.0, 75.0, 2000.0),
    ('iron', 8.0, 18.0, 45.0),
    ('magnesium', 400.0, 310.0, 0.0),
    ('zinc', 11.0, 8.0, 40.0),
]
# AI/estimate references (flagged is_prior=True).
_REF_ANY_PRIOR = [
    ('healthy-fat', 65.0, 0.0), ('vitamin-b5', 5.0, 0.0),
    ('vitamin-b7', 30.0, 0.0), ('boron', 1.0, 20.0),
    ('silicon', 25.0, 0.0),
]
_REF_SEX_PRIOR = [
    ('vitamin-k', 120.0, 90.0, 0.0),
    ('omega-3', 1.6, 1.1, 0.0),
    ('potassium', 3400.0, 2600.0, 0.0),
    ('manganese', 2.3, 1.8, 11.0),
    ('chromium', 35.0, 25.0, 0.0),
]


def _any_row(nutrient, rda, upper, prior):
    return {'name': f'{nutrient}-any-19-50', 'nutrient_name': nutrient,
            'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
            'rda_per_day': rda, 'upper_limit_per_day': upper,
            'is_prior': prior, 'provenance_id': 'nut-1'}


def _sex_rows(nutrient, male, female, upper, prior):
    return [
        {'name': f'{nutrient}-male-19-50', 'nutrient_name': nutrient,
         'sex': 'male', 'age_min': 19.0, 'age_max': 120.0,
         'rda_per_day': male, 'upper_limit_per_day': upper,
         'is_prior': prior, 'provenance_id': 'nut-1'},
        {'name': f'{nutrient}-female-19-50', 'nutrient_name': nutrient,
         'sex': 'female', 'age_min': 19.0, 'age_max': 120.0,
         'rda_per_day': female, 'upper_limit_per_day': upper,
         'is_prior': prior, 'provenance_id': 'nut-1'},
    ]

SEED_NUTRIENT_REFERENCES = (
    [_any_row(n, rda, up, False) for (n, rda, up) in _REF_ANY]
    + [_any_row(n, rda, up, True) for (n, rda, up) in _REF_ANY_PRIOR]
    + [r for (n, m, f, up) in _REF_SEX
       for r in _sex_rows(n, m, f, up, False)]
    + [r for (n, m, f, up) in _REF_SEX_PRIOR
       for r in _sex_rows(n, m, f, up, True)]
    # protein: per-kg body mass (0.8 g/kg), no flat RDA.
    + [{'name': 'protein-any-19-50', 'nutrient_name': 'protein',
        'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
        'rda_per_day': 0.0, 'per_kg_body_mass': 0.8,
        'upper_limit_per_day': 0.0, 'is_prior': False,
        'source': 'NIH DRI (0.8 g/kg)', 'provenance_id': 'nut-1'}]
    # sodium / chloride: AI (plant-none — the saltwater gap).
    + [{'name': 'sodium-any-19-50', 'nutrient_name': 'sodium',
        'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
        'rda_per_day': 1500.0, 'upper_limit_per_day': 2300.0,
        'is_prior': True, 'source': 'NIH AI', 'provenance_id': 'nut-1'},
       {'name': 'chloride-any-19-50', 'nutrient_name': 'chloride',
        'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
        'rda_per_day': 2300.0, 'upper_limit_per_day': 3600.0,
        'is_prior': True, 'source': 'NIH AI', 'provenance_id': 'nut-1'}]
    # calories: computed in nut-3 (no flat RDA), a marker row so the
    # vocabulary check finds a reference for every nutrient.
    + [{'name': 'calories-any-19-50', 'nutrient_name': 'calories',
        'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
        'rda_per_day': 0.0, 'upper_limit_per_day': 0.0,
        'is_prior': False,
        'source': 'computed from BMR/TDEE (nut-3)',
        'notes': 'calorie target is computed per person, not a flat RDA',
        'provenance_id': 'nut-1'}]
)
