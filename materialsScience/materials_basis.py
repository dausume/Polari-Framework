"""
@cross-cutting
@module materialsScience.materials_basis
@tags @xc:bindings

The MaterialsScienceMaterial BASIS — one identity per material, with
per-scale definitions as explicit, piecemeal-first rows.

The legacy module (modules/polariMaterialsScienceModule/) grew THREE
unlinked material roots: Material (property/resolution/purpose trees),
RawMaterial (the seeded formulation world) and ReferenceMaterial
(literature values). MaterialsScienceMaterial does not replace them —
it is the coherent anchor that BRIDGES them (loose-id links, the
module's own convention), so every existing row gains a shared identity
without a destructive rewrite.

Multi-scale is likewise made explicit instead of label-only:
MaterialScaleDefinition rows say, per material and per scale level
(0 experimental → 4 quantum), WHAT defines the material there, WHERE
that definition lives (class + ref), and — when derived — WHICH other
scale definition it came from and by what method. Not every material
can be defined at every scale; absence is honest data the gates in
scale_presence.py act on (same philosophy as the condensation space).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.materials_basis_seed (bridge rows for the wax world)
  - materialsScience.scale_presence (profiles + gates)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: scale_level semantics, matching the legacy resolutions/ taxonomy.
SCALE_LEVELS = {
    0: 'experimental',   # mm-m   — measured / rules-of-mixtures
    1: 'continuum',      # µm-mm  — FEM
    2: 'mesoscale',      # nm-µm  — CGMD / DPD
    3: 'atomistic',      # Å-nm   — MD
    4: 'quantum',        # Å      — DFT
}

DERIVATION_METHODS = (
    'measured', 'rules-of-mixtures', 'homogenized', 'coarse-grained',
    'dft-parameterized', 'literature',
)


#: The material CATEGORY vocabulary (msci-22) — the primary role a
#: material plays in composite-building; finer navigation lives in
#: free-form tags. A material with several roles picks its PRIMARY
#: category and tags the rest.
MATERIAL_CATEGORIES = {
    'matrix': 'Host/binder phases composites are built IN '
              '(waxes, geopolymer, sol-gel silica, epoxies)',
    'filler': 'Functional/reinforcement phases composites are built '
              'WITH (ferrite, CNT, grog, fibers)',
    'nanoparticle': 'Nanoscale filler particles (LASiS FeOx/SiOx/'
                    'CuOx/C)',
    'structural': 'Bulk structural/refractory materials used as-is '
                  '(alumina, silicon, sintered ceramics)',
    'composite': 'Named matrix+filler combinations with their own '
                 'identity (ferrite-ceramic, geopolymer-ferrite)',
    'elemental': 'Element/compound reference materials '
                 '(silicon as a substance)',
}


class MaterialsScienceMaterial(treeObject):
    """One material identity, bridging the three legacy roots."""

    @treeObjectInit
    def __init__(
        self,
        # Identity: kebab-case key, unique ('beeswax', 'wax-filament-mvp').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # 'pure' | 'mixture' | 'composite' | 'reference'
        material_kind: str = 'pure',
        # Primary role per MATERIAL_CATEGORIES ('' = uncategorized —
        # an honest gap the browser surfaces, not an error).
        category: str = '',
        # Free-form navigation tags, JSON list of kebab-case strings
        # ('["magnetic", "refractory", "fossil-free"]').
        tags_json: str = '[]',
        # Bridges into the legacy roots (loose ids/names, '' = no link):
        # modules/.../material.py Material.id
        legacy_material_id: str = '',
        # modules/.../rawMaterials RawMaterial.name (seed rows key by name)
        raw_material_name: str = '',
        # modules/.../referenceMaterials ReferenceMaterial class name
        reference_material_name: str = '',
        # Elemental composition as ChemicalElementDefinition symbols,
        # e.g. '["C", "H", "O"]' — ties into the periodic-table space.
        element_symbols_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.material_kind = material_kind
        self.category = category
        self.tags_json = tags_json
        self.legacy_material_id = legacy_material_id
        self.raw_material_name = raw_material_name
        self.reference_material_name = reference_material_name
        self.element_symbols_json = element_symbols_json
        self.provenance_id = provenance_id
        self.notes = notes


class MaterialScaleDefinition(treeObject):
    """One material's definition AT one scale level — presence, home,
    and (when derived) lineage. Piecemeal-first: a material has only
    the rows it has honestly earned."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<material>@L<level>' by convention
        # ('beeswax@L0'); variants may suffix ('beeswax@L0-dsc').
        name: str = '',
        # MaterialsScienceMaterial.name this row belongs to.
        material_name: str = '',
        # 0-4 per SCALE_LEVELS.
        scale_level: int = 0,
        # Denormalized SCALE_LEVELS label (kept queryable/displayable).
        scale_category: str = 'experimental',
        # WHERE the actual definition lives: a class name + row ref —
        # e.g. ('RawMaterial', 'Beeswax'),
        # ('ConsistentFiniteElementMaterial', '<id>'),
        # ('SimulationDefinition', 'wax-condensation').
        definition_class: str = '',
        definition_ref: str = '',
        # 'defined' (usable) | 'partial' (exists, known-incomplete) |
        # 'planned' (declared intent only — gates treat as absent).
        status: str = 'defined',
        # Lineage when derived: another MaterialScaleDefinition.name +
        # one of DERIVATION_METHODS ('' = primary/underived).
        derived_from_name: str = '',
        derivation_method: str = '',
        # Level-specific parameters (JSON — force field, mesh size,
        # functional, mixture fractions…), inspectable at the object.
        parameters_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_name = material_name
        self.scale_level = scale_level
        self.scale_category = scale_category
        self.definition_class = definition_class
        self.definition_ref = definition_ref
        self.status = status
        self.derived_from_name = derived_from_name
        self.derivation_method = derivation_method
        self.parameters_json = parameters_json
        self.provenance_id = provenance_id
        self.notes = notes
