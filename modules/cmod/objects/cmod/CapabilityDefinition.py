"""
@module cmod.objects.cmod.CapabilityDefinition

CapabilityDefinition — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CapabilityDefinition(treeObject):
    """What it is: a GENERALIZED, nameable capability over a `CGraph` (demo-4, his ruling: "then we generalize that along
    with its code as 'temperature sensor solution' ... and be able to define multiple temperature sensors"). It names the
    graph the capability is drawn from, the `TargetDefinition` rows it REQUIRES (so dropping it onto the canvas shows, at
    a glance, what it still needs bound), and the class fields it exposes once wired (`exposes_fields`, e.g. 'temp_c').
    A capability is a TEMPLATE; each use on a canvas is one `CapabilityInstance` (demo-4: two temperature sensors =
    two instances of the same CapabilityDefinition, each with its own target bindings).
    Related concepts: `CGraph`, `TargetDefinition`, `CapabilityInstance`.
    """

    plain_words = ('A capability definition is a named, reusable ability a firmware drawing provides (like "read a '
                   'temperature sensor"), with the targets it needs and the fields it exposes.')

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', title: str = '', purpose: str = '', required_targets: str = '',
                 exposes_fields: str = '', instance_count: int = 0, notes: str = '', manager=None):
        self.name = name
        self.graph = graph                        # the CGraph this capability is drawn from
        self.title = title
        self.purpose = purpose
        self.required_targets = required_targets  # csv of TargetDefinition port_refs this capability needs bound
        self.exposes_fields = exposes_fields       # csv of class fields this capability makes available (temp_c)
        self.instance_count = instance_count       # derived: how many CapabilityInstance rows use this definition
        self.notes = notes
