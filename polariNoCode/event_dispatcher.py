"""
@module polariNoCode.event_dispatcher

cal-2 — the runtime behind EventTrigger rows: "when X happens, run
solution Y", with every firing a TriggerFiring ROW.

Sources → entry points:
  object    dispatch_object_change(manager, class, op, ids)
            — called from the CRUDE lifecycle hook
              (grpcbridge.custom.transport_mux.publish_crude_change) and
              from the GenerateEvent/ModifyEvent nodes' own writes
  event     dispatch_trace_events(manager, trace, params)
            — called by SolutionExecutionEngine.execute() after a
              top-level run; reads `_emitted_events`
  schedule  EventDispatcher.tick(now) — occurrences of the trigger's
  window    schedule / events entering the window; one tick thread
            (POLARI_EVENT_TICK_S, default 60; '0' disables)

Every firing runs the solution as ONE complete execution through
graph_builder.execute (the advance() idiom — no pause/resume),
bounded by max_depth (chained events), cooldown_s, and idempotent
by occurrence_key. Failures are rows with the error text; a
disabled trigger is a 'refused' row with the reason. Nothing here
raises into CRUDE or the engine (belt and braces at both callers).

@consumers polariCRUDE (via transport_mux), SolutionExecutionEngine,
  polariServer (tick thread), the nutrition triggers (cal-4)
"""

import json
import threading
import traceback
import uuid
from datetime import datetime, timedelta

from polariNoCode.calendar_events import (
    _loads, _rows, calendar_by_name, definition_by_name,
    resolve_calendar_events, resolve_definition_events,
)
from polariNoCode.recurrence import expand_schedule

TRIGGER_DEPTH_KEY = '_trigger_depth'
TRIGGER_NAME_KEY = '_trigger_name'
TRIGGER_SOURCE_KEY = '_trigger_source'
_SCALAR = (str, int, float, bool, type(None))


# ---------------------------------------------------------------
# instance creation — the CRUDE idiom, with a fake-manager fallback
# ---------------------------------------------------------------

def create_instance(manager, class_name, fields, depth=0, notify=True):
    """A new row of `class_name` through the same create path CRUDE
    uses (the typing's create method + saveInstanceInDB); on a
    manager without typing (selftests) a plain namespace row is
    registered in objectTables. Returns the instance."""
    from types import SimpleNamespace
    fields = dict(fields or {})
    fields.setdefault('name', f'{class_name.lower()}-{uuid.uuid4().hex[:8]}')
    typing = (getattr(manager, 'objectTypingDict', None) or {}).get(class_name)
    inst = None
    if typing is not None and hasattr(typing, 'getCreateMethod'):
        create = typing.getCreateMethod(returnTupWithParams=True)
        inst = create(**fields, manager=manager)
    else:
        inst = SimpleNamespace(id=uuid.uuid4().hex[:10], **fields)
        tables = getattr(manager, 'objectTables', None)
        if tables is not None:
            tables.setdefault(class_name, {})[inst.id] = inst
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(inst)
        except Exception as e:  # never break the caller
            print(f'[EventDispatcher] could not persist {class_name} '
                  f'{fields.get("name")}: {e}', flush=True)
    if notify:
        dispatch_object_change(manager, class_name, 'create',
                               [str(getattr(inst, 'id', ''))], depth=depth)
    return inst


def find_instance(manager, class_name, ref):
    ref = str(ref)
    for inst in _rows(manager, class_name):
        if ref in (str(getattr(inst, 'name', '')), str(getattr(inst, 'id', '')),
                   str(getattr(inst, 'polariId', ''))):
            return inst
    return None


def save_instance(manager, inst):
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(inst)


def snapshot(inst):
    """Scalar attributes of a row — the payload an object trigger hands
    its solution."""
    out = {}
    for k, v in vars(inst).items() if hasattr(inst, '__dict__') else []:
        if k.startswith('_') or k in ('manager', 'inTree', 'branch'):
            continue
        if isinstance(v, _SCALAR):
            out[k] = v
    return out


# ---------------------------------------------------------------
# the dispatcher
# ---------------------------------------------------------------

