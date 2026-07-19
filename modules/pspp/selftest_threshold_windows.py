"""
Self-test for the threshold-shaped (banded/asymmetric) ReactionWindow
variant: p.193 preferred bands + crack thresholds, band validation,
merged grading (banded beats symmetric), and the MR<1.20 Q0 gate.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_threshold_windows
"""

import json
import sys

from pspp.reaction_windows import SEED_REACTION_WINDOWS
from pspp.threshold_windows import (
    SEED_THRESHOLD_WINDOWS, banded_window_dict, grade_composition_merged,
    grade_value_banded, merged_family_windows, validate_banded_window,
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


def _window(name):
    return next(w for w in SEED_THRESHOLD_WINDOWS if w['name'] == name)


def test_seed_validation():
    print('[seed validation]')
    for seed in SEED_THRESHOLD_WINDOWS:
        check(f"seed window {seed['name']!r} validates",
              validate_banded_window(seed)['ok'])
    check('seeds carry citations',
          all(seed['source_reference']
              for seed in SEED_THRESHOLD_WINDOWS))


def test_band_validation_refusals():
    print('[band validation refusals]')
    good = banded_window_dict(_window('k-ps:M2O/Al2O3:banded'))
    noCover = dict(good, bands=good['bands'][1:])
    check('bands not covering the line refused',
          validate_banded_window(noCover)['ok'] is False)
    gapped = dict(good, bands=[
        dict(good['bands'][0]),
        dict(good['bands'][1], lo=1.0),
    ])
    check('non-contiguous bands refused',
          validate_banded_window(gapped)['ok'] is False)
    badGrade = dict(good, bands=[dict(b, grade='amazing')
                                 for b in good['bands']])
    check('undeclared grade refused',
          validate_banded_window(badGrade)['ok'] is False)
    badRole = dict(good, windowRole='vibes')
    check('unknown window role refused',
          validate_banded_window(badRole)['ok'] is False)


def test_p193_asymmetry():
    print('[p.193 asymmetric bands: SiO2/Al2O3]')
    w = _window('k-ps:SiO2/Al2O3:banded')
    cases = [
        (3.0, 'failure'),   # outside claim
        (3.5, 'failure'),   # inside claim, below crack threshold
        (3.8, 'acceptable'),
        (4.1, 'ideal'),     # preferred
        (4.3, 'acceptable'),
        (5.0, 'failure'),   # free K-silicate phase
    ]
    for value, expected in cases:
        verdict = grade_value_banded(w, value)
        check(f'{value} grades {expected}',
              verdict['ok'] and verdict['grade'] == expected)
    below = grade_value_banded(w, 3.5)
    check('crack band carries the crack note (its OWN evidence)',
          'cracks' in below['behaviorNote'])
    above = grade_value_banded(w, 5.0)
    check('high band carries the free-silicate note (asymmetric '
          'failure modes)', 'potassium-silicate' in above['behaviorNote'])


def test_p193_m2o_al2o3():
    print('[p.193 asymmetric bands: M2O/Al2O3]')
    w = _window('k-ps:M2O/Al2O3:banded')
    for value, expected in [(1.0, 'failure'), (1.2, 'acceptable'),
                            (1.4, 'ideal'), (1.55, 'acceptable'),
                            (1.7, 'failure')]:
        verdict = grade_value_banded(w, value)
        check(f'{value} grades {expected}',
              verdict['ok'] and verdict['grade'] == expected)


def test_q0_gate():
    print('[MR<1.20 Q0-depolymerization condition gate]')
    gate = _window('na-silicate:mr-q0-depolymerization')
    check('gate declares the condition-gate role',
          gate['window_role'] == 'condition-gate')
    open_ = grade_value_banded(gate, 1.0)
    closed = grade_value_banded(gate, 1.5)
    check('MR=1.0 opens the gate (not failure)',
          open_['ok'] and open_['grade'] != 'failure')
    check('MR=1.5 closes the gate (failure)',
          closed['ok'] and closed['grade'] == 'failure')
    check('closed verdict names the closed routes',
          'CLOSED' in closed['behaviorNote'])
    boundary = grade_value_banded(gate, 1.20)
    check('half-open boundary: MR=1.20 exactly is closed',
          boundary['grade'] == 'failure')


def test_merged_grading():
    print('[merged grading: banded beats symmetric]')
    winners, superseded = merged_family_windows(
        SEED_REACTION_WINDOWS, SEED_THRESHOLD_WINDOWS,
        'k-ps-kaliophilite')
    check('both symmetric k-ps rows superseded by their banded '
          'variants', sorted(superseded)
          == ['k-ps:M2O/Al2O3', 'k-ps:SiO2/Al2O3'])
    check('non-collided symmetric windows survive the merge',
          any('bands' not in w and w['descriptor'] == 'H2O/Al2O3'
              for w in winners))
    check('the condition-gate window never enters quality grading',
          not any(w.get('windowRole') == 'condition-gate'
                  for w in winners))

    # 3.5 was 'ideal' under the binary symmetric claim [3.3, 4.5];
    # the banded row knows it CRACKS — the merge must surface that.
    ratios = {'SiO2/Al2O3': 3.5, 'M2O/Al2O3': 1.4,
              'H2O/Al2O3': 15.0, 'M2O/SiO2': 0.35}
    merged = grade_composition_merged(
        SEED_REACTION_WINDOWS, SEED_THRESHOLD_WINDOWS, ratios,
        'k-ps-kaliophilite')
    check('merged grading ok', merged['ok'])
    byKey = {g['descriptor']: g for g in merged['graded'] if g.get('ok')}
    check('SiO2/Al2O3=3.5 fails via the banded crack band (binary '
          'claim would have said ideal)',
          byKey['SiO2/Al2O3']['grade'] == 'failure'
          and byKey['SiO2/Al2O3']['windowKind'] == 'banded')
    check('M2O/Al2O3=1.4 is ideal via the banded preferred band',
          byKey['M2O/Al2O3']['grade'] == 'ideal')
    check('H2O/Al2O3 still graded by the surviving symmetric row',
          byKey['H2O/Al2O3']['windowKind'] == 'symmetric')
    check('overall = worst graded (failure)',
          merged['overall'] == 'failure')
    check('unknown family still refuses with the no-transfer '
          'suggestion',
          grade_composition_merged(SEED_REACTION_WINDOWS,
                                   SEED_THRESHOLD_WINDOWS, ratios,
                                   'martian-regolith')['ok'] is False)


def test_bands_round_trip():
    print('[row shape]')
    w = banded_window_dict(_window('k-ps:SiO2/Al2O3:banded'))
    check('bands_json round-trips through the dict view',
          len(w['bands']) == 6
          and json.dumps(w['bands']))


def main():
    test_seed_validation()
    test_band_validation_refusals()
    test_p193_asymmetry()
    test_p193_m2o_al2o3()
    test_q0_gate()
    test_merged_grading()
    test_bands_round_trip()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
