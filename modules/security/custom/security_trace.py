"""
security.custom.security_trace — THE TRACE TARGET, THE MAP AND THE EFFECT JOURNAL (ct-1).

Design: AI-Notes/designs/CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2. Builds on ct-0's cause context
(`accessControl.cause_context`), which mints the chain; this module decides what is WORTH recording and records
it, in two ledgers:

    Ledger A — `CausalEdge`          the MAP: one counted row per (cause node, effect node, means). Kept.
    Ledger B — `WriteJournalEntry`   the effect JOURNAL: instance-level rows for the current question.
                                     CLEARED when the next target is armed (design §2).

His rules, all of them enforced here:

  * **One class at a time** — nothing records unless exactly one `TraceTarget` row is `active`; a second `arm()`
    while one is active is REFUSED naming the active one.
  * **Dev posture only** — `arm()` refuses in production with the reason, and every recorder is a no-op there
    (ct-0 mints no cause at all outside dev, so the recorders find nothing to attach to either way).
  * **Budgets, stated not silent** — the FIRST budget hit disarms the target, stamps `stopped_because` and
    writes ONE `SecurityEvent` (control `trace`, the observe-mode notice pattern). Afterwards, for as long as
    the window would have lasted, every declined write increments `dropped`, so a map read as "complete" can be
    checked against it.
  * **Counted rows never duplicate** — `CausalEdge.name` is `cause|effect|means`, so the same crossing seen a
    thousand times is one row with `count` 1000.
  * **A person is a Keycloak `sub`** (D18-1) — `started_by` and the journal's `actor` hold that and nothing else.

THE SCOPE RULE (design §2). A chain becomes *traced* at the first seam that touches the target class —
`touch(manager, class_name, verb)` returns whether it is. From that point the edge that REACHED the target and
everything DOWNSTREAM of it is recorded, to `max_depth`. A chain that never touches the target writes nothing:
the cause is still minted (a dict, cheap) and both ledgers ignore it. Traced-ness is keyed by `trace_id`, not by
the cause dict, because ct-0's `child_cause()` builds a fresh dict at each seam — the CHAIN is traced, not the
frame.

THE KNOB (`<data>/security/trace.json`, `POLARI_TRACE_KNOB`) mirrors `observe.json` and holds the active
target's name. RESTART BEHAVIOUR — the simpler of the two the design allows, chosen deliberately: a process that
finds a name in the knob but has no in-process arming (the flag, the traced-chain set and the open-trace count
all die with the process) DISARMS that target with `stopped_because='restart'` and clears the knob. The row's
counters are persisted, so they survive and read honestly; what does not survive is the arming, and saying so is
better than resuming a target whose live state is gone.
"""
import calendar
import os
import time

from moduleService import posture as _posture
from security.custom.security_observe import (_all_rows, _new_row, _plain_row, _schedule_persist, _now,
                                              actor_of, record as _record_event)

#: the CRUDE vocabulary a target's `verbs` may name; [] = all of them
TRACE_VERBS = ('read', 'create', 'update', 'delete', 'events')

#: the budget defaults (design §2/§10)
DEFAULTS = {'max_traces': 200, 'max_edges': 500, 'max_journal_rows': 5000,
            'max_depth': 8, 'window_seconds': 3600}

#: the map's own ceiling — twenty targets over a year cannot grow it without bound
MAP_MAX_ROWS_ENV = 'POLARI_TRACE_MAP_MAX_ROWS'
DEFAULT_MAP_MAX_ROWS = 5000

TARGET_KEYS = ('name', 'class_name', 'verbs_json', 'max_traces', 'max_edges', 'max_journal_rows', 'max_depth',
               'window_seconds', 'started_by', 'started_at', 'stopped_at', 'stopped_because',
               'traces_opened', 'edges_written', 'journal_written', 'dropped', 'active')
EDGE_KEYS = ('name', 'cause', 'effect', 'means', 'detail', 'count', 'first_seen', 'last_seen',
             'min_depth', 'max_depth', 'run_as', 'sample_trace_id', 'target')

#: in-process arming state. Dies with the process ON PURPOSE — see the module docstring's restart rule.
_STATE = {'armed': False, 'name': '', 'class_name': '', 'resumed': False,
          'stopped_name': '', 'stopped_until': 0.0}
