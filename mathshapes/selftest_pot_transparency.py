"""
Selftest — pot render transparency toggles (aquaponics-pot-shape
phase 5) + the separate water-flow scene (phase 3).

Run from polari-framework/:
    python3 -m mathshapes.selftest_pot_transparency

Covers: wall_transparent/soil_transparent are explicit PotDefinition
knobs — DEFAULT TRUE as of 2026-07-15 (Dustin: "the pots and soil
only mostly transparent so we can see the water flow"; a fresh pot is
now see-through by default, opaque is the opt-OUT); pot_shape_from_
definition reports them straight off the pot row; ensure_pot_viz_scene
picks the '-transparent' style variant for that layer ONLY (wall+
bottom share ONE toggle — the vessel "shell" — soil has its own,
independent); toggling one to False leaves the other alone; holes
render at 'matte-gray-transparent' UNCONDITIONALLY (fully transparent
by default, untouched by either toggle — same rule as before, just a
different fixed style now). Also covers ensure_pot_water_viz_scene:
a SEPARATE {pot}-water-viz scene from {pot}-viz, always-transparent
shell/soil regardless of the pot's own knobs, plus the live
waterslice: freestanding entry.
"""

import json
from types import SimpleNamespace

from mathshapes.pot_scene import (
    ensure_pot_viz_scene, ensure_pot_water_viz_scene,
)
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
       'reservoir_height_mm': 0.0, 'material_name': '',
       # Mirrors PotDefinition's own constructor defaults (2026-07-15:
       # both now True) — this fixture builds a raw SimpleNamespace
       # rather than a real PotDefinition instance, so it must state
       # the default explicitly rather than relying on __init__.
       'wall_transparent': True, 'soil_transparent': True}
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


def _styles(manager, pot_name='demo-pot', suffix='-viz'):
    scene = manager.objectTables['SimSpaceDefinition'][f'{pot_name}{suffix}']
    entries = json.loads(scene.definition)['freestanding']
    return {e['id']: e['styleRef'] for e in entries}


