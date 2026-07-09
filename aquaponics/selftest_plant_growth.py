"""
Selftest — aqp-8: per-part plant growth / growth-failure + volume
interactions.

Run from polari-framework/:
    python3 -m aquaponics.selftest_plant_growth

Covers: logistic growth saturates at V_max under ample supply;
starving ONE species drives the dependent part to stressed->failure
with THAT species named; the interaction estimate responds to volume
(bigger leaves -> stronger root-demand coupling); a healthy vs a
resource-starved run diverge; volumes + conditions accompany every
interaction claim.
"""

from types import SimpleNamespace

from aquaponics.plant_growth import (
    estimate_interactions, grow, supply_factor,
)
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS

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
    })


if __name__ == '__main__':
    manager = _mgr()

    print('logistic growth under ample supply')
    # Ample supply: give every 'in' species well above needed.
    ample = {sp: 1e6 for sp in (
        'nitrate-n', 'ammonium-n', 'phosphorus-p', 'potassium-k',
        'calcium-ca', 'magnesium-mg', 'iron-fe')}
    healthy = grow(manager, 'sweet-basil', days=120.0, supply=ample)
    check('grow ok + per-part results', healthy['ok']
          and len(healthy['perPart']) == 3)
    leaf = next(p for p in healthy['perPart']
                if p['part'] == 'sweet-basil-leaf')
    check('leaf saturates near V_max under ample supply',
          leaf['fractionOfMax'] > 0.9 and leaf['finalVolumeCm3']
          <= leaf['maxVolumeCm3'] + 1e-6)
    check('all parts survive under ample supply',
          healthy['survived']
          and all(p['condition'] == 'healthy'
                  for p in healthy['perPart']))

    print('growth failure names the limiting species')
    # Starve nitrate for the root (which needs nitrate-n).
    starved = grow(manager, 'sweet-basil', days=120.0, supply=ample,
                   supply_by_part={'sweet-basil-root':
                                   dict(ample, **{'nitrate-n': 0.0})})
    root = next(p for p in starved['perPart']
                if p['part'] == 'sweet-basil-root')
    check('starved root fails or is stressed',
          root['condition'] in ('failed', 'stressed'))
    check('the limiting species is named nitrate-n',
          root['limitingSpecies'] == 'nitrate-n')
    check('failure summary present when a part fails',
          (not starved['survived']) == (root['condition'] == 'failed'))
    fail_transitions = [t for t in starved['conditionTransitions']
                        if t['part'] == 'sweet-basil-root']
    check('condition transition recorded w/ limiting species',
          any(t['limitingSpecies'] == 'nitrate-n'
              for t in fail_transitions))

    print('healthy vs starved diverge')
    check('starved root ends smaller than healthy root',
          root['finalVolumeCm3']
          < next(p for p in healthy['perPart']
                 if p['part'] == 'sweet-basil-root')['finalVolumeCm3'])

    print('volume-based interaction estimate')
    inter = healthy['interactions']['ranked']
    check('interactions ranked by magnitude', inter
          and all(abs(inter[i]['magnitude'])
                  >= abs(inter[i + 1]['magnitude'])
                  for i in range(len(inter) - 1)))
    check('every interaction carries source volume + condition + why',
          all('sourceVolumeCm3' in f and 'sourceCondition' in f
              and f.get('why') for f in inter))
    # Volume responsiveness: a bigger leaf volume -> stronger leaf->root
    # demand magnitude.
    small = estimate_interactions({
        'l': {'part': 'leaf', 'volume': 20.0, 'condition': 'healthy'},
        'r': {'part': 'root', 'volume': 30.0, 'condition': 'healthy'}})
    big = estimate_interactions({
        'l': {'part': 'leaf', 'volume': 200.0, 'condition': 'healthy'},
        'r': {'part': 'root', 'volume': 30.0, 'condition': 'healthy'}})

    def _leaf_root(est):
        return next(f['magnitude'] for f in est['ranked']
                    if f['source'] == 'leaf' and f['target'] == 'root')

    check('bigger leaf volume -> stronger leaf->root demand coupling',
          abs(_leaf_root(big)) > abs(_leaf_root(small)))
    check('leaf->root is a demand (negative sign)',
          _leaf_root(big) < 0)

    print('supply_factor helper (Liebig minimum)')
    root_part = next(SimpleNamespace(**p) for p in SEED_PLANT_PARTS
                     if p['name'] == 'sweet-basil-root')
    factor, limiting = supply_factor(root_part, {'nitrate-n': 0.0})
    check('zero nitrate -> factor 0, limiting nitrate-n',
          factor == 0.0 and limiting == 'nitrate-n')
    factor2, _ = supply_factor(root_part, {sp: 1e6 for sp in (
        'nitrate-n', 'ammonium-n', 'phosphorus-p', 'potassium-k',
        'calcium-ca', 'magnesium-mg', 'iron-fe')})
    check('ample supply -> factor 1.0', abs(factor2 - 1.0) < 1e-9)

    print('honest priors')
    check('grow flags abstract interaction priors',
          'ABSTRACT' in healthy['note']
          and 'estimate' in healthy['interactions']['note'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
