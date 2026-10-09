"""
@module board.objects.board.ButtonClockEvent

ButtonClockEvent — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ButtonClockEvent(treeObject):
    """What it is: ONE transition of the uno-button-clock demo (ucd-0e2, not yet built) — a press, an LED change, a
    sensed edge on D3, or a clock sync — stamped with the device's own clock at the moment it happened. Telemetry
    ONLY: no command fields (compare ButtonClockState, which carries both telemetry and the SET_TIME/SET_LED/SNAPSHOT
    command fields). The device queues these drop-oldest (ButtonClockState.dropped_events counts what was lost) and
    replays the queue on a SNAPSHOT.

    `boot_session` is carried here too (not only on ButtonClockState) so a consumer reading ONLY the event stream can
    still tell a reboot (new boot_session) from a transport gap (same boot_session, a hole in `seq`) without cross
    -referencing the state class.

    Related concepts: ButtonClockState (the sibling state class — the same seq/boot_session/uptime_ms/epoch_s/ms
    quartet, so one wire class's frame can be correlated against the other's by time, never by inference).
    """

    @treeObjectInit
    def __init__(self, name: str = '', seq: int = 0, boot_session: int = 0, kind: str = '', uptime_ms: int = 0,
                 epoch_s: int = 0, ms: int = 0, manager=None):
        self.name = name  # the Push match key (one row per event; never converged/reused across events)
        self.seq = seq  # wire frame counter of the EVENT stream (independent of ButtonClockState's own seq)
        self.boot_session = boot_session  # the device reset epoch this event happened within
        self.kind = kind  # press | led_on | led_off | sense_rise | sense_fall | sync
        self.uptime_ms = uptime_ms  # device's monotonic clock at the moment of the transition
        self.epoch_s = epoch_s  # device's wall-clock estimate at the moment of the transition, seconds
        self.ms = ms  # ... milliseconds within the second