if __name__ == '__main__':
    print('\ndefault: both layers TRANSPARENT (2026-07-15 default flip)\n')
    m = _mgr()
    built = pot_shape_from_definition(m, 'demo-pot')
    check('default wall_transparent/soil_transparent are both True '
          '(see-through by default, opaque is now the opt-out)',
          built['wallTransparent'] is True
          and built['soilTransparent'] is True)
    ensure_pot_viz_scene(m, 'demo-pot', built['wallShape'],
                         built['bottomShape'], None, built['holeShapes'],
                         wall_transparent=built['wallTransparent'],
                         soil_transparent=built['soilTransparent'])
    styles = _styles(m)
    check('wall + bottom use the TRANSPARENT vessel style by default',
          styles[built['wallShape']] == 'matte-blue-transparent'
          and styles[built['bottomShape']] == 'matte-blue-transparent')
    check('holes render fully transparent by default '
          "('matte-gray-transparent')",
          all(styles[h] == 'matte-gray-transparent'
              for h in built['holeShapes']))

    print('\nwall_transparent=False opts the shell BACK to opaque, '
          'soil untouched\n')
    m2 = _mgr({'wall_transparent': False})
    built2 = pot_shape_from_definition(m2, 'demo-pot')
    ensure_pot_viz_scene(m2, 'demo-pot', built2['wallShape'],
                         built2['bottomShape'], 'demo-pot-soil',
                         built2['holeShapes'],
                         wall_transparent=built2['wallTransparent'],
                         soil_transparent=built2['soilTransparent'])
    styles2 = _styles(m2)
    check('wall_transparent=false reads off the pot row',
          built2['wallTransparent'] is False)
    check('wall + bottom both switch back to the opaque vessel style',
          styles2[built2['wallShape']] == 'matte-blue'
          and styles2[built2['bottomShape']] == 'matte-blue')
    check("soil stays TRANSPARENT (its own default) — wall_transparent "
          "doesn't leak into it",
          styles2['demo-pot-soil'] == 'soil-brown-transparent')
    check('holes stay fully transparent regardless — untouched by '
          'either toggle',
          all(styles2[h] == 'matte-gray-transparent'
              for h in built2['holeShapes']))

    print('\nsoil_transparent=False opts soil BACK to opaque, shell '
          'untouched\n')
    m3 = _mgr({'soil_transparent': False})
    built3 = pot_shape_from_definition(m3, 'demo-pot')
    ensure_pot_viz_scene(m3, 'demo-pot', built3['wallShape'],
                         built3['bottomShape'], 'demo-pot-soil',
                         built3['holeShapes'],
                         wall_transparent=built3['wallTransparent'],
                         soil_transparent=built3['soilTransparent'])
    styles3 = _styles(m3)
    check('soil_transparent=false reads off the pot row',
          built3['soilTransparent'] is False)
    check('soil switches back to the opaque variant',
          styles3['demo-pot-soil'] == 'soil-brown')
    check("shell (wall+bottom) stays TRANSPARENT (its own default) — "
          "soil_transparent doesn't leak into it",
          styles3[built3['wallShape']] == 'matte-blue-transparent'
          and styles3[built3['bottomShape']] == 'matte-blue-transparent')

    print('\nboth opted back to opaque together\n')
    m4 = _mgr({'wall_transparent': False, 'soil_transparent': False})
    built4 = pot_shape_from_definition(m4, 'demo-pot')
    ensure_pot_viz_scene(m4, 'demo-pot', built4['wallShape'],
                         built4['bottomShape'], 'demo-pot-soil',
                         built4['holeShapes'],
                         wall_transparent=built4['wallTransparent'],
                         soil_transparent=built4['soilTransparent'])
    styles4 = _styles(m4)
    check('both layers switch to opaque independently when both '
          'opted out',
          styles4[built4['wallShape']] == 'matte-blue'
          and styles4[built4['bottomShape']] == 'matte-blue'
          and styles4['demo-pot-soil'] == 'soil-brown')

    print('\nseparate water-flow scene ({pot}-water-viz) — phase 3\n')
    m5 = _mgr({'wall_transparent': False, 'soil_transparent': False})
    built5 = pot_shape_from_definition(m5, 'demo-pot')
    ensure_pot_viz_scene(m5, 'demo-pot', built5['wallShape'],
                         built5['bottomShape'], 'demo-pot-soil',
                         built5['holeShapes'],
                         wall_transparent=built5['wallTransparent'],
                         soil_transparent=built5['soilTransparent'])
    ensure_pot_water_viz_scene(m5, 'demo-pot', built5['wallShape'],
                               built5['bottomShape'], 'demo-pot-soil',
                               built5['holeShapes'])
    tables = m5.objectTables['SimSpaceDefinition']
    check('water-viz scene is a DIFFERENT row from the static -viz scene',
          'demo-pot-water-viz' in tables and 'demo-pot-viz' in tables
          and tables['demo-pot-water-viz'] is not tables['demo-pot-viz'])
    water_styles = _styles(m5, suffix='-water-viz')
    check('water scene ALWAYS renders shell+soil transparent, even '
          "though this same pot's static scene is opaque "
          '(wall_transparent=False set above)',
          water_styles[built5['wallShape']] == 'matte-blue-transparent'
          and water_styles[built5['bottomShape']] == 'matte-blue-transparent'
          and water_styles['demo-pot-soil'] == 'soil-brown-transparent')
    check('water scene holes also transparent',
          all(water_styles[h] == 'matte-gray-transparent'
              for h in built5['holeShapes']))
    check('water scene carries exactly one live waterslice: entry',
          water_styles.get('demo-pot-water-slice') == 'water-blue')
    water_entry = next(
        e for e in json.loads(tables['demo-pot-water-viz'].definition)
        ['freestanding'] if e['id'] == 'demo-pot-water-slice')
    check("waterslice: shapeRef names the pot (dynamic per-request "
          'resolution, not a stored MathShapeDefinition)',
          water_entry['shapeRef'] == 'waterslice:demo-pot')
    check('static -viz scene is untouched by the water scene call '
          '(still opaque, per this test case)',
          _styles(m5)[built5['wallShape']] == 'matte-blue')

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
