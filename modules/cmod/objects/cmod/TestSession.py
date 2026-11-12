"""
@module cmod.objects.cmod.TestSession

TestSession - one class per file (design section 7); msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestSession(treeObject):
    """What it is: ONE PERSON WORKING THROUGH ONE TestProcedure ON ONE BuiltUnit, by the guided sheet (manual) or touch and confirm (a device's
    data passes the step, msv-3). It stops and resumes; a resumed session asks the stimulus steps again before the next measurement, so the board is
    back in the node's state. Its readings are ordinary MeasurementReadings naming it; its other steps are TestStepMarks.
    Related concepts: `TestProcedure`, `BuiltUnit`, `MeasurementReading`, `TestStepMark`.
    """

    plain_words = ('One sitting (or several) of someone testing one built device step by step.')

    @treeObjectInit
    def __init__(self, name: str = '', unit: str = '', procedure: str = '', mode: str = 'guided', who: str = '', state: str = 'open', at: str = '', resumed_at: str = '', notes: str = '', prime_window_s: float = -1.0, manager=None):
        self.name = name    # '<unit>-<procedure>-t<n>'
        self.unit = unit    # a BuiltUnit name
        self.procedure = procedure    # a TestProcedure name
        self.mode = mode    # guided | touch
        self.who = who
        self.state = state    # open | done
        self.at = at
        self.resumed_at = resumed_at    # the last resume (the stimulus steps before it are asked again)
        self.notes = notes
        self.prime_window_s = prime_window_s    # msv-3: how long a primed step waits for the meter; -1 = the knob (test_primes.PRIME_WINDOW_S)