#: trace ids whose chain has touched the target class — the scope rule, keyed by CHAIN not by frame
_TRACED = {}
#: re-entrancy: writing a ledger row constructs tree objects, which walk the same seams
_WRITING = {'on': False}
#: (trace_id, class, id) of rows CREATED in this chain. The fields a constructor assigns all pass through
#: `treeObject.__setattr__`, so without this one create would land as a create row plus N update rows; those
#: field values belong to the create, and the journal says so once.
_CREATED = {}
_CREATED_MAX = 2000


# ---- the switches ---------------------------------------------------------------------------------------

def tracing_enabled(env=None):
    """Dev posture only (his ruling 2026-09-18). Never raises: an unreadable posture is production."""
    try:
        return bool(_posture.is_dev(env))
    except Exception:                       # noqa: BLE001 — a switch that cannot be read is off
        return False


def _knob_path():
    base = os.environ.get('POLARI_APP_DEBS_DIR', '/app/data/app-debs').rsplit('/app-debs', 1)[0]
    return os.environ.get('POLARI_TRACE_KNOB', os.path.join(base, 'security', 'trace.json'))


def knob_state():
    """{target, armed_at, by, source}. The knob holds the ACTIVE target's name and nothing about a person but
    their `sub` (D18-1)."""
    import json
    st = {'target': '', 'armed_at': '', 'by': '', 'source': 'none'}
    try:
        d = json.load(open(_knob_path()))
        if isinstance(d, dict):
            st.update({'target': str(d.get('target') or ''), 'armed_at': d.get('armed_at', ''),
                       'by': d.get('by', ''), 'source': 'knob'})
    except Exception:                       # noqa: BLE001 — no knob is a valid state (nothing armed)
        pass
    return st


def _write_knob(target, by=''):
    import json
    p = _knob_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        json.dump({'target': target or '', 'armed_at': _now() if target else '', 'by': by}, open(tmp, 'w'))
        os.replace(tmp, p)
        return True
    except Exception:                       # noqa: BLE001 — an unwritable knob loses the restart notice, nothing else
        return False


def map_max_rows():
    raw = (os.environ.get(MAP_MAX_ROWS_ENV) or '').strip()
    try:
        n = int(raw)
        return n if n > 0 else DEFAULT_MAP_MAX_ROWS
    except ValueError:
        return DEFAULT_MAP_MAX_ROWS


def _set_armed_flag(on, class_name=''):
    """The module-level flag `treeObject.__setattr__` reads FIRST, before anything else it does. It lives in
    objectTreeDecorators so the hot path is one global read and never an import."""
    try:
        import objectTreeDecorators
        objectTreeDecorators.set_trace_armed(bool(on), class_name or '')
    except Exception:                       # noqa: BLE001 — the tree must never break on bookkeeping
        pass


# ---- the target -----------------------------------------------------------------------------------------

def _targets(manager):
    return _all_rows(manager, 'TraceTarget')


def _target_row(manager, name):
    return next((r for r in _targets(manager) if getattr(r, 'name', '') == name), None)


def _epoch(stamp):
    try:
        return calendar.timegm(time.strptime(str(stamp or ''), '%Y-%m-%dT%H:%M:%SZ'))
    except Exception:                       # noqa: BLE001
        return 0.0


def _resume(manager):
    """Once per process: a knob naming a target that this process did not arm is a RESTART. The row is stopped
    with `stopped_because='restart'` and the knob cleared — the counters stay, the arming does not."""
    if _STATE['resumed']:
        return
    _STATE['resumed'] = True
    name = knob_state()['target']
    if not name or _STATE['armed']:
        return
    row = _target_row(manager, name)
    if row is not None and bool(getattr(row, 'active', False)):
        row.active = False
        row.stopped_at = _now()
        row.stopped_because = 'restart'
        _schedule_persist(manager)
    _write_knob('')


def active_target(manager):
    """The one armed `TraceTarget` row, or None. Disarms lazily on the window (design §2: `window_seconds`
    disarms itself on the next write or status read)."""
    if not tracing_enabled():
        return None
    _resume(manager)
    if not _STATE['armed']:
        return None
    row = _target_row(manager, _STATE['name'])
    if row is None or not bool(getattr(row, 'active', False)):
        _clear_state()
        return None
    window = int(getattr(row, 'window_seconds', 0) or 0)
    started = _epoch(getattr(row, 'started_at', ''))
    if window > 0 and started and time.time() - started > window:
        _stop(manager, row, 'window')
        return None
    return row


