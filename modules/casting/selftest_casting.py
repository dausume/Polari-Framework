"""
Selftest — cast-1: the inversion primitive.

Run from polari-framework/:
    python3 -m casting.selftest_casting

Covers: mold body derived as stock DIFFERENCE part with correct field
signs and grid volume; auto stock sizing; exact shrink scaling on both
the quadric and the primitive path; derived rows reconverge over
hand-edits with the drift named; honest refusals (missing part,
imported-mesh trap, non-volumetric family, bad allowance); cast-1b
wax-master feasibility (self-support, melt-margin blocker, thin-wall
blocker, print time from real waxprint condition rows); cast-2
OccupancyGrid (volume parity with shape_properties, flood-fill,
two-chamber connectivity), mesh voxelization (cube parity, exact
vertex-scale shrink), and the imported-part grid derivation
(ImportedCadObject resolution, importer-volume cross-check, named
absences).
"""

import json
import math
from types import SimpleNamespace

from casting.casting_seed import (
    SEED_CASTING_MODULES, SEED_MASTER_FEEDSTOCKS, SEED_MOLDS,
)
from casting.chain_analysis import (
    chain_report, shrink_compensation_report,
)
from casting.chain_seed import SEED_CASTING_STAGES, SEED_NESTING_CHAINS
from casting.mesh_voxelize import mesh_grid
from casting.pour_loading import exotherm_check, pour_loading_report
from pspp.ceramics_ladder import SEED_LADDER_RUNGS
from pspp.ceramics_samples import SEED_CERAMIC_SAMPLES
from casting.mold_geometry import derive_mold, scale_quadric_flat
from casting.voxel_grid import OccupancyGrid
from casting.wax_feasibility import (
    master_report, print_time_estimate, printable_criteria,
    wax_master_report, wax_self_support,
)
from mathshapes.shape_analysis import evaluate_point, shape_properties
from mathshapes.shape_seed import SEED_MATH_SHAPES
from waxprint.waxprint_seed import (
    SEED_ASSEMBLIES, SEED_CONDITIONS, SEED_FEEDSTOCKS,
)
from waxsupply.wax_seed import SEED_WAX_SOURCES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _table(seed_list):
    return {r['name']: SimpleNamespace(**r) for r in seed_list}


def _mgr(extra_molds=()):
    molds = [dict(m) for m in SEED_MOLDS] + [dict(m) for m in extra_molds]
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _table(SEED_MATH_SHAPES),
        'MoldDefinition': _table(molds),
        'MasterFeedstockDefinition': _table(SEED_MASTER_FEEDSTOCKS),
        'MoldNestingChain': _table(SEED_NESTING_CHAINS),
        'CastingStageDefinition': _table(SEED_CASTING_STAGES),
        'LadderRung': _table(SEED_LADDER_RUNGS),
        'CeramicSample': _table(SEED_CERAMIC_SAMPLES),
        'WaxSourceDefinition': _table(SEED_WAX_SOURCES),
        'WaxFeedstockDefinition': _table(SEED_FEEDSTOCKS),
        'PrinterAssemblyDefinition': _table(SEED_ASSEMBLIES),
        'PrintConditionDefinition': _table(SEED_CONDITIONS)})


