"""
@module bizops.selftest_bizops

biz-1 selftests: the setup axiom + upgrade gates, the local-economy
track deriving from live-shaped rows, and the order planner's three
answers (capacity, supply, mold-ladder reuse) over fixture orders.

Run from polari-framework/: python3 -m bizops.selftest_bizops
"""

import json
import types

from bizops.bizops_flows import (
    business_flow_report, local_economy_report,
)
from bizops.bizops_planner import order_plan
from bizops.bizops_seed import (
    SEED_BUSINESS_PROFILES, SEED_BUSINESS_STAGES,
    SEED_BUSINESS_UPGRADES, SEED_ECONOMY_MILESTONES,
    SEED_PROCESS_WORKFLOWS,
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


def _order(name, vol, qty):
    return types.SimpleNamespace(
        name=name, product_item_ref='geopolymer-mix',
        variant_note='', unit_volume_l=vol, quantity=qty,
        due_days=30, status='requested')


def _mgr():
    return types.SimpleNamespace(objectTables={
        'SupplySourceProfile': _rows(SEED_SUPPLY_SOURCES),
        'PriceCitation': _rows(SEED_PRICE_CITATIONS),
        'SourcePreferencePolicy': _rows(SEED_SOURCE_POLICIES),
        'ProductInputRequirement': _rows(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': _rows(SEED_PRODUCT_FORMULAS),
        'BusinessStageDefinition': _rows(SEED_BUSINESS_STAGES),
        'BusinessUpgradeStep': _rows(SEED_BUSINESS_UPGRADES),
        'BusinessProfile': _rows(SEED_BUSINESS_PROFILES),
        'LocalEconomyMilestone': _rows(SEED_ECONOMY_MILESTONES),
        'ProcessWorkflowDefinition': _rows(SEED_PROCESS_WORKFLOWS),
        'ProductOrder': {},
        'WaxReclaimBatch': {},
        'MoldLifecycleRecord': {},
    })


if __name__ == '__main__':
    mgr = _mgr()

    print('== suite: setup flow (the axiom) ==')
    out = business_flow_report(mgr, 'wax-mold-goods')
    check('live business sits AT the origin stage',
          out.get('ok') and out['stage']['index'] == 0
          and out['stage']['name'] == 'stage-0-solo-offtime')
    check('origin = off-time + markets + retail-available '
          '(the axiom as data)',
          'farmer-market' in out['stage']['salesChannels']
          and out['stage']['sourcingPosture'] == 'retail-available')
    names = {u['name'] for u in out['availableUpgrades']}
    check('upgrades applicable from stage 0: commit-hours + the '
          'stage-free capability adds',
          'commit-hours' in names
          and 'adopt-wax-reclaim-loop' in names
          and 'add-waterglass-production' in names
          and 'hire-caster' not in names)
    check('every upgrade carries its evidence gate (suggestions, '
          'never auto)',
          all(u['evidenceGate'] for u in out['availableUpgrades']))
    check('unknown business refused',
          not business_flow_report(mgr, 'nope').get('ok'))

    print('== suite: local economy track ==')
    out = local_economy_report(mgr)
    by = {m['name']: m for m in out['milestones']}
    check('track evaluates all seeded milestones',
          out.get('ok') and out['totalCount'] == 8)
    check('makeable milestones DONE (waterglass + metakaolin '
          'recipes exist)',
          by['ms-waterglass-makeable']['done']
          and by['ms-metakaolin-makeable']['done'])
    check('mutual loop DONE (the farm supplies AND demands)',
          by['ms-mutual-loop']['done'])
    check('local wax feedstock NOT done (farm still potential) — '
          'derived, not hand-flipped',
          not by['ms-local-wax-feedstock']['done'])
    check('reclaim + crush milestones honestly not done (no '
          'physical batches)',
          not by['ms-reclaim-running']['done']
          and not by['ms-crush-loop-logged']['done'])
    check('nextGap points at the FIRST open rung',
          out['nextGap']['name'] == 'ms-local-wax-feedstock')
    check('progress % consistent',
          abs(out['progressPct']
              - 100.0 * out['doneCount'] / 8) < 0.1)

    print('== suite: order planner — empty registrar ==')
    out = order_plan(mgr, 'wax-mold-goods')
    check('empty registrar answered honestly',
          out.get('ok') and out.get('orders') == 0
          and 'empty' in out['note'])

    print('== suite: order planner — the three answers ==')
    mgr.objectTables['ProductOrder'] = {
        'a': _order('ord-cups', 0.5, 200),
        'b': _order('ord-pots', 1.0, 60),
        'c': _order('ord-planters', 4.0, 10),
    }
    out = order_plan(mgr, 'wax-mold-goods', horizon_days=30)
    check('plan ok over 3 orders in 3 size rungs',
          out.get('ok') and out['ordersConsidered'] == 3
          and len(out['rungs']) == 3)
    check('(1) capacity answered: needed vs available hours, '
          'infeasible at stage-0 off-time',
          out['capacity']['laborHoursNeeded'] > 0
          and out['capacity']['laborHoursAvailable'] == 42.9
          and out['capacity']['feasible'] is False)
    check('infeasible -> defer SUGGESTIONS free enough hours',
          out['capacity']['deferSuggestions']
          and sum(d['hoursFreed']
                  for d in out['capacity']['deferSuggestions'])
          >= out['capacity']['laborHoursNeeded']
          - out['capacity']['laborHoursAvailable'])
    check('(2) supply answered as a priced manifest riding the '
          'cascade', out['supply']['geopolymerMixKg'] > 0
          and out['supply']['estimatedMaterialCost'] > 0
          and 'inventory' in out['supply']['note'])
    check('(3) reuse: ladder collapses 270 naive molds to a '
          'handful', out['reuse']['moldsNaive'] == 270
          and out['reuse']['moldsPlanned'] <= 30
          and out['reuse']['moldSavingsPct'] > 85)
    check('no ceramic strategy without the capability',
          all(r['strategy'] != 'ceramic-fired'
              for r in out['rungs']))
    check('reclaim NOT applied without the capability, and the '
          'assumption names the upgrade lever',
          all(not r['reclaimApplied'] for r in out['rungs'])
          and any('adopt-wax-reclaim-loop' in a
                  for a in out['assumptions']))

    print('== suite: capabilities change the plan ==')
    biz = mgr.objectTables['BusinessProfile']['wax-mold-goods']
    biz.capabilities_json = json.dumps(
        ['wax-printing', 'geopolymer-casting', 'wax-reclaim-loop',
         'ceramic-firing'])
    biz.weekly_hours = 55.0
    out2 = order_plan(mgr, 'wax-mold-goods', horizon_days=30)
    check('ceramic strategy now available and picked somewhere',
          any(r['strategy'] == 'ceramic-fired'
              for r in out2['rungs']))
    check('reclaim shrinks the net wax line',
          out2['supply']['waxKgNet'] < out['supply']['waxKgNet'])
    check('more hours move capacity toward feasible',
          out2['capacity']['laborHoursAvailable']
          > out['capacity']['laborHoursAvailable'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
