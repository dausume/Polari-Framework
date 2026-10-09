"""
@module hwnocode.custom.button_clock

THE BACKEND LEDGER'S ARITHMETIC for `uno-button-clock` (ucd-1, UNO_CORE_DEMO_PLAN.md §5 D-ucd-5) — the compute half of the
backend solution `button-clock-ledger` (hwnocode.custom.button_clock_ledger), registered as the AnalysisDefinition
`hwnocode-button-clock-derive` and run by the engine's EXISTING AnalysisCall node (`fn(manager, **params) -> dict`,
polariNoCode.analysis_calls — the SAME seam `hwnocode.custom.derive.temp_derive` uses for uno-temp-split).

One frame in (the bridge already upserted the LATEST `ButtonClockState` row onto the board instance's own name — this
module never duplicates that write, it only READS the row) →
  (a) `presses_per_min`: the count of `press` ButtonClockEvent rows within the last 60 s of the device's OWN
      `uptime_ms` (monotonic, always valid even before the first SET_TIME — never the wall clock), scaled up while the
      device has been up less than a minute so an early reading is not understated;
  (b) the invariant (UNO_CORE_DEMO_PLAN.md §1): `sense_rises + sense_falls == button_presses` (D3 is the independent
      witness of the LED line) and `led_on == (sense_rises > sense_falls)` — a break NAMES the actual numbers, never
      just "false";
  (c) a `ButtonClockDerived` row upserted (one per board instance) with those two results plus the wire's own health
      fields (`dropped_events`, `sync_generation`, `drift_ms`) mirrored through for one-stop reading.

Retention (D-ucd-5's knob, default 10 000) is a SEPARATE pure function (`prune_events`) + a door the relay calls
(`hwnocode_api.on_post_button_clock_prune`) — never run inside this per-frame compute, so a frame push is never blocked
on a bulk prune pass of a bounded-but-large event table (the house rule named in the task: "never in a request path
that a frame push blocks on").
"""
import datetime

from hwnocode.custom.derive import _rows, _create, _save  # the manager-agnostic row helpers (reused, not duplicated)

#: D-ucd-5 (UNO_CORE_DEMO_PLAN.md §5): the event ledger's bound — beyond this many ButtonClockEvent rows, the oldest
#: (by boot_session then seq — the wire's own ordering, never wall-clock, since epoch_s may be unsynced) are pruned.
#: 10 000 is the plan's own recommended default (a bare-C demo at a handful of edges/second keeps days of history).
RETENTION = 10000

#: UNO_CORE_DEMO_PLAN.md §3 "Relay-out (SET_TIME ... every SYNC_EVERY_S)" — the knob naming how often the host
#: resyncs the device's wall-clock estimate after the attach-time sync (actually issuing that PUT on a timer is bridge/
#: installer lifecycle work out of scope here, ucd-0e3/ucd-4; this module only names the knob the no-code canvas reads).
SYNC_EVERY_S = 300

ANALYSIS = 'hwnocode-button-clock-derive'


def invariant(sense_rises, sense_falls, button_presses, led_on):
    """(ok, why) — UNO_CORE_DEMO_PLAN.md §1's two checks, named with the actual numbers on a break, never just a bool."""
    sense_rises, sense_falls, button_presses = int(sense_rises or 0), int(sense_falls or 0), int(button_presses or 0)
    led_on = bool(led_on)
    edges = sense_rises + sense_falls
    ok_count = edges == button_presses
    ok_led = led_on == (sense_rises > sense_falls)
    if ok_count and ok_led:
        return True, ('ok: sense_rises(%d) + sense_falls(%d) == button_presses(%d); led_on(%s) == '
                       '(sense_rises > sense_falls)(%s)' % (sense_rises, sense_falls, button_presses, led_on, sense_rises > sense_falls))
    why = []
    if not ok_count:
        why.append('sense_rises(%d) + sense_falls(%d) = %d != button_presses(%d)' % (sense_rises, sense_falls, edges, button_presses))
    if not ok_led:
        why.append('led_on(%s) != (sense_rises(%d) > sense_falls(%d)) = %s' % (led_on, sense_rises, sense_falls, sense_rises > sense_falls))
    return False, 'broken: ' + '; '.join(why)


def _presses_per_min(events, now_uptime_ms):
    """count of `press` events within the last 60 s of the device's own monotonic clock, scaled up if the device has
    been up less than a minute (so an early reading right after boot does not read as artificially low)."""
    window_ms = 60000
    window_start = now_uptime_ms - window_ms
    in_window = [e for e in events if str(getattr(e, 'kind', '')) == 'press' and window_start <= int(getattr(e, 'uptime_ms', 0) or 0) <= now_uptime_ms]
    span = max(1, min(window_ms, now_uptime_ms)) if now_uptime_ms > 0 else window_ms
    return len(in_window) * window_ms / float(span)


def _latest_state(manager, board_instance):
    states = [r for r in _rows(manager, 'ButtonClockState') if not board_instance or str(getattr(r, 'name', '')) == board_instance]
    if not states:
        states = _rows(manager, 'ButtonClockState')
    return states[0] if states else None


