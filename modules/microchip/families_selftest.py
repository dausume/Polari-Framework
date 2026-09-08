"""
Selftest for microchip.chip_families_basis (rank-1 device families,
MICROCHIP_LADDER_PLAN §2c): FET live with counted artifacts, every
non-FET family an honest SHELL (contract as data, no classes, first
target + plan pointer), refusals by name.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m microchip.families_selftest
"""

import json
import sys
import types

from microchip.chip_families_basis import (
    SEED_DEVICE_FAMILIES, DeviceFamilyDefinition, families_report,
    family_report,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(with_fet_rows=True):
    tables = {'DeviceFamilyDefinition': {}}
    mgr = types.SimpleNamespace(objectTables=tables, db=None)
    for seed in SEED_DEVICE_FAMILIES:
        row = types.SimpleNamespace(**seed)
        tables['DeviceFamilyDefinition'][id(row)] = row
    if with_fet_rows:
        tables['AlignedCNTFETDevice'] = {
            1: types.SimpleNamespace(name='cnt-aligned-s1')}
        tables['SiliconMOSFET'] = {
            1: types.SimpleNamespace(name='si-nmos-planar-90'),
            2: types.SimpleNamespace(name='si-pmos-planar-90')}
    return mgr


def main():
    check('rows construct from every seed; fet is the ONE live '
          'family, all others shells',
          all(hasattr(DeviceFamilyDefinition(**{**s,
                                                'manager': None}),
                      'contract_json')
              for s in SEED_DEVICE_FAMILIES)
          and [s['name'] for s in SEED_DEVICE_FAMILIES
               if s['status'] == 'live'] == ['fet']
          and len(SEED_DEVICE_FAMILIES) == 7)

    rep = families_report(_mgr())
    fams = {f['family']: f for f in rep['families']}
    check('device-families/1: 7 families, fet first (live sorts '
          'ahead), principle stated',
          rep['ok'] and rep['schema'] == 'device-families/1'
          and len(rep['families']) == 7
          and rep['families'][0]['family'] == 'fet'
          and 'FET is a FAMILY' in rep['principle'])
    check('fet: artifact classes COUNTED on this instance (1 CNT + '
          '2 Si rows here)',
          fams['fet']['liveRows'] == 3
          and any(c['class'] == 'SiliconMOSFET' and c['rows'] == 2
                  for c in fams['fet']['artifactClasses']))
    check('every shell: zero artifact classes, non-empty contract '
          'with quantity+unit+why, first target, plan pointer, the '
          'schema-freeze shell note',
          all(f['status'] == 'shell'
              and not f['artifactClasses']
              and f['contract']
              and all({'quantity', 'unit', 'why'} <= set(t)
                      for t in f['contract'])
              and f['firstTarget'] and f['planPointer']
              and 'schema-freeze' in f['notes']
              for f in rep['families'] if f['family'] != 'fet'))
    check('mixed-family compositions declared: 1T1C = fet + '
          'capacitor; RRAM crossbar = memristor + fet',
          any('fet' in c['with'] and 'capacitor' in c['with']
              for c in fams['capacitor']['composes'])
          and any('fet' in c['with']
                  for c in fams['memristor']['composes']))
    check('capacitor names the D6 default-first role',
          'D6' in fams['capacitor']['firstTarget']
          or 'first family' in fams['capacitor']['firstTarget'])

    one = family_report(_mgr(), 'photonic')
    check('single-family report: contract + composes ride it',
          one['ok'] and one['family'] == 'photonic'
          and one['contract'] and one['composes'])
    bad = family_report(_mgr(), 'quantum')
    check('unknown family refuses NAMING the known set',
          not bad['ok'] and 'fet' in bad['error']
          and 'capacitor' in bad['error'])

    empty = families_report(_mgr(with_fet_rows=False))
    check('no device rows on the instance: fet still listed, '
          'liveRows honestly 0',
          empty['ok']
          and next(f for f in empty['families']
                   if f['family'] == 'fet')['liveRows'] == 0)

    passed = sum(1 for _l, okc in _results if okc)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
