"""
@cross-cutting
@module nutrition.fdc_seed
@tags @xc:bindings

nmp-0 — the starter base-ingredient pantry as FoodItem +
NutrientContent seed rows, built from the vendored FDC subset
(vendor/fdc_foundation_subset.csv, CC0). Decision 8: meals are built
STRICTLY from base ingredients + meats, so this pantry (49 whole
foods: meats/fish, dairy-as-ingredient, staples, produce) is the
ingredient space recipes draw from; our own GROWN foods keep coming
from the aqp harvest side (nut-2) with fdc_id=0.

Rows are derived deterministically from the CSV at import time —
the CSV is the versioned source of truth; nothing here is typed
twice. Amounts are per 100 g EDIBLE, raw/dry as described; cooking
transforms arrive with nmp-3 (retention x yield).

@consumers
  - polariServer seed pairs (foods before contents)
  - nutrition.selftest_data
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0
"""

from nutrition.vendor_data import fdc_subset

_PREP_OVERRIDES = {
    'flour-whole-wheat': 'flour',
    'flour-all-purpose': 'flour',
    'lentils-dry': 'dried',
    'black-beans-dry': 'dried',
    'chickpeas-dry': 'dried',
    'pasta-dry': 'dried',
    'oats-rolled': 'dried',
    'rice-white-raw': 'dried',
    'rice-brown-raw': 'dried',
    'quinoa-raw': 'dried',
}


def _build():
    foods, contents, seen = [], [], {}
    for r in fdc_subset():
        slug = r['food_slug']
        if slug not in seen:
            seen[slug] = True
            foods.append({
                'name': slug,
                # the FDC description IS the honest display name —
                # it says exactly what was measured
                'display_name': r['fdc_description'],
                'plant_name': '',
                'edible_parts_json': '[]',
                'preparation': _PREP_OVERRIDES.get(slug, 'raw'),
                'fdc_id': int(r['fdc_id']),
                'fdc_dataset': r['fdc_dataset'],
                'provenance_id': 'nmp-0',
                'notes': 'USDA FDC per-100g basis (see vendor/)',
            })
        contents.append({
            'name': f"{slug}-{r['nutrient']}",
            'food_name': slug,
            'nutrient_name': r['nutrient'],
            'amount_per_100g': float(r['amount_per_100g']),
            'unit': r['unit'],
            'is_prior': True,
            'source': (f"USDA FDC {r['fdc_dataset']} "
                       f"fdc_id={r['fdc_id']} "
                       f"nbr={r['fdc_nutrient_nbr']}"),
            'provenance_id': 'nmp-0',
            'notes': r['derivation'],
        })
    return foods, contents


SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS = _build()
