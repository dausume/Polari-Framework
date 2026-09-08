"""
Self-test for mtt-2 geopolymer -> ceramic/glass transition: the
DATA-BACKED thermal-conversion stages (Table 8.8), the crystallization
rules per band, and the honest glass-branch refusal.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.geopolymer_ceramic_transition_selftest
"""

import sys

from pspp.custom.geopolymer_ceramic_transition import (
    porosity_at, transition_stages,
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


def test_stages():
    print('[geopolymer->ceramic: measured thermal-conversion stages]')
    t = transition_stages()
    check('transition reads ok (data-backed)', t['ok'])
    by_temp = {s['temperatureC']: s for s in t['stages']}
    check('amorphous geopolymer at low temperature (<=800 C)',
          by_temp[20]['stage'] == 'amorphous-geopolymer'
          and by_temp[800]['stage'] == 'amorphous-geopolymer')
    check('kalsilite crystallization band at 1000 C',
          by_temp[1000]['stage'] == 'crystallizing-kalsilite'
          and 'K' in (by_temp[1000]['xrdPhases'] or ''))
    check('leucite ceramic band at 1200 C',
          by_temp[1200]['stage'] == 'ceramic-leucite'
          and 'L' in (by_temp[1200]['xrdPhases'] or ''))
    check('the 1000 C stage cites the kalsilite crystallization rule',
          by_temp[1000]['crystallizationRule']
          == 'kalsilite-framework-polycondensation')
    check('the 1200 C stage cites the leucite rule',
          by_temp[1200]['crystallizationRule']
          == 'leucite-framework-polycondensation')
    check('porosity numbers are the MEASURED values (not modeled)',
          by_temp[20]['openPorosityPct'] == 29.5
          and by_temp[1400]['openPorosityPct'] == 27.6)
    check('stages ascend in temperature',
          [s['temperatureC'] for s in t['stages']]
          == sorted(s['temperatureC'] for s in t['stages']))


def test_glass_branch_refuses():
    print('[geopolymer->ceramic: glass branch is honest above-range]')
    t = transition_stages()
    glass = t['glassBranch']
    check('glass branch onsets above the measured range (>1400 C)',
          glass['onsetC'] >= 1400 and glass['refuses'] is True)
    check('glass branch explains the fusing-phase mechanism',
          'Ca-pentamer' in glass['what']
          or 'fusing' in glass['what'])
    check('assumptions state the stages are MEASURED, not modeled',
          any('MEASURED' in a for a in t['assumptions']))


def test_porosity_at():
    print('[geopolymer->ceramic: porosity at a temperature]')
    p = porosity_at(1000)
    check('reads porosity + stage at 1000 C',
          p['ok'] and p['stage'] == 'crystallizing-kalsilite')
    # XRD phases are categorical -> between-point exact only; porosity
    # interpolates within the domain.
    mid = porosity_at(900)
    check('porosity interpolates between measured points',
          mid['ok'])
    off = porosity_at(2000)
    check('above the domain refuses (no extrapolation)',
          off['ok'] is False)


def main():
    test_stages()
    test_glass_branch_refuses()
    test_porosity_at()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
