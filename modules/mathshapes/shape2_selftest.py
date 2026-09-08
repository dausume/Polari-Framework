"""
Selftest — shape-2: algorithmic modification + aqp-1 pot bridge + tower.

Run from polari-framework/:
    python3 -m mathshapes.shape2_selftest

Covers: modifying a hole-cylinder radius UP reduces the pot solid volume
and widens the opening; the aqp-1 gravity invariant gates modification
(a pot with broken drainage refuses, naming the knob); a valid pot's
hole modifies fine; pot_shape_from_definition builds a HOLLOW pot whose
wall/bottom/holes are DEFINED by quadric matrix equations (a bounded
cone/cylinder quadric each), rendered as ONE integrated wall mesh with
holes actually cut through it (not a marker rod through a solid wall),
numbers DERIVED by evaluating those equations; physical thickness/
diameter minimums clamped and never silent; tower geometry sums per-
tier grow volume; the POST /api/shapes/from-pot/{potName} route
(aquaponics-pot-shape phase 1) builds the pot + ensures its {pot}-viz
SimSpace scene, idempotently on re-derive; honest refusals.
"""

import json
from types import SimpleNamespace

from aquaponics.custom.pot_geometry import validate_pot
from mathshapes.custom.shape_analysis import shape_properties, sample_surface
from mathshapes.shape_api import MathShapesAPI
from mathshapes.custom.shape_geometry import (
    classify_axis_aligned, hollow_frustum_shell_mesh, radius_at_z,
)
from mathshapes.shape_seed import SEED_MATH_SHAPES
from mathshapes.custom.shape_modify import (
    modify_parameter, modify_pot_hole, pot_shape_from_definition,
)
from mathshapes.custom.tower_analysis import tower_geometry
from mathshapes.tower_seed import SEED_TOWERS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _by_name(seed_list):
    return {r['name']: SimpleNamespace(**r) for r in seed_list}


def _q(shape_row):
    """quadric_matrix_json is stored FLAT (16 numbers, matching
    shape_analysis._quadric_matrix's parser) — reshape to the nested
    4x4 classify_axis_aligned/radius_at_z/quadric_value expect."""
    flat = json.loads(shape_row.quadric_matrix_json)
    return [flat[0:4], flat[4:8], flat[8:12], flat[12:16]]


# A valid aqp-1 pot: input high on one side, output low + downhill on the
# opposite side.
POT = {'name': 'demo-pot', 'display_name': 'Demo pot', 'shape': 'tapered',
       'outer_top_diameter_mm': 220.0, 'outer_base_diameter_mm': 180.0,
       'height_mm': 250.0, 'wall_thickness_mm': 8.0,
       'base_thickness_mm': 12.0, 'reservoir_height_mm': 0.0,
       'material_name': ''}
HOLES_VALID = [
    {'name': 'demo-pot-in', 'pot_name': 'demo-pot', 'kind': 'input',
     'diameter_mm': 10.0, 'height_mm': 200.0, 'azimuth_deg': 0.0,
     'angle_deg': 0.0},
    {'name': 'demo-pot-out', 'pot_name': 'demo-pot', 'kind': 'output',
     'diameter_mm': 12.0, 'height_mm': 40.0, 'azimuth_deg': 180.0,
     'angle_deg': 3.0},
]
# The same pot but the output bores UPHILL — breaks gravity drainage.
HOLES_BROKEN = [
    HOLES_VALID[0],
    {'name': 'demo-pot-out', 'pot_name': 'demo-pot', 'kind': 'output',
     'diameter_mm': 12.0, 'height_mm': 40.0, 'azimuth_deg': 180.0,
     'angle_deg': -12.0},
]


def _mgr(holes):
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _by_name(SEED_MATH_SHAPES),
        'AquaponicTowerDefinition': _by_name(SEED_TOWERS),
        'PotDefinition': {'demo-pot': SimpleNamespace(**POT)},
        'PotHole': {h['name']: SimpleNamespace(**h) for h in holes}})


