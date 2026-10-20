"""
@module board.objects.board.BenchInteraction

BenchInteraction - one class per file (design section 7); sim-3 (HARDWARE_BENCH_CONVERGENCE_PLAN.md sections 3 and 8, D-hbc-4).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchInteraction(treeObject):
    """What it is: ONE thing a person did to a simulated board on the sim bench page - pressed its button, turned its knob, set a temperature, reset it, or changed
    which pins are watched - recorded the moment the twin acknowledged it. A session's interactions, in order, are what a person's manual test consisted of; they can be
    saved as a ScenarioRun of kind attested (a person's confirmation, never promoted to a proof by itself).

    Fields: `session` the TwinSession it happened in; `seq` its number in that session (1, 2, 3 ...); `who` the person's opaque subject id ('' when the request carried
    none - said so in `words`, never invented); `part` the part on the picture that was used (SW1) or '' for the whole board; `what` the plain-words action ("pressed
    SW1: D2 set to 0"); `kind` press | release | toggle | adc | reset | watch | other; `pin` the twin pin or ADC channel it touched; `value` the level (0/1) or the millivolts;
    `at` UTC seconds on the server when it was acknowledged; `twin_cycle` the twin's own CPU cycle from the acknowledgement (-1 when the twin's acknowledgement carries none:
    the ADC and watch acknowledgements do not); `ok` whether the twin accepted it; `reply` the twin's answer in words.

    Related concepts: TwinSession (the session), ScenarioRun (kind attested, where a session is recorded as evidence), LightState (what the board reports back).
    """

    plain_words = ('A bench interaction is one thing you did to the simulated board on the bench page - a press, a turn of the knob, a reset - kept with who did it, '
                   'when, and the exact moment in the board\'s own clock when it took effect.')

    @treeObjectInit
    def __init__(self, name: str = '', session: str = '', seq: int = 0, who: str = '', part: str = '', what: str = '', kind: str = 'other', pin: str = '',
                 value: float = 0.0, at: float = 0.0, twin_cycle: int = -1, ok: bool = True, reply: str = '', manager=None):
        self.name = name  # '<session>#<seq>'
        self.session = session
        self.seq = seq
        self.who = who
        self.part = part
        self.what = what
        self.kind = kind
        self.pin = pin
        self.value = value
        self.at = at
        self.twin_cycle = twin_cycle
        self.ok = ok
        self.reply = reply
