"""
Selftest for foodstate fsp-2/mpa-0 — the transform engine v1: mass
balance is exact bookkeeping over stated yields, retention rides the
R6 rung, model rungs REFUSE by name (I5), mixing is mass-weighted,
and the template chain's per-meal amounts AGREE with the nmp-4
rollup (two-modules-agree guard).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m foodstate.food_transforms_selftest
"""

import json
from types import SimpleNamespace

from foodstate.custom.food_composition import (
    build_composition_claim_seeds, vendor_food_index,
)
from foodstate.food_materials_basis import build_food_material_seeds
from foodstate.food_pspp_seed import SEED_FOOD_PROCESSES
from foodstate.custom.food_transforms import (
    apply_transform, derive_mix, derive_transform,
    template_state_chain,
)
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
from nutrition.custom.meal_analysis import template_rollup
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


MANAGER = SimpleNamespace(objectTables={
    'PropertyClaim': _rows(build_composition_claim_seeds()),
    'MaterialProcessDefinition': _rows(SEED_FOOD_PROCESSES),
    'FoodMaterial': _rows(
        build_food_material_seeds(vendor_food_index())),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
})


def comp(claims, quantity):
    for c in claims:
        if c['property_meaning_name'] == quantity:
            return c
    return None


# ── 1. chop is an identity pass with a stated structure claim ──
chop = derive_transform(MANAGER, 'food-chop', 'tomato-raw#as-defined',
                        {'target_particle_size_m': 0.01})
check('chop derives ok', chop.get('ok'), json.dumps(chop)[:200])
raw_protein = 0.695625
c = comp(chop['claims'], 'protein') if chop.get('ok') else None
check('chop conserves composition (protein per-100g unchanged)',
      c is not None and abs(c['value'] - raw_protein) < 1e-6)
c = comp(chop['claims'], 'particle-size') if chop.get('ok') else None
check('chop writes the STATED particle-size claim as estimated',
      c is not None and c['evidence_method'] == 'estimated'
      and c['value'] == 0.01)
check('chop parents the new state on the canonical subject',
      chop.get('ok') and json.loads(
          chop['outputState']['parent_state_ids_json'])
      == ['tomato-raw#as-defined'])

# ── 2. simmer concentrates by exact mass balance ──────────
simmer = derive_transform(
    MANAGER, 'food-simmer', 'tomato-raw#as-defined',
    {'yield_percent': 70.0})
check('simmer derives ok', simmer.get('ok'),
      json.dumps(simmer)[:200])
c = comp(simmer['claims'], 'protein') if simmer.get('ok') else None
check('simmer concentrates protein by exactly 100/70',
      c is not None
      and abs(c['value'] - raw_protein / 0.70) < 1e-6)
check('simmer names the A7 water assumption on the claim',
      c is not None and any('WATER (assumption A7)' in a
                            for a in json.loads(
                                c['assumptions_json'])))
check('simmer REFUSES the model-rung quantities by name (I5)',
      simmer.get('ok') and sorted(
          r['quantity'] for r in simmer['refusals'])
      == sorted(['starch-gelatinization-fraction',
                 'protein-denaturation-fraction', 'cell-integrity']))

# ── 3. retention rung rides R6 ────────────────────────────
boiled = derive_transform(
    MANAGER, 'food-boil', 'broccoli-raw#as-defined',
    {'yield_percent': 95.0, 'retention_code': '3784'})
check('boil+retention derives ok', boiled.get('ok'),
      json.dumps(boiled)[:200])
if boiled.get('ok'):
    vitc = comp(boiled['claims'], 'vitamin-c')
    prot = comp(boiled['claims'], 'protein')
    check('vitamin-c claim rides the retention-factor rung',
          vitc is not None
          and vitc['evidence_method'] == 'retention-factor')
    check('macros stay mass-balance (no R6 rows for protein)',
          prot is not None
          and prot['evidence_method'] == 'mass-balance')

# ── 4. honest refusals ────────────────────────────────────
check('heating without a stated yield REFUSES (no invented '
      'kinetics)',
      not derive_transform(MANAGER, 'food-simmer',
                           'tomato-raw#as-defined', {}).get('ok'))
check('observational process REFUSES (I2: measurements attach '
      'claims)',
      not derive_transform(MANAGER, 'food-measure-ph',
                           'tomato-raw#as-defined',
                           {'yield_percent': 100}).get('ok'))
check('unknown material refuses on missing claims',
      not derive_transform(MANAGER, 'food-simmer',
                           'dragonfruit#as-defined',
                           {'yield_percent': 80}).get('ok'))
