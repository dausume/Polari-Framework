"""
@module supplychain.selftest_molds

mold-1 selftests: strategy economics over the cited stack (wax vs
geopolymer-cast vs ceramic-fired), the mandatory-release-agent and
slip-casting honesty, the crush-to-aggregate credit, and the fleet
report that replaces cycle-life estimates with measured retirements.

Run from polari-framework/: python3 -m supplychain.selftest_molds
"""

import types

from supplychain.mold_analysis import (
    mold_fleet_report, mold_strategy_compare,
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
        'MoldLifecycleRecord': {},
    })


if __name__ == '__main__':
    mgr = _mgr()

    print('== suite: strategy comparison (100 casts) ==')
    out = mold_strategy_compare(mgr, casts=100)
    by = {s['strategy']: s for s in out['strategies']}
    check('three strategies costed from the cited stack',
          out.get('ok') and set(by) == {'wax-printed',
                                        'geopolymer-cast',
                                        'ceramic-fired'})
    check('geopolymer mold cost rides the CASCADED mix (~1.67 = '
          '1.5kg x 1.11)',
          abs(by['geopolymer-cast']['moldCost'] - 1.665) < 0.03
          and out['inputs']['geopolymer']['via'] == 'made')
    check('release agent costed on geopolymer + ceramic, NOT on '
          'wax molds',
          by['geopolymer-cast']['releasePerCast'] > 0
          and by['ceramic-fired']['releasePerCast'] > 0
          and by['wax-printed']['releasePerCast'] == 0)
    check('crush-to-aggregate credit applied to geopolymer + '
          'ceramic molds',
          by['geopolymer-cast']['crushCreditPerMold'] > 0
          and by['ceramic-fired']['crushCreditPerMold'] > 0
          and by['wax-printed']['crushCreditPerMold'] == 0)
    check('every cycle life is FLAGGED as an estimate',
          all(s['cyclesIsEstimate'] for s in out['strategies']))
    check('per-cast costs are all sub-dollar (mold cost is not '
          'the business bottleneck)',
          all(s['costPerCast'] < 1.0 for s in out['strategies']))
    check('slip-casting explicitly REFUSED, pressing allowed',
          out['refused']
          and 'capillary' in out['refused'][0]['refusal'])
    check('assumptions name the bond risk + kiln-energy exclusion',
          any('bonds to cured' in a for a in out['assumptions'])
          and any('EXCLUDED' in a for a in out['assumptions']))

    print('== suite: volume crossover ==')
    small = mold_strategy_compare(mgr, casts=10)
    small_by = {s['strategy']: s for s in small['strategies']}
    check('at 10 casts one geopolymer mold covers it (moldsNeeded '
          '1), wax needs 1 too',
          small_by['geopolymer-cast']['moldsNeeded'] == 1
          and small_by['wax-printed']['moldsNeeded'] == 1)
    big = mold_strategy_compare(mgr, casts=1000)
    big_by = {s['strategy']: s for s in big['strategies']}
    check('at 1000 casts wax needs 100 molds, ceramic only 5',
          big_by['wax-printed']['moldsNeeded'] == 100
          and big_by['ceramic-fired']['moldsNeeded'] == 5)

    print('== suite: fleet report (measured beats estimated) ==')
    out = mold_fleet_report(mgr)
    check('empty fleet -> honest note', out.get('ok')
          and not out['fleets'] and 'estimates' in out['note'])
    mgr.objectTables['MoldLifecycleRecord'] = {
        'a': types.SimpleNamespace(
            mold_material='geopolymer', casts_completed=37,
            condition='retired', retired_reason='edge chipping',
            crushed_kg_recovered=1.4),
        'b': types.SimpleNamespace(
            mold_material='geopolymer', casts_completed=12,
            condition='in-service', retired_reason='',
            crushed_kg_recovered=0.0),
    }
    out = mold_fleet_report(mgr)
    fleet = out['fleets']['geopolymer']
    check('fleet counts molds, retirements, max casts',
          fleet['molds'] == 2 and fleet['retired'] == 1
          and fleet['castsMax'] == 37)
    check('crushed kg tracked back into the loop',
          abs(fleet['crushedKgRecovered'] - 1.4) < 0.001)
    check('retirement reasons tallied (the failure-mode data)',
          fleet['retiredReasons'] == {'edge chipping': 1})

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
