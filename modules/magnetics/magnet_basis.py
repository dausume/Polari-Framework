"""
@module magnetics.magnet_basis

Section A of MAGNETIC_MATERIALS_PLAN: the material option catalog
(§1c) with its REALIZATION LADDER, the functional role taxonomy
(mag-2r) whose viability is DERIVED from property rows via predicate
knobs, and the theoretical-powder designer rows (mag-2t).

Honesty spine:
- realization_level is EARNED, never declared: 'theoretical' ->
  'literature-demonstrated' -> 'recipe-seeded' -> 'made-and-measured';
  buyable_cited is the ORTHOGONAL flag derived live from supplychain
  PriceCitation rows, never stored here.
- Gates (magnet_analysis.gates_for): SIMULATION open at every level
  (watermark travels), COSTING needs buyable-cited OR recipe-seeded,
  BUSINESS/planner use needs made-and-measured.
- Role viability is derived (predicates over property values); missing
  data = 'unassessed' with the measurement ask, never assumed viable.
  Overrides are rows-with-reasons, not silent stamps.
- Property VALUES carry per-value provenance
  ('measured'|'vendor'|'literature-est'|'theoretical').

@consumers polariServer seed_pairs, magnetics.custom.magnet_analysis,
magnetics.magnet_api
"""

from objectTreeDecorators import treeObject, treeObjectInit

REALIZATION_LEVELS = ('theoretical', 'literature-demonstrated',
                      'recipe-seeded', 'made-and-measured')

#: Families group the catalog for browsing; roles decide USE.
OPTION_FAMILIES = ('soft-magnetic', 'hard-magnetic',
                   'electric-conductor', 'containment-structural',
                   'reference')

#: The form axis (mag-2r): a material can be viable for a role in one
#: form and not another — search filters on the (role, form) pair.
MATERIAL_FORMS = ('powder', 'castable-block', 'mortar', 'wire',
                  'potting', 'sintered-part', 'trace')


class MaterialUseRole(treeObject):
    """One functional role in the taxonomy (mag-2r), with
    required-property PREDICATES as editable JSON knobs so viability
    is DERIVED from property rows, never hand-stamped."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 predicates_json='{}', applicable_forms_json='[]',
                 honesty_note='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        #: {'all': [{prop, op, value, unit?}, ...]} — every predicate
        #: must hold; or {'any': [{mechanism, all: [...]}, ...]} —
        #: alternative mechanisms, the MATCHED mechanism is tagged on
        #: the verdict (flux-containment's shunt-vs-fence split).
        self.predicates_json = predicates_json
        #: JSON list of MATERIAL_FORMS where this role makes sense.
        self.applicable_forms_json = applicable_forms_json
        #: Physics honesty that TRAVELS WITH EVERY MATCH (Earnshaw on
        #: magnetic-bearing, the copper gap on signal conduction).
        self.honesty_note = honesty_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MagneticMaterialOption(treeObject):
    """One row of the §1c option catalog: identity + realization
    level + forms + property values with per-value provenance.
    Role viability is NOT stored — magnet_analysis derives it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', family='',
                 realization_level='theoretical', item_ref='',
                 msci_material_ref='', powder_ref='',
                 forms_json='[]', properties_json='{}',
                 role_overrides_json='{}', is_reference_only=False,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.family = (family if family in OPTION_FAMILIES
                       else 'reference')
        self.realization_level = (
            realization_level
            if realization_level in REALIZATION_LEVELS
            else 'theoretical')
        #: supplychain item vocabulary link ('' = not a priced item);
        #: buyable_cited/recipe-seeded checks resolve THROUGH this.
        self.item_ref = item_ref
        #: MaterialsScienceMaterial.name — object coherence: numeric
        #: mu_eff etc. REFERENCE the msci row, values here carry
        #: their own provenance tags.
        self.msci_material_ref = msci_material_ref
        #: MagneticPowderDefinition.name when this option IS a powder.
        self.powder_ref = powder_ref
        self.forms_json = forms_json
        #: {prop: {'value': float, 'unit': str, 'provenance':
        #: 'measured'|'vendor'|'literature-est'|'theoretical',
        #: 'note': str}} — None/absent = honest unknown.
        self.properties_json = properties_json
        #: {role_name: {'verdict': 'viable'|'unviable',
        #: 'reason': str}} — the admin knob, reason REQUIRED.
        self.role_overrides_json = role_overrides_json
        #: NdFeB / electrical steel: priced for parity honesty,
        #: against the local ethos for USE — reports say so.
        self.is_reference_only = is_reference_only
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MagneticPowderDefinition(treeObject):
    """One powder's intrinsic property set (mag-2t). Real powders
    cite; THEORETICAL powders are watermarked hypotheses — open in
    SIMULATION everywhere, REFUSED in cost/business (no citation can
    exist; the refusal names the sourcing hunt)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', is_theoretical=False,
                 item_ref='', mu_i=None, b_sat_t=None, h_c_ka_m=None,
                 b_r_t=None, density_kg_m3=None, particle_size_um=None,
                 sigma_s_m=None, property_provenance='literature-est',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.is_theoretical = is_theoretical
        #: supplychain item vocabulary ('' for theoretical powders —
        #: nothing to cite BY CONSTRUCTION).
        self.item_ref = item_ref
        #: Intrinsic relative permeability (linear small-signal).
        self.mu_i = mu_i
        self.b_sat_t = b_sat_t
        self.h_c_ka_m = h_c_ka_m
        self.b_r_t = b_r_t
        self.density_kg_m3 = density_kg_m3
        self.particle_size_um = particle_size_um
        self.sigma_s_m = sigma_s_m
        #: One tag for the numeric set ('theoretical' for designed
        #: powders; per-value nuance lives on the catalog option).
        self.property_provenance = property_provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
