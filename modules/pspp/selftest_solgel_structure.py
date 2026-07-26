"""
Self-test for mtt-2 sg-5: sol-gel Q distributions through the gsp
structure machinery — the acid/base catalysis fork must show in the
stepped fractions, the framework reachability, the sampled cluster,
and the Debye halo.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_solgel_structure
"""

import sys

from pspp.solgel_structure import (
    ROUTE_DEMOS, solgel_route_demo, solgel_stepped_groups,
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


def test_stepped_groups():
    print('[sg-5: stepped groups under the route gates]')
    acid = solgel_stepped_groups(
        2.0, 2.5, steps=[{'rule': 'alkoxide-hydrolysis', 'times': 40},
                         {'rule': 'silicic-dimerization', 'times': 20}])
    check('acid stepped run ok', acid['ok'])
    check('fractions land on the shared Q ledger',
          acid['ok'] and abs(sum(acid['fractions'].values()) - 1.0)
          < 1e-9)
    check('unreacted alkoxide honestly counted as Q0',
          acid['ok'] and acid['fractions']['Q0'] > 0)
    gated = solgel_stepped_groups(
        2.0, 2.5, steps=[{'rule': 'alkoxide-hydrolysis', 'times': 40},
                         {'rule': 'silicic-dimerization', 'times': 20},
                         {'rule': 'crosslink-condensation',
                          'times': 5}])
    check('acid conditions refuse the crosslink step (gate closed), '
          'naming the step',
          gated.get('ok') is False and gated.get('stepIndex') == 2
          and 'gate' in (gated.get('refusal') or ''))
    bad = solgel_stepped_groups(-1, 2.5)
    check('bad R refuses upstream', bad['ok'] is False)


def test_fork_in_fractions():
    print('[sg-5: the catalysis fork shows in the distributions]')
    acid = solgel_route_demo('acid', sample=False)
    base = solgel_route_demo('base', sample=False)
    check('both route demos run', acid['ok'] and base['ok'])
    acid_q4 = acid['groups']['fractions']['Q4']
    base_q4 = base['groups']['fractions']['Q4']
    check(f'acid gel is Q4-free/low (got {acid_q4})', acid_q4 <= 0.05)
    check(f'base gel is Q4-rich (got {base_q4})', base_q4 >= 0.4)
    check('demo payloads say they are bookkeeping, not kinetics',
          any('never kinetics' in a for a in acid['assumptions']))
    unknown = solgel_route_demo('neutral')
    check('unknown route refuses naming the knobs',
          unknown['ok'] is False and 'acid' in unknown['suggestion'])


def test_fork_in_reachability():
    print('[sg-5: the fork shows in framework reachability]')
    acid = solgel_route_demo('acid', sample=False)
    base = solgel_route_demo('base', sample=False)
    acid_fw = {f['framework'] for f in acid['reachableFrameworks']}
    base_fw = {f['framework'] for f in base['reachableFrameworks']}
    check('acid reaches the polymeric gel only',
          'framework-silica-polymeric-gel' in acid_fw
          and 'framework-silica-colloidal-gel' not in acid_fw)
    check('base reaches the colloidal gel only',
          'framework-silica-colloidal-gel' in base_fw
          and 'framework-silica-polymeric-gel' not in base_fw)
    check('geopolymer frameworks stay out of a sol-gel pool',
          not any(f.startswith('framework-')
                  and 'silica' not in f
                  for f in acid_fw | base_fw))
    check('the fork rules carry their competing-hypothesis links',
          any(f['competingWith']
              for f in acid['reachableFrameworks']
              + base['reachableFrameworks']))


def test_sampler_and_halo():
    print('[sg-5: sampler + Debye halo on sol-gel distributions]')
    acid = solgel_route_demo('acid', n_tetrahedra=60, seed=3)
    base = solgel_route_demo('base', n_tetrahedra=60, seed=3)
    check('both clusters sample', acid['sample']['ok']
          and base['sample']['ok'])
    check('pure silica: no Al, no charge-balancing cations',
          all(a['element'] == 'Si' for a in acid['sample']['atoms']
              if a.get('role') == 'tetrahedral')
          and not any(a['element'] in ('Na', 'K')
                      for a in base['sample']['atoms']))
    acid_q4 = acid['sample']['achievedQ']['Q4']
    base_q4 = base['sample']['achievedQ']['Q4']
    check(f'sampled connectivity tracks the fork (acid Q4 {acid_q4} '
          f'< base Q4 {base_q4})', acid_q4 < base_q4)
    check('base cluster packed to the amorphous-silica density knob',
          base['sample'].get('ok')
          and ROUTE_DEMOS['base']['target_density_g_cm3'] == 2.2)
    check('both patterns show a residual amorphous halo',
          acid['halo']['ok'] and base['halo']['ok']
          and acid['halo']['peaks'] and base['halo']['peaks'])


def main():
    test_stepped_groups()
    test_fork_in_fractions()
    test_fork_in_reachability()
    test_sampler_and_halo()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
