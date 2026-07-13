"""
Selftest — pot render transparency toggles (aquaponics-pot-shape
phase 5).

Run from polari-framework/:
    python3 -m mathshapes.selftest_pot_transparency

Covers: wall_transparent/soil_transparent are explicit PotDefinition
knobs (default False — opaque, never a silent see-through default);
pot_shape_from_definition reports them straight off the pot row;
ensure_pot_viz_scene picks the '-transparent' style variant for that
layer ONLY (wall+bottom share ONE toggle — the vessel "shell" — soil
has its own, independent); toggling one leaves the other alone; holes
are never affected by either toggle.
"""

import json
from types import SimpleNamespace

from mathshapes.pot_scene import ensure_pot_viz_scene
from mathshapes.shape_modify import pot_shape_from_definition
from mathshapes.shape_seed import SEED_MATH_SHAPES
from mathshapes.tower_seed import SEED_TOWERS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _by_name(seed_list):
    return {r['name']: SimpleNamespace(**r) for r in seed_list}


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


def _styles(manager, pot_name='demo-pot'):
    scene = manager.objectTables['SimSpaceDefinition'][f'{pot_name}-viz']
    entries = json.loads(scene.definition)['freestanding']
    return {e['id']: e['styleRef'] for e in entries}


if __name__ == '__main__':
    print('\ndefault: both layers opaque\n')
    m = _mgr()
    built = pot_shape_from_definition(m, 'demo-pot')
    check('default wall_transparent/soil_transparent are both False '
          '(opaque by default, never a silent see-through)',
          built['wallTransparent'] is False
          and built['soilTransparent'] is False)
    ensure_pot_viz_scene(m, 'demo-pot', built['wallShape'],
                         built['bottomShape'], None, built['holeShapes'],
                         wall_transparent=built['wallTransparent'],
                         soil_transparent=built['soilTransparent'])
    styles = _styles(m)
    check('wall + bottom use the opaque vessel style by default',
          styles[built['wallShape']] == 'matte-blue'
          and styles[built['bottomShape']] == 'matte-blue')

    print('\nwall_transparent toggles ONLY the shell (wall+bottom), '
          'soil untouched\n')
    m2 = _mgr({'wall_transparent': True})
    built2 = pot_shape_from_definition(m2, 'demo-pot')
    ensure_pot_viz_scene(m2, 'demo-pot', built2['wallShape'],
                         built2['bottomShape'], f"demo-pot-soil",
                         built2['holeShapes'],
                         wall_transparent=built2['wallTransparent'],
                         soil_transparent=built2['soilTransparent'])
    styles2 = _styles(m2)
    check('wall_transparent=true reads off the pot row',
          built2['wallTransparent'] is True)
    check('wall + bottom both switch to the transparent vessel variant',
          styles2[built2['wallShape']] == 'matte-blue-transparent'
          and styles2[built2['bottomShape']] == 'matte-blue-transparent')
    check("soil stays OPAQUE — wall_transparent doesn't leak into it",
          styles2['demo-pot-soil'] == 'soil-brown')
    check('holes are never affected by either transparency toggle',
          all(styles2[h] == 'matte-gray' for h in built2['holeShapes']))

    print('\nsoil_transparent toggles ONLY soil, shell untouched\n')
    m3 = _mgr({'soil_transparent': True})
    built3 = pot_shape_from_definition(m3, 'demo-pot')
    ensure_pot_viz_scene(m3, 'demo-pot', built3['wallShape'],
                         built3['bottomShape'], 'demo-pot-soil',
                         built3['holeShapes'],
                         wall_transparent=built3['wallTransparent'],
                         soil_transparent=built3['soilTransparent'])
    styles3 = _styles(m3)
    check('soil_transparent=true reads off the pot row',
          built3['soilTransparent'] is True)
    check('soil switches to the transparent variant',
          styles3['demo-pot-soil'] == 'soil-brown-transparent')
    check("shell (wall+bottom) stays OPAQUE — soil_transparent doesn't "
          'leak into it',
          styles3[built3['wallShape']] == 'matte-blue'
          and styles3[built3['bottomShape']] == 'matte-blue')

    print('\nboth toggled together\n')
    m4 = _mgr({'wall_transparent': True, 'soil_transparent': True})
    built4 = pot_shape_from_definition(m4, 'demo-pot')
    ensure_pot_viz_scene(m4, 'demo-pot', built4['wallShape'],
                         built4['bottomShape'], 'demo-pot-soil',
                         built4['holeShapes'],
                         wall_transparent=built4['wallTransparent'],
                         soil_transparent=built4['soilTransparent'])
    styles4 = _styles(m4)
    check('both layers switch to their transparent variant independently',
          styles4[built4['wallShape']] == 'matte-blue-transparent'
          and styles4[built4['bottomShape']] == 'matte-blue-transparent'
          and styles4['demo-pot-soil'] == 'soil-brown-transparent')

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
