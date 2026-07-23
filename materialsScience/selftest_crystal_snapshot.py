"""
Self-test for the lattice 3D scene compiler + scene seeds (ssp-2).

Run from polari-framework/:
    python3 -m materialsScience.selftest_crystal_snapshot
"""

import json
import math
import sys

from materialsScience import crystal_snapshot
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def _seed(name):
    return next(s for s in SEED_CRYSTAL_STRUCTURES
                if s['name'] == name)


def _rotate_y_unit(rotation):
    """Apply three.js Euler XYZ (R = Rx @ Ry @ Rz) to the +Y unit
    vector — the cylinder axis — to recover a stick's direction."""
    ex, ey, ez = rotation
    # Rz then Ry then Rx applied to (0, 1, 0):
    v = (-math.sin(ez), math.cos(ez), 0.0)
    v = (v[0] * math.cos(ey) + v[2] * math.sin(ey), v[1],
         -v[0] * math.sin(ey) + v[2] * math.cos(ey))
    v = (v[0], v[1] * math.cos(ex) - v[2] * math.sin(ex),
         v[1] * math.sin(ex) + v[2] * math.cos(ex))
    return v


def test_scene_objects_shapes():
    print('[scene objects]')
    result = crystal_snapshot.scene_objects(_seed('silicon-diamond'),
                                            supercell=(2, 2, 2))
    check('silicon 2x2x2 scene builds', result['ok'])
    counts = result['counts']
    check('atom count includes ghost replicas (64 + boundary)',
          counts['atoms'] == 95)
    check('12 cell edges', counts['edges'] == 12)
    check('bonds present', counts['bonds'] > 0)
    atoms = [e for e in result['freestanding']
             if e['id'].startswith('atom')]
    check('atoms are spheres with element styles',
          all(e['shapeRef'] == 'sphere'
              and e['styleRef'].startswith('element-')
              for e in atoms))
    positions = [e['position'] for e in atoms]
    center = [sum(p[i] for p in positions) / len(positions)
              for i in range(3)]
    spread = max(max(abs(v) for v in p) for p in positions)
    check('scene is origin-centered',
          all(abs(c) < 1.0 for c in center) and spread > 3.0)


def test_bond_geometry():
    print('[bond stick geometry]')
    result = crystal_snapshot.scene_objects(_seed('silicon-diamond'),
                                            supercell=(1, 1, 1))
    entries = result['freestanding']
    atom_pos = {e['id']: e['position'] for e in entries
                if e['id'].startswith('atom')}
    bonds = [e for e in entries if e['id'].startswith('bond')]
    check('unit cell has bonds', len(bonds) > 0)
    ok_length = ok_direction = True
    for bond in bonds:
        length = bond['scale'][1]
        if not abs(length - 2.352) < 0.01:
            ok_length = False
        direction = _rotate_y_unit(bond['rotation'])
        # The stick's endpoints must land on two atoms.
        mid = bond['position']
        half = length / 2.0
        ends = [tuple(round(mid[i] + s * half * direction[i], 2)
                      for i in range(3)) for s in (1, -1)]
        atom_points = {tuple(round(v, 2) for v in p)
                       for p in atom_pos.values()}
        if not all(e in atom_points for e in ends):
            ok_direction = False
    check('every Si bond stick is 2.352 A long', ok_length)
    check('every bond stick spans two atom centers (Euler XYZ '
          'orientation verified)', ok_direction)


def test_seeded_scenes_and_materials():
    print('[seeded scenes + materials]')
    from materialsScience import crystal_scene_seed  # noqa: F401
    from simSpace3D.seed_data import (SEED_MATERIALS_3D,
                                      SEED_SIM_SPACES_3D)
    scenes = [s for s in SEED_SIM_SPACES_3D
              if s['name'].startswith('crystal-')]
    check('one scene per seeded structure',
          len(scenes) == len(SEED_CRYSTAL_STRUCTURES))
    check('scenes are 3d/math/freestandingOnly',
          all(s['dimensionality'] == '3d'
              and s['coordinate_system'] == 'math'
              and json.loads(s['definition']).get('freestandingOnly')
              for s in scenes))
    material_names = {m['name'] for m in SEED_MATERIALS_3D}
    used_styles = set()
    for s in scenes:
        for e in json.loads(s['definition'])['freestanding']:
            used_styles.add(e['styleRef'])
    check('every styleRef a scene uses is a seeded material',
          used_styles <= material_names)
    check('element materials carry jmol colors (Fe is a red-brown, '
          'O red)',
          any(m['name'] == 'element-fe' and m['color'] == '#e06633'
              for m in SEED_MATERIALS_3D)
          and any(m['name'] == 'element-o'
                  and m['color'] == '#ff0d0d'
                  for m in SEED_MATERIALS_3D))
    page = crystal_scene_seed.SEED_SSP_PAGE_DISPLAYS[0]
    blob = json.dumps(page)
    check('crystal-structures page hosts crystal-structure-view',
          page['pageRoute'] == 'crystal-structures'
          and 'crystal-structure-view' in blob)


def test_refusals():
    print('[refusals]')
    verdict = crystal_snapshot.scene_objects(
        _seed('silicon-diamond'), supercell=(7, 1, 1))
    check('supercell beyond 6 refuses naming the knob',
          not verdict['ok']
          and verdict['suggestion']['knob'] == 'supercell')
    verdict = crystal_snapshot.scene_objects(
        _seed('magnetite-spinel'), supercell=(4, 4, 4))
    check('scene over the object bound refuses naming ssp-8',
          not verdict['ok'] and 'ssp-8' in verdict['error'])
    broken = dict(_seed('silicon-diamond'), basis_json='[]')
    verdict = crystal_snapshot.scene_definition(broken)
    check('build refusals pass through scene_definition',
          not verdict['ok'] and 'no sites' in verdict['error'])


def main():
    test_scene_objects_shapes()
    test_bond_geometry()
    test_seeded_scenes_and_materials()
    test_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
