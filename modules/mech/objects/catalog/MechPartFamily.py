"""
@module mech.objects.catalog.MechPartFamily

Row class MechPartFamily of the mech module — one class per file (design §7).
mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.1, §9.1: the family is NEW — standards,
dimension tables, variants and licences exist nowhere else — but carries
`archetype_ref` into composition.PartArchetypeDefinition and does NOT re-list
equations / failure modes / roles). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechPartFamily(treeObject):
    """ONE STANDARD OR GEOMETRIC ARCHETYPE at the standards level — no
    design in it. The electronics parallel is a BoardDefinition: what the
    part IS, how its variants are picked (the size key + a length rule),
    the dimension table per size, and the FEATURE TEMPLATES every variant
    of the family exposes. Material is by id into the materials registry
    (another agent's rows); geometry is regenerated from parameters by a
    named generator (D-mxc-3), '' until mxc-3b writes it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', category='hardware',
                 archetype_ref='', standard='', standard_url='',
                 variant_axes_json='[]', size_key_rule='',
                 dimension_table_json='{}', length_rule_json='{}',
                 interfaces_json='[]', generator='', generator_version='',
                 dimension_source_ref='', material_default_ids_json='[]',
                 material_alternative_ids_json='[]',
                 material_legacy_ids_json='[]', is_prior=True,
                 provenance_id='', notes='', manager=None):
        #: The naming contract key: 'iso4762', 'extrusion', 'gridfinity-bin'...
        self.name = name
        self.display_name = display_name
        #: One of catalog._shared.CATEGORIES.
        self.category = category
        #: composition.PartArchetypeDefinition name ('at-screw', 'at-shaft'
        #: ...). Equations, failure modes and material roles are read THERE.
        self.archetype_ref = archetype_ref
        #: 'ISO 4762' | 'DIN 508' | 'Gridfinity 1.0' | '' (vendor-generic).
        self.standard = standard
        self.standard_url = standard_url
        #: The VARIANT_AXES this family varies along, in order.
        self.variant_axes_json = variant_axes_json
        #: How a variant's size key is formed from the axes, e.g.
        #: '<thread>x<nominal_length>' or '<series>-L<cut_length>'.
        self.size_key_rule = size_key_rule
        #: {size_key_value: {named dims}} — the upstream table, one row per
        #: size, dimension names as the standard names them (P, b, dk, k,
        #: s ...). Numbers only; -1 = not given by the table.
        self.dimension_table_json = dimension_table_json
        #: {'kind': 'none' | 'stepped' | 'continuous', ...}: stepped =
        #: {'series': [standard lengths], 'per_size': {size: [min, max]}}
        #: (the WB *range tables); continuous = {'min', 'max', 'step'}.
        self.length_rule_json = length_rule_json
        #: Feature TEMPLATES: [{'kind', 'key', 'role', 'count' | 'count_rule',
        #: 'dims' (by reference into the dimension row: 'dk', 'cw'...),
        #: 'dof_free', 'origin_rule', 'axis', 'notes'}]. Resolved per
        #: variant into MechFeature rows; '{thread}' / '{cw}' placeholders
        #: are filled from the size row.
        self.interfaces_json = interfaces_json
        #: Name of the geometry generator (a MathShape form, mxc-3b); ''
        #: until one exists — the catalogue is honest that nothing draws
        #: this part yet.
        self.generator = generator
        self.generator_version = generator_version
        #: DimensionSource name the table came from. REQUIRED (selftest).
        self.dimension_source_ref = dimension_source_ref
        #: materials_registry ids (strings) — the Polari default(s) for this
        #: part, from collab/mech-parts/data/part_material_roles.json.
        self.material_default_ids_json = material_default_ids_json
        self.material_alternative_ids_json = material_alternative_ids_json
        #: Legacy / harmful materials found in existing kits, for comparison
        #: only — never a default.
        self.material_legacy_ids_json = material_legacy_ids_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
