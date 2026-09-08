"""
Selftest — mathshapes.custom.soil_modify (aquaponics-pot-shape phase 4).

Run from polari-framework/:
    python3 -m mathshapes.soil_selftest

Covers: soil is a real quadric equation (+ derived LaTeX) whose
radius profile is read directly off the wall's OWN inner-surface
taper (never independently computed — hand-verified against
_pot_core_dimensions' numbers); the render mesh is a capped solid
frustum (reads solid, not hollow); soil sits exactly on the wall's
own floor (no gap, same z the wall/bottom flush check uses);
soil_fill_height_mm is an explicit knob, clamped to the usable
interior height when it would otherwise reach the rim (never
silent); honest refusal when the fill height resolves to ~0; the
from-pot route auto-derives soil and lists it in the {pot}-viz scene.
"""

import json
from types import SimpleNamespace

from mathshapes.custom.shape_analysis import sample_surface
from mathshapes.shape_api import MathShapesAPI
from mathshapes.custom.shape_geometry import radius_at_z
from mathshapes.custom.shape_modify import _pot_core_dimensions, pot_shape_from_definition
from mathshapes.shape_seed import SEED_MATH_SHAPES
from mathshapes.custom.soil_modify import soil_shape_from_definition
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
    flat = json.loads(shape_row.quadric_matrix_json)
    return [flat[0:4], flat[4:8], flat[8:12], flat[12:16]]


POT = {'name': 'demo-pot', 'display_name': 'Demo pot', 'shape': 'tapered',
       'outer_top_diameter_mm': 220.0, 'outer_base_diameter_mm': 180.0,
       'height_mm': 250.0, 'wall_thickness_mm': 8.0,
       'base_thickness_mm': 12.0, 'soil_fill_height_mm': 150.0,
       'reservoir_height_mm': 0.0, 'material_name': ''}
HOLES = [
    {'name': 'demo-pot-in', 'pot_name': 'demo-pot', 'kind': 'input',
     'diameter_mm': 10.0, 'height_mm': 200.0, 'azimuth_deg': 0.0,
     'angle_deg': 0.0},
    {'name': 'demo-pot-out', 'pot_name': 'demo-pot', 'kind': 'output',
     'diameter_mm': 12.0, 'height_mm': 40.0, 'azimuth_deg': 180.0,
     'angle_deg': 3.0},
]


def _mgr(pot_overrides=None):
    pot = dict(POT, **(pot_overrides or {}))
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _by_name(SEED_MATH_SHAPES),
        'AquaponicTowerDefinition': _by_name(SEED_TOWERS),
        'PotDefinition': {'demo-pot': SimpleNamespace(**pot)},
        'PotHole': {h['name']: SimpleNamespace(**h) for h in HOLES}})


if __name__ == '__main__':
    print('\nsoil fill — quadric-defined, derived from the wall it sits in\n')

    m = _mgr()
    built = pot_shape_from_definition(m, 'demo-pot')
    check('pot builds ok first (soil derives from its geometry)',
          built.get('ok'))
    soil = soil_shape_from_definition(m, 'demo-pot')
    check('soil builds ok', soil.get('ok'), str(soil.get('error')))
    check('soil not clamped for a sane fill height (150mm < usable '
          'interior)', soil.get('fillHeightClamped') is False)

    soil_eq = m.objectTables['MathShapeDefinition'][soil['soilEquation']]
    check('soil equation is a real quadric (family + flat 16-number matrix)',
          soil_eq.family == 'quadric'
          and len(json.loads(soil_eq.quadric_matrix_json)) == 16)
    check('soil equation carries a derived LaTeX display',
          'x^2' in soil_eq.notes and 'y^2' in soil_eq.notes)

    soil_render = m.objectTables['MathShapeDefinition'][soil['soilShape']]
    sp = json.loads(soil_render.parameters_json)
    check('soil render mesh is a CAPPED solid frustum (reads solid, '
          'not hollow)',
          soil_render.family == 'primitive'
          and soil_render.primitive_kind == 'frustum'
          and sp.get('cap_base') is True and sp.get('cap_top') is True)

    dims = _pot_core_dimensions(m.objectTables['PotDefinition']['demo-pot'])
    check("soil's floor sits EXACTLY on the wall's own bottom (no gap) "
          '— same number _pot_core_dimensions gives the wall',
          abs((sp['center'][2] - sp['height'] / 2.0) - dims['wall_bottom_z'])
          < 1e-6)
    check("soil's radius is read from the WALL's own inner-surface "
          "taper (radius_at_z on soil's own equation matches the "
          'linear interpolation of wall_bottom_inner_r/wall_top_inner_r)',
          abs(radius_at_z(_q(soil_eq), 'z',
                          sp['center'][2] - sp['height'] / 2.0)
              - dims['wall_bottom_inner_r']) < 1e-6)
    check("soil never pokes past the wall's inner radius",
          sp['base_radius'] <= dims['wall_bottom_inner_r'] + 1e-6
          and sp['top_radius'] <= dims['wall_top_inner_r'] + 1e-6)

    soil_surface = sample_surface(m, soil['soilShape'], n=16)
    check('soil shape has a real triangulated mesh (not CSG point cloud)',
          soil_surface.get('ok') and len(soil_surface.get('triangles', [])) > 0)

    print('\nsoil_fill_height_mm is an explicit knob, clamped never silent\n')
    m_tall = _mgr({'soil_fill_height_mm': 5000.0})
    pot_shape_from_definition(m_tall, 'demo-pot')
    soil_tall = soil_shape_from_definition(m_tall, 'demo-pot')
    check('an oversized fill height still builds ok (clamped)',
          soil_tall.get('ok'))
    check('clamped flag is set + fillHeightMm caps at the usable '
          'interior height (not 5000mm)',
          soil_tall.get('fillHeightClamped') is True
          and soil_tall['fillHeightMm'] < 250.0,
          str(soil_tall.get('fillHeightMm')))

    print('\nhonest refusal — fill height resolves to ~0\n')
    m_zero = _mgr({'soil_fill_height_mm': 0.0})
    pot_shape_from_definition(m_zero, 'demo-pot')
    soil_zero = soil_shape_from_definition(m_zero, 'demo-pot')
    check('zero fill height refuses, names the knob',
          not soil_zero.get('ok')
          and soil_zero.get('suggestion', {}).get('knob')
          == 'PotDefinition.soil_fill_height_mm')

    print('\nfrom-pot route auto-derives soil + lists it in the scene\n')
    m2 = _mgr()
    api = SimpleNamespace(manager=m2)
    resp = SimpleNamespace(media=None, status=None)
    MathShapesAPI.on_post_from_pot(api, None, resp, 'demo-pot')
    check('from-pot response carries the soil result',
          resp.media.get('soil', {}).get('ok'))
    scene = m2.objectTables['SimSpaceDefinition']['demo-pot-viz']
    scene_def = json.loads(scene.definition)
    refs = [e['shapeRef'] for e in scene_def['freestanding']]
    check('scene lists wall + bottom + soil + 2 holes (5 total)',
          len(refs) == 5)
    check('soil shape is in the scene with the soil-brown style',
          any(e['shapeRef'] == f"mathshape:{resp.media['soil']['soilShape']}"
              and e['styleRef'] == 'soil-brown'
              for e in scene_def['freestanding']))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
