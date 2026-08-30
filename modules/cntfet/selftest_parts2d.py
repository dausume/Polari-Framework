"""
Selftest for cntfet.cnt_parts_svg (fg-3: the 2-D parts view as
data — regions from the same rows the parts list names).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_parts2d
"""

import json
import sys

from cntfet import cnt_derive as cd
from cntfet import selftest_cntfet as st
from cntfet.cnt_parts_svg import (
    KIND_STYLE, SCHEMA2D, SEED_FET_2D_SCENES, fet2d_scene,
    parts2d_report, scene2d_name,
)
from cntfet.selftest_summary import _mgr, _seed_si
from sifet.si_device import derive_si_device
from sifet.si_device import get_row as si_get

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


ALL_KINDS = {'contact', 'extension', 'channel', 'oxide', 'gate'}


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    ok_cnt = cd.derive_device(
        mgr, device,
        parameter_factory=st._row_factory(mgr, 'CNTFETParameterRow'))['ok']
    ok_si = all(derive_si_device(
        mgr, si_get(mgr, 'SiliconMOSFET', n))['ok']
        for n in ('si-nmos-planar-90', 'si-nmos-finfet-solgel-hfo2'))
    check('derive: S1 + planar-90 + finfet derive', ok_cnt and ok_si)

    s1 = parts2d_report(mgr, 'cnt-aligned-s1')
    check('CNT: cnt-gaa template, every region kind drawn, row-backed '
          '(no sketch flag on the axial regions)',
          s1['ok'] and s1['schema'] == SCHEMA2D
          and s1['template'] == 'cnt-gaa'
          and {r['kind'] for r in s1['regions']} == ALL_KINDS
          and not any(r['sketch'] for r in s1['regions']),
          f"kinds={ {r['kind'] for r in s1.get('regions', [])} }")
    check('CNT: regions carry their part payload (material, doping '
          'statement, the ROW it comes from) for every kind',
          all(any(r['part'] and r['part'].get('doping')
                  and r['part'].get('row')
                  for r in s1['regions'] if r['kind'] == kind)
              for kind in ALL_KINDS))
    check('CNT: field overlay at the device\'s OWN Vdd by default '
          '(potential, eV, vg = vd = 0.6)',
          s1['field'].get('ok') and s1['field']['unit'] == 'eV'
          and abs(s1['field']['vg'] - 0.6) < 1e-9
          and abs(s1['field']['vd'] - 0.6) < 1e-9
          and len(s1['field']['x_nm']) == len(s1['field']['value']),
          str({kk: s1['field'].get(kk)
               for kk in ('ok', 'refusal', 'unit', 'vg')}))
    mat = parts2d_report(mgr, 'cnt-aligned-s1', field='material')
    check('CNT: ?field=material rides the same overlay contract '
          '(region-index rows)',
          mat['field'].get('ok')
          and mat['field']['unit'] == 'region index')

    si = parts2d_report(mgr, 'si-nmos-planar-90')
    fin = parts2d_report(mgr, 'si-nmos-finfet-solgel-hfo2')
    check('Si: si-planar / si-finfet templates from the device\'s own '
          'shape; every region kind drawn; sketch lengths labelled '
          'per region',
          si['ok'] and si['template'] == 'si-planar'
          and fin['template'] == 'si-finfet'
          and {r['kind'] for r in si['regions']} == ALL_KINDS
          and any(r['sketch'] for r in si['regions'])
          and any(not r['sketch'] for r in si['regions']),
          f"si={si.get('template')} fin={fin.get('template')}")
    check('Si: oxide thickness + junction depth are row-backed '
          '(oxide rect h = the dielectric row\'s thickness)',
          any(r['kind'] == 'oxide' and r['part']
              and r['h'] == r['part']['dimensions']['thickness_nm']
              for r in si['regions']))
    check('Si: field overlay now SERVES the si_fields sketch at the '
          'device\'s own Vdd (fg-4 basis landed), labelled F1 '
          'SKETCH, x aligned with the parts2d lengths',
          si['field'].get('ok') is True
          and si['field']['unit'] == 'eV'
          and abs(si['field']['vg'] - 1.0) < 1e-9
          and 'SKETCH' in si['field'].get('fidelity', '')
          and len(si['field']['x_nm']) == len(si['field']['value']),
          str({kk: si['field'].get(kk)
               for kk in ('ok', 'refusal', 'unit', 'vg')}))

    lg30 = parts2d_report(mgr, 'cnt-aligned-s1-lg30')
    check('underived comparator: still answers — its component rows '
          'are shared with S1, so the geometry stays row-backed '
          '(the managerless scene check covers the sketch fallback)',
          lg30['ok']
          and {r['kind'] for r in lg30['regions']} == ALL_KINDS)
    check('unknown device refuses',
          not parts2d_report(mgr, 'no-such-fet')['ok'])

    sc = fet2d_scene('cnt-aligned-s1', manager=mgr)
    sc_cold = fet2d_scene('cnt-aligned-s1')          # seed pass, no mgr
    sc_si = fet2d_scene('si-nmos-planar-90', manager=mgr)
    blob = json.loads(sc['definition'])
    check('scenes: fet-2d-{device} SimSpaceDefinition rows — 2d, '
          'freestandingOnly, one sized rectangle per region, styles '
          'from KIND_STYLE; managerless seed pass falls back to the '
          'sketch; Si devices get one too',
          sc['name'] == scene2d_name('cnt-aligned-s1')
          and sc['dimensionality'] == '2d'
          and blob['freestandingOnly']
          and len(blob['freestanding']) >= 8
          and all(e['shapeRef'] == 'rectangle'
                  and e['styleRef'] in set(KIND_STYLE.values())
                  and len(e['scale']) == 2
                  for e in blob['freestanding'])
          and json.loads(sc_cold['definition'])['freestanding']
          and json.loads(sc_si['definition'])['template'] == 'si-planar')
    seeds = SEED_FET_2D_SCENES(
        ['cnt-aligned-s1', 'si-nmos-planar-90'], manager=mgr)
    check('SEED_FET_2D_SCENES: one row per device, unique names',
          len(seeds) == 2
          and len({s['name'] for s in seeds}) == 2)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
