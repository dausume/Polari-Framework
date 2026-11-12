"""
@module mech.objects.material.MechMaterialOption

Row class MechMaterialOption of the mech module — one class per file (design §7).
mxc-1, MECH_FREECAD_INTERCHANGE_PLAN section 3.3 / 9.1 / D-mxc-9: NO fourth
material identity. This row mirrors `magnetics.MagneticMaterialOption`'s
shape exactly (name, msci_material_ref, item_ref, properties_json
{prop: {value, unit, provenance}}, realization fields) and is REGISTERED
in `composition.custom.data_refs.MATERIAL_PROPERTY_CLASSES` so
`material_prop` / `role_viability` read it unchanged. The registry's
IARC / status / feedstock / replaced_by fields ride on top.
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.material._shared import (
    CLASS_ALIASES, CONFIDENCES, MATERIAL_CLASSES, REALIZATION_LEVELS,
    STATUSES, worst_iarc,
)


class MechMaterialOption(treeObject):
    """One material of the Polari critical-materials registry (one row
    per registry id: 'uhmwpe', 'al_6063', 'tpu_mdi') with its property
    values, each tagged with provenance. Role viability is NOT stored —
    composition's `role_viability()` derives it from properties_json."""

    @treeObjectInit
    def __init__(self, name='', display_name='', material_class='polymer',
                 realization_level='literature-demonstrated', item_ref='',
                 msci_material_ref='', forms_json='[]',
                 properties_json='{}', role_overrides_json='{}',
                 is_reference_only=False, is_prior=True,
                 status='polari_preferred', feedstocks_json='[]',
                 worst_feedstock_iarc='none', end_of_life='',
                 bio_option=False, caveats_json='[]',
                 replaced_by_json='[]', confidence='good',
                 source='', provenance_id='', notes='', manager=None):
        #: = registry id (snake_case); the key MechPartInstance,
        #: MechMaterialPreference and material_prop look up.
        self.name = name
        self.display_name = display_name
        #: MATERIAL_CLASSES; the registry's 'plastic' lands as 'polymer'.
        material_class = CLASS_ALIASES.get(material_class, material_class)
        self.material_class = (material_class
                               if material_class in MATERIAL_CLASSES
                               else 'polymer')
        #: Same ladder as magnetics / composition. Registry materials
        #: are commercial: 'literature-demonstrated' (datasheet-backed,
        #: not measured by us) until a measured row lands.
        self.realization_level = (realization_level
                                  if realization_level in REALIZATION_LEVELS
                                  else 'literature-demonstrated')
        #: supplychain item vocabulary link ('' = not a priced item).
        self.item_ref = item_ref
        #: MaterialsScienceMaterial.name — the bridge identity; ''
        #: where materialsScience has no row yet (most of them).
        self.msci_material_ref = msci_material_ref
        #: JSON list of forms this material is used in here
        #: (extrusion, sheet, filament, wire, cord, plating ...).
        self.forms_json = forms_json
        #: {prop: {'value', 'unit', 'provenance', 'note'?}} exactly as
        #: MagneticMaterialOption carries it — composition's
        #: material_prop reads this field by name. Names the roles
        #: read: tensile_mpa, hardness_hv, friction_coefficient
        #: (the headline pair), fatigue_class; plus density_kg_m3,
        #: youngs_modulus_gpa, poisson_ratio, yield_mpa,
        #: hardness_shore_a/d, hardness_rockwell_r, and
        #: friction_json whose value is {counter_id: {mu_static,
        #: mu_kinetic, basis}} ('@rolling' suffix = rolling contact).
        #: provenance: 'textbook-prior' | 'plan-knob' | 'measured' |
        #: 'vendor' | 'literature-est'. value -1 = no number held.
        self.properties_json = properties_json
        #: {role_name: {'verdict', 'reason'}} — admin knob, reason
        #: REQUIRED (same as magnetics).
        self.role_overrides_json = role_overrides_json
        #: True = kept for comparison only (every legacy_harmful row).
        self.is_reference_only = is_reference_only
        self.is_prior = is_prior
        #: STATUSES. legacy_harmful may be named on a MechPartInstance
        #: only with legacy_reason set (plan 3.3).
        self.status = status if status in STATUSES else 'polari_preferred'
        #: JSON [{name, iarc, note}] — the monomers / process
        #: chemicals / plating baths the material is made from, each
        #: with its IARC group as the registry states it.
        self.feedstocks_json = feedstocks_json
        #: Derived worst IARC group over feedstocks_json (IARC_GROUPS
        #: order); recomputed here so it can never disagree.
        try:
            feed = json.loads(feedstocks_json or '[]')
        except (TypeError, ValueError):
            feed = []
        self.worst_feedstock_iarc = (worst_iarc(feed) if feed
                                     else worst_feedstock_iarc)
        self.end_of_life = end_of_life
        self.bio_option = bool(bio_option)
        #: JSON list of strings — the named caveats behind a
        #: polari_acceptable status.
        self.caveats_json = caveats_json
        #: JSON list of registry ids that replace a legacy material.
        self.replaced_by_json = replaced_by_json
        #: 'good' | 'check' — 'check' rows (AEM, the wood rows) need
        #: the monograph read before anyone relies on them.
        self.confidence = (confidence if confidence in CONFIDENCES
                           else 'check')
        #: 'collab-mech-parts' (the econ-core registry) or
        #: 'mech-mxc-1' (rows mech added: birch_plywood, mdf).
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
