"""
@cross-cutting
@module nutrition.nutrient_seed
@tags @xc:bindings

nut-1 seeds — the full dietary-nutrient vocabulary (Dustin's canonical
list; do NOT drop any). The reference table moved to nutrition.dri_seed
in nmp-0 (full NASEM life-stage transcription) and is re-exported here
under its historical name. Idempotent-by-name.

Calories carry no flat RDA (computed from BMR/TDEE in nut-3); protein
scales per-kg body mass.

@consumers
  - polariServer seed_pairs (nutrients before references)
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-1 + Appendix A;
     AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0
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

# References: nmp-0 SUPERSEDED the adult-only single-band table that
# lived here with the full NASEM DRI life-stage transcription
# (EAR + RDA/AI + UL, adults 19+ per DRI band + pregnancy/lactation).
# Re-exported under the historical name so every consumer — the
# legacy seed list, person_analysis, the selftests — keeps working
# against the one richer table.
from nutrition.dri_seed import SEED_DRI_REFERENCES as \
    SEED_NUTRIENT_REFERENCES  # noqa: F401  (re-export)