def _clear_state():
    _STATE['armed'] = False
    _STATE['name'] = ''
    _STATE['class_name'] = ''
    _set_armed_flag(False, '')


def _stop(manager, row, because):
    """Disarm, stated: the row is stamped, one SecurityEvent is written for every reason but a plain manual
    stop, and the window during which declines still count as `dropped` is remembered."""
    row.active = False
    row.stopped_at = _now()
    row.stopped_because = because
    window = int(getattr(row, 'window_seconds', 0) or 0) or int(DEFAULTS['window_seconds'])
    _STATE['stopped_name'] = getattr(row, 'name', '')
    _STATE['stopped_until'] = time.time() + window
    _clear_state()
    _write_knob('')
    if because.startswith('budget') or because == 'window':
        _record_event(manager, 'trace', 'budget %s' % because, getattr(row, 'class_name', ''),
                      reason=('the trace target %s stopped: %s (traces %s, edges %s, journal %s)'
                              % (getattr(row, 'name', ''), because, getattr(row, 'traces_opened', 0),
                                 getattr(row, 'edges_written', 0), getattr(row, 'journal_written', 0))),
                      actor=str(getattr(row, 'started_by', '') or ''), outcome='observed', would_deny=False,
                      source='security.custom.security_trace', save=False)
    _schedule_persist(manager)
    return row


def _stopped_target(manager):
    """The target that JUST stopped, while its window would still have been running — what a declined write
    increments `dropped` on, so the stop is accountable rather than a silent gap."""
    if not _STATE['stopped_name'] or time.time() > _STATE['stopped_until']:
        return None
    return _target_row(manager, _STATE['stopped_name'])


def _target_for_write(manager):
    """(row, allowed). `allowed` False with a row = count a drop; None = nothing to record against."""
    row = active_target(manager)
    if row is not None:
        return row, True
    return _stopped_target(manager), False


def _drop(manager, row):
    if row is None:
        return None
    row.dropped = int(getattr(row, 'dropped', 0) or 0) + 1
    _schedule_persist(manager)
    return None


def arm(manager, class_name, verbs=None, max_traces=None, max_edges=None, max_journal_rows=None,
        max_depth=None, window_seconds=None, user_info=None):
    """Arm the ONE target. Refuses outside dev posture, and refuses a second arm naming the active one.

    Arming CLEARS the previous target's journal rows — the journal is evidence for the CURRENT question
    (design §2). Only `origin='local'` rows go: the remote-write journal (xsim-4) is an audit trail of
    cross-instance writes and is not this arc's to delete."""
    import json
    if not tracing_enabled():
        return {'ok': False, 'refusal': ('tracing happens only on a dev-posture instance (his ruling 2026-09-18: '
                                         '"tracing should not occur in production, only finalized security posture '
                                         'rows derived from them"). This instance is %s.' % _posture.posture())}
    class_name = str(class_name or '').strip()
    if not class_name:
        return {'ok': False, 'refusal': 'class_name required — tracing follows ONE class at a time'}
    if getattr(manager, 'objectTables', None) is None:
        return {'ok': False, 'refusal': 'no manager'}
    _resume(manager)
    current = active_target(manager)
    if current is not None:
        return {'ok': False, 'refusal': ('a trace target is already armed: %s (class %s, armed %s by %s). Only one '
                                         'class is traced at a time — DELETE /api/security/observe/trace first.'
                                         % (getattr(current, 'name', ''), getattr(current, 'class_name', ''),
                                            getattr(current, 'started_at', ''), getattr(current, 'started_by', '') or '-')),
                'active': target_dict(current)}
    verbs = [v for v in (verbs or []) if v in TRACE_VERBS]
    fields = {
        'name': class_name, 'class_name': class_name, 'verbs_json': json.dumps(sorted(set(verbs))),
        'max_traces': int(max_traces or DEFAULTS['max_traces']),
        'max_edges': int(max_edges or DEFAULTS['max_edges']),
        'max_journal_rows': int(max_journal_rows or DEFAULTS['max_journal_rows']),
        'max_depth': int(max_depth or DEFAULTS['max_depth']),
        'window_seconds': int(window_seconds if window_seconds is not None else DEFAULTS['window_seconds']),
        'started_by': actor_of(user_info), 'started_at': _now(), 'stopped_at': '', 'stopped_because': '',
        'traces_opened': 0, 'edges_written': 0, 'journal_written': 0, 'dropped': 0, 'active': True,
    }
    tables = manager.objectTables
    row, new = _plain_row(tables, 'TraceTarget', class_name, None)
    if new:
        from security.objects.security.TraceTarget import TraceTarget
        row = _new_row(manager, tables, 'TraceTarget', TraceTarget, fields)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    cleared = clear_journal(manager)
    _TRACED.clear()
    _CREATED.clear()
    _STATE.update({'armed': True, 'name': class_name, 'class_name': class_name,
                   'stopped_name': '', 'stopped_until': 0.0})
    _set_armed_flag(True, class_name)
    _write_knob(class_name, by=fields['started_by'])
    _schedule_persist(manager)
    return {'ok': True, 'armed': True, 'target': target_dict(row), 'journal_cleared': cleared,
            'how': ('act on %s now: the CRUDE gate, the tree seams and the dispatcher record every chain that '
                    'touches it, to depth %d, until a budget or %ds passes. GET /api/security/trace/edges is the '
                    'map; /api/security/trace/journal is the instance-level evidence.'
                    % (class_name, fields['max_depth'], fields['window_seconds']))}


