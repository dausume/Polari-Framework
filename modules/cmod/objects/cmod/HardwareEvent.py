"""
@module cmod.objects.cmod.HardwareEvent

HardwareEvent - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Edge: trigger edge").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareEvent(treeObject):
    """What it is: ONE TRIGGER a Bench Solution offers - an ACTUATION (a person presses or releases a button, hits reset, plugs the USB; the environment
    changes what a sensor reads; a period of time elapses) or an EXTERNAL SIGNAL from one of various sources (a Polari command through a bridge, a frame
    from another board or a test harness, a network message). `what` names the line or the frame; `origin` names the row it was derived from (a
    CatomAssertion's pin and event, a CatomVariable's role, a BridgePath) or 'person' when added by hand. A trigger `StructEdge` names one of these.
    Derived rows are re-derived on read (cmod.custom.bench_events); a person's rows are kept.
    Related concepts: `StructEdge`, `CatomAssertion`, `CatomVariable`, grpcbridge `BridgePath`, board `BenchSolution`.
    """

    plain_words = ('A hardware event is one thing that can happen to the bench from outside the code: a press, a release, a reset, a command '
                   'arriving, a temperature change, a timer firing.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bench_solution: str = '', kind: str = 'actuation', source: str = 'person', what: str = '',
                 value: str = '', origin: str = '', notes: str = '', manager=None):
        self.name = name                      # '<bench_solution>:<slug>'
        self.title = title
        self.bench_solution = bench_solution  # a BenchSolution name
        self.kind = kind                      # actuation | external-signal
        self.source = source                  # person | environment | time | polari | board | harness | network
        self.what = what                      # the line (PD2) or the frame kind (a command frame on uno-1-bridge)
        self.value = value                    # the level / the bytes / the sample it carries, when it carries one ('' = none)
        self.origin = origin                  # the row it came from, or 'person'
        self.notes = notes
