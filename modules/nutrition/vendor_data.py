"""
@cross-cutting
@module nutrition.vendor_data
@tags @xc:bindings

nmp-0 — loaders for the vendored license-clean datasets in
nutrition/vendor/ (see vendor/README.md for source, license, sha256
and retrieval date of every file). Pure stdlib csv, lazy + cached:
nothing is parsed until a consumer asks, and the big tables never
become DB rows wholesale — phases materialize only what they
reference (the retention engine in nmp-3, the MET vocabulary in
nmp-5).

@consumers
  - nutrition.fdc_seed (FoodItem/NutrientContent seed rows)
  - nmp-3 retention/yield engine, nmp-5 activity seeds (planned)
  - nutrition.selftest_data
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0
"""

import csv
import os

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'vendor')
_cache = {}


def _read(filename):
    if filename in _cache:
        return _cache[filename]
    path = os.path.join(_VENDOR, filename)
    with open(path, newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f)]
    _cache[filename] = rows
    return rows


def retention_factors():
    """USDA Nutrient Retention Factors R6 (CC0), 7018 rows.

    Keys: retention_code, food_group_code, retention_description,
    nutrient_code, nutrient_description, retention_percent,
    add_mod_date. retention_percent is 0-100 (percent RETAINED
    after the described cooking method)."""
    return _read('usda_retention_factors_r6.csv')


def cooking_yields():
    """USDA Cooking Yields for Meat & Poultry (CC0), sheet-flattened.

    The source workbook's three sheets are concatenated; '# sheet:'
    marker rows separate them and header rows repeat per sheet, so
    consumers filter rows where 'Cooking Yield %' parses as a
    number. Kept verbatim rather than reshaped."""
    path = os.path.join(_VENDOR, 'usda_cooking_yields_meat_poultry.csv')
    if 'yields' not in _cache:
        with open(path, newline='', encoding='utf-8') as f:
            _cache['yields'] = [r for r in csv.reader(f)]
    return _cache['yields']


def compendium_mets():
    """2024 Adult Compendium of Physical Activities, 1111 rows.

    Keys: activity_code, met_value, description, category. Values
    VERBATIM (the license requires values unaltered); attribution:
    Herrmann et al., 2024 Adult Compendium of Physical Activities,
    pacompendium.com."""
    return _read('compendium_2024_adult_mets.csv')


def fdc_subset():
    """USDA FoodData Central starter subset (CC0), per-100g rows.

    Keys: food_slug, fdc_id, fdc_dataset, fdc_description, nutrient,
    amount_per_100g, unit, fdc_nutrient_nbr, derivation. Only foods
    the module references (decision 8: base ingredients + meats);
    the full FDC stays an API lookup."""
    return _read('fdc_foundation_subset.csv')