def disarm(manager, because='manual', user_info=None):
    """Stop the armed target. `user_info` is accepted for symmetry with `arm` and never written: the person who
    armed it is the one the row records (D18-1)."""
    _resume(manager)
    row = active_target(manager)
    if row is None:
        return {'ok': True, 'armed': False, 'note': 'no trace target was armed', 'coverage': coverage(manager)}
    if because not in ('manual', 'window', 'restart') and not because.startswith('budget'):
        because = 'manual'
    _stop(manager, row, because)
    return {'ok': True, 'armed': False, 'stopped': target_dict(row), 'coverage': coverage(manager)}


def target_dict(row):
    if row is None:
        return None
    out = {k: getattr(row, k, '') for k in TARGET_KEYS}
    out['active'] = bool(out.get('active'))
    return out


def coverage(manager):
    """Every class that has EVER been a target, with when it started and stopped — design §2's "coverage, not
    silence": a closure over an untraced class answers *not traced*, never *nothing reaches it*."""
    rows = [{'class_name': getattr(r, 'class_name', ''), 'started_at': getattr(r, 'started_at', ''),
             'stopped_at': getattr(r, 'stopped_at', ''), 'stopped_because': getattr(r, 'stopped_because', ''),
             'traces_opened': getattr(r, 'traces_opened', 0), 'edges_written': getattr(r, 'edges_written', 0),
             'journal_written': getattr(r, 'journal_written', 0), 'dropped': getattr(r, 'dropped', 0),
             'active': bool(getattr(r, 'active', False))}
            for r in _targets(manager)]
    rows.sort(key=lambda d: d['class_name'])
    return rows


def status(manager):
    row = active_target(manager)
    return {'ok': True, 'posture': _posture.posture(), 'tracing': tracing_enabled(), 'armed': row is not None,
            'target': target_dict(row), 'coverage': coverage(manager), 'knob': knob_state(),
            'open_traces': len(_TRACED), 'map_rows': len(_all_rows(manager, 'CausalEdge')),
            'map_ceiling': map_max_rows(), 'journal_rows': len(_journal_rows(manager)),
            'defaults': dict(DEFAULTS),
            'how': ('POST {"class_name": "<Class>"} arms ONE class (dev posture only, admins or the role-play '
                    'permission); DELETE disarms it. Budgets disarm the target themselves and say why; `dropped` '
                    'counts what was declined afterwards.')}


# ---- the scope rule -------------------------------------------------------------------------------------

def _verbs_of(row):
    import json
    try:
        v = json.loads(getattr(row, 'verbs_json', '') or '[]')
        return [x for x in v if x in TRACE_VERBS] if isinstance(v, list) else []
    except Exception:                       # noqa: BLE001
        return []


