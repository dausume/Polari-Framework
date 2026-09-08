"""
Self-test for mtt-2 ceramics samples: the temperature ladder, the
local vs olivine tracks, the steelmaking-temperature filter, and the
accessibility/consistency honesty.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.ceramics_samples_selftest
"""

import sys

from pspp.ceramics_samples_basis import (
    SEED_CERAMIC_SAMPLES, SEED_CERAMICS_DATASETS, sample_dict,
    samples_meeting_temp, temperature_ladder, validate_samples,
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


def test_ladder_ordering():
    print('[ceramics: the gradual escalating temperature ladder]')
    ladder = temperature_ladder()
    temps = [s['maxServiceTempC'] for s in ladder]
    check('ladder is sorted ascending by service temperature',
          temps == sorted(temps))
    check('earthenware sits at the bottom, a refractory at the top',
          ladder[0]['family'] == 'earthenware'
          and ladder[-1]['maxServiceTempC'] >= 1700)
    cordierite = next(s for s in ladder if s['family'] == 'cordierite')
    check('cordierite is the thermal-shock (gradual-escalation) champ',
          cordierite['thermalShock'] == 'excellent')


def test_local_and_olivine_tracks():
    print('[ceramics: local vs non-local olivine tracks]')
    by_name = {sample_dict(r)['name']: sample_dict(r)
               for r in SEED_CERAMIC_SAMPLES}
    forsterite = by_name['forsterite-olivine']
    check('forsterite is non-local, mined, carbon-negative-capable',
          forsterite['track'] == 'non-local'
          and forsterite['accessibilityTier'] == 'mined-nonlocal'
          and forsterite['carbonProfile'] == 'carbon-negative-capable')
    check('forsterite is a BASIC refractory (steel-slag resistant)',
          forsterite['refractoryClass'] == 'basic')
    dol = by_name['dolomitic-basic-refractory']
    check('the LOCAL basic steel refractory (dolomitic) exists + is '
          'carbon-positive (calcining releases CO2)',
          dol['track'] == 'local' and dol['refractoryClass'] == 'basic'
          and dol['carbonProfile'] == 'carbon-positive')


def test_steelmaking_filter():
    print('[ceramics: what can line a steelmaking furnace (~1600 C)]')
    all_hot = samples_meeting_temp(1600)
    names = {s['name'] for s in all_hot['samples']}
    check('mullite/alumina/dolomitic/forsterite all clear 1600 C',
          {'mullite', 'alumina', 'dolomitic-basic-refractory',
           'forsterite-olivine'} <= names)
    check('earthenware does NOT clear 1600 C',
          'earthenware-terracotta' not in names)
    local = samples_meeting_temp(1600, local_only=True)
    lnames = {s['name'] for s in local['samples']}
    check('local-only filter drops the mined olivine track',
          'forsterite-olivine' not in lnames
          and 'dolomitic-basic-refractory' in lnames)
    cneg = samples_meeting_temp(1600, carbon_negative_only=True)
    check('carbon-negative-only leaves the olivine forsterite',
          {s['name'] for s in cneg['samples']} == {'forsterite-olivine'})
    check('every result carries the approximate-temp caveat',
          'approximate' in all_hot['note'])


def test_carbonation_dataset_refuses():
    print('[ceramics: olivine carbon-negative NUMBERS refuse]')
    from pspp.custom.dataset_interpolation import read_dataset
    from pspp.digitized_datasets_basis import dataset_dict
    ds = dataset_dict(SEED_CERAMICS_DATASETS[0])
    verdict = read_dataset(ds, {'temperature_C': 185,
                                'particle_size_um': 10})
    check('olivine carbonation dataset refuses (provisional) — '
          'exact stoichiometry, unmeasured yield',
          verdict['ok'] is False
          and 'provisional' in (verdict.get('refusal') or ''))
    check('the row names the exact stoichiometry + the data ask',
          'Mg2SiO4' in SEED_CERAMICS_DATASETS[0]
          ['source_conditions_json']
          and 'DATA ASK' in SEED_CERAMICS_DATASETS[0]['notes'])


def test_validate():
    print('[ceramics: sample honesty]')
    result = validate_samples()
    check('all samples pass structural validation (tiers/classes/'
          'accessibility rollup)', result['ok'])


def main():
    test_ladder_ordering()
    test_local_and_olivine_tracks()
    test_steelmaking_filter()
    test_carbonation_dataset_refuses()
    test_validate()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
