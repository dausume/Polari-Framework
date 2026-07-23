"""
@module materialsScience.crystal_snapshot

Crystal lattice -> SimSpace 3D scene (ssp-2): compile a
CrystalStructureDefinition into a pure-static `freestandingOnly`
SimSpaceDefinition blob the existing sim-space viewer renders with no
new primitives — atoms as element-colored spheres (jmol colors,
covalent-radius sizes), bonds and unit-cell edges as thin cylinders
oriented between their endpoints.

Display choices are knobs with honest defaults: supercell repeat,
atom-radius display scale (0.5 = ball-and-stick), bond radius, ghost
replicas of boundary atoms (a lattice drawn without them reads wrong).
Scenes are Angstrom-as-world-unit, centered on the origin (math
coordinate system).

@consumers
  - materialsScience.crystal_scene_seed (seeded scenes + materials)
  - materialsScience.crystal_structure_api (POST scene refresh)
  - materialsScience.selftest_crystal_snapshot
"""

import json
import math

import numpy as np

from materialsScience import crystal_ops

ATOM_DISPLAY_SCALE = 0.5   # covalent radius multiplier (ball-and-stick)
BOND_RADIUS_A = 0.12
EDGE_RADIUS_A = 0.03
MAX_SCENE_ATOMS = 2000     # the renderer is one Object3D per atom —
                           # instancing is the ssp-8 seam

BOND_MATERIAL = 'lattice-bond'
EDGE_MATERIAL = 'lattice-cell-edge'


def element_material_name(symbol):
    return f'element-{symbol.lower()}'


def element_materials(symbols):
    """Material3DDefinition seed dicts for the given element symbols,
    colored per the jmol convention ASE ships."""
    from ase.data import atomic_numbers
    from ase.data.colors import jmol_colors
    rows = []
    for symbol in sorted(set(symbols)):
        z = atomic_numbers[symbol]
        r, g, b = (int(round(c * 255)) for c in jmol_colors[z])
        rows.append({
            'name': element_material_name(symbol),
            'description': f'{symbol} atom (jmol color convention).',
            'material_type': 'standard',
            'color': f'#{r:02x}{g:02x}{b:02x}',
            'emissive': '#000000', 'emissive_intensity': 0.0,
            'metalness': 0.1, 'roughness': 0.6,
            'opacity': 1.0, 'transparent': False,
        })
    return rows


def structural_materials():
    return [
        {'name': BOND_MATERIAL, 'description':
            'Crystal bond stick.', 'material_type': 'standard',
         'color': '#9e9e9e', 'emissive': '#000000',
         'emissive_intensity': 0.0, 'metalness': 0.1,
         'roughness': 0.7, 'opacity': 1.0, 'transparent': False},
        {'name': EDGE_MATERIAL, 'description':
            'Unit-cell edge line.', 'material_type': 'standard',
         'color': '#455a64', 'emissive': '#000000',
         'emissive_intensity': 0.0, 'metalness': 0.0,
         'roughness': 0.9, 'opacity': 1.0, 'transparent': False},
    ]


def _cylinder_between(p0, p1, radius, style, entry_id):
    """A freestanding cylinder entry spanning p0 -> p1 (the builtin
    cylinder is radius 0.5, height 1, along +Y; Euler order XYZ)."""
    d = np.asarray(p1, float) - np.asarray(p0, float)
    length = float(np.linalg.norm(d))
    if length < 1e-9:
        return None
    n = d / length
    nx = max(-1.0, min(1.0, float(n[0])))
    ez = -math.asin(nx)
    ex = (math.atan2(float(n[2]), float(n[1]))
          if abs(nx) < 1.0 - 1e-12 else 0.0)
    mid = (np.asarray(p0, float) + np.asarray(p1, float)) / 2.0
    return {
        'id': entry_id,
        'position': [round(float(v), 4) for v in mid],
        'rotation': [round(ex, 5), 0.0, round(ez, 5)],
        'scale': [round(2 * radius, 4), round(length, 4),
                  round(2 * radius, 4)],
        'shapeRef': 'cylinder', 'styleRef': style,
    }


def _replicated_positions(atoms, supercell):
    """Cartesian positions + symbols for the supercell block, with
    ghost replicas of boundary atoms (frac ~ 0 duplicated at the far
    face) so the block reads as a complete lattice."""
    from itertools import product
    cell = np.asarray(atoms.cell)
    scaled = atoms.get_scaled_positions(wrap=True)
    symbols = atoms.get_chemical_symbols()
    nx, ny, nz = supercell
    positions, out_symbols = [], []
    for index in range(len(atoms)):
        frac = scaled[index]
        for cell_index in product(range(nx), range(ny), range(nz)):
            # Per-axis ghost offsets: an atom on the near face of a
            # zero-index cell reappears on the far face of the BLOCK.
            axis_offsets = []
            for axis, n_axis in enumerate((nx, ny, nz)):
                offs = [0.0]
                if frac[axis] < 1e-6 and cell_index[axis] == 0:
                    offs.append(float(n_axis))
                axis_offsets.append(offs)
            for ghost in product(*axis_offsets):
                target = frac + np.array(cell_index, float) \
                    + np.array(ghost)
                positions.append(target @ cell)
                out_symbols.append(symbols[index])
    return np.array(positions), out_symbols


