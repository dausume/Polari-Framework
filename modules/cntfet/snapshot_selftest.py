"""
@module cntfet.snapshot_selftest
The committed FET initial data (module data convention): files parse in
the generic format, rows fit the CURRENT constructors, the expensive
rows are present and coherent (every run names a snapshotted device,
Liberty parses, nom_voltage = the device Vdd, one library per device),
nothing excluded leaked in, total size stays small; the generic
json_seeds layer round-trips (write → read → seed_pairs → serve).
"""

import os
import re
import sys
import tempfile

from cntfet.custom.cnt_snapshot import (
    EXCLUDED, SNAPSHOT_CLASSES, latest_per_key, load_snapshot,
    snapshot_inventory, snapshot_path, snapshot_rows,
)
from moduleService import json_seeds

PASSED = FAILED = 0
LIMIT_BYTES = 2_000_000


def check(label, cond, extra=''):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f'PASS: {label}')
    else:
        FAILED += 1
        print(f'FAIL: {label}' + (f' — {extra}' if extra else ''))


def main():
    inv = snapshot_inventory()
    present = [c for c in inv['classes'] if c['present']]
    check('initialData: every SNAPSHOT_CLASSES file present in its OWN '
          f'package, schema {json_seeds.SCHEMA}, plain .json, total < '
          f'{LIMIT_BYTES / 1e6:g} MB',
          len(present) == len(SNAPSHOT_CLASSES)
          and all(load_snapshot(c['class'])['schema'] == json_seeds.SCHEMA
                  for c in present)
          and snapshot_path('SiliconMOSFET').split(os.sep)[-3] == 'sifet'
          and snapshot_path('CellCharacterizationRun').split(os.sep)[-3] == 'cntfet'
          and inv['totalBytes'] < LIMIT_BYTES,
          f'inventory={inv}')
    check('initialData: excluded tables are stated with a reason and none '
          'has a file in either package',
          len(EXCLUDED) >= 8
          and not any(os.path.exists(os.path.join(json_seeds.data_dir(p), f'{n}.json'))
                      for p in ('cntfet', 'sifet')
                      for n in ('FETFieldSample', 'CNTFETSimResult',
                                'EvidenceItem', 'CNTCellDefinition')))
    by, skipped = snapshot_rows()
    check('initialData: generic loader imports every class from its package '
          'and keeps only CURRENT constructor fields; every row named',
          not skipped and set(by) == {n for n, _p, _m in SNAPSHOT_CLASSES}
          and all(r.get('name') for rows in by.values() for r in rows),
          f'skipped={skipped} classes={sorted(by)}')
    devices = {r['name'] for r in by.get('AlignedCNTFETDevice', [])} | {
        r['name'] for r in by.get('SiliconMOSFET', [])}
    runs = by.get('CellCharacterizationRun', [])
    libs = [r for r in runs if str(r.get('cell', '')).startswith('library')]
    check('initialData: derived devices present (S1 + planar-90 + '
          'freepdk45-class), every run names a snapshotted device, ONE '
          'library per device (latest), Liberty parses, nom_voltage = row '
          'vdd_v = device Vdd',
          {'cnt-aligned-s1', 'si-nmos-planar-90',
           'si-nmos-freepdk45-class'} <= devices
          and all(r.get('derived_at') for r in by['AlignedCNTFETDevice']
                  if r['name'] == 'cnt-aligned-s1')
          and all(r['device'] in devices for r in runs)
          and len({r['device'] for r in libs}) == len(libs) >= 3
          and _liberty_ok(libs, by),
          f'devices={sorted(devices)} runs={[(r["name"], r.get("vdd_v")) for r in runs]}')
    check('initialData: open library + blocks rows carried',
          any(r.get('name') == 'polari-open-si-planar-90'
              for r in by.get('OpenCellLibrary', []))
          and len(by.get('FunctionalBlock', [])) >= 4)
    d = latest_per_key([{'k': 1, 'ran_at': '2026-01'}, {'k': 1, 'ran_at': '2026-02'},
                        {'k': 2, 'ran_at': '2025-01'}], lambda r: r['k'])
    check('snapshot: latest_per_key keeps the newest per key',
          sorted(x['ran_at'] for x in d) == ['2025-01', '2026-02'])
    # generic layer round-trip on a scratch package dir
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, 'fakepkg')
        os.makedirs(pkg)
        orig = json_seeds.MODULES_ROOT
        json_seeds.MODULES_ROOT = tmp
        try:
            path = json_seeds.write_file('fakepkg', 'AlignedCNTFETDevice',
                                         [{'name': 'b', 'id': 'drop-me', 'polarity': 'p'},
                                          {'name': 'a', 'polarity': 'n'}], source='test')
            served = json_seeds.serve('fakepkg')
            pairs, sk = json_seeds.seed_pairs('cntfet', manager=None,
                                              payloads=served['files'])
            rows = pairs[0][2] if pairs else []
        finally:
            json_seeds.MODULES_ROOT = orig
        check('json_seeds: write → serve → seed_pairs round-trips (sorted by '
              'name, meta id dropped, constructor-filtered, schema stamped, '
              'package resolved for a modules/<id> package)',
              os.path.basename(path) == 'AlignedCNTFETDevice.json'
              and served['schema'] == json_seeds.SCHEMA
              and served['files'][0]['count'] == 2
              and [r['name'] for r in rows] == ['a', 'b']
              and 'id' not in rows[1] and rows[1]['polarity'] == 'p' and not sk
              and json_seeds.resolve_package('cntfet') == 'cntfet',
              f'rows={rows} sk={sk}')
    ms_pairs, ms_skipped = json_seeds.seed_pairs('materials_science',
                                                 manager=None)
    check('json_seeds: a legacy bare-list initialData dir (materials science, '
          'Feb 2026) lists, loads nothing, and is skipped LOUDLY per file — '
          'never raises',
          not ms_pairs and len(ms_skipped) >= 5
          and all('rename to <ClassName>.json' in why for _f, why in ms_skipped),
          f'skipped={ms_skipped[:2]}')
    check('json_seeds: packages_with_data lists cntfet and sifet',
          {'cntfet', 'sifet'} <= set(json_seeds.packages_with_data()))
    print(f'{PASSED}/{PASSED + FAILED} checks passed')
    return 0 if not FAILED else 1


def _liberty_ok(libs, by):
    from cntfet.cnt_cell_scoring_seed import parse_liberty
    # CNT rows carry no vdd_v (device_vdd's 0.6 V default); Si rows do
    vdd_of = {r['name']: float(r.get('vdd_v') or 0.6)
              for n in ('AlignedCNTFETDevice', 'SiliconMOSFET')
              for r in by.get(n, [])}
    for r in libs:
        text = r.get('liberty_text') or ''
        if 'INVX1' not in parse_liberty(text)['cells']:
            return False
        m = re.search(r'nom_voltage\s*:\s*([0-9.]+)', text)
        if not m or abs(float(m.group(1)) - vdd_of.get(r['device'], -1)) > 1e-9:
            return False
        if abs(float(r.get('vdd_v') or 0) - float(m.group(1))) > 1e-9:
            return False
    return True


if __name__ == '__main__':
    sys.exit(main())
