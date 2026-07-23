"""
@module materialsScience.crystal_scene_seed

Seed the lattice 3D scenes (ssp-2) — trigger-on-import (the waxprint
sim_seed idiom): importing this module appends element/bond
Material3DDefinition rows to SEED_MATERIALS_3D and one pure-static
SimSpaceDefinition per seeded crystal structure to SEED_SIM_SPACES_3D,
so the shared seed loops create them at boot.

Seeded scenes are snapshots of the SEEDED structure rows; editing a
structure later does NOT silently rewrite its scene — POST
/api/msci/structures/{name}/scene is the explicit regenerate knob.

Small conventional cells repeat 2x2x2 so the lattice reads as a
lattice; big cells (spinel, corundum) stay single-cell.

@consumers
  - polariServer seed loop (via simSpace3D.seed_data lists)
  - materialsScience.selftest_crystal_snapshot
"""

import json

from simSpace3D.seed_data import SEED_MATERIALS_3D, SEED_SIM_SPACES_3D
from materialsScience import crystal_ops, crystal_snapshot
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)

#: Explicit supercell overrides; everything else repeats 2x2x2 when
#: the conventional cell holds <= 8 atoms, 1x1x1 otherwise.
SCENE_SUPERCELLS = {
    'graphite-hexagonal': (2, 2, 1),   # keep the c stacking readable
}


def _supercell_for(seed):
    override = SCENE_SUPERCELLS.get(seed['name'])
    if override:
        return override
    built = crystal_ops.build_atoms(seed)
    n_atoms = len(built['atoms']) if built['ok'] else 999
    return (2, 2, 2) if n_atoms <= 8 else (1, 1, 1)


def _seed_scenes():
    symbols = set()
    for seed in SEED_CRYSTAL_STRUCTURES:
        for site in json.loads(seed['basis_json']):
            symbols.add(site['element'])
    existing_materials = {m['name'] for m in SEED_MATERIALS_3D}
    for row in (crystal_snapshot.element_materials(symbols)
                + crystal_snapshot.structural_materials()):
        if row['name'] not in existing_materials:
            SEED_MATERIALS_3D.append(row)
            existing_materials.add(row['name'])

    existing_scenes = {s['name'] for s in SEED_SIM_SPACES_3D}
    for seed in SEED_CRYSTAL_STRUCTURES:
        verdict = crystal_snapshot.scene_definition(
            seed, supercell=_supercell_for(seed))
        if verdict['ok'] \
                and verdict['scene']['name'] not in existing_scenes:
            SEED_SIM_SPACES_3D.append(verdict['scene'])


_seed_scenes()


#: The crystal-structures page: structure picker + facts + the lattice
#: scene (crystal-structure-view is the ssp-2 Angular component).
SEED_SSP_PAGE_DISPLAYS = [{
    'name': 'crystal-structures',
    'description': 'Crystal lattices — structure browser with 3D '
                   'lattice view, facts and bonds (ssp-2).',
    'source_class': 'CrystalStructureDefinition',
    'isPage': True,
    'pageRoute': 'crystal-structures',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [{
        'index': 0, 'rowSegments': 12, 'minRowHeight': 640,
        'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
        'items': [{
            'id': 'crystal-structures-item', 'index': 0,
            'type': 'component', 'rowSegmentsUsed': 12,
            'gridColumnStart': None,
            'title': 'Crystal structures', 'visible': True,
            'collapsed': False, 'cssClass': '',
            'componentProps': {
                'componentName': 'crystal-structure-view',
                'inputs': {'structureName': 'silicon-diamond'}},
            'item': None, 'nestedRows': []}],
    }]}),
}]