def button_clock_derive(manager, board_instance='', object='', solution=''):
    """The AnalysisCall callable (`fn(manager, **params) -> dict`): reads the latest ButtonClockState row + every
    ButtonClockEvent row, computes presses_per_min + the invariant, upserts ButtonClockDerived, and returns the
    numbers the backend solution's StateChangeCommit state binds back onto the row (the temp-analysis idiom: this
    function may ALSO persist directly — the engine's own commit then re-asserts the same fields, never a second
    source of truth, just the same belt-and-suspenders temp_derive uses)."""
    name = str(board_instance or object or '')
    state = _latest_state(manager, name)
    if state is None:
        return {'ok': False, 'error': 'no ButtonClockState row yet (board_instance=%r) — the bridge has not pushed a frame' % name}
    name = name or str(getattr(state, 'name', '')) or 'uno-button-clock'
    events = _rows(manager, 'ButtonClockEvent')
    now_uptime = int(getattr(state, 'uptime_ms', 0) or 0)
    ppm = round(_presses_per_min(events, now_uptime), 3)
    ok, why = invariant(getattr(state, 'sense_rises', 0), getattr(state, 'sense_falls', 0),
                        getattr(state, 'button_presses', 0), getattr(state, 'led_on', False))
    now_iso = datetime.datetime.now().isoformat(timespec='milliseconds')
    fields = {'board_instance': name, 'presses_per_min': ppm, 'invariant_ok': ok, 'invariant_why': why,
             'events_seen': len(events), 'dropped_events_total': int(getattr(state, 'dropped_events', 0) or 0),
             'last_sync_generation': int(getattr(state, 'sync_generation', 0) or 0), 'drift_ms': int(getattr(state, 'drift_ms', 0) or 0),
             'received_at': now_iso, 'computed_at': now_iso}
    row = next((r for r in _rows(manager, 'ButtonClockDerived') if str(getattr(r, 'name', '')) == name), None)
    if row is None:
        _create(manager, 'ButtonClockDerived', dict(fields, name=name))
    else:
        for k, v in fields.items():
            setattr(row, k, v)
        _save(manager, row)
    return {'ok': True, 'board_instance': name, 'presses_per_min': ppm, 'invariant_ok': ok, 'invariant_why': why,
            'events_seen': len(events), 'dropped_events_total': fields['dropped_events_total'],
            'last_sync_generation': fields['last_sync_generation'], 'drift_ms': fields['drift_ms']}


def rows_to_prune(manager, retention=RETENTION):
    """PURE: which ButtonClockEvent rows are beyond `retention`, oldest-first by (boot_session, seq) — the wire's own
    ordering (never wall-clock: epoch_s may be unsynced). Nothing is deleted here."""
    events = _rows(manager, 'ButtonClockEvent')
    retention = max(0, int(retention or 0))
    if len(events) <= retention:
        return []
    ordered = sorted(events, key=lambda e: (int(getattr(e, 'boot_session', 0) or 0), int(getattr(e, 'seq', 0) or 0)))
    excess = len(ordered) - retention
    return ordered[:excess]


def prune_events(manager, retention=RETENTION):
    """The door's action: delete what `rows_to_prune` names, oldest-first, keep the newest `retention`. Never called
    from the per-frame compute path (button_clock_derive) — a separate door/CLI act, D-ucd-5."""
    doomed = rows_to_prune(manager, retention)
    tables = (getattr(manager, 'objectTables', None) or {}).get('ButtonClockEvent') or {}
    deleter = getattr(manager, 'deleteTreeNode', None)
    removed = 0
    for row in doomed:
        rid = getattr(row, 'id', None)
        done = False
        if deleter is not None and rid:
            try:
                deleter(className='ButtonClockEvent', nodePolariId=rid)
                done = True
            except Exception:  # noqa: BLE001 — fall through to the managerless-selftest pop below
                done = False
        if not done:
            for k, v in list(tables.items()):
                if v is row:
                    tables.pop(k, None)
                    done = True
                    break
        if done:
            removed += 1
    kept = len(_rows(manager, 'ButtonClockEvent'))
    return {'ok': True, 'removed': removed, 'kept': kept, 'retention': retention}


def chart_rows(manager, board_instance='', last=200):
    """The /display/uno-core-demo sci-xy-chart's rows, oldest first: uptime_ms (+ the _s convenience), the event kind,
    and three RUNNING CUMULATIVE counters (presses, rises, falls) so the chart reads as the demo's own events-over-time
    line plot (UNO_CORE_DEMO_PLAN.md §3's alternative to a numeric-lane encoding — the plan accepts either)."""
    events = [e for e in _rows(manager, 'ButtonClockEvent')]
    events.sort(key=lambda e: (int(getattr(e, 'boot_session', 0) or 0), int(getattr(e, 'seq', 0) or 0)))
    rows, presses, rises, falls = [], 0, 0, 0
    for e in events:
        kind = str(getattr(e, 'kind', ''))
        if kind == 'press':
            presses += 1
        elif kind == 'sense_rise':
            rises += 1
        elif kind == 'sense_fall':
            falls += 1
        uptime_ms = int(getattr(e, 'uptime_ms', 0) or 0)
        rows.append({'uptime_ms': uptime_ms, 'uptime_s': round(uptime_ms / 1000.0, 3), 'kind': kind,
                     'presses_cum': presses, 'rises_cum': rises, 'falls_cum': falls,
                     'seq': int(getattr(e, 'seq', 0) or 0), 'boot_session': int(getattr(e, 'boot_session', 0) or 0)})
    return rows[-int(last or 200):]
