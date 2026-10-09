"""
@module board.objects.board.ButtonClockState

ButtonClockState — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ButtonClockState(treeObject):
    """What it is: the latest state of an UNO running the uno-button-clock variant (ucd-0e2, not yet built) — one row
    per bound board instance (brd-wire idiom, same as SimRigState / UnoAnalogState). THE WIRE CONTRACT (ucd-0e1):
    telemetry the device reports every frame, plus COMMAND fields the host sets (presence-masked PUT, the SAME
    mechanism SimRigState's led_on/pwm_duty use — never a second message kind).

    The time model (UNO_CORE_DEMO_PLAN.md §5g, adopted): `uptime_ms` is the device's own monotonic clock (never
    reset by a sync); `epoch_s`/`ms` are the device's ESTIMATE of wall-clock time, seeded and corrected by SET_TIME;
    `sync_generation` counts which SET_TIME this estimate descends from (bumped by the host on every sync);
    `sync_uncertainty_ms` is the device's own bound on how far its estimate may have drifted since that sync;
    `drift_ms` is measured ONLY at the moment of a sync (device time before the set minus the host's new time) —
    a history of least two syncs is what lets the host later derive a drift RATE, never carried on the wire itself.
    `boot_session` is minted once at reset (never equal to the packet `seq`, which free-runs within a session and
    wraps): a NEW boot_session on an otherwise-live link means the device rebooted (fresh counters, no gap alarm); the
    SAME boot_session with a `seq` gap means the transport lost frames (counted, alarmed). `status` mirrors
    SimRigState's enum idiom: idle (no command yet) | commanded (a PUT applied, not a time sync) | synced (a SET_TIME
    applied) | snapshot (this frame answers a SNAPSHOT request with the full state + replays queued events).

    Host-side only, never on the wire: `received_at` (when the relay/bridge pushed this frame) has no field here —
    UnoAnalogState carries no such field either, and this class follows the same exclusion: it belongs on the
    downstream ledger row (button-clock-ledger, 0e3), not on the wire contract.

    Related concepts: ButtonClockEvent (the sibling event class — one row per edge, telemetry only, no commands);
    SimRigState / UnoAnalogState (the wire classes this one follows field-for-field in mechanism); FirmwareVariant
    uno-button-clock (0e2 adds the app — this class's header is proven directly through the generator, not through
    `pol board gen`, until that app exists: `custom/firmware/uno/apps/` is out of scope here, see 0e1's report).
    """

    @treeObjectInit
    def __init__(self, name: str = '', seq: int = 0, boot_session: int = 0, uptime_ms: int = 0, epoch_s: int = 0,
                 ms: int = 0, clock_synced: bool = False, sync_generation: int = 0, sync_uncertainty_ms: int = 0,
                 drift_ms: int = 0, button_presses: int = 0, led_on: bool = False, led_changed_at: int = 0,
                 sense_rises: int = 0, sense_falls: int = 0, last_edge_at: int = 0, last_edge_ms: int = 0,
                 dropped_events: int = 0, status: str = '',
                 # COMMAND fields (host -> device; presence-masked, like SimRigState's led_on/pwm_duty):
                 set_epoch_s: int = 0, set_ms: int = 0, set_sync_generation: int = 0,   # = SET_TIME
                 set_led: bool = False,   # = SET_LED (host override; parity with blink-on-command)
                 snapshot: bool = False,   # = SNAPSHOT (device answers a full state frame + replays queued events)
                 manager=None):
        self.name = name  # the Push match key (RIG_NAME of the firmware)
        self.seq = seq  # wire frame counter (NOT boot_session — see the class docstring)
        self.boot_session = boot_session  # minted at reset; a new value = reboot, not a transport gap
        self.uptime_ms = uptime_ms  # monotonic device clock, never reset by a sync
        self.epoch_s = epoch_s  # device's wall-clock estimate, seconds
        self.ms = ms  # device's wall-clock estimate, milliseconds within the second
        self.clock_synced = clock_synced  # false until the first SET_TIME lands
        self.sync_generation = sync_generation  # which SET_TIME this estimate descends from
        self.sync_uncertainty_ms = sync_uncertainty_ms  # the device's own drift bound since that sync
        self.drift_ms = drift_ms  # measured AT the last sync only (device time before set - host time)
        self.button_presses = button_presses  # D2 INT0 debounced count
        self.led_on = led_on  # D6 (+ D13) state
        self.led_changed_at = led_changed_at  # epoch_s of the last LED change
        self.sense_rises = sense_rises  # D3 INT1 rising edges seen on the LED's own line
        self.sense_falls = sense_falls  # D3 INT1 falling edges seen on the LED's own line
        self.last_edge_at = last_edge_at  # epoch_s of the last D3 edge
        self.last_edge_ms = last_edge_ms  # ms (within the second) of the last D3 edge
        self.dropped_events = dropped_events  # ButtonClockEvent queue: drop-oldest count since the last read
        self.status = status  # idle | commanded | synced | snapshot
        self.set_epoch_s = set_epoch_s
        self.set_ms = set_ms
        self.set_sync_generation = set_sync_generation
        self.set_led = set_led
        self.snapshot = snapshot