def scene_objects(structure, supercell=(1, 1, 1),
                  atom_scale=ATOM_DISPLAY_SCALE,
                  bond_radius=BOND_RADIUS_A, ghost_replicas=True,
                  cell_edges=True):
    """Freestanding entries + framing for one structure ->
    {'ok', 'freestanding', 'center', 'extent', 'counts'} | refusal."""
    supercell = tuple(int(v) for v in supercell)
    if any(v < 1 or v > 6 for v in supercell):
        return {'ok': False,
                'error': f'supercell {supercell} outside 1..6 per '
                         'axis',
                'suggestion': {'knob': 'supercell',
                               'action': 'repeat 1-6 cells per axis'}}
    built = crystal_ops.build_atoms(structure)
    if not built['ok']:
        return built
    atoms = built['atoms']
    struct = crystal_ops.structure_dict(structure)
    if ghost_replicas:
        positions, symbols = _replicated_positions(atoms, supercell)
    else:
        block = atoms * supercell
        positions = block.get_positions()
        symbols = block.get_chemical_symbols()
    if len(positions) > MAX_SCENE_ATOMS:
        return {'ok': False,
                'error': f'{len(positions)} atoms exceed the '
                         f'{MAX_SCENE_ATOMS}-object scene bound (one '
                         'renderer Object3D per atom; instanced '
                         'rendering is the ssp-8 gap)',
                'suggestion': {'knob': 'supercell',
                               'action': 'reduce the repeat'}}

    from ase.data import atomic_numbers, covalent_radii
    center = (positions.max(axis=0) + positions.min(axis=0)) / 2.0 \
        if len(positions) else np.zeros(3)
    entries = []
    radii = np.array([covalent_radii[atomic_numbers[s]]
                      for s in symbols])
    for idx, (pos, symbol) in enumerate(zip(positions, symbols)):
        display_radius = float(radii[idx]) * atom_scale
        entries.append({
            'id': f'atom-{idx}',
            'position': [round(float(v), 4)
                         for v in (pos - center)],
            'scale': round(2 * display_radius, 4),
            'shapeRef': 'sphere',
            'styleRef': element_material_name(symbol),
            'userData': {'element': symbol},
        })

    # Bonds among DISPLAYED atoms: plain pairwise distances under the
    # row's covalent cutoff rule (no pbc — the block is what is shown).
    scale = struct['bondCutoffScale']
    n_atoms = len(positions)
    bond_count = 0
    if n_atoms > 1:
        deltas = positions[:, None, :] - positions[None, :, :]
        dists = np.linalg.norm(deltas, axis=2)
        cutoffs = (radii[:, None] + radii[None, :]) * scale
        bonded = (dists <= cutoffs) & (dists > 1e-6)
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                if bonded[i, j]:
                    stick = _cylinder_between(
                        positions[i] - center, positions[j] - center,
                        bond_radius, BOND_MATERIAL,
                        f'bond-{bond_count}')
                    if stick:
                        entries.append(stick)
                        bond_count += 1

    edge_count = 0
    if cell_edges:
        cell = np.asarray(atoms.cell)
        block = cell * np.array(supercell)[:, None]
        corners = [np.zeros(3), block[0], block[1], block[2],
                   block[0] + block[1], block[0] + block[2],
                   block[1] + block[2], block[0] + block[1] + block[2]]
        edges = [(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (2, 4),
                 (2, 6), (3, 5), (3, 6), (4, 7), (5, 7), (6, 7)]
        for a, b in edges:
            stick = _cylinder_between(
                corners[a] - center, corners[b] - center,
                EDGE_RADIUS_A, EDGE_MATERIAL, f'edge-{edge_count}')
            if stick:
                entries.append(stick)
                edge_count += 1

    extent = (positions.max(axis=0) - positions.min(axis=0)
              + 2.0) if len(positions) else np.ones(3)
    return {'ok': True, 'freestanding': entries,
            'center': [0.0, 0.0, 0.0],
            'extent': [round(float(v), 3) for v in extent],
            'counts': {'atoms': n_atoms, 'bonds': bond_count,
                       'edges': edge_count}}


def scene_name(structure_name):
    return f'crystal-{structure_name}'


def scene_definition(structure, supercell=(1, 1, 1), **kwargs):
    """A full SimSpaceDefinition seed dict for one structure —
    {'ok': True, 'scene': {...}} | refusal."""
    struct = crystal_ops.structure_dict(structure)
    objects = scene_objects(structure, supercell=supercell, **kwargs)
    if not objects['ok']:
        return objects
    display = structure.get('display_name', '') \
        if isinstance(structure, dict) \
        else getattr(structure, 'display_name', '')
    counts = objects['counts']
    scene = {
        'name': scene_name(struct['name']),
        'description': f'Crystal lattice of {display or struct["name"]}'
                       f' — {counts["atoms"]} atoms, '
                       f'{counts["bonds"]} bonds, '
                       f'{"x".join(str(v) for v in supercell)} cells '
                       '(Angstrom world units). Regenerate via POST '
                       f'/api/msci/structures/{struct["name"]}/scene.',
        'dimensionality': '3d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps({
            'center': objects['center'],
            'extent': objects['extent']}),
        'bound_classes_json': '[]',
        'definition': json.dumps({
            'freestandingOnly': True,
            'freestanding': objects['freestanding']}),
        'category': 'materials-science',
        'owning_module': 'materialsScience',
    }
    return {'ok': True, 'scene': scene, 'counts': counts}
