"""
@module pcb.objects.pcb.PartPowerInput

PartPowerInput — one class per file (design §7); bob-3g, the Boards on the Bench plan (AI-Notes/plans/BENCH_BOARDS_PLAN.md bob-3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PartPowerInput(treeObject):
    """What it is: THE POWER A PERSON GIVES for one placed part of one PCB, instead of (or before) a simulation run - its watts and, for the thermal
    view over time, how it is switched: on for the whole run (on_s 0), one pulse of on_s seconds (period_s 0), or on for on_s at the start of every
    period_s (a duty cycle). A given figure wins over the run's average for that part; clearing it hands the part back to the run.
    Every value -1 is 'not given' (power_w) - 0 W is a real figure (the part is off).
    Related concepts: `PartThermalModel` (the part's own datasheet thermal behaviour), `SpiceRun` (the run's figures), the Board Details Thermal tabs.
    """

    plain_words = 'How much power one part on a board uses, typed in by a person, and whether it is on all the time, once, or in pulses.'

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', power_w: float = -1.0, on_s: float = 0.0, period_s: float = 0.0,
                 origin: str = 'given on the page', notes: str = '', manager=None):
        self.name = name            # '<board>:<ref>'
        self.board = board          # the PcbBoard name
        self.ref = ref              # the part's reference (R4, U1) - its PcbPad ref
        self.power_w = power_w      # W while on; -1 = not given (the run's figure is used)
        self.on_s = on_s            # 0 = on for the whole run; > 0 = on for this many seconds (per period when period_s > 0)
        self.period_s = period_s    # 0 = a single pulse (or always on); > 0 = repeat every period_s seconds
        self.origin = origin        # who / what gave it, in words
        self.notes = notes
