"""
@module cmod.objects.cmod.TestStepPrime

TestStepPrime - one class per file (design section 7); msv-3 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b, touch and confirm).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestStepPrime(treeObject):
    """What it is: ONE PRIMED MEASURE STEP - the step armed to expect the meter's data within a window, so a person keeps both hands on the probes
    and the button. The user (2026-11-04): "People only have two hands, they cannot hit the button and be doing the probe at the same time, what
    you can do is prime it to expect a signal soon and it waits for a certain (configurable) period of time and awaits the data, confirming it once
    it comes." It confirms as soon as a steady value a correct build may read arrives. At the window's end it keeps the last steady value (a fault
    reads steady too), or says no data / not steady / wrong mode.
    Related concepts: `TestSession`, `TestProcedureStep`, `MeasurementReading`, instruments `InstrumentEndpoint`.
    """

    plain_words = ('A measurement step set to wait for the meter: you probe, and it records the value by itself once it settles.')

    @treeObjectInit
    def __init__(self, name: str = '', session: str = '', step: str = '', endpoint: str = '', instrument: str = '', source: str = 'endpoint', window_s: float = 30.0, armed_at: str = '', ends_at: str = '', state: str = 'armed', reading: str = '', lines_seen: int = 0, chain: bool = False, note: str = '', manager=None):
        self.name = name    # '<session>:<step>#p<n>'
        self.session = session    # a TestSession name
        self.step = step    # a measure TestProcedureStep
        self.endpoint = endpoint    # the sigrok InstrumentEndpoint listened to ('' = lines from a Bridge)
        self.instrument = instrument    # the meter model (its accuracy judges)
        self.source = source    # endpoint | bridge
        self.window_s = window_s    # how long it waits for the data
        self.armed_at = armed_at
        self.ends_at = ends_at
        self.state = state    # armed | confirmed | kept-last | not-steady | wrong-mode | no-data | cancelled
        self.reading = reading    # the MeasurementReading it kept
        self.lines_seen = lines_seen    # how many meter lines came through
        self.chain = chain    # on confirmation, prime the next measure step with the same meter
        self.note = note