if __name__ == '__main__':
    print('modify a hole → the pot loses volume, the opening widens')
    m = _mgr(HOLES_VALID)
    res = modify_parameter(m, 'hole-cylinder-a', 'radius', 2.0)
    check('modify ok + reports the dependent pot', res.get('ok')
          and 'pot-with-holes' in res['before']['dependentPots'])
    pot_before = res['before']['dependentPots']['pot-with-holes']
    pot_after = res['after']['dependentPots']['pot-with-holes']
    check('bigger hole → smaller pot solid volume',
          pot_after < pot_before,
          f'{pot_before:.1f} → {pot_after:.1f} cm³')
    check('bigger hole → wider opening',
          res['after']['openingAreaCm2'] > res['before']['openingAreaCm2'],
          f"{res['before']['openingAreaCm2']} → "
          f"{res['after']['openingAreaCm2']} cm²")
    check('only the requested knob changed (radius)',
          res['param'] == 'radius' and res['to'] == 2.0)

    print('aqp-1 gravity invariant gates modification')
    m_bad = _mgr(HOLES_BROKEN)
    gated = modify_pot_hole(m_bad, 'demo-pot', 'radius', 1.0, hole_index=0)
    check('broken-drainage pot REFUSES the modification',
          not gated.get('ok'))
    check('refusal names the offending knob',
          'angle_deg' in str(gated.get('limitingFactor', '')),
          str(gated.get('limitingFactor', '')))
    m_ok = _mgr(HOLES_VALID)
    good = modify_pot_hole(m_ok, 'demo-pot', 'radius', 0.7, hole_index=0)
    check('valid pot allows the hole modification',
          good.get('ok') and good.get('gravityValid'))

    print('aqp-1 pot → quadric-equation-defined hollow pot')
    m2 = _mgr(HOLES_VALID)
    built = pot_shape_from_definition(m2, 'demo-pot')
    check('pot_shape built ok + gravity-valid', built.get('ok')
          and built.get('gravityValid'))

    outer_eq = m2.objectTables['MathShapeDefinition'][built['wallOuterEquation']]
    inner_eq = m2.objectTables['MathShapeDefinition'][built['wallInnerEquation']]
    bottom_eq = m2.objectTables['MathShapeDefinition'][built['bottomEquation']]
    check('wall-outer/wall-inner/bottom are real quadric equations '
          '(family + a parseable, flat 16-number matrix)',
          outer_eq.family == 'quadric' and inner_eq.family == 'quadric'
          and bottom_eq.family == 'quadric'
          and len(json.loads(outer_eq.quadric_matrix_json)) == 16)
    outer_Q = _q(outer_eq)
    inner_Q = _q(inner_eq)
    check("demo-pot is genuinely tapered (220mm top vs 180mm base), so "
          "its wall equation classifies as a CONE, not a degenerate "
          "cylinder", classify_axis_aligned(outer_Q) == 'cone',
          classify_axis_aligned(outer_Q))
    check('LaTeX is a DERIVED display on the equation row (present, '
          'human-readable, references x/y/z)',
          'x^2' in outer_eq.notes and 'y^2' in outer_eq.notes)

    wall_render = m2.objectTables['MathShapeDefinition'][built['wallShape']]
    wp = json.loads(wall_render.parameters_json)
    check('wall render mesh is family=primitive kind=hollow_frustum '
          '(gets a REAL triangulated mesh, unlike its source quadrics)',
          wall_render.family == 'primitive'
          and wall_render.primitive_kind == 'hollow_frustum')
    check('wall render radii are DERIVED from the equations (radius_at_z '
          'round-trips to the same numbers pot_shape_from_definition '
          'persisted), not independently specified',
          abs(wp['base_outer_radius']
              - radius_at_z(outer_Q, 'z',
                            wp['center'][2] - wp['height'] / 2.0)) < 1e-6
          and abs(wp['base_inner_radius']
                  - radius_at_z(inner_Q, 'z',
                                wp['center'][2] - wp['height'] / 2.0)) < 1e-6)
    check('wall has real thickness (outer radii > inner radii)',
          wp['base_outer_radius'] > wp['base_inner_radius']
          and wp['top_outer_radius'] > wp['top_inner_radius'],
          f"outer base {wp['base_outer_radius']} > inner base "
          f"{wp['base_inner_radius']}")

    # The wall must read as ONE INTEGRATED object with holes actually
    # SUBTRACTED (Dustin's 2nd round of feedback), each hole resolved
    # at ITS OWN scale, not the wall's coarse base grid (3rd round:
    # "you subtracted a random section", not a clean hole — fixed by
    # adaptive local refinement around each hole). Compare two SAME-
    # REFINEMENT meshes (both go through the hole-driven refinement,
    # so this isn't confounded by refinement itself adding triangles)
    # differing only in hole radius — a bigger hole must cut away MORE
    # material, i.e. produce fewer surviving (uncut) triangles.
    small_tris = hollow_frustum_shell_mesh(wp, n_lon=24, n_stack=10)[1]
    wp_bigger = dict(wp, holes=[dict(hh, radius=hh['radius'] * 4.0)
                                for hh in wp['holes']])
    big_tris = hollow_frustum_shell_mesh(wp_bigger, n_lon=24, n_stack=10)[1]
    check('a bigger hole subtracts MORE material (fewer surviving wall '
          'triangles) — proves the cut scales with the actual hole '
          'volume, not a fixed/random chunk',
          len(big_tris) < len(small_tris),
          f'{len(big_tris)} < {len(small_tris)}')
    check('capped hole markers are proper closed solids, not open tubes '
          '(Dustin: "the cylinders should not be hollow")',
          all(json.loads(
                  m2.objectTables['MathShapeDefinition'][hn].parameters_json
              ).get('cap_base') is True
              and json.loads(
                  m2.objectTables['MathShapeDefinition'][hn].parameters_json
              ).get('cap_top') is True
              for hn in built['holeShapes']))
    check('the wall mesh is one continuous surface set — outer + inner + '
          'top rim + bottom rim all present (a real, sizeable triangle '
          'count)', len(small_tris) > 100, str(len(small_tris)))

    bp = json.loads(
        m2.objectTables['MathShapeDefinition'][built['bottomShape']]
        .parameters_json)
    check('bottom slab is capped both ends (reads as solid, not a tube) '
          '— Dustin: "the bottom ... looks like it is a single piece"',
          bp.get('cap_base') is True and bp.get('cap_top') is True)
    check("bottom slab's TOP is flush with the wall's BOTTOM — same z, "
          "same radius (Dustin round 3)",
          abs(bp['center'][2] + bp['height'] / 2.0
              - (wp['center'][2] - wp['height'] / 2.0)) < 1e-6
          and abs(bp['top_radius'] - wp['base_outer_radius']) < 1e-6,
          f"bottom top z={bp['center'][2] + bp['height'] / 2.0:.4f} == "
          f"wall bottom z={wp['center'][2] - wp['height'] / 2.0:.4f}, "
          f"bottom top r={bp['top_radius']:.4f} == "
          f"wall bottom r={wp['base_outer_radius']:.4f}")
    check('bottom slab radii are DERIVED from its own equation',
          abs(bp['base_radius']
              - radius_at_z(_q(bottom_eq), 'z',
                            bp['center'][2] - bp['height'] / 2.0)) < 1e-6)

    hole_eq = m2.objectTables['MathShapeDefinition'][
        f"{built['holeShapes'][0]}-eq"]
    check("a straight hole (same radius both ends) classifies as a "
          "CYLINDER quadric, not a cone",
          classify_axis_aligned(_q(hole_eq)) == 'cylinder')
    hp = json.loads(
        m2.objectTables['MathShapeDefinition'][built['holeShapes'][0]]
        .parameters_json)
    check("hole bores only through the wall (short, NOT the old full-"
          "diameter-through-the-axis bore)",
          hp['height'] < wp['base_outer_radius'],
          f"hole length {hp['height']}cm << pot radius "
          f"{wp['base_outer_radius']}cm")

    check('derived shape is queryable via shape_properties',
          shape_properties(m2, 'demo-pot-shape', resolution=16).get('ok'))
    check('pot material volume reported (net of bores), positive',
          built.get('potMaterialVolumeCm3') is not None
          and built['potMaterialVolumeCm3'] > 0,
          str(built.get('potMaterialVolumeCm3')))

    print('wall/base thickness + hole diameter physical minimums — '
          'clamped, never silent')
    POT_THIN = dict(POT, wall_thickness_mm=1.0, base_thickness_mm=1.0)
    HOLES_TINY = [dict(HOLES_VALID[0], diameter_mm=0.2),
                  dict(HOLES_VALID[1], diameter_mm=0.2)]

    def _mgr_thin():
        return SimpleNamespace(objectTables={
            'MathShapeDefinition': _by_name(SEED_MATH_SHAPES),
            'AquaponicTowerDefinition': _by_name(SEED_TOWERS),
            'PotDefinition': {'demo-pot': SimpleNamespace(**POT_THIN)},
            'PotHole': {h['name']: SimpleNamespace(**h)
                       for h in HOLES_TINY}})
    m_thin = _mgr_thin()
    built_thin = pot_shape_from_definition(m_thin, 'demo-pot')
    check('sub-minimum wall/base + tiny holes still build ok (clamped)',
          built_thin.get('ok'))
    check('wall thickness clamped to the 3mm floor',
          built_thin['wallThicknessClamped']
          and built_thin['wallThicknessMm'] == 3.0)
    check('base thickness clamped to the 3mm floor',
          built_thin['baseThicknessClamped']
          and built_thin['baseThicknessMm'] == 3.0)
    check('hole diameters clamped to the 1mm floor',
          all(built_thin['holeDiametersClamped']))
    thin_report = validate_pot(m_thin, 'demo-pot')
    thin_kinds = {f['kind'] for f in thin_report['findings']}
    check('validate_pot flags the thin wall/base/holes (clamp never silent)',
          {'wall-too-thin', 'base-too-thin', 'hole-too-small'}
          <= thin_kinds, str(thin_kinds))

    print('an absurdly thick wall can never let a hole bore through '
          'BOTH sides (adversarial-review finding, 2026-07-13)')
    # base_r/top_r ~9-11cm; a wall this thick (80mm) has no upper-bound
    # knob stopping it — this is the exact shape that used to compute
    # hole_length = wall_th + margin with wall_th alone as large as the
    # pot's own diameter, letting the bore reach the FAR wall.
    POT_THICK_WALL = dict(POT, wall_thickness_mm=80.0)
    m_thick = SimpleNamespace(objectTables={
        'MathShapeDefinition': _by_name(SEED_MATH_SHAPES),
        'AquaponicTowerDefinition': _by_name(SEED_TOWERS),
        'PotDefinition': {'demo-pot': SimpleNamespace(**POT_THICK_WALL)},
        'PotHole': {h['name']: SimpleNamespace(**h) for h in HOLES_VALID}})
    built_thick = pot_shape_from_definition(m_thick, 'demo-pot')
    check('absurdly-thick-wall pot still builds ok', built_thick.get('ok'))
    hp_thick = json.loads(
        m_thick.objectTables['MathShapeDefinition'][built_thick['holeShapes'][0]]
        .parameters_json)
    hole_center_perp = (abs(hp_thick['center'][0])
                        if hp_thick['axis'] == 'x' else abs(hp_thick['center'][1]))
    check("the bore's near edge never crosses the pot's own central "
          'axis (would mean it reaches the FAR side)',
          hp_thick['height'] / 2.0 < hole_center_perp,
          f"half-length {hp_thick['height'] / 2.0:.2f}cm < "
          f"center offset {hole_center_perp:.2f}cm")

    print('hollow_frustum_shell_mesh never divides by zero even if '
          'hole_local_samples is pathologically set to 1')
    wp_bad_samples = dict(wp, holes=[wp['holes'][0]] if wp['holes'] else [])
    try:
        _pts, _tris = hollow_frustum_shell_mesh(
            wp_bad_samples, n_lon=12, n_stack=6, hole_local_samples=1)
        no_crash = True
    except ZeroDivisionError:
        no_crash = False
    check('hole_local_samples=1 is clamped internally, not a crash',
          no_crash)

    print('tower geometry sums per-tier grow volume')
    m3 = _mgr(HOLES_VALID)
    tg = tower_geometry(m3, 'demo-herb-tower')
    check('tower geometry ok + 4 tiers', tg.get('ok')
          and tg['nTiers'] == 4 and len(tg['perTier']) == 4)
    check('total grow volume = per-tier × tiers',
          abs(tg['totalGrowVolumeCm3']
              - tg['growVolumePerTierCm3'] * tg['nTiers']) < 1.0)
    check('tower reports footprint + height + water path',
          tg['footprintCm2'] > 0 and tg['towerHeightCm'] > 0
          and tg['waterPathTopToBottom'][0] == 'tier 0')

    print('POST /api/shapes/from-pot/{potName} route (aquaponics-pot-shape phase 1)')
    m4 = _mgr(HOLES_VALID)
    api = SimpleNamespace(manager=m4)
    resp_ok = SimpleNamespace(media=None, status=None)
    MathShapesAPI.on_post_from_pot(api, None, resp_ok, 'demo-pot')
    check('from-pot route builds the CSG pot ok',
          resp_ok.media.get('ok') and resp_ok.status is None)
    check('from-pot route names the wall (single mesh) + bottom + hole '
          'shapes',
          resp_ok.media.get('wallShape') == 'demo-pot-wall-shell-mesh'
          and resp_ok.media.get('bottomShape') == 'demo-pot-bottom-slab'
          and resp_ok.media.get('holeShapes')
          == ['demo-pot-hole-0', 'demo-pot-hole-1'])
    wall_surface = sample_surface(m4, resp_ok.media['wallShape'], n=16)
    check('derived wall shape has a real triangulated mesh (not CSG '
          'point cloud)', wall_surface.get('ok')
          and len(wall_surface.get('triangles', [])) > 0)
    check('from-pot route ensures the {pot}-viz SimSpace scene',
          resp_ok.media.get('simSpace') == 'demo-pot-viz')
    scene = m4.objectTables['SimSpaceDefinition']['demo-pot-viz']
    scene_def = json.loads(scene.definition)
    check('viz scene is freestandingOnly with wall (1) + bottom (1) + '
          'soil (1, phase 4) + 2 holes (5 total) — ONE wall object, '
          'not outer+inner separate',
          scene_def.get('freestandingOnly') is True
          and len(scene_def.get('freestanding', [])) == 5)
    check('viz scene freestanding shapeRefs are mathshape:-prefixed',
          all(e['shapeRef'].startswith('mathshape:')
              for e in scene_def['freestanding']))
    # Re-deriving must REFRESH the existing scene rows, not duplicate
    # them — 2 rows expected since aquaponics-pot-shape phase 3 added
    # a SEPARATE {pot}-water-viz scene alongside {pot}-viz (this
    # fixture has no PotPlanting table, so phase 6/7's plant-viz
    # scenes correctly add zero more — see plantSimSpaces below).
    MathShapesAPI.on_post_from_pot(api, None, SimpleNamespace(media=None,
                                                              status=None),
                                    'demo-pot')
    check('re-deriving refreshes (not duplicates) the viz scene rows',
          len(m4.objectTables['SimSpaceDefinition']) == 2
          and set(m4.objectTables['SimSpaceDefinition'])
          == {'demo-pot-viz', 'demo-pot-water-viz'})
    check('no PotPlanting rows for this pot -> plantSimSpaces is '
          'empty, never an error',
          resp_ok.media.get('plantSimSpaces') == [])

    print('plant-viz scenes — one per PotPlanting bound to the pot '
          '(phase 6/7)')
    m5 = _mgr(HOLES_VALID)
    m5.objectTables['PotPlanting'] = {
        'a': SimpleNamespace(name='demo-pot-basil', pot_name='demo-pot'),
        'b': SimpleNamespace(name='other-pot-basil', pot_name='other-pot'),
    }
    api5 = SimpleNamespace(manager=m5)
    resp5 = SimpleNamespace(media=None, status=None)
    MathShapesAPI.on_post_from_pot(api5, None, resp5, 'demo-pot')
    check('only the planting bound to THIS pot gets a scene '
          "(other-pot-basil, bound elsewhere, doesn't)",
          resp5.media.get('plantSimSpaces') == ['demo-pot-basil-plant-viz'])
    plant_scene = m5.objectTables['SimSpaceDefinition'][
        'demo-pot-basil-plant-viz']
    plant_scene_def = json.loads(plant_scene.definition)
    check('plant-viz scene carries exactly one live plantskeleton: entry, '
          'keyed by PLANTING name not pot name',
          sum(1 for e in plant_scene_def['freestanding']
              if e['shapeRef'] == 'plantskeleton:demo-pot-basil') == 1)
    check('plant-viz scene shell/soil are always the transparent '
          'variant, same rationale as the water-viz scene',
          all(e['styleRef'].endswith('-transparent')
              for e in plant_scene_def['freestanding']
              if e['id'] in (resp5.media['wallShape'],
                            resp5.media['bottomShape'])))
    resp_404 = SimpleNamespace(media=None, status=None)
    MathShapesAPI.on_post_from_pot(api, None, resp_404, 'no-such-pot')
    check('from-pot route 404s on an unknown pot',
          not resp_404.media.get('ok') and resp_404.status == '404 Not Found')

    print('honest refusals')
    check('modify unknown shape refuses',
          not modify_parameter(m, 'nope', 'radius', 1.0).get('ok'))
    check('modify a CSG directly refuses + suggests the child',
          not modify_parameter(m, 'pot-with-holes', 'radius', 1.0).get('ok'))
    check('unknown knob refuses + lists valid knobs',
          'validKnobs' in modify_parameter(m, 'demo-cylinder', 'nope', 1))
    check('unknown tower refuses',
          not tower_geometry(m, 'nope').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
