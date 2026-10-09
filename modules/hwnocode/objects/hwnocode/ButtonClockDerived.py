"""
@module hwnocode.objects.hwnocode.ButtonClockDerived

ButtonClockDerived — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ButtonClockDerived(treeObject):
    """What it is: the small DERIVED class the backend solution `button-clock-ledger` writes (ucd-1, UNO_CORE_DEMO_PLAN.md
    §5 D-ucd-5), one row per board instance of the uno-button-clock demo — the SAME relationship SimRigTempDerived has to
    SimRigState/SimRigTempSample, but over ButtonClockState/ButtonClockEvent: `presses_per_min` (count of `press` events in
    the last 60 s of the device's OWN `uptime_ms`, scaled up while the device has been up less than a minute), the invariant
    verdict (`sense_rises + sense_falls == button_presses` and `led_on == (sense_rises > sense_falls)` — D3's independent
    witness of the LED line, UNO_CORE_DEMO_PLAN.md §1) with `invariant_why` naming the actual numbers on a break, never just
    'false', `events_seen` (how many ButtonClockEvent rows existed at the moment this was computed — before any retention
    prune), `dropped_events_total` (mirrors the wire's own `ButtonClockState.dropped_events`), `last_sync_generation` /
    `drift_ms` (mirrors the wire's own SET_TIME bookkeeping, so a person reads clock health here too). `received_at` is the
    SERVER's own wall clock at commit time (allowed — it is the server's clock, never a device/host fact, UNO_CORE_DEMO_PLAN.md
    §5c); `computed_at` is when THIS row was last written (may differ from `received_at` if computed off a prune pass).
    Related concepts: `ButtonClockState`/`ButtonClockEvent` (board module, the wire classes), `SimRigTempDerived` (the
    uno-temp-split sibling this follows field-for-field in mechanism), `hwnocode.custom.button_clock` (the compute).
    """

    plain_words = ('The button-clock ledger is the server\'s running view of the button-and-LED demo: how often the '
                   'button is pressed, whether the board\'s own count of presses agrees with the independent witness '
                   'wire, and how well its clock is synced.')

    @treeObjectInit
    def __init__(self, name: str = '', board_instance: str = '', presses_per_min: float = 0.0, invariant_ok: bool = True,
                 invariant_why: str = '', events_seen: int = 0, dropped_events_total: int = 0, last_sync_generation: int = 0,
                 drift_ms: int = 0, received_at: str = '', computed_at: str = '', manager=None):
        self.name = name                              # = board_instance (one row per board, ucd-1 has exactly one)
        self.board_instance = board_instance
        self.presses_per_min = presses_per_min
        self.invariant_ok = invariant_ok
        self.invariant_why = invariant_why            # plain words naming the numbers when invariant_ok is False
        self.events_seen = events_seen
        self.dropped_events_total = dropped_events_total
        self.last_sync_generation = last_sync_generation
        self.drift_ms = drift_ms
        self.received_at = received_at                # server wall clock when this computation ran
        self.computed_at = computed_at
