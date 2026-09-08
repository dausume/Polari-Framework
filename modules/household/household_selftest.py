"""
@module household.household_selftest

hh-1 selftest — the household layer on its own (no nutrition import,
no server): availability from PersonSchedule recurrences, a step's
minutes bounded BELOW by the safety floor, who may do a hazard step,
refinement that never rewards rushing, the percentage-share
allocation over a small fake manager (the step-builder registry
extended with a chore category), and the fairness readout.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m household.household_selftest
"""

import sys
from datetime import datetime
from types import SimpleNamespace

from household.custom.household_analysis import (
    STEP_BUILDERS, WTYPE_OF_CATEGORY, assign_work, availability_windows,
    fairness_readout, refine_speed_factors, register_step_builder,
    safety_check, step_minutes, where_is,
)
from household.household_basis import (
    HOUSEHOLD_SEED_PAIRS, SKILL_FACTORS, SPEED_FACTOR_FLOOR,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


def _manager():
    tables = {cls: _rows(seeds) for cls, _c, seeds in HOUSEHOLD_SEED_PAIRS}
    # a method table by NAME (household reads rows, never a nutrition
    # import): the base minutes the refinement loop divides by.
    tables['StepMethod'] = _rows([{'name': 'dice-knife', 'base_min': 5.0}])
    return SimpleNamespace(objectTables=tables)


def main():
    mgr = _manager()
    print('hh-1 household layer')

    # --- availability --------------------------------------------------
    av = availability_windows(mgr, 'demo-alex', '2026-08-31', '2026-09-06')
    kinds = {b['kind'] for b in av['busy']}
    check('availability: Alex\'s work, commute and sleep expand from PersonSchedule recurrences',
          {'work', 'commute', 'sleep'} <= kinds and av['free'], str(kinds))
    check('sleep crossing midnight expands as one block (23:00 → 07:00 next day)',
          any(b['kind'] == 'sleep' and b['start'].endswith('T23:00') and b['end'].endswith('T07:00')
              for b in av['busy']))
    check('where_is: Alex is at the workplace Tuesday noon, home Tuesday 20:00',
          where_is(mgr, 'demo-alex', datetime(2026, 9, 1, 12, 0))[0] == 'workplace'
          and where_is(mgr, 'demo-alex', datetime(2026, 9, 1, 20, 0))[0] == 'home')
    check('a person with no schedule is simply home and free',
          where_is(mgr, 'demo-nobody', datetime(2026, 9, 1, 12, 0)) == ('home', '', 'free'))

    # --- step minutes with a safety floor ------------------------------
    sam = step_minutes(mgr, 'demo-sam', 'dice-mandoline', 1.0)
    alex = step_minutes(mgr, 'demo-alex', 'dice-mandoline', 1.0)
    check('step_minutes: a novice\'s raw minutes = base × the level factor',
          abs(sam['raw'] - 1.0 * SKILL_FACTORS['novice']) < 1e-9, str(sam))
    check('the safety floor (2.0 min) bounds BOTH the novice and the experienced cook',
          sam['minutes'] == 2.0 and alex['minutes'] == 2.0
          and sam['boundedBySafety'] and alex['boundedBySafety'], f'{sam} {alex}')
    check('above the floor the experienced cook is faster (skill shortens, floor bounds)',
          step_minutes(mgr, 'demo-alex', 'dice-knife', 10.0)['minutes']
          < step_minutes(mgr, 'demo-sam', 'dice-knife', 10.0)['minutes'])
    check('an unknown method has no factors and no floor (base minutes pass through)',
          step_minutes(mgr, 'demo-sam', 'no-such-method', 7.0)['minutes'] == 7.0)

    # --- safety --------------------------------------------------------
    check('safety_check: Sam (experienced kitchen-safety) dices alone',
          safety_check(mgr, 'demo-sam', 'dice-knife')['verdict'] == 'alone')
    kid = safety_check(mgr, 'demo-kid', 'dice-knife')
    check('an unknown person is a novice by default → knife work is supervised, the rule named',
          kid['verdict'] == 'supervised' and kid['reasons'] and 'rule wants intermediate' in kid['reasons'][0],
          str(kid))
    check('the method\'s own skill floor: Sam is novice at knife-work, the mandoline wants intermediate → supervised',
          safety_check(mgr, 'demo-sam', 'dice-mandoline')['verdict'] == 'supervised')
    mgr.objectTables['MethodSkillRequirement']['x'] = SimpleNamespace(
        id='x', name='req-pressure-cook', method_name='pressure-cook', task_kind='pressure-cook',
        skills_json='[]', safety_floor_min=0.0, hazard_tags_json='["pressure"]')
    check('a below_floor=unassigned rule (pressure) refuses a novice outright',
          safety_check(mgr, 'demo-kid', 'pressure-cook')['verdict'] == 'unassigned')

    # --- refinement never rewards rushing -------------------------------
    ref = refine_speed_factors(mgr, 'demo-alex')
    prop = [p for p in ref['proposals'] if p.get('status') == 'proposal']
    check('refine_speed_factors: 3 observations of Alex dicing (4.5/5/4 vs base 5) → median 0.9 proposed',
          prop and prop[0]['skill'] == 'knife-work' and prop[0]['proposedFactor'] == 0.9
          and not ref['safetyQuestions'], str(ref))
    for o in mgr.objectTables['DurationObservation'].values():
        o.observed_min = 2.0
    ref2 = refine_speed_factors(mgr, 'demo-alex')
    check('observed 60 % faster than the method → a SAFETY QUESTION; the factor stays at the floor',
          ref2['safetyQuestions'] and ref2['proposals'][0]['proposedFactor'] == SPEED_FACTOR_FLOOR,
          str(ref2))
    check('nobody with fewer than 3 observations gets a proposal (Sam has none)',
          not [p for p in refine_speed_factors(mgr, 'demo-sam')['proposals']
               if p.get('status') == 'proposal'])

    # --- the allocation over the step-builder registry ------------------
    check('household registers the generic builders (purchase, cleanup); meal ones are nutrition\'s',
          {'purchase', 'cleanup'} <= set(STEP_BUILDERS) and WTYPE_OF_CATEGORY['cleanup'] == 'cleanup')

    def _vacuum(event, payload, base_min):
        return [{'label': 'vacuum', 'method': '', 'baseMin': float(payload.get('minutes') or base_min)}]
    register_step_builder('vacuum', _vacuum, 'cleanup')
    check('register_step_builder: a chore category extends the registry and names its workload type',
          STEP_BUILDERS['vacuum'] is _vacuum and WTYPE_OF_CATEGORY['vacuum'] == 'cleanup')

    def ev(name, cat, start, end, **payload):
        return {'name': name, 'category': cat, 'span': {'start': start, 'end': end},
                'payload_json': payload}
    # Monday 2026-08-31 evening: Alex home after 17:00, Sam off (works Tue–Sat).
    events = [
        ev('shop', 'purchase', '2026-08-31T10:00', '2026-08-31T11:00', estTotal=60.0),
        ev('dishes-1', 'cleanup', '2026-08-31T19:30', '2026-08-31T19:50', minutes=20.0),
        ev('dishes-2', 'cleanup', '2026-08-31T20:00', '2026-08-31T20:20', minutes=20.0),
        ev('dishes-3', 'cleanup', '2026-08-31T20:30', '2026-08-31T20:50', minutes=20.0),
        ev('vacuum-1', 'vacuum', '2026-08-31T21:00', '2026-08-31T21:30', minutes=30.0),
        ev('mystery', 'no-such-category', '2026-08-31T21:30', '2026-08-31T21:45', minutes=15.0),
    ]
    work = assign_work(mgr, events, 'demo-household')
    check('assign_work: ok, both members known', work['ok'] and set(work['people']) == {'demo-alex', 'demo-sam'})
    shop = [a for a in work['allocation'] if a['event'] == 'shop']
    check('purchase-trip policy = everyone → both adults go (his 2-adult example)',
          shop and set(shop[0]['assignees']) == {'demo-alex', 'demo-sam'} and shop[0]['mode'] == 'everyone',
          str(shop))
    cleanup = work['readout'].get('cleanup', {})
    check('cleanup (40/60 shares): the chore category rides the cleanup policy; readout carries targets',
          cleanup.get('targetPct') == {'demo-alex': 40, 'demo-sam': 60}
          and cleanup.get('minutes', {}).get('demo-sam', 0) > 0
          and cleanup.get('minutes', {}).get('demo-alex', 0) > 0, str(cleanup))
    check('the vacuum chore was allocated to someone (registry-driven, no meal import)',
          any(a['event'] == 'vacuum-1' and a['assignees'] for a in work['allocation']))
    check('an unregistered category is skipped, never guessed',
          not any(a['event'] == 'mystery' for a in work['allocation']) and not work['unassigned'])
    cmp = work['purchaseVsDelivery']
    check('purchase vs delivery comparison: basket, both shoppers, fee + markup + min-order',
          cmp and cmp['basket'] == 60.0 and len(cmp['shoppers']) == 2 and cmp['delivery']['fee'] == 7.99
          and cmp['delivery']['meetsMinOrder'] is True, str(cmp))
    # a busy window: Tuesday 13:00 — Alex at work, Sam on shift → nobody free
    busy = assign_work(mgr, [ev('dishes-busy', 'cleanup', '2026-09-01T13:00', '2026-09-01T13:20', minutes=20.0)],
                       'demo-household')
    check('a step nobody is free for is left unassigned and NAMED',
          busy['unassigned'] and 'busy' in busy['unassigned'][0]['why'], str(busy['unassigned']))
    check('an unknown household refuses honestly',
          not assign_work(mgr, events, 'no-such-household')['ok'])

    # --- fairness ------------------------------------------------------
    fair0 = fairness_readout(mgr, 'demo-household')
    check('fairness_readout: no ledger rows → says so, no lines', fair0['ok'] and not fair0['lines']
          and 'no WorkLedger rows' in fair0['status'])
    mgr.objectTables['WorkLedger'] = _rows([
        {'name': 'l1', 'household_name': 'demo-household', 'person_name': 'demo-alex',
         'workload_type': 'cleanup', 'minutes': 30.0, 'date': '2026-08-31'},
        {'name': 'l2', 'household_name': 'demo-household', 'person_name': 'demo-sam',
         'workload_type': 'cleanup', 'minutes': 10.0, 'date': '2026-09-01'},
    ])
    fair = fairness_readout(mgr, 'demo-household')
    line = {l['person']: l for l in fair['lines'] if l['workload'] == 'cleanup'}
    check('actuals 75/25 vs targets 40/60 → drift +35 / −35, one flat line per person',
          line['demo-alex']['actualPct'] == 75.0 and line['demo-alex']['driftPct'] == 35.0
          and line['demo-sam']['driftPct'] == -35.0, str(fair['lines']))
    check('drift beyond 10 points → a suggestion toward the person under target (never a reassignment)',
          fair['byType']['cleanup']['suggestion'] == 'rebalance toward demo-sam')
    check('date filters narrow the ledger', fairness_readout(mgr, 'demo-household', from_date='2026-09-01')['records'] == 1)

    print(f'\n{len(failures)} failure(s)' if failures else '\nall household checks passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
