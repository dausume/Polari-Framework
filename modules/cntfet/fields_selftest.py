"""
Selftest for fv-4 (cnt_fields + cnt_scene).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.fields_selftest
"""

import json
import sys
import types

from cntfet.custom import cnt_derive as cd
from cntfet import cnt_fields_basis as cf
from cntfet import cnt_scene_seed as cs
from cntfet import cntfet_selftest as st
from cntfet.cntfet_selftest import check

DEV = 'cnt-aligned-s1'


def _mgr():
    mgr = st._mgr()
    st._seed_all(mgr)
    for t in ('FETFieldSample', 'FETFieldBand', 'SimSpaceBindingDefinition',
              'SimSpaceDefinition', 'Material3DDefinition'):
        mgr.objectTables[t] = {}
    mgr.objectTypingDict = {}
    return mgr


def main():
    mgr = _mgr()
    dev = cd.get_row(mgr, 'AlignedCNTFETDevice', DEV)

    # refusal before derive
    prof = cf.field_profile(mgr, DEV, 'potential')
    check('fv-4: underived device refuses (names derive)',
          not prof['ok'] and 'derive' in prof['error'], str(prof))

    rep = cd.derive_device(mgr, dev, parameter_factory=st._row_factory(
        mgr, 'CNTFETParameterRow'))
    check('fv-4: S1 derives', rep['ok'])

    # regions
    geo = cf.device_regions(mgr, dev)
    regs = geo['regions']
    check('fv-4: 5 regions ordered along x, contiguous',
          geo['ok'] and len(regs) == 5
          and all(regs[i]['x1'] == regs[i + 1]['x0'] for i in range(4))
          and [r['kind'] for r in regs] == ['contact', 'extension',
                                            'channel', 'extension',
                                            'contact'],
          str([(r['kind'], r['x0'], r['x1']) for r in regs]))
    check('fv-4: regions row-backed (Pd from CNTContact, CNT (16,0) from '
          'CNTMaterialState, HfO2 from GateStack)',
          regs[0]['material'] == 'Pd'
          and regs[0]['componentRow'] == {'className': 'CNTContact',
                                          'name': 'cnt-s1-pd-contact'}
          and regs[2]['material'] == 'CNT (16,0)'
          and regs[2]['componentRow']['className'] == 'CNTMaterialState'
          and geo['radial'][1]['material'] == 'HfO2'
          and geo['radial'][1]['componentRow']['className'] == 'GateStack'
          and geo['radial'][2]['x0'] == regs[2]['x0'],
          json.dumps([r['material'] for r in regs] + geo['radial']))
    check('fv-4: sketch extension length is STATED (l_ext_nm = 0 on the row)',
          any('sketch' in n for n in geo['notes']), str(geo['notes']))

    # potential
    heights, drains = [], []
    for vg in (0.0, 0.2, 0.4, 0.6):
        p = cf.field_profile(mgr, DEV, 'potential', vg=vg, vd=0.6)
        heights.append(p['barrier_height_ev'])
        drains.append(p['drain_lead_ev'])
    check('fv-4: potential barrier height at x0 DECREASES monotonically '
          'with Vg over {0,0.2,0.4,0.6}',
          all(heights[i] > heights[i + 1] for i in range(3)),
          f'heights={heights}')
    p_lo = cf.field_profile(mgr, DEV, 'potential', vg=0.3, vd=0.1)
    p_hi = cf.field_profile(mgr, DEV, 'potential', vg=0.3, vd=0.6)
    drop = p_lo['drain_lead_ev'] - p_hi['drain_lead_ev']
    check('fv-4: drain-side Ec drops by ~Vds when Vd rises 0.1 -> 0.6 V',
          abs(drop - 0.5) < 0.05 and p_lo['source_lead_ev'] == p_hi['source_lead_ev'],
          f'drop={drop} source={p_lo["source_lead_ev"]}')
    check('fv-4: every potential payload says F1 SKETCH',
          'SKETCH' in p_lo['fidelity'] and 'SKETCH' in p_lo['note'])
    print(f'  [info] barrier height Vg=0: {heights[0]:.4f} eV, '
          f'Vg=0.6: {heights[-1]:.4f} eV; lambda={p_lo["lambda_nm"]:.3f} nm')

    # density
    d0 = cf.field_profile(mgr, DEV, 'electron-density', vg=0.0)
    d6 = cf.field_profile(mgr, DEV, 'electron-density', vg=0.6)
    ch = regs[2]
    i_ch = [i for i, x in enumerate(d0['x_nm']) if ch['x0'] <= x <= ch['x1']]
    i_ext = [i for i, x in enumerate(d0['x_nm'])
             if regs[1]['x0'] <= x < regs[1]['x1']]
    i_con = [i for i, x in enumerate(d0['x_nm']) if x < regs[0]['x1']]
    min0 = min(d0['value'][i] for i in i_ch)
    min6 = min(d6['value'][i] for i in i_ch)
    n_ext = d0['n_ext_per_m']
    check('fv-4: density at the barrier top increases with Vg and equals '
          'n_ext in the extensions; None in metal',
          min6 > min0 * 10
          and all(d0['value'][i] == n_ext for i in i_ext)
          and all(d0['value'][i] is None for i in i_con)
          and n_ext > 0,
          f'min0={min0:.3e} min6={min6:.3e} n_ext={n_ext:.3e}')
    print(f'  [info] n_ext = {n_ext:.4e} /m; Qxo/q(Vg=0.6) = '
          f'{d6["qxo_per_m"]:.4e} /m')

    # doping
    nd = cf.field_profile(mgr, DEV, 'n-doping')
    pd_ = cf.field_profile(mgr, DEV, 'p-doping')
    check('fv-4: n-doping 0 in channel, n_ext in extensions, refused in metal',
          all(nd['value'][i] == 0.0 for i in i_ch)
          and all(nd['value'][i] == n_ext for i in i_ext)
          and all(nd['value'][i] is None for i in i_con)
          and 'metal — no doping' in nd['refusals'])
    check('fv-4: p-doping 0 everywhere semiconducting on the n device',
          all(v == 0.0 for v in pd_['value'] if v is not None)
          and any(v is None for v in pd_['value']))
    # p twin
    twin = types.SimpleNamespace(**{**vars(dev), 'name': 'cnt-p-twin',
                                    'polarity': 'p'})
    st._insert(mgr, 'AlignedCNTFETDevice', twin)
    pt = cf.field_profile(mgr, 'cnt-p-twin', 'p-doping')
    nt = cf.field_profile(mgr, 'cnt-p-twin', 'n-doping')
    check('fv-4: p device mirrors — p-doping = n_ext in extensions, '
          'n-doping 0, regions labelled p+',
          pt['ok'] and all(pt['value'][i] == n_ext for i in i_ext)
          and all(v == 0.0 for v in nt['value'] if v is not None)
          and pt['regions'][1]['material'].endswith('p+'),
          str(pt.get('error')))

    # material
    m = cf.field_profile(mgr, DEV, 'material')
    check('fv-4: material rows label every x',
          m['ok'] and len(m['material']) == len(m['x_nm'])
          and all(isinstance(s, str) and s for s in m['material'])
          and m['value'][0] == 0 and m['value'][-1] == 4)

    # field_rows / curve builders
    rows = cf.field_rows(p_hi)
    styles = {r['style'] for r in rows}
    bands = {r['series'] for r in rows if r['style'] == 'band'}
    check('fv-4: field_rows carry line + region bands + guides',
          {'line', 'band', 'guide'} <= styles and len(bands) == 5
          and all('lo' in r and 'hi' in r for r in rows
                  if r['style'] == 'band'),
          f'styles={styles} bands={bands}')
    from cntfet.cnt_device_viz_seed import device_model
    id_fn, p, dev_row, _ = device_model(mgr, DEV)
    built = {k: fn(id_fn, p, dev_row, mgr) for k, fn in cf.CURVE_BUILDERS.items()}
    n_series = len({r['series'] for r in built['field-potential']
                    if r['style'] == 'line'})
    check('fv-4: CURVE_BUILDERS: 4 curves, potential has 3 Vg line series, '
          'density strictly positive (log y), material dot per x',
          set(built) == {'field-material', 'field-potential',
                         'field-density', 'field-doping'}
          and n_series == 3
          and all(r['y'] > 0 for r in built['field-density']
                  if r['style'] == 'line')
          and sum(1 for r in built['field-material'] if r['style'] == 'dot')
          == len(m['x_nm']),
          f'series={n_series}')
    # a fake D13 SCF row is drawn beside the sketch
    st._insert(mgr, 'CNTFETSimResult', types.SimpleNamespace(
        name='scf-fake', device=DEV, physics_fidelity='F3_NEGF_SCF',
        ran_at='2026-08-27T00:00:00', metrics_json=json.dumps({
            'profiles': [{'vg_v': 0.3, 'vd_v': 0.6,
                          'x_nm': [-5.0, 0.0, 5.0],
                          'ec_ev': [-0.1, 0.1, -0.7]}]})))
    pot = cf.CURVE_BUILDERS['field-potential'](id_fn, p, dev_row, mgr)
    scf = [r for r in pot if r['series'].startswith('SCF')]
    check('fv-4: D13 SCF row-backed profile drawn beside the sketch '
          '(dashed, shifted onto the region axis)',
          len(scf) == 3 and all(r['dash'] for r in scf)
          and scf[1]['x'] == geo['x_channel_center_nm'],
          str(scf))

    # graph seeds round-trip
    ok_graphs = True
    for g in cf.SEED_CNT_FIELD_GRAPHS:
        cfg = json.loads(g['definition'])['graphConfig']
        ok_graphs = ok_graphs and g['name'].startswith('cnt-device-field-') \
            and cfg['xDimension'] == 'x' and 'SKETCH' in g['description']
    check('fv-4: 4 GraphDefinition seeds round-trip, named cnt-device-field-*',
          ok_graphs and len(cf.SEED_CNT_FIELD_GRAPHS) == 4
          and {g['name'] for g in cf.SEED_CNT_FIELD_GRAPHS} == {
              'cnt-device-field-material', 'cnt-device-field-potential',
              'cnt-device-field-density', 'cnt-device-field-doping'})

    # bands + materials
    style_names = set(cf.SEEDED_STYLE_NAMES)
    check('fv-4: every band has a seeded Material3DDefinition; region '
          'materials seeded',
          all(b['style_ref'] in style_names for b in cf.SEED_FET_FIELD_BANDS)
          and {'fet-pd-contact', 'fet-cnt-channel', 'fet-cnt-extension-n',
               'fet-hfo2-oxide', 'fet-gate-metal', 'fet-band-none'}
          <= style_names
          and next(mm for mm in cf.SEED_FET_FIELD_MATERIALS_3D
                   if mm['name'] == 'fet-hfo2-oxide')['transparent'])

    # sample_fields
    vg_list = (0.0, 0.2, 0.4, 0.6)
    rep = cf.sample_fields(mgr, DEV, vg_list=vg_list, n_cells=30,
                           row_factory=st._row_factory(mgr, 'FETFieldSample'))
    samples = list(mgr.objectTables['FETFieldSample'].values())
    per = rep['perField']
    check('fv-4: sample_fields -> n_cells x len(vg_list) rows per scalar '
          'field, bands in range, band_style ⊆ seeded materials',
          rep['ok'] and all(per[f] == 30 * len(vg_list) for f in cf.SCALAR_FIELDS)
          and len(samples) == 3 * 30 * len(vg_list)
          and all(s.band_style in style_names for s in samples)
          and all(cf.band_for(s.field, s.value)['order'] == s.band
                  for s in samples if s.band >= 0)
          and all(s.simulation_run_ref == cf.run_ref(DEV, s.field)
                  for s in samples),
          f'per={per} n={len(samples)}')
    rep2 = cf.sample_fields(mgr, DEV, vg_list=vg_list, n_cells=30,
                            row_factory=st._row_factory(mgr, 'FETFieldSample'))
    check('fv-4: re-sampling replaces the older samples of the device',
          rep2['replaced'] == rep['rows']
          and len(mgr.objectTables['FETFieldSample']) == rep['rows'])

    # scene seed + binding through compile_3d
    scene = cs.device_scene_seeds(DEV, manager=mgr)
    blob = json.loads(scene['definition'])
    ids = {e['id'] for e in blob['freestanding']}
    check('fv-4/fg-6: scene seed json parses; every piece is a '
          'MATH-SHAPE reference (fet-part rows: boxes, x-axis '
          'cylinders, CSG shells) with the view transform stated, '
          'scene named fet-3d-*',
          scene['name'] == f'fet-3d-{DEV}'
          and not blob['freestandingOnly']
          and json.loads(scene['bound_classes_json'])[0]['className']
          == 'FETFieldSample'
          and {'piece-channel', 'piece-source-contact',
               'piece-oxide-shell', 'piece-gate-metal-shell'} <= ids
          and len(blob['freestanding']) == 7
          and all(e['shapeRef'].startswith('mathshape:fet-part-')
                  for e in blob['freestanding'])
          and json.loads(scene['camera_json'])['projection'] == 'orthographic'
          and blob['freestanding'][0]['userData']['componentRow'] is not None,
          str(sorted(ids)))
    sketch = cs.device_scene_seeds('never-derived-x', manager=mgr)
    check('fv-4: seed pass without a derived device falls back to the '
          'STATED sketch geometry',
          'sketch geometry' in sketch['description'])
    try:
        from simSpace.compilers.compile_3d import compile_3d
        mgr.objectTables['SimSpaceBindingDefinition'] = {
            b['name']: types.SimpleNamespace(**b)
            for b in cs.SEED_FET_FIELD_BINDINGS}
        warnings, resolved = [], []
        objs, _c, _v = compile_3d(mgr, types.SimpleNamespace(**scene),
                                  warnings, resolved,
                                  run_filter=cf.run_ref(DEV, 'potential'))
        cells = [o for o in objs if o.get('classRef', {}).get('className')
                 == 'FETFieldSample']
        free = [o for o in objs if 'classRef' not in o]
        check('fv-4: compile_3d on the seeded scene: region meshes + ONLY '
              'the potential samples (run filter), styled by band, '
              'temporalValue = vg',
              len(free) == 7 and len(cells) == 30 * len(vg_list)
              and all(o['styleRef'] in style_names for o in cells)
              and {o['temporalValue'] for o in cells} == set(vg_list)
              and all(o['scale'] > 0 for o in cells)
              and any(o['styleRef'].startswith('fet-band-potential')
                      for o in cells),
              f'free={len(free)} cells={len(cells)} warn={warnings}')
        objs_none, _c, _v = compile_3d(mgr, types.SimpleNamespace(**scene),
                                       [], [], run_filter=None)
        objs_other, _c, _v = compile_3d(
            mgr, types.SimpleNamespace(**{**scene, 'bound_classes_json': '[]'}),
            [], [], run_filter=None)
        check('fv-4: without ?run all fields pour in; a scene that does '
              'not bind the class gets NO samples (defaultVisible False)',
              len(objs_none) == 7 + 3 * 30 * len(vg_list)
              and len(objs_other) == 7,
              f'{len(objs_none)} {len(objs_other)}')
    except ImportError as exc:
        check(f'fv-4: compile_3d importable ({exc})', False)

    items = cs.scene_page_items(DEV)
    check('fv-4: scene_page_items -> one sim-space-viewer item per scalar '
          'field with the run input selecting the field',
          len(items) == 3
          and all(i['componentProps']['componentName'] == 'sim-space-viewer'
                  and i['componentProps']['inputs']['simSpaceName']
                  == scene['name']
                  and i['componentProps']['inputs']['run']
                  == cf.run_ref(DEV, f)
                  for i, f in zip(items, cf.SCALAR_FIELDS)))

    passed = sum(1 for _l, ok in st._results if ok)
    total = len(st._results)
    print(f'\n{passed}/{total} checks passed')
    return passed == total


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
