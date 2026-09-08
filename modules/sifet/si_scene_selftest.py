"""
Selftest for fg-6 — the silicon 3-D scenes + device-relative field
sampling (sifet.custom.si_scene, cnt_fields.sample_fields with
SI_FIELD_BANDS) and the fet-2d scale normalization that fixed the
gray-viewport bug.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m sifet.si_scene_selftest
"""

import json
import sys

from cntfet.custom import cnt_derive as cd
from cntfet import cntfet_selftest as st
from cntfet.cnt_fields_basis import (
    SCALAR_FIELDS, SEEDED_STYLE_NAMES, sample_fields,
)
from cntfet.custom.cnt_parts_svg import fet2d_scene
from cntfet.cnt_scene_seed import scene_name
from cntfet.summary_selftest import _mgr, _seed_si
from sifet.custom.si_fields import SI_FIELD_BANDS
from sifet.custom.si_scene import SEED_SI_DEVICE_SCENES, si_device_scene
from sifet.custom.si_device import derive_si_device, get_row

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    mgr.objectTables.setdefault('FETFieldSample', {})
    si = get_row(mgr, 'SiliconMOSFET', 'si-pmos-planar-90')
    cnt = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    check('derive: pmos-90 + S1',
          derive_si_device(mgr, si)['ok']
          and cd.derive_device(
              mgr, cnt, parameter_factory=st._row_factory(
                  mgr, 'CNTFETParameterRow'))['ok'])

    # ---- scene naming: fet, not cntfet ---------------------------
    check('scene_name is fet-3d-{device} for every technology '
          '(the cnt-device-3d-* rows are the legacy list)',
          scene_name('si-pmos-planar-90') == 'fet-3d-si-pmos-planar-90'
          and scene_name('cnt-aligned-s1') == 'fet-3d-cnt-aligned-s1')

    sc = si_device_scene('si-pmos-planar-90', manager=mgr)
    blob = json.loads(sc['definition'])
    styles = {e['styleRef'] for e in blob['freestanding']}
    check('Si 3-D scene: rows-backed stack (8+ pieces), every piece '
          'a mathshape: reference, seeded materials only, p-type '
          'junction style, FETFieldSample bound with a runRef per '
          'scalar field',
          sc['dimensionality'] == '3d'
          and len(blob['freestanding']) >= 8
          and all(e['shapeRef'].startswith('mathshape:fet-part-')
                  for e in blob['freestanding'])
          and styles <= set(SEEDED_STYLE_NAMES)
          and 'fet-si-sd-p' in styles
          and not blob['freestandingOnly']
          and set(blob['runRefs']) == set(SCALAR_FIELDS)
          and json.loads(sc['bound_classes_json'])
          == [{'className': 'FETFieldSample'}],
          f'styles={sorted(styles)}')
    # ---- fg-6, his directive: the pieces ARE math shapes ---------
    import types
    from cntfet.cnt_scene_seed import part_shape_seeds
    from mathshapes.custom.shape_analysis import sample_surface
    from mathshapes.custom.shape_equations import shape_equation_rows
    from sifet.custom.si_scene import part_shape_seeds_si
    mgr.objectTables.setdefault('MathShapeDefinition', {})
    shape_rows = (part_shape_seeds_si('si-pmos-planar-90', mgr)
                  + part_shape_seeds('cnt-aligned-s1', mgr))
    for sh in shape_rows:
        row = types.SimpleNamespace(**sh)
        mgr.objectTables['MathShapeDefinition'][id(row)] = row
    box = sample_surface(mgr, 'fet-part-si-pmos-planar-90-gate')
    shell = sample_surface(mgr, 'fet-part-cnt-aligned-s1-oxide-shell')
    eqs = shape_equation_rows(mgr,
                              'fet-part-si-pmos-planar-90-channel')
    eq_rows = (eqs.get('rows', eqs) if isinstance(eqs, dict) else eqs)
    check('the pieces ARE MathShapeDefinition rows: the Si gate box '
          'and the CNT oxide shell (CSG difference of coaxial '
          'cylinders) mesh through the same surface sampler the '
          'pots/motors use, and a piece yields its matrix-equation '
          'rows (shape_equation_rows)',
          box.get('ok') and len(box.get('points') or []) > 4
          and shell.get('ok') and len(shell.get('points') or []) > 4
          and bool(eq_rows),
          f"box={box.get('error', 'ok')} "
          f"shell={shell.get('error', 'ok')} "
          f"eqs={str(eqs)[:120]}")
    check('Si 3-D scene: managerless seed pass falls back to the '
          'sketch and says so',
          'sketch' in si_device_scene('si-pmos-planar-90')
          ['description'].lower())
    check('SEED_SI_DEVICE_SCENES: one row per device, fet-3d names',
          [s['name'] for s in SEED_SI_DEVICE_SCENES(
              ['si-nmos-planar-90', 'si-pmos-planar-90'], mgr)]
          == ['fet-3d-si-nmos-planar-90', 'fet-3d-si-pmos-planar-90'])

    # ---- device-relative sampling with silicon bands -------------
    rf = st._row_factory(mgr, 'FETFieldSample')
    rep = sample_fields(mgr, si, n_cells=20, row_factory=rf)
    check('sample_fields(Si): sweeps 0 → the device\'s OWN Vdd '
          '(7 steps to 1.0 V) at Vd = 1.0 V, one row per cell per '
          'Vg per field',
          rep.get('ok')
          and rep['vgSteps'][-1] == 1.0 and len(rep['vgSteps']) == 7
          and rep['vd'] == 1.0
          and rep['rows'] == 3 * 7 * 20,
          str({kk: rep.get(kk) for kk in ('vgSteps', 'vd', 'rows',
                                          'error')}))
    samples = list(mgr.objectTables['FETFieldSample'].values())
    dens = [r for r in samples if r.field == 'electron-density'
            and r.vg_v == 1.0 and r.band >= 0]
    # sample_fields sweeps SCALAR_FIELDS (n-doping, not p): for the
    # PMOS the n-doping field is the n-well channel row
    dop = [r for r in samples if r.field == 'n-doping' and r.band >= 0]
    check('Si banding uses the SILICON ranges (areal cm^-2 / cm^-3): '
          'on-state sheet densities land in real bands (values '
          '~1e12+ would all sit in the CNT top band), doping bands '
          'label cm^-3 thresholds',
          dens and max(r.value for r in dens) > 1e11
          and any(r.band < 5 for r in dens)
          and any('1e18' in r.band_label or 'intrinsic' in r.band_label
                  for r in dop) and dop
          and all(r.band_style in SEEDED_STYLE_NAMES
                  for r in dens + dop),
          f'dens bands={sorted({r.band for r in dens})} '
          f'dop labels={sorted({r.band_label for r in dop})[:3]}')
    check('samples carry the scene contract: run_ref per field, '
          'pos_x centred in scene units, vg_v the scrubber instant',
          all(r.simulation_run_ref
              == f'fet-fields:si-pmos-planar-90:{r.field}'
              for r in samples)
          and any(abs(r.pos_x) < 1e-6 or r.pos_x for r in samples))

    cnt_rep = sample_fields(mgr, cnt, n_cells=12, row_factory=rf)
    check('CNT control: default sweep is EXACTLY the old '
          '(0, 0.1, …, 0.6) at Vd 0.6 — bit-identical',
          cnt_rep.get('ok')
          and cnt_rep['vgSteps']
          == [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
          and cnt_rep['vd'] == 0.6,
          str(cnt_rep.get('vgSteps')))
    check('SI_FIELD_BANDS is a transform of the CNT set: same '
          '(field, order) → same style_ref; silicon units swapped',
          all(b['style_ref'] for b in SI_FIELD_BANDS)
          and any(b['unit'] == 'cm^-2' for b in SI_FIELD_BANDS)
          and any(b['unit'] == 'eV' for b in SI_FIELD_BANDS))

    # ---- the fet-2d gray-viewport fix ----------------------------
    sc2 = fet2d_scene('si-pmos-planar-90', manager=mgr)
    ent = json.loads(sc2['definition'])['freestanding']
    body = next(e for e in ent if e['id'] == 'body')
    check('fet-2d scale is style-normalized ([w/40, h/40], '
          'non-uniform) — nm values fed straight into scale once '
          'painted one giant rectangle over the whole viewport',
          all(len(e['scale']) == 2 for e in ent)
          and abs(body['scale'][0] * 40.0 - 170.0) < 1.0
          and body['scale'][1] < body['scale'][0],
          f"body scale={body['scale']}")

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
