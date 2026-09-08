"""
Self-test for the experiment-guidance synthesis: independent
sections, merged-window grading inside guidance, pathway + cure
composition, and the gap list as the experiment plan.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.experiment_guidance_selftest
"""

import sys

from pspp.custom.experiment_guidance import experiment_guide

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


def test_full_guide():
    print('[full guidance: composition + pathways + cure]')
    # Mass mix whose MOLAR ratios land the p.193 preferred bands
    # (SiO2/Al2O3 ≈ 4.10, M2O/Al2O3 ≈ 1.40).
    guide = experiment_guide(
        None,
        composition={'SiO2': 31.4, 'Al2O3': 13.0, 'K2O': 16.8,
                     'H2O': 40.2},
        family='k-ps-kaliophilite', cation='Na', mr=1.0,
        cure_temperature_c=80.0)
    check('guide ok', guide['ok'])
    grading = guide['sections']['composition']['grading']
    check('composition graded through the MERGED windows (banded '
          'supersedes symmetric)', grading['ok']
          and grading['supersededWindows'])
    byKey = {g['descriptor']: g for g in grading['graded']
             if g.get('ok')}
    check('SiO2/Al2O3~4.1 lands the p.193 preferred band (ideal)',
          byKey['SiO2/Al2O3']['grade'] == 'ideal'
          and byKey['SiO2/Al2O3']['windowKind'] == 'banded')
    pathways = guide['sections']['pathways']
    check('pathways section carries reachable frameworks with rule '
          'chains', any(f['pathway']
                        for f in pathways['reachableFrameworks']))
    check('blocked rules ride along with reasons',
          all('reason' in b for b in pathways['blockedRules']))
    cure = guide['sections']['cure']
    check('cure section refuses honestly for MR=1.0 (off the '
          'measured §8.2.8 table) and lands in gaps',
          cure['ok'] is False
          and any(g['section'] == 'cure' for g in guide['gaps']))


def test_partial_inputs():
    print('[independent sections + gap list]')
    onlyMix = experiment_guide(
        None, composition={'SiO2': 52.0, 'Al2O3': 13.0, 'K2O': 18.0,
                           'H2O': 17.0},
        family='k-ps-kaliophilite')
    check('composition-only guide still grades',
          onlyMix['sections']['composition']['grading']['ok'])
    gapSections = {g['section'] for g in onlyMix['gaps']}
    check('missing cation/MR produce pathway + cure gaps with '
          'next-data asks', {'pathways', 'cure'} <= gapSections
          and all(g['nextData'] for g in onlyMix['gaps']))

    onlyMr = experiment_guide(None, cation='Na', mr=1.83,
                              cure_temperature_c=80.0)
    check('MR-only guide gives a cure schedule',
          onlyMr['sections']['cure']['ok']
          and onlyMr['sections']['cure']['completionHours'] > 0)
    check('MR=1.83 pathway inventory refuses (between Table 5.6 '
          'MRs) and the gap names the constraint',
          any(g['section'] == 'pathways' for g in onlyMr['gaps']))

    noFamily = experiment_guide(
        None, composition={'SiO2': 52.0, 'Al2O3': 13.0})
    check('family-less composition refuses with the no-transfer '
          'evidence', not
          noFamily['sections']['composition']['grading']['ok'])

    empty = experiment_guide(None)
    check('empty guide is ALL gaps, each with a suggestion',
          empty['ok'] and len(empty['gaps']) == 3
          and all(g['nextData'] for g in empty['gaps']))


def test_k_asymmetry():
    print('[K mix: honest dataset asymmetry]')
    k = experiment_guide(None, cation='K', mr=1.83)
    check('K pathways refuse (Table 5.6 is Na-only) with the '
          'dataset ask',
          any(g['section'] == 'pathways'
              and 'DigitizedDataset' in g['nextData']
              for g in k['gaps']))
    check('K cure still answers (§8.2.8 IS the K-silicate table)',
          k['sections']['cure']['ok'])


def main():
    test_full_guide()
    test_partial_inputs()
    test_k_asymmetry()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
