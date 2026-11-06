"""
@module mech.objects.material.MechMaterialPreference

Row class MechMaterialPreference of the mech module — one class per file
(design §7). mxc-1, plan section 9.1 (the `MaterialRole` row, renamed):
NOT a third role taxonomy. One row per part category of the registry's
part_material_roles → default / alternative / legacy registry ids, plus
`role_refs_json` naming the COMPOSITION roles the part plays (keys of
composition.custom.part_roles.ROLE_REQUIREMENTS). A preference is
checked by `role_viability()` against the option's properties
(mech.custom.material_registry.preference_check), never by predicates
of its own.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechMaterialPreference(treeObject):
    """Which registry materials a part category defaults to, may use,
    and used to be made of — with the composition roles that decide
    whether a given material is viable for it."""

    @treeObjectInit
    def __init__(self, name='', category='', part='', display_name='',
                 default_ids_json='[]', alternative_ids_json='[]',
                 legacy_ids_json='[]', polari_default_json='[]',
                 polari_alternatives_json='[]', legacy_harmful_json='[]',
                 role_refs_json='[]', notes='', is_prior=True,
                 provenance_id='', manager=None):
        #: Unique key: the part string slugged ('deep_groove_ball_bearing',
        #: 'low_friction_slider_pad'); registry categories repeat
        #: (frame_joint x3, linear x5) so the part is the key.
        self.name = name
        #: Registry family: frame_profile, frame_joint, slot_fastener,
        #: screw, nut, washer, insert, standoff, rod_pin,
        #: retaining_ring, bearing, linear, transmission, misc,
        #: printed_part.
        self.category = category
        #: The registry's part string as written ('T-nut (sliding /
        #: drop-in / roll-in)').
        self.part = part
        self.display_name = display_name or part
        #: JSON lists of MechMaterialOption names (registry ids), the
        #: flattened form: 'steel_carbon+zinc_trivalent' contributes
        #: both ids. Duplicates removed, order kept.
        self.default_ids_json = default_ids_json
        self.alternative_ids_json = alternative_ids_json
        self.legacy_ids_json = legacy_ids_json
        #: The registry's COMBINATION strings as written ('steel_carbon
        #: (52100) + steel_carbon shield (ZZ)') — the substrate+finish
        #: pairing the flat id lists lose.
        self.polari_default_json = polari_default_json
        self.polari_alternatives_json = polari_alternatives_json
        self.legacy_harmful_json = legacy_harmful_json
        #: JSON list of composition role names (ROLE_REQUIREMENTS keys
        #: only: sliding, static-structural, press-fitted, moving,
        #: colliding, torque-magnet-active ...). A slide = sliding +
        #: static-structural; a screw = static-structural; a seal =
        #: sliding. Empty = the part plays no property-checked role
        #: (cable insulation).
        self.role_refs_json = role_refs_json
        self.notes = notes
        self.is_prior = is_prior
        self.provenance_id = provenance_id
