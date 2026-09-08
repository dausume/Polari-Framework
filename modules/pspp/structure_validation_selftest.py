"""
Self-test for gsp-4b (stepped-population -> Q distribution) and
gsp-5 (Debye amorphous-halo validation).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.structure_validation_selftest
"""

import sys

from pspp.custom.structure_groups import stepped_groups
from pspp.custom.structure_sampling import build_geopolymer_sample
from pspp.custom.structure_validation import simulated_halo

PASS = 0
FAIL = 0

TARGET = {'Q0': 0.05, 'Q1': 0.15, 'Q2': 0.40, 'Q3': 0.25, 'Q4': 0.15}


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_stepped_no_steps():
    print('[gsp-4b — zero steps = the solution distribution]')
    verdict = stepped_groups('Na', 2.0)
    check('ok with no steps', verdict.get('ok') is True)
    if not verdict.get('ok'):
        return
    check('mode is stepped', verdict['mode'] == 'stepped')
    total = sum(g['fraction'] for g in verdict['groups'])
    check('fractions sum ~1', abs(total - 1.0) < 5e-4)
    check('Q4 artifact caveat rides along',
          any('artifact' in c for c in verdict['caveats']))
    check('di-siloxonate not double-counted (alias skipped)',
          'di-siloxonate' not in verdict['unmappedQuantified'])
    check('metakaolin present-unquantified',
          'metakaolin-layer' in verdict['presentUnquantified'])


def test_stepped_with_rule():
    print('[gsp-4b — one real step]')
    verdict = stepped_groups(
        'Na', 2.0, steps=[{'rule': 'ortho-sialate-formation'}])
    check('step applied ok', verdict.get('ok') is True)
    if verdict.get('ok'):
        check('stepsApplied records the rule',
              verdict['stepsApplied']
              == [{'rule': 'ortho-sialate-formation', 'times': 1}])
        check('product outside the Q ledger reported',
              'ortho-sialate' in verdict['unmappedQuantified'])
        check('unmapped honesty in assumptions',
              any('unmapped' in a for a in verdict['assumptions']))


def test_stepped_refusals():
    print('[gsp-4b — refusals]')
    unknown = stepped_groups('Na', 2.0,
                             steps=[{'rule': 'no-such-rule'}])
    check('unknown rule refuses with stepIndex',
          unknown.get('ok') is False
          and unknown.get('stepIndex') == 0)
    k = stepped_groups('K', 2.0)
    check('K refuses (Na-only solution table)',
          k.get('ok') is False)


def test_halo():
    print('[gsp-5 — Debye halo]')
    sample = build_geopolymer_sample(TARGET, n_tetrahedra=80, seed=4,
                                     si_al_ratio=2.0)
    verdict = simulated_halo(sample)
    check('halo computation ok', verdict.get('ok') is True)
    if not verdict.get('ok'):
        return
    curve = verdict['curve']
    check('curve lengths match points',
          len(curve['twoTheta']) == len(curve['intensity'])
          == verdict['counts']['points'])
    check('intensity normalized to 1',
          abs(max(curve['intensity']) - 1.0) < 1e-6)
    halo, peaks = verdict['halo'], verdict['peaks']
    print(f"    strongest {halo['position2Theta']} deg "
          f"(d={halo['dSpacingA']} A); peaks: "
          f"{[(p['position2Theta'], p['dSpacingA']) for p in peaks]}")
    check('at least two residual peaks', len(peaks) >= 2)
    check('first-shell T-T peak present (d 2.5-3.5 A)',
          any(2.5 <= p['dSpacingA'] <= 3.5 for p in peaks))
    check('short-range (bond/O-O scale) peak present (d 1.4-2.0 A)',
          any(1.4 <= p['dSpacingA'] <= 2.0 for p in peaks))
    check('gel-band verdict computed',
          halo['anyPeakInBand'] is not None)
    check('f=Z approximation recorded',
          any('f=Z' in a for a in verdict['assumptions']))
    again = simulated_halo(build_geopolymer_sample(
        TARGET, n_tetrahedra=80, seed=4, si_al_ratio=2.0))
    check('deterministic for the same sampling params',
          again == verdict)


def test_halo_refusals():
    print('[gsp-5 — refusals + variants]')
    sample = build_geopolymer_sample(TARGET, n_tetrahedra=20, seed=1)
    mo = simulated_halo(sample, wavelength='MoKa')
    check('MoKa works with band=None',
          mo.get('ok') is True and mo['halo']['band'] is None
          and mo['halo']['anyPeakInBand'] is None)
    check('unknown wavelength refuses',
          simulated_halo(sample, wavelength='FeKa').get('ok')
          is False)
    check('too-few-atoms refuses',
          simulated_halo({'atoms': []}).get('ok') is False)


def main():
    test_stepped_no_steps()
    test_stepped_with_rule()
    test_stepped_refusals()
    test_halo()
    test_halo_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
