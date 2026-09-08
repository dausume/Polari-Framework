"""
@module pspp.custom.structure_scene

gsp-3 (GEOPOLYMER_STRUCTURE_SAMPLING_PLAN): compile one sampled
geopolymer cluster (pspp.custom.structure_sampling) into the SAME
freestanding sphere+cylinder scene the crystal lattices use, so
crystals and amorphous samples read as siblings in the viewer.

Reuses materialsScience.crystal_snapshot helpers (cylinder emission,
element materials); adds one style of its own — terminal
(non-bridging) oxygens render paler than bridging so the network's
connectivity is visible at a glance.

@consumers
  - pspp.pspp_api (/api/pspp/structure/scene)
  - pspp.structure_sampling_selftest
"""

import json

import numpy as np

from materialsScience.crystal_snapshot import (
    _cylinder_between,
    element_material_name,
    element_materials,
    structural_materials,
)

ATOM_DISPLAY_SCALE = 0.5
BOND_RADIUS_A = 0.12
TERMINAL_O_MATERIAL = 'geopolymer-terminal-o'

#: covalent radii lookup goes through ASE like the crystal path


def geopolymer_materials(sample):
    """Material3DDefinition seed dicts this sample's scene needs."""
    symbols = {a['element'] for a in sample['atoms']}
    rows = element_materials(symbols) + structural_materials()
    rows.append({
        'name': TERMINAL_O_MATERIAL,
        'description': 'Terminal (non-bridging) oxygen — paler than '
                       'bridging O so network connectivity reads.',
        'material_type': 'standard',
        'color': '#ffb3a7', 'emissive': '#000000',
        'emissive_intensity': 0.0, 'metalness': 0.1,
        'roughness': 0.6, 'opacity': 1.0, 'transparent': False,
    })
    return rows


def scene_name(cation, mr=None, state_key=None, seed=1):
    tag = (state_key or f'{cation}-mr{mr:g}').replace(' ', '_')
    return f'geopolymer-sample-{tag}-seed{int(seed)}'


def scene_objects(sample, atom_scale=ATOM_DISPLAY_SCALE,
                  bond_radius=BOND_RADIUS_A):
    """Freestanding entries for one sample ->
    {'ok', 'freestanding', 'center', 'extent', 'counts'}."""
    from ase.data import atomic_numbers, covalent_radii
    atoms = sample['atoms']
    positions = np.array([a['position'] for a in atoms], float)
    center = (positions.max(axis=0) + positions.min(axis=0)) / 2.0
    entries = []
    for idx, atom in enumerate(atoms):
        symbol = atom['element']
        radius = float(covalent_radii[atomic_numbers[symbol]])
        style = (TERMINAL_O_MATERIAL
                 if atom['role'] == 'terminal-oxygen'
                 else element_material_name(symbol))
        display_radius = radius * atom_scale
        entries.append({
            'id': f'atom-{idx}',
            'position': [round(float(v), 4) for v in
                         positions[idx] - center],
            'rotation': [0.0, 0.0, 0.0],
            'scale': [round(2 * display_radius, 4)] * 3,
            'shapeRef': 'sphere', 'styleRef': style,
        })
    bond_count = 0
    for bond_index, (a, b) in enumerate(sample['bonds']):
        entry = _cylinder_between(
            positions[a] - center, positions[b] - center,
            bond_radius, 'lattice-bond', f'bond-{bond_index}')
        if entry is not None:
            entries.append(entry)
            bond_count += 1
    extent = float(np.abs(positions - center).max()) + 2.0
    return {'ok': True, 'freestanding': entries,
            'center': [0.0, 0.0, 0.0], 'extent': round(extent, 2),
            'counts': {'atoms': len(atoms), 'bonds': bond_count}}


def scene_definition(sample, name, description=None, **kwargs):
    """Full SimSpaceDefinition seed dict for one sampled cluster."""
    objects = scene_objects(sample, **kwargs)
    if not objects['ok']:
        return objects
    achieved = sample['achievedQ']
    top = max(achieved, key=achieved.get)
    scene = {
        'name': name,
        'description': description or (
            f'ONE SAMPLE from the geopolymer ensemble (seed '
            f'{sample["seed"]}) — {sample["counts"]["tetrahedra"]} '
            f'tetrahedra, dominant motif {top} '
            f'({achieved[top]:.0%} achieved). Not THE structure: '
            'amorphous materials only have distributions; resample '
            'with a new seed via POST /api/pspp/structure/scene.'),
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
        'owning_module': 'pspp',
    }
    return {'ok': True, 'scene': scene, 'counts': objects['counts']}