class EventDispatcher:
    def __init__(self, manager, tick_seconds=60):
        self.manager = manager
        self.tick_seconds = tick_seconds
        self._lock = threading.RLock()
        self._last_tick = None
        self._thread = None
        self._stop = threading.Event()

    # ---- rows ----
    def triggers(self, kind=None):
        rows = _rows(self.manager, 'EventTrigger')
        return [t for t in rows if kind is None or getattr(t, 'source_kind', '') == kind]

    def _solution(self, name):
        for row in _rows(self.manager, 'SolutionDefinition'):
            if str(getattr(row, 'name', '')) == str(name) \
                    or str(getattr(row, 'solutionName', '')) == str(name):
                raw = getattr(row, 'definition', None) or getattr(row, 'solutionDefinition', None)
                parsed = _loads(raw, None) if not isinstance(raw, dict) else raw
                if isinstance(parsed, dict):
                    if 'stateInstances' not in parsed and isinstance(parsed.get('definition'), dict):
                        parsed = parsed['definition']
                    parsed.setdefault('solutionName', name)
                    return parsed
        return None

    def _already_fired(self, trigger_name, occurrence_key):
        if not occurrence_key:
            return False
        for f in _rows(self.manager, 'TriggerFiring'):
            if getattr(f, 'trigger_name', '') == trigger_name \
                    and getattr(f, 'occurrence_key', '') == occurrence_key \
                    and getattr(f, 'status', '') == 'fired':
                return True
        return False

    def _record(self, trigger, status, source_kind, source_ref, occurrence_key,
                depth, execution_id='', outcome=None, error=''):
        row = create_instance(self.manager, 'TriggerFiring', {
            'name': f'firing-{uuid.uuid4().hex[:10]}',
            'trigger_name': getattr(trigger, 'name', ''),
            'fired_at': datetime.now().isoformat(timespec='seconds'),
            'source_kind': source_kind, 'source_ref': str(source_ref)[:400],
            'occurrence_key': occurrence_key, 'execution_id': execution_id,
            'status': status, 'run_as': getattr(trigger, 'run_as', 'definer'),
            'depth': depth, 'outcome_json': json.dumps(outcome or {}, default=str)[:4000],
            'error': str(error)[:1000],
        }, depth=depth, notify=False)
        if status == 'fired':
            trigger.last_fired = row.fired_at
            trigger.fire_count = int(getattr(trigger, 'fire_count', 0) or 0) + 1
            try:
                save_instance(self.manager, trigger)
            except Exception:
                pass
        return row

    # ---- one firing ----
    def fire(self, trigger, payload, source_kind, source_ref, occurrence_key='', depth=0):
        """Run `trigger`'s solution with `payload`; always returns the
        TriggerFiring row it wrote (fired / skipped / refused / failed)."""
        name = getattr(trigger, 'name', '')
        if not getattr(trigger, 'enabled', True):
            return self._record(trigger, 'refused', source_kind, source_ref, occurrence_key,
                                depth, error=f"trigger '{name}' is disabled")
        max_depth = int(getattr(trigger, 'max_depth', 8) or 8)
        if depth > max_depth:
            return self._record(trigger, 'refused', source_kind, source_ref, occurrence_key,
                                depth, error=(f"chained-event depth {depth} exceeds max_depth "
                                              f"{max_depth} — a trigger loop? (raise max_depth "
                                              f"on the row only if the chain is intended)"))
        if self._already_fired(name, occurrence_key):
            return self._record(trigger, 'skipped', source_kind, source_ref, occurrence_key,
                                depth, error='already fired for this occurrence')
        cooldown = float(getattr(trigger, 'cooldown_s', 0) or 0)
        last = getattr(trigger, 'last_fired', '') or ''
        if cooldown > 0 and last:
            try:
                if datetime.now() - datetime.fromisoformat(last) < timedelta(seconds=cooldown):
                    return self._record(trigger, 'skipped', source_kind, source_ref,
                                        occurrence_key, depth,
                                        error=f'within cooldown ({cooldown:g}s since {last})')
            except ValueError:
                pass
        solution = self._solution(getattr(trigger, 'solution_name', ''))
        if solution is None:
            return self._record(trigger, 'failed', source_kind, source_ref, occurrence_key,
                                depth, error=(f"SolutionDefinition "
                                              f"'{getattr(trigger, 'solution_name', '')}' "
                                              f"is not on this node"))
        # the trigger's own inputs_json are its KNOBS — they win over
        # the generic payload keys (a PersonSchedule change can still
        # name the plan it re-coordinates).
        params = dict(payload or {})
        params.update(_loads(getattr(trigger, 'inputs_json', '{}'), {}))
        params[TRIGGER_NAME_KEY] = name
        params[TRIGGER_DEPTH_KEY] = depth + 1
        params[TRIGGER_SOURCE_KEY] = str(source_ref)
        try:
            from polariNoCode.graph_builder import execute
            trace = execute(solution, manager=self.manager, params=params)
        except Exception as e:
            return self._record(trigger, 'failed', source_kind, source_ref, occurrence_key,
                                depth, error=f'{type(e).__name__}: {e}')
        status = getattr(trace, 'status', '')
        outcome = {'status': status, 'return': getattr(trace, 'final_return_value', None),
                   'error': getattr(trace, 'error_summary', None)}
        return self._record(trigger, 'fired' if status == 'completed' else 'failed',
                            source_kind, source_ref, occurrence_key, depth,
                            execution_id=getattr(trace, 'execution_id', ''),
                            outcome=outcome, error=getattr(trace, 'error_summary', '') or '')

    # ---- sources ----
    def object_changed(self, class_name, operation, instance_ids, depth=0):
        firings = []
        for trigger in self.triggers('object'):
            src = _loads(getattr(trigger, 'source_json', '{}'), {})
            if src.get('class') != class_name:
                continue
            ops = src.get('operations') or ['create', 'update', 'delete']
            if operation not in ops:
                continue
            for inst_id in (instance_ids or [None]):
                inst = find_instance(self.manager, class_name, inst_id) if inst_id else None
                fields = snapshot(inst) if inst is not None else {}
                flt = src.get('fieldFilter') or {}
                if flt and any(str(fields.get(k)) != str(v) for k, v in flt.items()):
                    continue
                payload = {'class': class_name, 'operation': operation,
                           'instanceId': inst_id, 'instanceName': fields.get('name', ''),
                           'instance': fields}
                # Flat 'instance.<field>' keys: the engine resolves
                # context paths by EXACT key, not by walking dicts, so
                # a solution reads var_src('instance.plan_name').
                for k, v in fields.items():
                    payload[f'instance.{k}'] = v
                firings.append(self.fire(trigger, payload, 'object',
                                         f'{class_name}:{fields.get("name", inst_id)}:{operation}',
                                         depth=depth))
        return firings

    def events_emitted(self, events, depth=0, origin=''):
        firings = []
        for event in events or []:
            if not isinstance(event, dict):
                continue
            for trigger in self.triggers('event'):
                src = _loads(getattr(trigger, 'source_json', '{}'), {})
                if src.get('eventName') and src['eventName'] != event.get('name'):
                    continue
                if src.get('channel') and src['channel'] != event.get('channel', 'backend'):
                    continue
                payload = {'eventName': event.get('name'), 'channel': event.get('channel'),
                           'sourceState': event.get('sourceState'),
                           'event': event.get('payload') or {}}
                firings.append(self.fire(trigger, payload, 'event',
                                         f'{origin}:{event.get("name")}', depth=depth))
        return firings

    def tick(self, now=None, lookback_seconds=None):
        """Schedule + window triggers for the interval ending at `now`."""
        with self._lock:
            now = now or datetime.now()
            if lookback_seconds:
                since = now - timedelta(seconds=lookback_seconds)   # explicit window
            else:
                since = self._last_tick or (now - timedelta(seconds=self.tick_seconds))
            self._last_tick = now
            firings = []
            for trigger in self.triggers('schedule'):
                src = _loads(getattr(trigger, 'source_json', '{}'), {})
                try:
                    occ = expand_schedule(src.get('schedule'), since, now)
                except ValueError as e:
                    firings.append(self._record(trigger, 'failed', 'schedule', 'tick', '', 0,
                                                error=str(e)))
                    continue
                for o in occ:
                    if not (since < o['start'] <= now):
                        continue
                    key = o['start'].isoformat(timespec='minutes')
                    payload = {'occurrence': {'start': key,
                                              'end': o['end'].isoformat(timespec='minutes') if o['end'] else None,
                                              'allDay': o['allDay']},
                               'occurrenceKey': key, 'now': now.isoformat(timespec='minutes')}
                    firings.append(self.fire(trigger, payload, 'schedule', key, occurrence_key=key))
            for trigger in self.triggers('window'):
                src = _loads(getattr(trigger, 'source_json', '{}'), {})
                within = float(src.get('withinMinutes', 60) or 60)
                relation = src.get('relation', 'starts')
                horizon = now + timedelta(minutes=within)
                if src.get('calendar'):
                    cal = calendar_by_name(self.manager, src['calendar'])
                    events = resolve_calendar_events(self.manager, cal, now, horizon)['events'] if cal else []
                else:
                    defn = definition_by_name(self.manager, src.get('eventDefinition', ''))
                    events = resolve_definition_events(self.manager, defn, now, horizon)['events'] if defn else []
                for ev in events:
                    stamp = ev.get('end' if relation == 'ends' else 'start') or ev.get('start')
                    key = f"{ev.get('id')}@{stamp}"
                    payload = {'event': ev, 'relation': relation, 'withinMinutes': within,
                               'now': now.isoformat(timespec='minutes')}
                    firings.append(self.fire(trigger, payload, 'window', key, occurrence_key=key))
            return firings

    # ---- the thread ----
    def start(self):
        if self._thread is not None or self.tick_seconds <= 0:
            return False

        def _loop():
            while not self._stop.wait(self.tick_seconds):
                try:
                    self.tick()
                except Exception:
                    print('[EventDispatcher] tick failed:\n' + traceback.format_exc(), flush=True)
        self._thread = threading.Thread(target=_loop, name='polari-event-tick', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------
# module-level entry points (one dispatcher per manager)
# ---------------------------------------------------------------

#: one dispatcher per manager, kept OFF the manager object (an
#: attribute there is walked by the tree's identifier scan and logged
#: as an "invalid instance value" on every pass).
_DISPATCHERS = {}


def get_dispatcher(manager, tick_seconds=60):
    if manager is None:
        return None
    key = id(manager)
    d = _DISPATCHERS.get(key)
    if d is None:
        d = EventDispatcher(manager, tick_seconds)
        _DISPATCHERS[key] = d
    return d


def dispatch_object_change(manager, class_name, operation, instance_ids, depth=0):
    """Never raises — the CRUDE hook calls this."""
    try:
        d = get_dispatcher(manager)
        if d is None or not (getattr(manager, 'objectTables', None) or {}).get('EventTrigger'):
            return []
        return d.object_changed(class_name, operation, instance_ids, depth=depth)
    except Exception:
        print('[EventDispatcher] object-change dispatch failed:\n' + traceback.format_exc(),
              flush=True)
        return []


def dispatch_trace_events(manager, trace, params=None):
    """Chain EmitEvent outputs of a completed top-level run into event
    triggers. Never raises — the engine calls this."""
    try:
        d = get_dispatcher(manager)
        if d is None or not (getattr(manager, 'objectTables', None) or {}).get('EventTrigger'):
            return []
        from polariNoCode.graph_compilers import final_context_of
        final = final_context_of(trace) or {}
        events = final.get('_emitted_events') or []
        if not events:
            return []
        depth = int((params or {}).get(TRIGGER_DEPTH_KEY, 0) or 0)
        return d.events_emitted(events, depth=depth,
                                origin=getattr(trace, 'solution_name', ''))
    except Exception:
        print('[EventDispatcher] emitted-event dispatch failed:\n' + traceback.format_exc(),
              flush=True)
        return []


def start_tick_thread(manager, tick_seconds):
    d = get_dispatcher(manager, tick_seconds)
    if d is None:
        return False
    d.tick_seconds = tick_seconds
    return d.start()
