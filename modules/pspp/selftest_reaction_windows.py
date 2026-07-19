"""
Self-test for reaction windows — graded verdicts (ideal/acceptable/
marginal/failure) over computed descriptors, honest absence when no
window exists, and NO seeded windows (Ch.8 numbers not yet
photographed — invariant I5).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_reaction_windows
"""

import sys

from pspp.reaction_windows import grade_composition, grade_value

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


# Synthetic window — NOT book data (Ch.8 ranges arrive as rows later).
WINDOW = {
    'name': 'test-family:SiO2/Al2O3',
    'material_family': 'test-family',
    'descriptor': 'SiO2/Al2O3',
    'center': 3.8, 'ideal_tolerance': 0.3,
    'acceptable_tolerance': 0.7, 'marginal_tolerance': 1.2,
    'behavior_note': 'low: excess reactive Al; high: unreacted silica',
    'source_reference': 'synthetic selftest window',
}


def test_grading():
    print('[graded verdicts]')
    check('center grades ideal',
          grade_value(WINDOW, 3.8)['grade'] == 'ideal')
    check('edge of ideal band inclusive',
          grade_value(WINDOW, 4.1)['grade'] == 'ideal')
    check('acceptable band', grade_value(WINDOW, 4.4)['grade']
          == 'acceptable')
    check('marginal band', grade_value(WINDOW, 2.7)['grade']
          == 'marginal')
    check('failure beyond marginal', grade_value(WINDOW, 5.5)['grade']
          == 'failure')
    check('verdict carries the physical behavior note',
          'unreacted silica' in grade_value(WINDOW, 5.5)['behaviorNote'])
    bad = grade_value(dict(WINDOW, ideal_tolerance=0.9,
                           acceptable_tolerance=0.5), 3.8)
    check('non-widening tolerances refused',
          bad['ok'] is False and 'non-widening' in bad['refusal'])


def test_composition_grading():
    print('[whole-composition grading]')
    ratios = {'SiO2/Al2O3': 4.4, 'H2O/M2O': 12.0, 'Na/K': None}
    graded = grade_composition([WINDOW], ratios, 'test-family')
    check('overall = worst graded descriptor (acceptable)',
          graded['ok'] and graded['overall'] == 'acceptable')
    check('descriptors without windows are unjudged, not judged',
          sorted(graded['unjudged']) == ['H2O/M2O', 'Na/K'])

    none = grade_composition([WINDOW], ratios, 'metakaolin-geopolymer')
    check('family with no windows refused — windows never transfer '
          'between families',
          none['ok'] is False and 'do NOT transfer' in none['suggestion'])


def main():
    test_grading()
    test_composition_grading()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
