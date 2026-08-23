"""
Selftest for microchip (design-level ladder + traversal).

Run from polari-framework/:
  PYTHONPATH=. python3 -m microchip.selftest_microchip

Fake manager; exercises: the level report (live vs refusing), full
traversal up/down the RV16X-NANO precedent and our ladder, honest
degradation when a referenced device module's rows are absent, and
the citation linkage riding the anchor references.
"""

import json
import sys
import types

from microchip import chip_traverse as ct
from microchip.chip_basis import (
    SEED_DESIGN_LEVELS, SEED_DESIGN_NODES,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(with_device_rows=True, with_anchor_rows=True):
    tables = {'DesignLevelDefinition': {}, 'MicrochipDesignNode': {}}
    mgr = types.SimpleNamespace(objectTables=tables, db=None)
    for seed in SEED_DESIGN_LEVELS:
        row = types.SimpleNamespace(**seed)
        tables['DesignLevelDefinition'][id(row)] = row
    for seed in SEED_DESIGN_NODES:
        row = types.SimpleNamespace(**seed)
        tables['MicrochipDesignNode'][id(row)] = row
    if with_device_rows:
        tables['AlignedCNTFETDevice'] = {}
        dev = types.SimpleNamespace(name='cnt-aligned-s1',
                                    derived_at='2026-08-21T00:00:00')
        tables['AlignedCNTFETDevice'][id(dev)] = dev
        tables['ElectronicDeviceDefinition'] = {}
        film = types.SimpleNamespace(name='cnt-nfet-led-switch',
                                     derived_at='')
        tables['ElectronicDeviceDefinition'][id(film)] = film
    if with_anchor_rows:
        tables['CNTCalibrationAnchor'] = {}
        for name, value, unit in (
                ('hil19-cnfet-count', 14702.0, 'CNFETs'),
                ('hil19-vdd', 1.8, 'V'),
                ('hil19-clock-measured', 10e3, 'Hz'),
                ('hil19-cell-library', 63.0, 'cells'),
                ('hil19-nor-yield', 1.0, 'fraction'),
                ('hil19-cnts-per-cnfet', 20.0, 'CNTs/CNFET'),
                ('hil19-dream-purity-relaxation', 1e4, 'ratio'),
                ('hil19-rinse-particle-reduction', 250.0, 'ratio')):
            row = types.SimpleNamespace(
                name=name, value=value, unit=unit,
                doi='10.1038/s41586-019-1493-8',
                figure='[HIL19]', status='ready')
            tables['CNTCalibrationAnchor'][id(row)] = row
    return mgr


def main():
    mgr = _mgr()

    levels = ct.levels_report(mgr)
    check('ladder: five levels in rank order '
          '(device..chip)',
          [lv['name'] for lv in levels] ==
          ['device', 'standard-cell', 'functional-block', 'core',
           'chip'])
    device = levels[0]
    check('ladder: the device level is LIVE, names its scale axes '
          '(manufacturing_regime + physics_fidelity), and counts '
          'live artifact rows',
          device['status'] == 'live'
          and {a['axis'] for a in device['scaleAxes']}
          == {'manufacturing_regime', 'physics_fidelity'}
          and all(a['present'] for a in device['artifactClasses'])
          and device['refusal'] is None)
    check('ladder: every unbuilt level REFUSES with its plan '
          'pointer (no fake cells/cores)',
          all(lv['refusal'] and lv['planPointer']
              for lv in levels[1:]))

    # RV16X-NANO precedent traversal, device rung upward.
    rep = ct.traverse(mgr, 'rv16x-cnfet')
    check('traverse: rv16x-cnfet climbs the full parent chain to '
          'the chip root',
          rep['ok'] and [n['name'] for n in rep['up']] ==
          ['rv16x-cell-library', 'rv16x-pipeline', 'rv16x-core',
           'rv16x-chip'])
    check('traverse: precedent nodes are status=reference with the '
          '[HIL19] citation riding every node',
          rep['node']['status'] == 'reference'
          and '10.1038/s41586-019-1493-8' in rep['node']['citation']
          and all('10.1038/s41586-019-1493-8' in n['citation']
                  for n in rep['up']))
    anchors = [a for a in rep['node']['artifacts']
               if a['kind'] == 'citation-anchor']
    check('traverse: the device node resolves its citation '
          'anchors (15-25 CNTs/FET, DREAM, RINSE) with values + '
          'DOI',
          len(anchors) == 3 and all(a['resolved'] for a in anchors)
          and any(a['value'] == 20.0 for a in anchors))

    # Downward from the chip.
    rep = ct.traverse(mgr, 'rv16x-chip')
    check('traverse: chip node walks DOWN to the core',
          rep['ok'] and [n['name'] for n in rep['down']]
          == ['rv16x-core'])

    # Our ladder: live device rung + honest unbuilt uppers.
    rep = ct.traverse(mgr, 'polari-aligned-cnt-s1')
    art = rep['node']['artifacts'][0]
    check('traverse: our S1 device node resolves the LIVE '
          'cnt-aligned-s1 row (derived)',
          rep['ok'] and art['resolved']
          and art['status'] == 'derived')
    check('traverse: our ladder tops out through UNBUILT rungs '
          '(cell-lib -> blocks -> core -> chip, all unbuilt)',
          [n['name'] for n in rep['up']] ==
          ['polari-cell-lib', 'polari-blocks', 'polari-rv32e-core',
           'polari-chip']
          and all(n['status'] == 'unbuilt' for n in rep['up']))

    tree = ct.design_tree(mgr, 'rv16x-nano-precedent')
    check('design tree: precedent nests chip -> core -> pipeline '
          '-> cell-library -> device',
          tree['ok'] and tree['nodeCount'] == 5
          and tree['tree'][0]['name'] == 'rv16x-chip'
          and tree['tree'][0]['children'][0]['children'][0][
              'children'][0]['children'][0]['name'] == 'rv16x-cnfet')
    check('design tree: unknown design refuses',
          not ct.design_tree(mgr, 'no-such-design')['ok'])
    check('traverse: unknown node refuses',
          not ct.traverse(mgr, 'no-such-node')['ok'])

    # Honest degradation without the device/cntfet modules.
    bare = _mgr(with_device_rows=False, with_anchor_rows=False)
    levels = ct.levels_report(bare)
    check('degradation: device level reports absent artifact '
          'modules by name (no import error, no pretense)',
          all(not a['present'] and 'module' in a['why']
              for a in levels[0]['artifactClasses']))
    rep = ct.traverse(bare, 'polari-aligned-cnt-s1')
    check('degradation: unresolved device row says WHICH module '
          'would provide it',
          rep['ok'] and not rep['node']['artifacts'][0]['resolved']
          and 'cntfet' in rep['node']['artifacts'][0]['why'])
    rep = ct.traverse(bare, 'rv16x-cnfet')
    check('degradation: unresolved citation anchors refuse with a '
          'reason',
          all((not a['resolved']) and a['why']
              for a in rep['node']['artifacts']))

    # /display/microchip page seed.
    from microchip.chip_pages_seed import (
        SEED_MICROCHIP_PAGE_DISPLAYS,
    )
    page = SEED_MICROCHIP_PAGE_DISPLAYS[0]
    page_def = json.loads(page['definition'])
    page_components = [item['componentProps']['componentName']
                       for row in page_def['rows']
                       for item in row['items']]
    check('page: /display/microchip seeds the interactive '
          'microchip-ladder component + the row tables',
          page['isPage'] and page['pageRoute'] == 'microchip'
          and page_components[0] == 'microchip-ladder'
          and set(page_components) <= {'microchip-ladder',
                                       'class-rows-table'})

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
