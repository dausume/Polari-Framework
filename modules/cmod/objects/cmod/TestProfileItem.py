"""
@module cmod.objects.cmod.TestProfileItem

TestProfileItem - one class per file (design section 7); bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestProfileItem(treeObject):
    """What it is: ONE THING A `TestProfile` WATCHES: a struct `field` (of `object_map`; watched by address, recorded when it changes), a `pin` (its
    level changes, read from the wire when the config carries one), or a `timing` (from the edge's stimulus to its node, in the run's assessment).
    `step_s` is an explicit step for a signal when a person wants one (-1 = the rule's); `engine` says who samples it.
    Related concepts: `TestProfile` (the parent), `StructNodeRunSignal` (what comes out).
    """

    plain_words = 'One profile item is one field, pin or timing to watch.'

    @treeObjectInit
    def __init__(self, name: str = '', profile: str = '', kind: str = 'field', signal: str = '', object_map: str = '', step_s: float = -1.0, engine: str = 'twin',
                 notes: str = '', manager=None):
        self.name = name              # '<profile>:<kind>:<signal>'
        self.profile = profile        # a TestProfile name
        self.kind = kind              # field | pin | timing
        self.signal = signal          # the field name, the pin (PD6), or 'edge'
        self.object_map = object_map  # a StructObjectMap name for a field
        self.step_s = step_s
        self.engine = engine          # twin | ngspice | cauer | scope
        self.notes = notes
