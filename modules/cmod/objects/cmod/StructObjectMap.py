"""
@module cmod.objects.cmod.StructObjectMap

StructObjectMap - one class per file (design section 7). HARDWARE_SYSTEM_PINS_PLAN.md section 7 (hsp-3a; D-hsp-8 ruled 2026-10-28).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructObjectMap(treeObject):
    """What it is: the DEFINITION of how a firmware struct type becomes a Polari object when it crosses a Polari Hardware Bridge - struct type -> Polari class,
    each field -> an attribute (`fields_json` = [{field, attribute, note}]). It lives at the Polari level beside the catoms (his ruling D-hsp-8: "the Bridges
    receive and use the maps but they are not where their definitions live"): several bridges reference ONE map by name, and catom assertions name the map
    whose field -> attribute pairs they ride, so a catom is tied to a bench through definitions only. The per-instance crossing (struct instance -> object id,
    the bridge it crossed, updater / timestamp) is a runtime row of the bridge, not this one.
    Related concepts: CatomAssertion (names `object_map`), PolariBridgeInstance (grpcbridge; `maps` = references), the Polari class it maps to (LightState).
    """

    plain_words = 'A struct-object map says which Polari object a firmware struct becomes once it crosses a bridge, field by field.'

    @treeObjectInit
    def __init__(self, name: str = '', struct: str = '', polari_class: str = '', fields_json: str = '[]', wire: str = '', basis: str = '', notes: str = '',
                 manager=None):
        self.name = name                  # 'LightState_t->LightState'
        self.struct = struct              # the C struct type: LightState_t
        self.polari_class = polari_class  # the Polari class: LightState
        self.fields_json = fields_json    # [{field, attribute, note}]
        self.wire = wire                  # the wire contract it travels as (the generated packets header)
        self.basis = basis
        self.notes = notes