def is_traced(trace_id=None):
    """Is THIS chain traced? Keyed by trace_id, because ct-0 builds a fresh cause dict at every seam."""
    if trace_id is None:
        from accessControl.cause_context import current_cause
        cause = current_cause()
        if not cause:
            return False
        trace_id = cause.get('trace_id', '')
    return bool(trace_id) and trace_id in _TRACED


def touch(manager, class_name, verb=''):
    """THE SCOPE RULE. Mark the current chain traced when `class_name` is the armed target's class (and `verb`,
    when given, is one the target opens on). Returns whether the chain is traced — a seam calls this first and
    records only when it answers True."""
    if _WRITING['on']:
        return False
    from accessControl.cause_context import current_cause
    cause = current_cause()
    if not cause:
        return False
    trace_id = cause.get('trace_id', '')
    if trace_id and trace_id in _TRACED:
        return True
    row = active_target(manager)
    if row is None or not trace_id:
        return False
    if class_name != getattr(row, 'class_name', ''):
        return False
    verbs = _verbs_of(row)
    if verb and verbs and verb not in verbs:
        return False
    opened = int(getattr(row, 'traces_opened', 0) or 0)
    if opened >= int(getattr(row, 'max_traces', 0) or 0):
        _stop(manager, row, 'budget-traces')
        _drop(manager, row)
        return False
    _TRACED[trace_id] = time.time()
    row.traces_opened = opened + 1
    _schedule_persist(manager)
    return True


def cause_node(cause=None):
    """The current cause as a map node (design §2's node vocabulary)."""
    if cause is None:
        from accessControl.cause_context import current_cause
        cause = current_cause() or {}
    kind = cause.get('entry_kind', 'api')
    ref = str(cause.get('entry_ref') or '')[:200]
    if kind == 'api':
        return 'endpoint:%s' % (ref or 'unknown')
    if kind == 'trigger':
        return 'event:%s' % ref if ref.startswith('trigger:') else 'event:trigger:%s' % ref
    if kind == 'schedule':
        return 'schedule:%s' % ref
    if kind == 'solution':
        return 'solution:%s' % (ref[9:] if ref.startswith('solution:') else ref)
    if kind == 'peer':
        return 'peer:%s' % ref
    return '%s:%s' % (kind, ref)


# ---- Ledger A: the map ----------------------------------------------------------------------------------

def _edges(manager):
    return _all_rows(manager, 'CausalEdge')


def _drop_row(manager, table, row):
    """Remove one row from the manager's table (and the test-double fallback), tombstoned so a flush in flight
    does not write it back."""
    from security.custom import security_observe as _obs
    tables = getattr(manager, 'objectTables', None) or {}
    live = tables.get(table)
    if isinstance(live, dict):
        for key, value in list(live.items()):
            if value is row:
                live.pop(key, None)
                try:
                    manager.noteTreeDeletion(table, key)
                except Exception:           # noqa: BLE001
                    pass
    fallback = _obs._FALLBACK.get(id(tables), {}).get(table, {})
    fallback.pop(getattr(row, 'name', ''), None)


def prune_map(manager, limit=0):
    """The map's ceiling: oldest `last_seen` pruned once the table is over it (design §2)."""
    limit = int(limit or 0) or map_max_rows()
    rows = _edges(manager)
    if len(rows) <= limit:
        return 0
    rows.sort(key=lambda r: str(getattr(r, 'last_seen', '') or ''))
    for row in rows[:len(rows) - limit]:
        _drop_row(manager, 'CausalEdge', row)
    return len(rows) - limit


