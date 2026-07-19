"""
Self-test for reaction windows — graded verdicts (ideal/acceptable/
marginal/failure) over computed descriptors, honest absence when no
window exists, and NO seeded windows (Ch.8 numbers not yet
photographed — invariant I5).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_reaction_windows
"""

import sys

from pspp.composition_math import ratios_from_moles
from pspp.reaction_windows import (
    SEED_REACTION_WINDOWS, grade_composition, grade_value,
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


def test_patent_windows():
    print('[pp.191-192 patent windows (Tables A + C)]')
    families = {w['material_family'] for w in SEED_REACTION_WINDOWS}
    check('two patent families seeded, never mixed',
          families == {'na-k-pss', 'k-ps-kaliophilite'})
    check('Table A: four (Na,K)-PSS windows',
          len([w for w in SEED_REACTION_WINDOWS
               if w['material_family'] == 'na-k-pss']) == 4)
    check('binary-range semantics documented on every patent window',
          all('binary range' in w['behavior_note']
              for w in SEED_REACTION_WINDOWS))

    sial = next(w for w in SEED_REACTION_WINDOWS
                if w['name'] == 'na-k-pss:SiO2/Al2O3')
    check('SiO2/Al2O3 window [3.5, 4.5] — deliberately above the '
          'stoichiometric 2',
          grade_value(sial, 4.0)['grade'] == 'ideal'
          and grade_value(sial, 2.0)['grade'] == 'failure')

    # p.183 benchmark: the MK-750 MR=1.82 mix must sit INSIDE the
    # Table A windows (formula 1.1Na2O:4SiO2:Al2O3:17H2O).
    bench = ratios_from_moles({'Na2O': 1.1, 'SiO2': 4.0,
                               'Al2O3': 1.0, 'H2O': 17.0})
    graded = grade_composition(SEED_REACTION_WINDOWS,
                               bench['ratios'], 'na-k-pss')
    check('MK-750 benchmark grades inside ALL four Table A windows',
          graded['ok'] and graded['overall'] == 'ideal'
          and len(graded['graded']) == 4)
    check('descriptors without na-k-pss windows stay unjudged '
          '(Si/Al, Na/K, H2O/Al2O3)',
          set(graded['unjudged']) >= {'Si/Al', 'H2O/Al2O3'})

    kps = grade_composition(SEED_REACTION_WINDOWS,
                            {'M2O/SiO2': 0.365, 'SiO2/Al2O3': 3.9,
                             'H2O/Al2O3': 17.5},
                            'k-ps-kaliophilite')
    check('Table C midpoints grade ideal in the K-PS family',
          kps['ok'] and kps['overall'] == 'ideal')


def main():
    test_grading()
    test_composition_grading()
    test_patent_windows()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
