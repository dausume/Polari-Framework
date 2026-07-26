"""
Self-test for mtt-2 sg-1/sg-2: the sol-gel species/rule library, the
pH catalysis-fork gates + R gate as data, and the stoichiometric
inventory builder.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_solgel_network
"""

import sys

from pspp.network_stepping import applicable_rules, step_once
from pspp.reaction_network import (
    SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES, rule_rate,
    validate_rule,
)
from pspp.solgel_network import (
    SOLGEL_CHEMICAL_SPECIES, SOLGEL_REACTION_RULES,
    SOLGEL_THRESHOLD_WINDOWS, solgel_inventory,
)
from pspp.threshold_windows import (
    SEED_THRESHOLD_WINDOWS, validate_banded_window,
)

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


ALL_SPECIES = SEED_CHEMICAL_SPECIES + SOLGEL_CHEMICAL_SPECIES
ALL_RULES = SEED_REACTION_RULES + SOLGEL_REACTION_RULES
ALL_WINDOWS = SEED_THRESHOLD_WINDOWS + SOLGEL_THRESHOLD_WINDOWS


def test_library_shape():
    print('[sg-1: species + rule library]')
    check('all sol-gel rules validate against the combined inventory',
          all(validate_rule(r, species_rows=ALL_SPECIES)['ok']
              for r in SOLGEL_REACTION_RULES))
    check('every sol-gel rule is family sol-gel, no alkali scoping',
          all(r['material_family'] == 'sol-gel'
              and r['cation_family'] == ''
              for r in SOLGEL_REACTION_RULES))
    check('rules are kinetics-free and rate queries refuse (I5)',
          all(rule_rate(r)['ok'] is False
              for r in SOLGEL_REACTION_RULES))
    check('unreacted precursors carry qn=0 (Q0 in 29Si NMR)',
          all(s.get('qn') == 0 for s in SOLGEL_CHEMICAL_SPECIES
              if s['name'] in ('silicon-alkoxide', 'teos', 'tmos',
                               'silicic-acid')))
    check('Al/Ti/Zr alkoxides are honest species-only rows',
          all('RULES PENDING' in s['notes']
              for s in SOLGEL_CHEMICAL_SPECIES
              if s['name'].endswith('-alkoxide')
              and s['name'] != 'silicon-alkoxide'))
    check('both product framework families are declared',
          {'framework-silica-polymeric-gel',
           'framework-silica-colloidal-gel'}
          <= {s['name'] for s in SOLGEL_CHEMICAL_SPECIES})


def test_windows():
    print('[sg-2: pH/R gates as ThresholdReactionWindow data]')
    check('all sol-gel windows validate (ordered/contiguous/total)',
          all(validate_banded_window(w)['ok']
              for w in SOLGEL_THRESHOLD_WINDOWS))
    roles = {w['name']: w['window_role']
             for w in SOLGEL_THRESHOLD_WINDOWS}
    check('pH fork + R gate are condition-gates, spinnability is '
          'quality',
          roles['sol-gel:ph-polymeric-route'] == 'condition-gate'
          and roles['sol-gel:ph-particulate-route'] == 'condition-gate'
          and roles['sol-gel:r-alcohol-condensation'] == 'condition-gate'
          and roles['sol-gel-spinnable:R:banded'] == 'quality')
    check('window names collide with no existing seed window',
          not ({w['name'] for w in SOLGEL_THRESHOLD_WINDOWS}
               & {w['name'] for w in SEED_THRESHOLD_WINDOWS}))


