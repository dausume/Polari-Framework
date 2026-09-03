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

# N6 (2026-09-03): total sugars, so the tracking readout can read
# "sweets" directly instead of through glycemic load + carbohydrate.
# The vendored FDC subset carries it as the CSV nutrient 'sugars-total'
# (fdc_seed maps CSV nutrient names to DietaryNutrient names 1:1) for
# the 24 of 49 foods whose FDC entry publishes a total-sugars row.
SUGARS_TOTAL_NOTE = ('FDC 269 — total sugars, NOT added sugars; DGA\'s '
                     'added-sugar line cannot be read from this (total '
                     '>= added, so any added-sugar ceiling applied to it '
                     'is conservative)')
SEED_DIETARY_NUTRIENTS.append({
    'name': 'sugars-total', 'display_name': 'Sugars, total',
    'category': 'carbohydrate', 'unit': 'g',
    'role': 'Mono- + disaccharides (the "sweets" signal); energy',
    'plant_availability': 'common', 'alternate_source': '',
    'provenance_id': 'N6', 'notes': SUGARS_TOTAL_NOTE})

# References: nmp-0 SUPERSEDED the adult-only single-band table that
# lived here with the full NASEM DRI life-stage transcription
# (EAR + RDA/AI + UL, adults 19+ per DRI band + pregnancy/lactation).
# Re-exported under the historical name so every consumer — the
# legacy seed list, person_analysis, the selftests — keeps working
# against the one richer table.
from nutrition.dri_seed import SEED_DRI_REFERENCES, JURISDICTION, EDITION

# N6: total sugars has NO DRI (no EAR/RDA/AI/UL exists — NASEM 2005
# only discusses ADDED sugars, and the DGA line is for added sugars
# too). The vocabulary rule "every nutrient has a reference row" is
# met with a 'none' MARKER row (the calories precedent): target 0 /
# max 0 so person_thresholds and coverage skip it (target <= 0), and
# the tracking readout applies its own labelled CEILING (dga_limits.
# total_sugars_ceiling_g) instead of a target.
_SUGARS_MARKER_REFERENCE = {
    'name': 'sugars-total-any-19-120', 'nutrient_name': 'sugars-total',
    'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
    'rda_per_day': 0.0, 'upper_limit_per_day': 0.0, 'ear_per_day': 0.0,
    'per_kg_body_mass': 0.0, 'value_type': 'none', 'life_stage': '',
    'jurisdiction': JURISDICTION, 'edition': EDITION,
    'source': 'no DRI exists for total sugars (marker row)',
    'is_prior': True,
    'notes': ('no EAR/RDA/AI/UL for total sugars; the only published '
              'line is the DGA added-sugar share (<10 % kcal), which '
              'tracking_periods applies as a labelled conservative '
              'ceiling, never a target'),
    'provenance_id': 'N6'}

SEED_NUTRIENT_REFERENCES = SEED_DRI_REFERENCES + [_SUGARS_MARKER_REFERENCE]
