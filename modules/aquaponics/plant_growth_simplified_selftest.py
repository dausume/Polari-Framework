"""
Selftest — the SIMPLIFIED/AGGREGATE growth model (renamed + rebuilt
2026-07-15, was aqp-8's plant_growth.py — see
aquaponics/custom/plant_growth_simplified.py's own module docstring for the
full "one real model + a distilled aggregate wrapper" design).

Run from polari-framework/:
    python3 -m aquaponics.plant_growth_simplified_selftest

Uses REAL seed rows (sweet-basil) throughout. Covers: constants are
pulled from the REAL detailed model (free_soil_constants), not an
independent lookup; the closed-form curve evaluated directly matches
the detailed model's own math exactly; supply_factor (a coarse overall
scalar) still saturates/starves growth correctly; failure is named
honestly without the detailed model's per-species machinery; count
scales an aggregate population; the abstract interaction estimate
still responds to volume, clearly labeled as NOT the real transport
mechanism.
"""

from types import SimpleNamespace

from aquaponics.plant_growth_normalized_basis import closed_form_logistic
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.custom.plant_growth_simplified import (
    estimate_interactions, grow,
)
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from plant_morphology.morphology_seed import SEED_ROOT_MODELS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(models=None):
    return SimpleNamespace(objectTables={
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(models if models is not None
                                  else SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('constants come from the REAL detailed model, not an '
          'independent lookup')
    healthy = grow(manager, 'sweet-basil', days=120.0)
    check('grow ok + per-part results (root/stem/leaf, real '
          'PlantGrowthModel rows)', healthy['ok']
          and len(healthy['perPart']) == 3)
    leaf = next(p for p in healthy['perPart']
               if p['part'] == 'sweet-basil-leaf')
    check("leaf's maxVolumeCm3 matches the real seeded "
          'PlantGrowthModel.max_volume_cm3 (120.0), sourced via '
          'free_soil_constants — not re-declared here',
          abs(leaf['maxVolumeCm3'] - 120.0) < 1e-6)

    print('the closed-form curve evaluated directly matches the '
          "detailed model's own math EXACTLY (same function, same "
          'numbers)')
    hand_computed = closed_form_logistic(
        0.02 * 120.0, 0.16 * 1.0, 120.0, 120.0)
    check('leaf finalVolumeCm3 is bit-for-bit the same closed_form_'
          'logistic() call the detailed model itself uses — genuinely '
          'pulling the curve, not approximating it',
          abs(leaf['finalVolumeCm3'] - round(hand_computed, 3)) < 1e-6)

    print('logistic growth under a favorable overall supply_factor')
    check('leaf saturates near V_max under supply_factor=1.0 '
          '(unconstrained, the default)',
          leaf['fractionOfMax'] > 0.9 and leaf['finalVolumeCm3']
          <= leaf['maxVolumeCm3'] + 1e-6)
    check('all parts survive under supply_factor=1.0',
          healthy['survived']
          and all(p['condition'] == 'healthy'
                  for p in healthy['perPart']))

    print('growth failure — a coarse OVERALL scalar now, not a '
          'per-species Liebig computation (the real per-stress-type '
          'machinery lives in the detailed model)')
    starved = grow(manager, 'sweet-basil', days=120.0,
                   supply_factor_by_part={'sweet-basil-root': 0.1})
    root = next(p for p in starved['perPart']
               if p['part'] == 'sweet-basil-root')
    check('a low per-part supply_factor drives that part to failed',
          root['condition'] == 'failed' and root['supplyFactor'] == 0.1)
    check('failure summary present, names a real REASON (not a '
          'species — that granularity moved to the detailed model)',
          not starved['survived']
          and starved['failureSummary'] is not None
          and 'sweet-basil-root' == starved['failureSummary'][0]['part']
          and 'below the failure threshold' in
              starved['failureSummary'][0]['reason'])
    check('other parts (not overridden) are unaffected — '
          'supply_factor_by_part is a PER-PART override, not global',
          next(p for p in starved['perPart']
              if p['part'] == 'sweet-basil-leaf')['condition']
          == 'healthy')

    print('healthy vs starved diverge — real numbers, not just labels')
    check('starved root ends smaller than healthy root',
          root['finalVolumeCm3']
          < next(p for p in healthy['perPart']
                if p['part'] == 'sweet-basil-root')['finalVolumeCm3'])

    print('count — the mass/aggregate-scale knob ("if we had a whole '
          'forest of these...")')
    single = grow(manager, 'sweet-basil', days=120.0, count=1)
    forest = grow(manager, 'sweet-basil', days=120.0, count=1000)
    leaf_single = next(p for p in single['perPart']
                       if p['part'] == 'sweet-basil-leaf')
    leaf_forest = next(p for p in forest['perPart']
                       if p['part'] == 'sweet-basil-leaf')
    check('count=1000 scales finalVolumeCm3 by EXACTLY 1000x — one '
          'representative trajectory times count, not 1000 '
          'independent simulations',
          abs(leaf_forest['finalVolumeCm3']
              - leaf_single['finalVolumeCm3'] * 1000) < 1.0)
    check('per-INDIVIDUAL maxVolumeCm3 in the note is scaled '
          'consistently (maxVolumeCm3 also carries count, by design — '
          'both final and max share the same population multiplier)',
          abs(leaf_forest['maxVolumeCm3']
              - leaf_single['maxVolumeCm3'] * 1000) < 1.0)
    check('fractionOfMax is population-INVARIANT (a per-individual '
          'ratio, count cancels out)',
          abs(leaf_forest['fractionOfMax'] - leaf_single['fractionOfMax'])
          < 1e-6)
    check("count is echoed back so a caller can't lose track of the "
          'population size',
          forest['count'] == 1000)

    print('volume-based interaction estimate — kept as an ABSTRACT '
          'prior, clearly labeled as not the real mechanism')
    inter = healthy['interactions']['ranked']
    check('interactions ranked by magnitude', inter
          and all(abs(inter[i]['magnitude'])
                  >= abs(inter[i + 1]['magnitude'])
                  for i in range(len(inter) - 1)))
    check('every interaction carries source volume + condition + why',
          all('sourceVolumeCm3' in f and 'sourceCondition' in f
              and f.get('why') for f in inter))
    small = estimate_interactions({
        'l': {'part': 'leaf', 'volume': 20.0, 'condition': 'healthy'},
        'r': {'part': 'root', 'volume': 30.0, 'condition': 'healthy'}})
    big = estimate_interactions({
        'l': {'part': 'leaf', 'volume': 200.0, 'condition': 'healthy'},
        'r': {'part': 'root', 'volume': 30.0, 'condition': 'healthy'}})

    def _leaf_root(est):
        return next(f['magnitude'] for f in est['ranked']
                    if f['source'] == 'leaf' and f['target'] == 'root')

    check('bigger leaf volume -> stronger leaf->root demand coupling '
          '(the old aqp-8 behavior, unchanged)',
          abs(_leaf_root(big)) > abs(_leaf_root(small)))
    check('interactions note explicitly points at the REAL mechanism '
          '(transport_factor) rather than implying this IS it',
          'transport_factor' in healthy['interactions']['note']
          and 'REAL' in healthy['interactions']['note'])

    print('honest labeling — this module says plainly what it is now')
    check('grow note names the detailed model as the constants/curve '
          'source', 'plant_growth_normalized' in healthy['note']
          and 'SIMPLIFIED' in healthy['note'])

    print('honest refusals')
    check('unknown plant refuses',
          not grow(manager, 'nope', days=10.0).get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