def record_edge(manager, cause_node_ref, effect_node, means, detail='', run_as=''):
    """THE ONE PUBLIC RECORDER (the outbound wrapper of ct-3 calls it by lazy import and tolerates its absence).

    A no-op when no target is armed or the current chain is not traced. Counted and deduped by
    `cause|effect|means`; honours `max_depth` and `max_edges`; prunes the map above its ceiling."""
    if _WRITING['on'] or not cause_node_ref or not effect_node or not means:
        return None
    try:
        from accessControl.cause_context import current_cause
        cause = current_cause()
        if not cause or not is_traced(cause.get('trace_id', '')):
            return None
        row, allowed = _target_for_write(manager)
        if row is None:
            return None
        if not allowed:
            return _drop(manager, row)
        depth = int(cause.get('depth', 0) or 0)
        if depth > int(getattr(row, 'max_depth', 0) or 0):
            return _drop(manager, row)
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return None
        name = ('%s|%s|%s' % (cause_node_ref, effect_node, means))[:200]
        now = _now()
        edge, new = _plain_row(tables, 'CausalEdge', name, None)
        if int(getattr(row, 'edges_written', 0) or 0) >= int(getattr(row, 'max_edges', 0) or 0):
            _stop(manager, row, 'budget-edges')
            return _drop(manager, row)
        _WRITING['on'] = True
        try:
            if not new:
                edge.count = int(getattr(edge, 'count', 0) or 0) + 1
                edge.last_seen = now
                edge.min_depth = min(int(getattr(edge, 'min_depth', depth) or 0), depth)
                edge.max_depth = max(int(getattr(edge, 'max_depth', depth) or 0), depth)
                edge.run_as = run_as or getattr(edge, 'run_as', '')
                edge.detail = detail or getattr(edge, 'detail', '')
                edge.target = getattr(row, 'name', '')
            else:
                from security.objects.security.CausalEdge import CausalEdge
                edge = _new_row(manager, tables, 'CausalEdge', CausalEdge, {
                    'name': name, 'cause': str(cause_node_ref)[:200], 'effect': str(effect_node)[:200],
                    'means': str(means)[:60], 'detail': str(detail)[:200], 'count': 1,
                    'first_seen': now, 'last_seen': now, 'min_depth': depth, 'max_depth': depth,
                    'run_as': run_as, 'sample_trace_id': cause.get('trace_id', ''),
                    'target': getattr(row, 'name', '')})
        finally:
            _WRITING['on'] = False
        row.edges_written = int(getattr(row, 'edges_written', 0) or 0) + 1
        prune_map(manager)
        _schedule_persist(manager)
        return edge
    except Exception:                       # noqa: BLE001 — a recorder NEVER raises into the thing it observes
        return None


def edges(manager, target='', cause='', effect='', means=''):
    out = [{k: getattr(r, k, '') for k in EDGE_KEYS} for r in _edges(manager)]
    if target:
        out = [e for e in out if e['target'] == target]
    if cause:
        out = [e for e in out if e['cause'] == cause or e['cause'].startswith(cause)]
    if effect:
        out = [e for e in out if e['effect'] == effect or e['effect'].startswith(effect)]
    if means:
        out = [e for e in out if e['means'] == means]
    out.sort(key=lambda e: (-int(e.get('count') or 0), e['cause'], e['effect']))
    return out


def closure(manager, start_nodes, *, max_depth=None):
    """THE CLOSURE (ct-4) — walk the map from `start_nodes` and say everything reachable, grouped, with the
    evidence and the coverage block.

    THE SIGNATURE IS STABLE. Other arcs read the closure through THIS name by lazy import
    (`from security.custom.security_trace import closure`) — ct-8's per-app decision coverage does exactly that
    — so it keeps `(manager, start_nodes, *, max_depth=None)` and the keys documented on
    `security.custom.security_closure.closure`, which is where the walk itself lives (small files, split by
    concern). `start_nodes` is any iterable of design §2 node strings; the answer always carries `coverage` and
    `not_traced`, so an empty branch reads *not traced*, never *nothing*."""
    from security.custom.security_closure import closure as _closure
    return _closure(manager, start_nodes, max_depth=max_depth)


def record_outbound(manager, system_kind, system_name, means, payload_classes=()):
    """What LEFT this instance: the effect node is `external:<kind>:<name>` (or `peer:<name>:<means>` for
    another Polari instance), the payload CLASSES ride in `detail` — never a payload (design §2/§5).

    This is the recorder ct-3's `polariApiServer/outbound.py` calls by lazy import."""
    kind = str(system_kind or '').strip() or 'external'
    name = str(system_name or '').strip() or 'unnamed'
    node = ('peer:%s:%s' % (name, means)) if kind == 'peer' else ('external:%s:%s' % (kind, name))
    classes = ','.join(sorted({str(c) for c in (payload_classes or []) if c}))
    return record_edge(manager, cause_node(), node, str(means or 'send'), detail=classes)


# ---- Ledger B: the effect journal -----------------------------------------------------------------------

def _journal_rows(manager):
    return [r for r in _all_rows(manager, 'WriteJournalEntry')
            if str(getattr(r, 'origin', 'remote')) == 'local']