check('non-food process refuses',
      not derive_transform(MANAGER, 'sealed-cure',
                           'tomato-raw#as-defined',
                           {'yield_percent': 80}).get('ok'))

# ── 5. mass gain dilutes (boiled rice) ────────────────────
rice = derive_transform(MANAGER, 'food-boil',
                        'rice-white-raw#as-defined',
                        {'yield_percent': 280.0})
if rice.get('ok'):
    carb_raw = None
    for row in MANAGER.objectTables['PropertyClaim'].values():
        if (row.subject_state_key == 'rice-white-raw#as-defined'
                and row.property_meaning_name == 'carbohydrate'):
            carb_raw = row.value
    c = comp(rice['claims'], 'carbohydrate')
    check('water uptake DILUTES per-100g (rice 280% yield)',
          c is not None and carb_raw is not None
          and abs(c['value'] - carb_raw / 2.8) < 1e-6)
    check('mass balance reports the water delta',
          abs(rice['massBalance']['waterDeltaG'] - 180.0) < 1e-6)
else:
    check('rice boil derives ok', False, json.dumps(rice)[:200])

# ── 6. mix is mass-weighted ───────────────────────────────
mix = derive_mix(MANAGER,
                 [{'subject': 'tomato-raw#as-defined', 'grams': 200},
                  {'subject': 'onion-raw#as-defined', 'grams': 100}],
                 output_material='demo-sauce')
check('mix derives ok', mix.get('ok'), json.dumps(mix)[:200])
if mix.get('ok'):
    t = MANAGER.objectTables['PropertyClaim']
    tom = onion = 0.0
    for row in t.values():
        if row.property_meaning_name == 'potassium':
            if row.subject_state_key == 'tomato-raw#as-defined':
                tom = row.value
            if row.subject_state_key == 'onion-raw#as-defined':
                onion = row.value
    expect = (tom * 2.0 + onion * 1.0) / 3.0
    c = comp(mix['claims'], 'potassium')
    check('mix potassium = mass-weighted mean',
          c is not None and abs(c['value'] - expect) < 1e-6)

# ── 7. the template chain agrees with the nmp rollup ──────
chain = template_state_chain(MANAGER, 'chicken-bowl-dinner')
check('template chain derives ok', chain.get('ok'),
      json.dumps(chain)[:300])
if chain.get('ok'):
    roll = template_rollup(
        MANAGER,
        SimpleNamespace(**[t for t in SEED_MEAL_TEMPLATES
                           if t['name'] == 'chicken-bowl-dinner'][0]))
    agree, compared = True, 0
    for nut in ('protein', 'iron', 'vitamin-c', 'calories'):
        a = chain['perMealAmounts'].get(nut)
        b = roll['perMeal'].get(nut, {}).get('amount')
        if a is None or b is None:
            continue
        compared += 1
        if b and abs(a - b) / max(abs(b), 1e-9) > 0.01:
            agree = False
            print(f'  disagree {nut}: chain {a} vs rollup {b}')
    check('two-modules-agree: chain per-meal amounts match the '
          'nmp-4 rollup within 1%', agree and compared >= 3,
          f'compared {compared}')
    check('terminal state is prepared-food on the template material',
          chain['terminalState']['name']
          == 'chicken-bowl-dinner#prepared-food'
          and chain['terminalState']['processing_stage'] == 'mixed')
    check('chain carries model-rung refusals (heated lines exist)',
          len(chain['modelRungRefusals']) > 0)

# ── 8. claims stay inside the pspp schema (zero new fields) ─
PSPP_CLAIM_FIELDS = {
    'name', 'subject_state_key', 'property_meaning_name',
    'scale_level', 'value', 'value_json', 'units', 'evidence_method',
    'assumptions_json', 'validity_json', 'source_execution_id',
    'confidence_json', 'provenance_id', 'notes'}
all_claims = (chop.get('claims', []) + simmer.get('claims', [])
              + mix.get('claims', []))
check('every derived claim uses ONLY PropertyClaim fields '
      '(zero pspp schema changes)',
      all(set(c) <= PSPP_CLAIM_FIELDS for c in all_claims))

# ── 9. persistence path degrades honestly off-server ──────
persisted = apply_transform(SimpleNamespace(objectTables={}),
                            {'ok': False})
check('apply_transform refuses a non-ok derivation',
      not persisted.get('ok'))

passed = sum(1 for _, ok in _results if ok)
print(f'\n{passed}/{len(_results)} checks passed')
if passed != len(_results):
    raise SystemExit(1)