if __name__ == '__main__':
    manager = _mgr()

    print('the inversion: unit-sphere mold')
    r = derive_mold(manager, 'demo-sphere-mold')
    check('derivation ok', r.get('ok'), r.get('error', ''))
    body = manager.objectTables['MathShapeDefinition'].get(
        r.get('bodyShape', ''))
    spec = json.loads(getattr(body, 'csg_json', '{}') or '{}')
    check('body = stock DIFFERENCE part',
          spec.get('op') == 'difference'
          and spec.get('shapes') == [r['stockShape'], 'unit-sphere'])
    stock = manager.objectTables['MathShapeDefinition'].get(
        r['stockShape'])
    sp = json.loads(getattr(stock, 'parameters_json', '{}'))
    check('auto stock = part AABB + 1cm margin each side (4×4×4 box)',
          sp.get('size') == [4.0, 4.0, 4.0]
          and sp.get('center') == [0.0, 0.0, 0.0])

    print('field signs (the negative is a negative)')
    inside_void = evaluate_point(manager, r['bodyShape'], 0.0, 0.0, 0.0)
    in_body = evaluate_point(manager, r['bodyShape'], 1.7, 1.7, 1.7)
    outside = evaluate_point(manager, r['bodyShape'], 5.0, 0.0, 0.0)
    check('cavity void (part interior) is NOT in the mold body',
          inside_void.get('ok') and inside_void.get('inside') is False)
    check('stock corner (outside part) IS mold body',
          in_body.get('ok') and in_body.get('inside') is True)
    check('beyond the stock is outside', outside.get('inside') is False)

    print('volumes (grid instrument)')
    vc = r.get('volumeCheck', {})
    sphere = 4.0 / 3.0 * math.pi
    check('volume cross-check ok', vc.get('ok'),
          f"dev={vc.get('relDeviation')}")
    check('body ≈ 64 − 4π/3',
          vc.get('bodyCm3') is not None
          and abs(vc['bodyCm3'] - (64.0 - sphere)) / 64.0 < 0.05,
          f"body={vc.get('bodyCm3')}")

    print('shrink allowance (primitive path, +2%)')
    r2 = derive_mold(manager, 'pot-frustum-mold')
    check('derivation ok', r2.get('ok'), r2.get('error', ''))
    check('scaled copy emitted', r2.get('scaledPartShape'))
    frustum = math.pi * 20.0 / 3.0 * (36.0 + 54.0 + 81.0)
    sc = shape_properties(manager, r2['scaledPartShape'])
    check('scaled part volume ≈ s³ × part volume (analytic primitive)',
          sc.get('ok')
          and abs(sc['volumeCm3'] - frustum * 1.02 ** 3) / frustum < 0.01,
          f"scaled={sc.get('volumeCm3')}")

    print('shrink allowance (quadric path, exact matrix transform)')
    q = json.loads('[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,-1]')
    q_scaled = scale_quadric_flat(q, 1.1)

    def _qval(q16, x, y, z):
        p = (x, y, z, 1.0)
        return sum(q16[4 * i + j] * p[i] * p[j]
                   for i in range(4) for j in range(4))
    check('scaled sphere surface sits at r=1.1 (F(1.1,0,0)=0)',
          abs(_qval(q_scaled, 1.1, 0.0, 0.0)) < 1e-9)
    check('r=1.05 inside, r=1.15 outside the scaled sphere',
          _qval(q_scaled, 1.05, 0, 0) < 0 < _qval(q_scaled, 1.15, 0, 0))

    print('derived rows reconverge — hand-edits are named, not kept')
    body.csg_json = json.dumps({'op': 'union',
                                'shapes': ['unit-sphere']})
    r3 = derive_mold(manager, 'demo-sphere-mold')
    recon = {c['name']: c['fields'] for c in r3.get('reconverged', [])}
    check('hand-edited body row was overwritten and named',
          'csg_json' in recon.get(r['bodyShape'], [])
          and r3.get('handEditNote'))
    spec_after = json.loads(body.csg_json)
    check('body restored to the derived difference',
          spec_after.get('op') == 'difference')

    print('honest refusals')
    bad = _mgr(extra_molds=[
        {'name': 'mesh-mold', 'part_shape_ref': 'bracket-v2',
         'part_source': 'imported-cad'},
        {'name': 'ghost-mold', 'part_shape_ref': 'no-such-shape',
         'part_source': 'mathshape'},
        {'name': 'winding-mold', 'part_shape_ref': 'a-winding',
         'part_source': 'mathshape'},
        {'name': 'neg-mold', 'part_shape_ref': 'unit-sphere',
         'part_source': 'mathshape', 'shrink_allowance_pct': -120.0},
    ])
    bad.objectTables['MathShapeDefinition']['a-winding'] = (
        SimpleNamespace(name='a-winding', family='winding'))
    mesh = derive_mold(bad, 'mesh-mold')
    check('imported-cad ref resolving nothing refuses',
          not mesh.get('ok')
          and 'names no imported-mesh' in mesh.get('error', ''))
    check('missing part refuses',
          not derive_mold(bad, 'ghost-mold').get('ok'))
    wind = derive_mold(bad, 'winding-mold')
    check('non-volumetric family refuses as a named absence',
          not wind.get('ok') and 'winding' in wind.get('error', ''))
    check('nonsensical shrink refuses',
          not derive_mold(bad, 'neg-mold').get('ok'))
    check('unknown mold refuses',
          not derive_mold(bad, 'nope').get('ok'))

    print('cast-1b: wax master feasibility')
    rep = wax_master_report(manager, 'demo-sphere-mold')
    check('report ok + feasible verdict', rep.get('ok')
          and rep.get('verdict') == 'feasible',
          '; '.join(rep.get('blockers', [])) or rep.get('error', ''))
    check("waxsupply's own mold ranking picks the wax (carnauba)",
          rep.get('wax') == 'carnauba')
    sup = rep.get('selfSupport', {})
    # 4cm body of ~997 kg/m³ wax: σ = ρgh ≈ 0.39 kPa vs 2 MPa floor.
    check('self-weight utilization is tiny for a 4cm mold',
          sup.get('ok') and 0.0 < sup.get('utilization', 1.0) < 0.01,
          f"σ={sup.get('baseStressKpa')}kPa "
          f"u={sup.get('utilization')}")
    check('density came from the bound feedstock row, not the prior',
          'WaxFeedstockDefinition' in sup.get('densitySource', ''))
    t = rep.get('printTime', {})
    # body ≈ 59.75 cm³ at 0.44×0.2×30 mm³/s ≈ 9.5 cm³/h ⇒ ~8.5h ×1.35
    check('print time plausible (5–15h for the demo mold)',
          t.get('ok') and 5.0 < (t.get('estimatedHours') or 0) < 15.0,
          f"{t.get('estimatedHours')}h at "
          f"{t.get('depositionRateCm3H')}cm³/h")
    check('overhead is a NAMED prior', 'prior' in t.get(
        'overheadClaim', ''))
    check('wall spans plenty of beads (10mm / 0.44mm)',
          (rep.get('wallBeads') or 0) > 20)

    print('cast-1b: blockers + refusals')
    hot = wax_self_support(manager, 'demo-sphere-mold',
                           wax_source_name='carnauba', ambient_c=80.0)
    check('ambient at melt −5°C guard blocks, naming the melt',
          not hot.get('ok')
          and any('melt' in b for b in hot.get('blockers', [])))
    jojoba = wax_self_support(manager, 'demo-sphere-mold',
                              wax_source_name='jojoba')
    check('liquid wax (jojoba, melt 10°C) blocks at room temp',
          not jojoba.get('ok') and jojoba.get('blockers'))
    check('wax without a strength prior refuses, naming the knob',
          'overrides' in wax_self_support(
              manager, 'demo-sphere-mold',
              wax_source_name='soy-wax').get('error', ''))
    thin = _mgr(extra_molds=[
        {'name': 'thin-mold', 'part_shape_ref': 'unit-sphere',
         'part_source': 'mathshape', 'stock_margin_cm': 0.05,
         'shrink_allowance_pct': 0.0}])
    derive_mold(thin, 'thin-mold')
    thin_rep = wax_master_report(thin, 'thin-mold')
    check('0.5mm wall blocks (under 2 beads across)',
          thin_rep.get('verdict') == 'blocked'
          and any('beads' in b for b in thin_rep.get('blockers', [])))
    check('missing condition row refuses',
          not print_time_estimate(
              manager, 'demo-sphere-mold--body', 'no-such').get('ok'))
    check('build envelope + CNC named as gaps, not silently passed',
          sum(1 for g in rep.get('gaps', [])
              if 'envelope' in g or 'CNC' in g) == 2)

    print('cast-2: OccupancyGrid — volume parity + connectivity')
    grid = OccupancyGrid.from_shape(manager, 'pot-with-holes',
                                    resolution=32)
    props = shape_properties(manager, 'pot-with-holes', resolution=32)
    check('grid volume matches shape_properties (same instrument)',
          isinstance(grid, OccupancyGrid) and props.get('ok')
          and abs(grid.volume_cm3() - props['volumeCm3'])
          / props['volumeCm3'] < 0.01,
          f"grid={grid.volume_cm3():.1f} "
          f"props={props.get('volumeCm3')}")
    check('from_shape refuses an imported mesh (the trap stays shut)',
          'mesh_voxelize' in (OccupancyGrid.from_shape(
              SimpleNamespace(objectTables={'MathShapeDefinition': {
                  'm': SimpleNamespace(name='m', family='imported-mesh')
              }}), 'm') or {}).get('error', ''))

    two = _mgr(extra_molds=[
        {'name': 'two-sphere-mold', 'part_shape_ref': 'two-spheres',
         'part_source': 'mathshape', 'stock_margin_cm': 1.0,
         'shrink_allowance_pct': 0.0}])
    shapes = two.objectTables['MathShapeDefinition']
    shapes['sphere-a'] = SimpleNamespace(
        name='sphere-a', family='primitive', primitive_kind='sphere',
        parameters_json=json.dumps({'radius': 1.0,
                                    'center': [0.0, 0.0, 0.0]}))
    shapes['sphere-b'] = SimpleNamespace(
        name='sphere-b', family='primitive', primitive_kind='sphere',
        parameters_json=json.dumps({'radius': 1.0,
                                    'center': [4.0, 0.0, 0.0]}))
    shapes['two-spheres'] = SimpleNamespace(
        name='two-spheres', family='csg', primitive_kind='',
        quadric_matrix_json='', bounds_json='', parameters_json='{}',
        csg_json=json.dumps({'op': 'union',
                             'shapes': ['sphere-a', 'sphere-b']}))
    r2s = derive_mold(two, 'two-sphere-mold')
    body_grid = OccupancyGrid.from_shape(two, r2s['bodyShape'],
                                         resolution=40)
    cavities = body_grid.complement().connected_components()
    check('two-chamber mold: complement finds exactly 2 cavities',
          len(cavities) == 2, f'found {len(cavities)}')
    check('the two cavities have equal volume (same spheres)',
          len(cavities) == 2
          and abs(len(cavities[0]) - len(cavities[1]))
          / len(cavities[0]) < 0.05)
    seed_a = body_grid.point_cell(0.0, 0.0, 0.0)
    reached = body_grid.complement().flood_fill((seed_a,))
    check('flood fill from chamber A never reaches chamber B',
          seed_a is not None and reached == set(cavities[0])
          or reached == set(cavities[1]))

    print('cast-2: mesh voxelization (the FreeCAD bridge)')
    cube_pts = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]]
    cube_tris = [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
                 [0, 1, 5], [0, 5, 4], [3, 2, 6], [3, 6, 7],
                 [0, 3, 7], [0, 7, 4], [1, 2, 6], [1, 6, 5]]
    cube_shape = SimpleNamespace(
        name='cube-shape', family='imported-mesh',
        parameters_json=json.dumps({'meshPoints': cube_pts,
                                    'triangles': cube_tris}),
        bounds_json=json.dumps([[-1, 1], [-1, 1], [-1, 1]]))
    mg = mesh_grid(cube_shape, resolution=24)
    check('cube mesh voxelizes to ~8 cm³',
          mg.get('ok')
          and abs(mg['grid'].volume_cm3() - 8.0) / 8.0 < 0.05,
          f"{mg.get('ok') and mg['grid'].volume_cm3():.3f}")
    mg_s = mesh_grid(cube_shape, resolution=24, scale=1.1)
    check('vertex-scale shrink is exact (×1.1 ⇒ ×1.331 volume)',
          mg_s.get('ok')
          and abs(mg_s['grid'].volume_cm3() - 8.0 * 1.331)
          / (8.0 * 1.331) < 0.05,
          f"{mg_s.get('ok') and mg_s['grid'].volume_cm3():.3f}")
    check('watertightness named as a gap, not assumed silently',
          any('watertight' in g.lower() for g in mg.get('gaps', [])))

    print('cast-2: imported-part mold derivation (grid path)')
    imp = _mgr(extra_molds=[
        {'name': 'bracket-mold', 'part_shape_ref': 'bracket-import',
         'part_source': 'imported-cad', 'stock_margin_cm': 1.0,
         'shrink_allowance_pct': 0.0}])
    imp.objectTables['MathShapeDefinition']['bracket-shape'] = (
        SimpleNamespace(
            name='bracket-shape', family='imported-mesh',
            parameters_json=cube_shape.parameters_json,
            bounds_json=cube_shape.bounds_json))
    imp.objectTables['ImportedCadObject'] = {
        'bracket-import': SimpleNamespace(
            name='bracket-import', shape_name='bracket-shape',
            volume_cm3=8.0)}
    ri = derive_mold(imp, 'bracket-mold')
    check('imported part derives on the grid path',
          ri.get('ok') and ri.get('mode') == 'grid',
          ri.get('error', ''))
    check('resolved via the ImportedCadObject name',
          ri.get('part') == 'bracket-shape')
    check('body ≈ stock − part (64 − 8)',
          abs((ri.get('bodyVolumeCm3') or 0) - 56.0) / 56.0 < 0.05,
          f"body={ri.get('bodyVolumeCm3')}")
    check('grid part volume cross-checks the importer volume',
          (ri.get('volumeCheck') or {}).get('ok') is True,
          f"dev={(ri.get('volumeCheck') or {}).get('relDeviation')}")
    check('no CSG body row — carried as a NAMED absence',
          ri.get('bodyShape') == ''
          and any('named absence' in g for g in ri.get('gaps', [])))
    rep_i = wax_master_report(imp, 'bracket-mold')
    check('wax report times the GRID body volume',
          rep_i.get('ok') and rep_i.get('verdict') == 'feasible'
          and (rep_i.get('printTime') or {}).get('ok'),
          f"{(rep_i.get('printTime') or {}).get('estimatedHours')}h")
    imp.objectTables['MathShapeDefinition']['bracket-shape'] \
       .parameters_json = '{}'
    bare = derive_mold(imp, 'bracket-mold')
    check('mesh without a cached mesh refuses, naming the re-import',
          not bare.get('ok')
          and 'no cached mesh' in bare.get('error', ''))
    trap = _mgr(extra_molds=[
        {'name': 'trap-mold', 'part_shape_ref': 'cube-shape',
         'part_source': 'mathshape'}])
    trap.objectTables['MathShapeDefinition']['cube-shape'] = cube_shape
    tr = derive_mold(trap, 'trap-mold')
    check("imported mesh under part_source='mathshape' refuses "
          '(silent-outside trap named)',
          not tr.get('ok') and 'EMPTY' in tr.get('error', ''))

    print('cast-2b: multi-feedstock masters (Dustin 2026-08-05)')
    mr = master_report(manager, 'demo-sphere-mold')
    check('default feedstock = the CORE natural local wax',
          mr.get('ok') and mr.get('feedstock') == 'carnauba-pellet'
          and mr.get('priority') == 'core' and mr.get('renewable'))
    check('core wax feasible on the auger route',
          mr.get('verdict') == 'feasible'
          and mr.get('route') == 'auger-pellet-print'
          and (mr.get('printTime') or {}).get('ok'))
    voron = master_report(manager, 'demo-sphere-mold',
                          feedstock_name='wax-filament-fdm')
    check('commercial wax filament prints on a standard Voron',
          voron.get('ok') and voron.get('verdict') == 'feasible'
          and (voron.get('printTime') or {}).get('machine', ''
               ).startswith('standard Voron'),
          f"{(voron.get('printTime') or {}).get('estimatedHours')}h")
    pla = master_report(manager, 'demo-sphere-mold',
                        feedstock_name='pla-filament')
    check('PLA mold feasible, faster than wax filament (80 mm/s)',
          pla.get('verdict') == 'feasible'
          and (pla.get('printTime') or {}).get('estimatedHours', 99)
          < (voron.get('printTime') or {}).get('estimatedHours', 0))
    check('PLA removal = burn-out with the thermal gate deferred to '
          'cast-3', (pla.get('removal') or {}).get('route')
          == 'burn-out'
          and 'cast-3' in (pla.get('removal') or {}).get('gate', ''))
    cnc = master_report(manager, 'demo-sphere-mold',
                        feedstock_name='machinable-wax-block')
    check('machinable wax: feasible via CNC, time a NAMED absence',
          cnc.get('verdict') == 'feasible' and cnc.get('route') == 'cnc'
          and not (cnc.get('printTime') or {}).get('ok')
          and any('feeds/speeds' in g for g in cnc.get('gaps', [])))
    check('wrong route for a feedstock blocks, naming its routes',
          any('not a make-route' in b for b in master_report(
              manager, 'demo-sphere-mold',
              feedstock_name='machinable-wax-block',
              route='fdm-voron').get('blockers', [])))
    crit = printable_criteria(_table(SEED_MASTER_FEEDSTOCKS)[
        'wax-filament-fdm'], ambient_c=42.0)
    check('printable criteria fail loudly (wax filament at 42°C '
          'ambient vs soften 45)', not crit.get('ok')
          and any(not c['ok'] for c in crit['checks']))
    check('unknown feedstock refuses',
          not master_report(manager, 'demo-sphere-mold',
                            feedstock_name='nope').get('ok'))
    check('commercial rows carry sourcing tier + non-renewable '
          'honestly',
          all(f['accessibility_tier'] == 'common-industrial'
              and not f['renewable']
              for f in SEED_MASTER_FEEDSTOCKS
              if f['priority'] == 'supported'))

    print('cast-2c: geopolymer pour loading (mold-collapse gate)')
    pour = pour_loading_report(manager, 'demo-sphere-mold')
    check('gravity geopolymer pour into the wax mold survives',
          pour.get('ok') and pour.get('verdict') == 'feasible',
          '; '.join(pour.get('blockers', [])))
    check('hydrostatic peak = ρgh (≈0.43 kPa for a 2cm cavity)',
          abs((pour.get('pressure') or {}).get('hydrostaticPeakKpa',
                                               0) - 0.432) < 0.01)
    check('wall bending carries model + utilization',
          (pour.get('wallBending') or {}).get('utilization', 1) < 0.01
          and 'plate' in (pour.get('wallBending') or {}).get('model',
                                                             ''))
    check('slurry mass computed (≈9.2 g in the sphere cavity)',
          abs((pour.get('cavity') or {}).get('massKg', 0) - 0.0092)
          < 0.001)
    check('exotherm vs carnauba soften = a 2°C FINDING, not silence',
          (pour.get('exotherm') or {}).get('marginC') == 2.0
          and any('exotherm' in f for f in pour.get('findings', [])))
    pla_pour = pour_loading_report(manager, 'demo-sphere-mold',
                                   feedstock_name='pla-filament')
    check('PLA mold BLOCKS: cure exotherm 70°C > Tg 60°C (softens '
          'from the inside)', pla_pour.get('verdict') == 'blocked'
          and any('FROM THE INSIDE' in b
                  for b in pla_pour.get('blockers', [])))
    inj = pour_loading_report(manager, 'demo-sphere-mold',
                              inject_pressure_kpa=50.0)
    check('injection reports required clamping against uplift',
          (inj.get('uplift') or {}).get('forceN', 0) > 0
          and any('clamping' in f for f in inj.get('findings', [])))
    tall = _mgr(extra_molds=[
        {'name': 'tall-thin-mold', 'part_shape_ref': 'frustum-pot',
         'part_source': 'mathshape', 'stock_margin_cm': 0.5,
         'shrink_allowance_pct': 0.0}])
    derive_mold(tall, 'tall-thin-mold')
    collapse = pour_loading_report(tall, 'tall-thin-mold')
    check('20cm pour against a 5mm wax wall COLLAPSES, naming the '
          'knob', collapse.get('verdict') == 'blocked'
          and any('collapses' in b and 'stock_margin_cm' in b
                  for b in collapse.get('blockers', [])),
          f"σ={(collapse.get('wallBending') or {}).get('stressKpa')}"
          f"kPa")
    check('cure outside the measured 40–85°C refuses to extrapolate',
          'refusal' in exotherm_check(
              _table(SEED_MASTER_FEEDSTOCKS)['carnauba-pellet'],
              cure_temp_c=25.0))
    check('unknown cast material refuses, listing what is known',
          'knownMaterials' in pour_loading_report(
              manager, 'demo-sphere-mold', cast_material='lava'))
    check('water bench-test suggested before a real mix',
          'water-test' in pour.get('note', ''))

    print('cast-3: chain parity — derived, nowhere stored')
    c1 = chain_report(manager, 'chain-wax-geopolymer')
    check('1 inversion ⇒ wax master is NEGATIVE (the wax IS the '
          'mold)', (c1.get('parity') or {}).get('waxMasterParity')
          == 'negative'
          and 'IS the mold' in c1['parity']['meaning'])
    c2 = chain_report(manager, 'chain-wax-gp-clay-fired')
    check('2 inversions + a conversion ⇒ wax is a POSITIVE (firing '
          'does not flip)',
          (c2.get('parity') or {}).get('waxMasterParity') == 'positive'
          and c2['parity']['invertingStages'] == 2
          and c2['parity']['conversionStages'] == 1)
    check('parity is not a seed field — nothing to hand-set',
          all('wax_master_parity' not in row and 'parity' not in row
              for row in SEED_NESTING_CHAINS))

    print('cast-3: thermal ordering — the clay-and-fire chain')
    check('clay chain FEASIBLE with the geopolymer SACRIFICED loudly',
          c2.get('verdict') == 'feasible'
          and any('SACRIFICED' in f for f in c2.get('findings', [])))
    check('every stage record carries pair + basis + margin',
          all('moldCeilingC' in s and 'processTempC' in s
              and 'marginC' in s for s in c2.get('stages', [])))
    check('firing checked against a real furnace rung',
          any((s.get('furnace') or {}).get('ok') is True
              for s in c2.get('stages', [])))
    hot = _table(SEED_CASTING_STAGES)
    hot['st-wg-1-geopolymer'].cure_temp_c = 60.0
    hotm = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=hot))
    ch = chain_report(hotm, 'chain-wax-geopolymer')
    check('cure at 60°C BLOCKS: exotherm 100°C vs carnauba 72°C, '
          'pair named', ch.get('verdict') == 'blocked'
          and any('100' in b and 'carnauba' in b
                  for b in ch.get('blockers', [])),
          '; '.join(ch.get('blockers', []))[:90])
    keep = _table(SEED_CASTING_STAGES)
    keep['st-wgc-3-fire'].mold_disposable = False
    km = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=keep))
    check('NON-disposable geopolymer at 1000°C firing blocks',
          chain_report(km, 'chain-wax-gp-clay-fired').get('verdict')
          == 'blocked')
    slip = _table(SEED_CASTING_STAGES)
    slip['st-wgc-2-press-clay'].fill_method = 'slip-cast'
    sm = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=slip))
    check('slip-casting into geopolymer REFUSED (capillarity rule)',
          any('capillarity' in b for b in chain_report(
              sm, 'chain-wax-gp-clay-fired').get('blockers', [])))
    hotfire = _table(SEED_CASTING_STAGES)
    hotfire['st-wgc-3-fire'].process_temp_c = 1800.0
    hm = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=hotfire))
    check('1800°C firing blocks on the furnace rung (best 1700)',
          any('furnace rung' in b and '1700' in b for b in
              chain_report(hm, 'chain-wax-gp-clay-fired'
                           ).get('blockers', [])))
    steel = _table(SEED_CASTING_STAGES)
    steel['st-wg-1-geopolymer'].cast_material_ref = 'molten-steel'
    stm = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=steel))
    check('molten metal blocks naming the ABSENT thermal table',
          any('CastingMaterialThermalProfile' in b for b in
              chain_report(stm, 'chain-wax-geopolymer'
                           ).get('blockers', [])))
    check('chain without stages refuses',
          not chain_report(SimpleNamespace(objectTables=dict(
              manager.objectTables, CastingStageDefinition={})),
              'chain-wax-geopolymer').get('ok'))

    print('cast-3: shrink compensation — the two-pass loop')
    sc = shrink_compensation_report(manager,
                                    'chain-wax-gp-clay-fired')
    # 0.99 (geopolymer ×2 stages? no: two CAST stages: geopolymer
    # 1% + clay 11%) → 0.99 × 0.89 = 0.8811; oversize ×1.1349.
    check('cumulative final scale = 0.99 × 0.89 (firing not double-'
          'counted)', abs(sc.get('expectedFinalScale', 0) - 0.8811)
          < 0.0005, f"{sc.get('expectedFinalScale')}")
    check('recommended master oversize ≈ +13.5%, NOT auto-applied',
          abs((sc.get('compensation') or {}).get('recommendedPct', 0)
              - 13.49) < 0.1
          and not sc['compensation']['applied'])
    check('pass one is DELIBERATELY uncompensated',
          'DELIBERATELY' in sc.get('passOne', ''))
    check('warp is a named gap',
          any('warp' in g.lower() for g in sc.get('gaps', [])))
    measured = _table(SEED_CASTING_STAGES)
    measured['st-wgc-2-press-clay'].measured_shrink_pct = 8.0
    mm = SimpleNamespace(objectTables=dict(
        manager.objectTables, CastingStageDefinition=measured))
    scm = shrink_compensation_report(mm, 'chain-wax-gp-clay-fired')
    check('MEASURED shrink replaces the prior (8% ⇒ scale 0.9108)',
          abs(scm.get('expectedFinalScale', 0) - 0.99 * 0.92)
          < 0.0005
          and any('MEASURED' in s['basis']
                  for s in scm.get('stages', [])))
    sca = shrink_compensation_report(manager, 'chain-wax-geopolymer',
                                     apply=True)
    check('apply=True writes the mold knob and re-derives (×1.0101)',
          (sca.get('compensation') or {}).get('applied')
          and abs(sca['compensation']['derivation']['scaleFactor']
                  - 1.0101) < 0.0005)

    print('module identity')
    check('PolariModule row present + owns MoldDefinition',
          SEED_CASTING_MODULES[0]['name'] == 'Casting-Mold-Nesting'
          and 'MoldDefinition' in json.loads(
              SEED_CASTING_MODULES[0]['manifest_json'])['objects'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
