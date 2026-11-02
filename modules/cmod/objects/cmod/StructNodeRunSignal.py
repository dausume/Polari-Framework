"""
@module cmod.objects.cmod.StructNodeRunSignal

StructNodeRunSignal - one class per file (design section 7); bss-2 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3c).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeRunSignal(treeObject):
    """What it is: THE ASSESSMENT OF ONE MONITORED SIGNAL OR DATUM in one `StructNodeRun` - not its trace. A watched struct word: its first and last
    value, how many times it changed, the cycles of its first and last change. A wired pin: its level changes. The trace existed only in the run's
    working buffer (the twin's events); a `WaveformCapture` is kept only when a person pinned it or the edge failed (3c), and `capture` names it then.
    Related concepts: `StructNodeRun` (the parent), `StructNodeRequirement` / `StructNodeCollateral` (what asked for it), instruments `WaveformCapture`.
    """

    plain_words = 'A run signal is the summary of one thing that was watched during a run: where it started, where it ended, how often it moved.'

    @treeObjectInit
    def __init__(self, name: str = '', run: str = '', kind: str = 'field', signal: str = '', first: str = '', last: str = '', changes: int = 0,
                 first_change_cycle: int = -1, last_change_cycle: int = -1, capture: str = '', manager=None):
        self.name = name              # '<run>:<kind>:<signal>'
        self.run = run                # a StructNodeRun name
        self.kind = kind              # field | pin | frame
        self.signal = signal          # the field (led_on), the pin (PD6), the bridge
        self.first = first
        self.last = last
        self.changes = changes
        self.first_change_cycle = first_change_cycle
        self.last_change_cycle = last_change_cycle
        self.capture = capture        # a WaveformCapture name when one was kept, else ''
