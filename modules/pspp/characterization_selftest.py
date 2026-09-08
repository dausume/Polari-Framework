"""
Self-test for mtt-2 characterization: the XRD + FTIR method catalog
(plain-language what/how + honest safety) and the simulated FTIR band
diagnostics (Si-O-T shift direction, carbonate/water bands, refusals).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.characterization_selftest
"""

import sys

from pspp.characterization_seed import (
    CHARACTERIZATION_METHODS, characterization_methods, simulated_ftir,
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


def test_method_catalog():
    print('[characterization: XRD + FTIR method catalog]')
    cat = characterization_methods()
    names = {m['name'] for m in cat['methods']}
    check('both XRD and FTIR are catalogued', {'xrd', 'ftir'} <= names)
    for m in CHARACTERIZATION_METHODS:
        check(f'{m["name"]} explains what + how in plain language',
              bool(m['measures']) and bool(m['how_plain'])
              and len(m['key_signals']) >= 2)
    xrd = next(m for m in CHARACTERIZATION_METHODS if m['name'] == 'xrd')
    ftir = next(m for m in CHARACTERIZATION_METHODS
                if m['name'] == 'ftir')
    check('XRD is honestly flagged a radiation hazard, not DIY-safe',
          'hazard' in xrd['safety'].lower()
          and xrd['local_buildable'] == 'hard')
    check('FTIR is honestly SAFE (non-ionizing) but ambitious to build',
          'non-ionizing' in ftir['safety'].lower()
          and ftir['local_buildable'] == 'ambitious')
    check('FTIR names the visible-spectrometer cousin as the easier '
          'first build',
          'VISIBLE' in ftir.get('build_note', '')
          or 'visible' in ftir.get('build_note', ''))
    check('FTIR suits amorphous materials where XRD is weak',
          'AMORPHOUS' in ftir['suits'] or 'amorphous' in ftir['suits'])


def test_ftir_band_shift():
    print('[characterization: simulated FTIR main-band shift]')
    low_al = simulated_ftir(si_al_ratio=3.0)   # more Si
    high_al = simulated_ftir(si_al_ratio=1.0)  # more Al
    main_low = low_al['bands'][0]['approxPositionCm']
    main_high = high_al['bands'][0]['approxPositionCm']
    check('main Si-O-T band is LOWER with more Al (Si:Al=1 < Si:Al=3)',
          main_high < main_low)
    check('both give the main band in the 950-1100 region',
          950 <= main_high <= 1100 and 950 <= main_low <= 1100)
    check('position is flagged approximate, direction is the reliable '
          'part',
          any('DIRECTION' in r or 'approximation' in r
              for r in low_al['refusals']))


def test_ftir_diagnostic_bands():
    print('[characterization: carbonate + water diagnostic bands]')
    carb = simulated_ftir(si_al_ratio=2.0, has_carbonate=True)
    assignments = ' '.join(b['assignment'] for b in carb['bands'])
    check('carbonate band appears when carbonation is present',
          'carbonate' in assignments.lower())
    check('the carbonate reading ties to CO2 uptake / carbon-negative '
          'verification',
          any('CO2' in b['reading'] or 'carbon-negative' in b['reading']
              for b in carb['bands']))
    dry = simulated_ftir(si_al_ratio=2.0, has_water=False)
    check('water band drops out when has_water is false',
          'water' not in ' '.join(
              b['assignment'].lower() for b in dry['bands']))


def test_ftir_refusals():
    print('[characterization: honest FTIR refusals]')
    r = simulated_ftir(si_al_ratio=2.0)
    check('intensities are explicitly NOT predicted',
          any('INTENSIT' in x.upper() for x in r['refusals']))
    no_comp = simulated_ftir()
    check('no composition -> main-band assignment still holds, '
          'position honestly absent',
          no_comp['bands'][0]['approxPositionCm'] is None
          and no_comp['bands'][0]['confidence'] == 'assignment-only')
    check('bad Si:Al refuses the position gracefully',
          simulated_ftir(si_al_ratio=-1)['bands'][0]['approxPositionCm']
          is None)


def main():
    test_method_catalog()
    test_ftir_band_shift()
    test_ftir_diagnostic_bands()
    test_ftir_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
