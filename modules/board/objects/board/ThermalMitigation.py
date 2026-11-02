"""
ThermalMitigation - one class per file (design section 7); bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ThermalMitigation(treeObject):
    """What it is: ONE THING THAT TAKES HEAT AWAY on an open-air bench, with its one cited number: a clip-on heat sink (`kind` sink, `value` its
    thermal resistance in K/W) or a breadboard fan (`kind` fan, `value` its airflow in m3/h). Every number is cited (`source`: the datasheet page or
    the measurement) or the row is a labelled knob (`source` 'knob'); none is seeded until it is cited. A `ThermalSolution` names the mitigations it
    uses; the `ThermalSystem` says which kinds are allowed.
    Related concepts: `ThermalSolution`, `ThermalSystem`, pcb `PartThermalModel` (the parts the heat comes from).
    """

    plain_words = ('A thermal mitigation is one helper that moves heat away - a clip-on heat sink or a small fan - with the one number that says how '
                   'well, and where that number came from.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'sink', part: str = '', value: float = 0.0, unit: str = 'K/W', source: str = 'knob',
                 notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.kind = kind        # sink | fan
        self.part = part        # the part's own name (a manufacturer part number is fine: it is public)
        self.value = value      # sink: Rth in K/W; fan: airflow in m3/h
        self.unit = unit        # K/W | m3/h
        self.source = source    # datasheet page / measurement / 'knob'
        self.notes = notes
