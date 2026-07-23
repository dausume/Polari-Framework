"""
@module materialsScience.crystal_structure_definition

CrystalStructureDefinition — a crystal lattice as a first-class object
(SOLID_STATE_PHYSICS_PLAN.md ssp-1). One row = one periodic structure:
cell parameters + a symmetry-reduced basis (representative Wyckoff
sites when space_group > 0, ALL atoms of a P1 cell when 0), built into
real atomic coordinates through ASE's bundled space-group tables
(pure Python — no spglib needed in the base image).

A crystal structure is NOT a scale level — it is the structural
REPRESENTATION that L3 (atomistic) and L4 (quantum) physics share.
Scale rows reference it via definition_class/definition_ref like any
other representation; derived properties land at the level of the
physics that computed them (see the plan §2).

`built_facts_json` is a derived cache (crystal_ops.refresh_built_facts)
holding the built cell, atom list, bonds and headline facts — a plain
field so objectRef bindings and the scene compiler (ssp-2) can consume
the built structure without re-running ASE.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.crystal_ops (build + facts + bonds)
  - materialsScience.crystal_structure_api (/api/msci/structures)
  - materialsScience.crystal_structures_seed
"""

from objectTreeDecorators import treeObject, treeObjectInit


class CrystalStructureDefinition(treeObject):
    """One periodic crystal structure. Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        # Unique kebab-case key ('silicon-diamond', 'magnetite-spinel').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # MaterialsScienceMaterial.name this structure belongs to
        # ('' = reference structure with no material identity yet —
        # honest, browsable, linkable later).
        material_name: str = '',
        # International Tables space-group number 1-230; 0 = no
        # symmetry expansion (basis_json lists ALL atoms of the cell).
        space_group: int = 0,
        # ITA origin choice where the group has two (Fd-3m etc.);
        # ASE's `setting` argument. Literature Wyckoff coordinates
        # state their origin choice — record the one the source used.
        space_group_setting: int = 1,
        # Conventional cell parameters: lengths in Angstrom, angles in
        # degrees.
        cell_a: float = 0.0,
        cell_b: float = 0.0,
        cell_c: float = 0.0,
        alpha: float = 90.0,
        beta: float = 90.0,
        gamma: float = 90.0,
        # JSON list of basis sites:
        #   [{"element": "Fe", "frac": [0.125, 0.125, 0.125],
        #     "site": "8a"}, ...]
        # Representative Wyckoff sites when space_group > 0 (ASE
        # expands the orbit); every atom of the cell when 0. "site" is
        # a provenance label, not consumed by the builder.
        basis_json: str = '[]',
        # Bond detection knob: atoms i,j are bonded when their
        # distance <= scale * (covalent_radius_i + covalent_radius_j).
        # 1.15 suits covalent/ionic structures; metals need ~1.2 (the
        # fcc nearest neighbor sits just past the covalent sum).
        bond_cutoff_scale: float = 1.15,
        # Derived cache — crystal_ops.refresh_built_facts writes the
        # built cell/atoms/bonds/facts here; never hand-edited.
        built_facts_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.material_name = material_name
        self.space_group = space_group
        self.space_group_setting = space_group_setting
        self.cell_a = cell_a
        self.cell_b = cell_b
        self.cell_c = cell_c
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.basis_json = basis_json
        self.bond_cutoff_scale = bond_cutoff_scale
        self.built_facts_json = built_facts_json
        self.provenance_id = provenance_id
        self.notes = notes
        self.enabled = enabled