def clear_journal(manager):
    """Drop the LOCAL journal rows (design §2: the journal is evidence for the current question and is cleared
    when the next target is armed). The remote-write journal (xsim-4's cross-instance audit trail) is left
    alone — it is not this arc's to delete."""
    rows = _journal_rows(manager)
    for row in rows:
        _drop_row(manager, 'WriteJournalEntry', row)
    return len(rows)


def _anonymised(manager, class_name):
    """op-0's `OwnedClassPolicy.anonymised` (design §5): the journal row keeps class + verb and drops BOTH the
    actor and the object id, so tracing a class whose owner is deliberately unlinkable cannot re-link them."""
    try:
        from security.custom.security_owned import policy_for
        pol = policy_for(manager, class_name)
        return bool(pol and pol.get('anonymised'))
    except Exception:                       # noqa: BLE001
        return False


def record_effect(manager, class_name, object_id, verb, fields_changed=None):
    """LEDGER B: one instance-level row per local write under a traced chain. No-op when nothing is armed or the
    chain is not traced."""
    if _WRITING['on'] or not class_name:
        return None
    try:
        from accessControl.cause_context import current_cause
        cause = current_cause()
        if not cause or not is_traced(cause.get('trace_id', '')):
            return None
        key = (cause.get('trace_id', ''), class_name, str(object_id or ''))
        if verb == 'create':
            if len(_CREATED) >= _CREATED_MAX:
                _CREATED.clear()
            _CREATED[key] = time.time()
        elif verb == 'update' and key in _CREATED:
            return None                     # the constructor's own assignments: already said as one create row
        row, allowed = _target_for_write(manager)
        if row is None:
            return None
        if not allowed:
            return _drop(manager, row)
        if int(cause.get('depth', 0) or 0) > int(getattr(row, 'max_depth', 0) or 0):
            return _drop(manager, row)
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return None
        if int(getattr(row, 'journal_written', 0) or 0) >= int(getattr(row, 'max_journal_rows', 0) or 0):
            _stop(manager, row, 'budget-journal')
            return _drop(manager, row)
        actor = str(cause.get('actor') or '')
        oid = str(object_id or '')
        if _anonymised(manager, class_name):
            actor, oid = '', ''
        from polariRefs.write_journal import WriteJournalEntry, journal_fields, prune_journal
        fields = journal_fields(run_id=cause.get('trace_id', ''), authority='local', class_name=class_name,
                                object_id=oid, fields=list(fields_changed or []), token_epoch=0,
                                outcome='applied', notes='', verb=str(verb or ''), origin='local',
                                actor=actor, target=getattr(row, 'name', ''))
        _WRITING['on'] = True
        try:
            entry = _new_row(manager, tables, 'WriteJournalEntry', WriteJournalEntry, fields)
        finally:
            _WRITING['on'] = False
        row.journal_written = int(getattr(row, 'journal_written', 0) or 0) + 1
        prune_journal(manager)
        _schedule_persist(manager)
        return entry
    except Exception:                       # noqa: BLE001 — a recorder NEVER raises into the thing it observes
        return None


#: the journal as the doors and the page speak it (camelCase, as `journal_rows` already answers)
JOURNAL_KEYS = (('name', 'name'), ('runId', 'run_id'), ('authority', 'authority'), ('className', 'class_name'),
                ('objectId', 'object_id'), ('fieldsChanged', 'fields_changed_json'), ('at', 'at'),
                ('outcome', 'outcome'), ('traceId', 'trace_id'), ('causeRef', 'cause_ref'), ('verb', 'verb'),
                ('origin', 'origin'), ('actor', 'actor'), ('target', 'target'))


def journal(manager, trace_id='', class_name=''):
    """The LOCAL half of the journal — the effect evidence for the current question. Reads through
    `_all_rows`, so a test double's rows are answered beside a real tree's."""
    rows = [{k: getattr(r, attr, '') for k, attr in JOURNAL_KEYS} for r in _journal_rows(manager)]
    if trace_id:
        rows = [r for r in rows if r['traceId'] == trace_id]
    if class_name:
        rows = [r for r in rows if r['className'] == class_name]
    rows.sort(key=lambda d: d.get('at') or '')
    return rows
