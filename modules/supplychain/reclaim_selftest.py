"""
@module supplychain.reclaim_selftest

wp-r selftests: the wax melt-off loopback economics (steady state +
cycle curve over cited costs, estimate honesty, refusals) and the
WaxReclaimBatch pool report that will replace the estimates with
measured recovery ratios.

Run from polari-framework/: python3 -m supplychain.reclaim_selftest
"""

import types

from supplychain.custom.reclaim_analysis import (
    reclaim_cycle_curve, reclaim_pool_report, reclaim_steady_state,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _rows(seed_list):
    return {s['name']: types.SimpleNamespace(**s) for s in seed_list}


def _mgr():
    return types.SimpleNamespace(objectTables={
        'SupplySourceProfile': _rows(SEED_SUPPLY_SOURCES),
        'PriceCitation': _rows(SEED_PRICE_CITATIONS),
        'SourcePreferencePolicy': _rows(SEED_SOURCE_POLICIES),
        'ProductInputRequirement': _rows(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': _rows(SEED_PRODUCT_FORMULAS),
        'WaxReclaimBatch': {},
    })


if __name__ == '__main__':
    mgr = _mgr()

    print('== suite: steady-state reclaim economics ==')
    out = reclaim_steady_state(mgr)
    check('steady state ok, virgin wax resolved from the cited '
          'stack (self-made blend)',
          out.get('ok') and out['virginWax']['via'] == 'made')
    no_r = out['noReclaimCostPerMold']
    steady = out['steadyStateCostPerMold']
    check('reclaim cuts the per-mold wax cost by ~83-85% at '
          'r=0.85 (makeup + citric wash)',
          steady < no_r * 0.2 and out['savingsPct'] > 80.0)
    check('default recovery fraction is FLAGGED as an estimate',
          out['recoveryFractionIsEstimate'] is True)
    check('assumptions name saponification, the wash, excluded '
          'energy, and the UNKNOWN generation ceiling',
          any('saponif' in a for a in out['assumptions'])
          and any('ENERGY' in a for a in out['assumptions'])
          and any('UNKNOWN' in a for a in out['assumptions']))
    check('breakdown = virgin makeup + citric wash, both > 0',
          out['breakdown']['virginMakeup'] > 0
          and out['breakdown']['citricWash'] > 0)

    print('== suite: refusals ==')
    check('r=1.0 refused (perpetual motion)',
          not reclaim_steady_state(
              mgr, recovery_fraction=1.0).get('ok'))
    bare = types.SimpleNamespace(objectTables={
        'PriceCitation': {}, 'SupplySourceProfile': {},
        'SourcePreferencePolicy': {},
        'ProductInputRequirement': {}, 'ProductFormula': {}})
    check('no cited wax at all -> honest refusal',
          not reclaim_steady_state(bare).get('ok'))

    print('== suite: cycle curve ==')
    out = reclaim_cycle_curve(mgr, cycles=10)
    curve = out['curve']
    check('cycle 1 = all-virgin cost; average falls monotonically',
          curve[0]['cumulativeAvgPerMold'] == out['firstCycle']
          and all(curve[i]['cumulativeAvgPerMold']
                  <= curve[i - 1]['cumulativeAvgPerMold']
                  for i in range(1, len(curve))))
    check('10-cycle average approaches steady state',
          curve[-1]['cumulativeAvgPerMold']
          < out['firstCycle'] * 0.35)

    print('== suite: pool report (the data that replaces the '
          'estimates) ==')
    out = reclaim_pool_report(mgr)
    check('no batches -> honest empty report',
          out.get('ok') and not out['pools']
          and 'estimates' in out['note'])
    mgr.objectTables['WaxReclaimBatch'] = {
        'a': types.SimpleNamespace(
            pool_name='pool-1', generation=1, melted_off_kg=1.0,
            recovered_kg=0.88, virgin_makeup_kg=0.12,
            printability='good'),
        'b': types.SimpleNamespace(
            pool_name='pool-1', generation=2, melted_off_kg=1.0,
            recovered_kg=0.84, virgin_makeup_kg=0.16,
            printability='untested'),
    }
    out = reclaim_pool_report(mgr)
    pool = out['pools']['pool-1']
    check('pool tracks the reuse-cycle counter (max generation 2)',
          pool['maxGeneration'] == 2 and pool['batches'] == 2)
    check('MEASURED recovery fraction computed from the rows '
          '(0.86)', abs(pool['measuredRecoveryFraction'] - 0.86)
          < 0.001)
    check('printability verdicts tallied',
          pool['printability'] == {'good': 1, 'untested': 1})

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
