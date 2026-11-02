"""
ThermalSystem - one class per file (design section 7); bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5, "template").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ThermalSystem(treeObject):
    """What it is: THE THERMAL TEMPLATE of a bench concept - the choices still open: which kinds of mitigation are ALLOWED (none, a clip-on heat
    sink, a breadboard fan; the user, 2026-11-01: Bench Solutions are open air for now, a sink and a fan are allowed, enclosures and venting are
    deferred to the embedding stage) and the ambient range the concept is meant for. A `ThermalSolution` makes the choices; its `BenchConditions`
    must fall inside this range (the whole check says so in words when they do not).
    Related concepts: `ThermalSolution`, `ThermalMitigation`, `BenchSystem` (composes it), `BenchConditions`.
    """

    plain_words = ('A thermal system is the template for how a bench concept handles heat: open air, which helpers are allowed (none, a clip-on '
                   'heat sink, a small fan) and the room temperatures it is meant for.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', air: str = 'open', mitigations_allowed: str = 'none,sink,fan', ambient_min_c: float = 15.0,
                 ambient_max_c: float = 35.0, notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.air = air                                  # open (the only value for now; enclosed / vented come with the embedding stage)
        self.mitigations_allowed = mitigations_allowed  # comma-separated ThermalMitigation kinds: none | sink | fan
        self.ambient_min_c = ambient_min_c              # the range the concept is meant for; a Solution's conditions must sit inside it
        self.ambient_max_c = ambient_max_c
        self.notes = notes