def test_catalysis_fork():
    print('[sg-2: the catalysis fork opens/closes routes]')
    inv = {'siloxonate-q2': 10.0, 'siloxonate-q3': 10.0,
           'silicic-acid': 10.0}
    acid = applicable_rules(inv, rules=ALL_RULES, windows=ALL_WINDOWS,
                            conditions={'pH': 2.5, 'R': 2.0},
                            cation=None)
    acid_blocked = {b['rule'] for b in acid['blocked']}
    acid_open = {a['rule'] for a in acid['applicable']}
    check('acid: crosslink + completion + site-addition CLOSED',
          {'crosslink-condensation', 'network-completion-condensation',
           'site-addition-condensation'} <= acid_blocked)
    check('acid: polymeric percolation OPEN',
          'polymeric-gel-percolation' in acid_open)
    base = applicable_rules(inv, rules=ALL_RULES, windows=ALL_WINDOWS,
                            conditions={'pH': 9.0, 'R': 2.0},
                            cation=None)
    base_open = {a['rule'] for a in base['applicable']}
    base_blocked = {b['rule'] for b in base['blocked']}
    check('base: crosslinking route OPEN',
          {'crosslink-condensation',
           'network-completion-condensation'} <= base_open)
    check('base: polymeric percolation CLOSED',
          'polymeric-gel-percolation' in base_blocked)
    undetermined = applicable_rules(
        inv, rules=ALL_RULES, windows=ALL_WINDOWS,
        conditions={'R': 2.0}, cation=None)
    blocked = {b['rule']: b for b in undetermined['blocked']}
    entry = blocked.get('crosslink-condensation', {})
    check('missing pH blocks gated rules honestly (never assumes)',
          any('not provided' in (g.get('reason') or '')
              for g in entry.get('gates', [])))


def test_r_gate():
    print('[sg-2: R-ratio gate on alcohol condensation]')
    inv = {'silicic-acid': 10.0, 'silicon-alkoxide': 10.0}
    low = applicable_rules(inv, rules=ALL_RULES, windows=ALL_WINDOWS,
                           conditions={'pH': 2.5, 'R': 2.0},
                           cation=None)
    check('R=2: alcohol condensation open (unhydrolyzed OR persists)',
          'alcohol-condensation'
          in {a['rule'] for a in low['applicable']})
    high = applicable_rules(inv, rules=ALL_RULES, windows=ALL_WINDOWS,
                            conditions={'pH': 2.5, 'R': 6.0},
                            cation=None)
    check('R=6: alcohol condensation closed (full-hydrolysis '
          'stoichiometry)',
          'alcohol-condensation'
          in {b['rule'] for b in high['blocked']})


def test_inventory():
    print('[sg-1: stoichiometric inventory builder]')
    mix = solgel_inventory(2.0, alkoxide='teos', amount=100.0)
    check('teos mix ok', mix['ok'])
    check('water pool = R x alkoxide',
          mix['inventory']['water'] == 200.0
          and mix['inventory']['silicon-alkoxide'] == 100.0)
    check('cosolvent present but unquantified (None)',
          mix['inventory']['alkanol'] is None)
    check('catalyst-as-condition recorded in assumptions',
          any('pH condition' in a for a in mix['assumptions']))
    check('unknown precursor refuses naming the pending Al/Ti/Zr gap',
          solgel_inventory(2.0, alkoxide='aluminum-alkoxide')['ok']
          is False)
    check('non-positive R refuses',
          solgel_inventory(0)['ok'] is False
          and solgel_inventory('x')['ok'] is False)
    stepped = step_once(dict(mix['inventory']), 'alkoxide-hydrolysis',
                        rules=ALL_RULES, windows=ALL_WINDOWS,
                        conditions={'pH': 2.5, 'R': 2.0},
                        cation=None, times=10)
    check('hydrolysis steps stoichiometrically',
          stepped['ok']
          and stepped['inventory']['silicic-acid'] == 10
          and stepped['inventory']['water'] == 190.0
          and stepped['inventory']['silicon-alkoxide'] == 90.0)
    check('geopolymer rules stay inert in a sol-gel pool (reactants '
          'absent)',
          step_once(dict(mix['inventory']), 'ortho-sialate-formation',
                    rules=ALL_RULES, windows=ALL_WINDOWS,
                    conditions={'pH': 2.5}, cation=None)['ok'] is False)


def main():
    test_library_shape()
    test_windows()
    test_catalysis_fork()
    test_r_gate()
    test_inventory()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
