"""
@module cmod.objects.cmod.HardwareEventState

HardwareEventState - one class per file (design section 7). Node kind 2 of 2 of a Bench Topology drawing (bss-5, BENCH_SOLUTION_SIM_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.topology_palette import palette


class HardwareEventState(treeObject):
    """What it is: the `hardware-event` NODE KIND, category **Bench Topology** - one `StructEdge` drawn as the box BETWEEN two struct nodes (the user,
    2026-11-02: "topologies of Struct states and Hardware Event States"): what moves the bench from one situation to the next - a Hardware Event
    (its title, kind, source and what), or the flash, the init, a cascade. Authored: the drawing writes back ONLY the title of a trigger's Hardware
    Event; the edge itself changes through the doors.
    Related concepts: `StructEdge`, `HardwareEvent`, `StructNodeState`, `cmod.custom.bench_topology_nocode`.
    """

    plain_words = 'One thing that happens between two situations of the bench: a press, a command, a timer, the flash, or the code itself.'

    statePalette = palette('hardware-event', 'Hardware event', plain_words,
                           [('title', 'What happens'), ('kind', 'Edge kind'), ('source', 'Source'), ('what', 'Line or frame'), ('event', 'Event row')], icon='bolt')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = '', source: str = '', what: str = '', event: str = '', manager=None):
        self.name = name
        self.title = title
        self.kind = kind
        self.source = source
        self.what = what
        self.event = event
