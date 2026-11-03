"""
ClockSource - one class per file (design section 7); cfg-1 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The clock group in detail").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ClockSource(treeObject):
    """What it is: ONE CLOCK SOURCE'S CITED DATASHEET BOUNDS - the thing that makes a chip's clock (a ceramic resonator, a crystal, the chip's own RC
    oscillator, an external oscillator) and how far its frequency may sit from nominal: the initial tolerance, the drift over a temperature range, the
    aging, each a maximum the datasheet prints. The bounds are used AS BOUNDS (the worst case anywhere in the range; unrated outside it), never drawn as
    curves the document does not give (the tmp-4 rule). board.custom.timing_drift reads these rows (its CLOCKS table is their seed) and the clock group's
    checks (cmod.custom.clock_checks) judge a serial link or a tick against them.
    Related concepts: `ClockPeer` (the far end of a link and its clock), `BenchConditions` (the ambient range the bound is taken over), cmod `ConfigOption`.
    """
    plain_words = ('A clock source is the part that sets how fast a chip runs, and this row says how far off its speed may be, straight from its '
                   'datasheet: a bit off when new, a bit more when hot or cold, a bit more with age.')

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = 'resonator', f_hz: float = 0.0, initial_pct: float = 0.0, temp_pct: float = 0.0, t_min_c: float = 0.0,
                 t_max_c: float = 0.0, aging_pct: float = 0.0, boards: str = '', what: str = '', source: str = '', notes: str = '', manager=None):
        self.name = name                # e.g. 'cstce16m0v53-r0'
        self.kind = kind                # resonator | crystal | rc | oscillator
        self.f_hz = f_hz                # nominal frequency
        self.initial_pct = initial_pct  # max initial tolerance (%)
        self.temp_pct = temp_pct        # max drift over t_min_c .. t_max_c (%)
        self.t_min_c = t_min_c
        self.t_max_c = t_max_c
        self.aging_pct = aging_pct      # max aging (%)
        self.boards = boards            # comma-separated BoardDefinition names whose main chip it clocks ('' = a catalogue entry)
        self.what = what
        self.source = source            # the datasheet, page and table
        self.notes = notes
