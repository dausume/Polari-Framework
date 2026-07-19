"""
Self-test for pspp-8 network stepping: measured-Q inventories, rule
applicability (species/site/cation/gate), stoichiometric step_once,
and kinetics-free framework reachability with hypothesis floors.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_network_stepping
"""

import sys

from pspp.network_stepping import (
    applicable_rules, reachable_frameworks, solution_inventory,
    step_once,
)
from pspp.reaction_network import SEED_REACTION_RULES, rule_rate

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_inventory():
    print('[solution inventory from measured Q data]')
    low = solution_inventory('Na', 1.0)
    check('MR=1.0 inventory ok', low['ok'])
    check('Q0 present with the Table 5.6 solution amount (20)',
          low['inventory'].get('siloxonate-q0') == 20.0)
    check('zero-amount Q motifs absent, not zero-stocked',
          'siloxonate-q4' not in low['inventory'])
    check('water/ions present but unquantified (None)',
          low['inventory']['water'] is None
          and low['inventory']['sodium-ion'] is None)
    check('di-siloxonate mirrors Q1 (p.184)',
          low['inventory']['di-siloxonate']
          == low['inventory']['siloxonate-q1'])
    between = solution_inventory('Na', 1.5)
    check('between-MR query refuses (no kinetic law in source)',
          between['ok'] is False)
    k = solution_inventory('K', 1.0)
    check('K inventory refuses naming the missing dataset',
          k['ok'] is False and 'DigitizedDataset' in k['suggestion'])


def test_applicability():
    print('[applicability: species / site / cation / gate]')
    inv = solution_inventory('Na', 1.0)['inventory']
    verdicts = applicable_rules(inv, conditions={'MR': 1.0},
                                cation='Na')
    names = {a['rule'] for a in verdicts['applicable']}
    blocked = {b['rule']: b for b in verdicts['blocked']}
    check('depolymerization OPEN at MR=1.0 (gate ideal)',
          'mild-oligo-depolymerization' in names)
    check('ortho-sialate formation open (unfamilied rule)',
          'ortho-sialate-formation' in names)
    check('K kalsilite route blocked on a Na mix',
          'kalsilite-pathway-condensation' in blocked
          and 'Na' in blocked['kalsilite-pathway-condensation']
          ['reason'])
    check('rules missing reactants blocked with the species named',
          'albite-pathway-condensation' in blocked
          and 'ortho-sialate' in
          blocked['albite-pathway-condensation']['reason'])

    closed = applicable_rules(inv, conditions={'MR': 2.0},
                              cation='Na')
    closedBlocked = {b['rule']: b for b in closed['blocked']}
    check('depolymerization CLOSED at MR=2.0 with gate evidence',
          'mild-oligo-depolymerization' in closedBlocked
          and closedBlocked['mild-oligo-depolymerization']
          ['reason'] == 'condition gate closed')

    undetermined = applicable_rules(inv, conditions=None, cation='Na')
    ub = {b['rule']: b for b in undetermined['blocked']}
    check('unprovided gate descriptor BLOCKS (honest absence, '
          'never assumed open)',
          'mild-oligo-depolymerization' in ub
          and any('not provided' in g['reason']
                  for g in ub['mild-oligo-depolymerization']['gates']))

    interior = applicable_rules(
        {'ortho-sialate': None, 'di-siloxonate': None,
         'sodium-ion': None}, site='interior',
        conditions={'MR': 1.0}, cation='Na')
    ib = {b['rule'] for b in interior['blocked']}
    ia = {a['rule'] for a in interior['applicable']}
    check('surface-only albite route blocked at the interior site '
          '(Fig 8.21)', 'albite-pathway-condensation' in ib)
    check('interior-only nepheline route open at the interior site',
          'nepheline-pathway-condensation' in ia)


