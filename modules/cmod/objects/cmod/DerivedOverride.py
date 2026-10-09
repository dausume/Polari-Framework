"""
@module cmod.objects.cmod.DerivedOverride

DerivedOverride — one class per file (design §7); ucd-attest (UNO_CORE_DEMO_PLAN.md, his ruling 2026-10-09: "all of
these need to be things that can be altered manually, so we should be able to manually change those values when we
prove them correct" -> "yes on attestation and overrides").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DerivedOverride(treeObject):
    """What it is: A PERSON'S OWN CORRECTION of one DERIVED field on one row, kept BESIDE the derivation rather than
    overwriting it (the same posture as a `ScenarioRun` of kind='attested' beside a measured one — a person's input
    is a ROW with who/when/why, never a silent edit). `target_class`/`target_name`/`field` name exactly what is being
    corrected ('PinClaim', 'uno-sim-rig:D6', 'pull'); `derived_value` is a copy of what the derivation said at the
    moment this override was authored (for the record — the LIVE derived value is still recomputed and shown fresh
    beside it every time a row is served, via `cmod.custom.overrides.apply_overrides`); `override_value` is the
    person's own replacement; `why` is required (a person's words — the override door refuses to write one without
    it). `status` is 'active' (in effect) or 'retired' (kept for the record, no longer applied) — DELETE retires,
    never deletes the row outright, so the record of the manual change survives. `name` is deterministic
    ('<target_class>:<target_name>:<field>'), so a repeat override of the SAME field is an upsert of the SAME row
    (one active override per field at a time — "an override row for the same field wins", never a growing stack of
    forgotten ones) and its own history (who changed it last, and why) is always the current row's own values.
    `provenance` is always 'canvas' (a person's own act) — there is no derived kind of this row.
    Related concepts: `PinClaim`, `TargetDefinition`, `HardwareBinding`, `RegisterAssignment.config_json` (the
    pre-existing, PinClaim-only special case this generalizes — `config_json` keeps working; an override row for
    the same field wins and is reported).
    """

    plain_words = ('A derived override is a person\'s own correction of one computed value — who changed it, when, '
                   'to what, and why — kept beside the computed value rather than erasing it.')

    @treeObjectInit
    def __init__(self, name: str = '', target_class: str = '', target_name: str = '', field: str = '',
                 derived_value: str = '', override_value: str = '', who: str = '', when: str = '', why: str = '',
                 status: str = 'active', provenance: str = 'canvas', notes: str = '', manager=None):
        self.name = name                        # '<target_class>:<target_name>:<field>'
        self.target_class = target_class        # 'PinClaim' | 'TargetDefinition' | 'HardwareBinding' (this slice)
        self.target_name = target_name           # the overridden row's own `name`
        self.field = field                       # the overridden column
        self.derived_value = derived_value       # what the derivation said when this override was authored (a record)
        self.override_value = override_value     # the person's own replacement
        self.who = who                           # the acting person's Keycloak subject id ('' when unauthenticated)
        self.when = when                         # ISO timestamp
        self.why = why                           # required — a person's words; never blank
        self.status = status                     # active | retired
        self.provenance = provenance             # always 'canvas' (a person's own act)
        self.notes = notes