def test_step_once():
    print('[stoichiometric step_once]')
    inv = solution_inventory('Na', 1.0)['inventory']
    q1, q2 = inv['siloxonate-q1'], inv['siloxonate-q2']
    step = step_once(inv, 'mild-oligo-depolymerization',
                     conditions={'MR': 1.0}, cation='Na', times=5)
    check('step ok', step['ok'])
    check('Q1/Q2 consumed 5 each (dynamic resources)',
          step['inventory']['siloxonate-q1'] == q1 - 5
          and step['inventory']['siloxonate-q2'] == q2 - 5)
    check('Q0 grew by 5', step['inventory']['siloxonate-q0']
          == inv['siloxonate-q0'] + 5)
    check('original inventory untouched (pure step)',
          inv['siloxonate-q1'] == q1)
    check('assumptions declare rule-application units + '
          'kinetics-free', any('kinetics-free' in a
                               for a in step['assumptions']))

    exhausted = step_once(inv, 'mild-oligo-depolymerization',
                          conditions={'MR': 1.0}, cation='Na',
                          times=1000)
    check('over-consumption refused naming the exhausted species',
          exhausted['ok'] is False and 'siloxonate' in
          exhausted['refusal'])
    gated = step_once(inv, 'mild-oligo-depolymerization',
                      conditions={'MR': 2.0}, cation='Na')
    check('closed gate refuses the step with gate verdicts',
          gated['ok'] is False and gated['gates'])
    wrongCation = step_once({'ortho-sialate': None,
                             'siloxonate-q0': None},
                            'leucite-pathway-condensation',
                            conditions={'MR': 1.0}, cation='Na')
    check('K route refused on a Na mix',
          wrongCation['ok'] is False and 'K route' in
          wrongCation['refusal'])
    ghost = step_once(inv, 'unobtainium-fusion')
    check('unknown rule refused', ghost['ok'] is False)


def test_reachability():
    print('[kinetics-free framework reachability]')
    inv = solution_inventory('Na', 1.0)['inventory']
    reach = reachable_frameworks(inv, conditions={'MR': 1.0},
                                 cation='Na')
    frameworks = {f['framework']: f
                  for f in reach['reachableFrameworks']}
    check('Na routes reach albite + nepheline + phillipsite '
          '(competing products COEXIST)',
          {'framework-albite', 'framework-nepheline',
           'framework-phillipsite'} <= set(frameworks))
    check('no K framework reachable from a Na mix',
          not any(f.startswith('framework-leucite')
                  or f.startswith('framework-kalsilite')
                  for f in frameworks))
    albite = frameworks['framework-albite']
    check('albite pathway is a concrete rule chain ending in its '
          'polycondensation',
          albite['pathway'][-1] == 'albite-framework-polycondensation'
          and 'ortho-sialate-formation' in albite['pathway'])
    check('albite pathway records its surface-only site',
          albite['sites'] == ['surface-only'])
    check('phillipsite pathway surfaces its competing branch (6a vs '
          '6b — alternatives, never resolved)',
          frameworks['framework-phillipsite']['competingWith'])
    check('book-supported chains carry a book-supported floor',
          albite['hypothesisFloor'] == 'book-supported')

    high = reachable_frameworks(solution_inventory('Na', 2.0)
                                ['inventory'],
                                conditions={'MR': 2.0}, cation='Na')
    highFw = {f['framework'] for f in high['reachableFrameworks']}
    check('MR=2.0 closes the Q0 gate: phillipsite unreachable',
          'framework-phillipsite' not in highFw)
    check('MR=2.0 still reaches albite + nepheline (ungated routes)',
          {'framework-albite', 'framework-nepheline'} <= highFw)
    check('the closed gate is visible in blockedRules',
          any(b['rule'] == 'mild-oligo-depolymerization'
              for b in high['blockedRules']))
    check('reachability declares presence-only closure (never '
          'which framework wins)',
          any('presence-only' in a for a in high['assumptions']))


def test_rates_still_refuse():
    print('[invariant I5 unchanged by stepping]')
    for rule in SEED_REACTION_RULES[:3]:
        check(f"rate query on {rule['name']!r} still refuses",
              rule_rate(rule)['ok'] is False)


def main():
    test_inventory()
    test_applicability()
    test_step_once()
    test_reachability()
    test_rates_still_refuse()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
