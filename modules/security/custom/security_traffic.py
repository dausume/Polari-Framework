"""
security.custom.security_traffic — THE TRAFFIC POLICIES (ct-9; design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §5a).

His ruling (2026-09-18): *"Outbound guard should be tracked in dev as well, and it should be closed by
default; we should suggest outbound and inbounds based on our monitoring of traffic in and out of polari …
we just know we cannot track objects outside of polari."*

So there are two allow-lists, `OutboundPolicy` (what may leave, per system × wire) and `InboundPolicy` (who may
call, per source), and they are built the way the permission profiles are built: DERIVED in dev from what was
actually observed, CONFIRMED by a person, ENFORCED in production.

    outbound_verdict(manager, kind, name, means, classes) -> {allowed, rule, why, knob, …}
    inbound_verdict(manager, source_kind, source, path_template) -> the same shape
    confirm_outbound / confirm_inbound(manager, name, user_info, decision)
    policies(manager) · suggestions(manager) · declared_flows(manager)

THE LADDER, and it is the SAME ladder every other gate in this codebase follows
(`accessControl.app_permissions_gate.gate_mode()` — one knob, `POLARI_APP_PERMISSIONS`):

    off        the verdict is computed and recorded, and NOTHING acts on it
    advisory   the send / the request proceeds; the would-deny rides `X-Polari-Traffic-Advisory`
    enforce    the send raises `outbound.OutboundRefused`; the request is 403 before the responder runs

His "**closed by default in production**" is realised when the production answer is `enforce`: a send or a
caller with no `confirmed` row is refused exactly as an unknown one is — `suggested` is a PROPOSAL, never a
grant. The home stack runs `advisory` by his standing rule (security WARN-ONLY in deployments, §17), so there
it warns and never blocks. That is the whole difference between the postures, and it is the knob's to make.

THE TWO POSTURE RULES, both enforced here:

* **Row writes happen ONLY in dev posture.** Every observed send or request with no row CREATES a `suggested`
  row, and every one with a row bumps its count — in dev. In production nothing is written at all: a missing
  row is simply refused under `enforce`, with a `SecurityEvent` (production's own ledger, which is not a trace)
  and no policy row. "No tracing in production": production carries the confirmed and denied rows it was given
  and derives nothing. The ONE write production does allow is a PERSON's ruling — `confirm_*` — because that
  is a decision, not an observation.
* **Nothing confirms itself.** `confirm_*` needs a signed-in caller (401 without one), an administrator (403
  otherwise), and stores their opaque Keycloak `sub` and nothing else (D18-1). A `suggested` row that nobody
  ruled on stays closed forever.

WHAT NEVER LANDS IN A ROW: a raw address, a bearer, a header value, a payload, a URL (a URL can carry a key).
Outbound rows hold the system's CONFIGURED name and the payload CLASS names; inbound rows hold a `PeerNode`
name, an Origin as scheme + host, or a CLASS (`anonymous`, `ip-literal`) — the classification itself lives in
`accessControl.traffic_middleware`, which is core-resident so the request path never needs this module.
"""
import json

from moduleService import posture as _posture
from security.custom.security_observe import (_all_rows, _new_row, _now, _plain_row, _schedule_persist,
                                              actor_of, record as _record_event)

#: the three states a policy row may hold (design §5a). `suggested` is a proposal, NOT a grant.
POLICY_STATES = ('suggested', 'confirmed', 'denied')

#: what a person may rule
DECISIONS = ('confirmed', 'denied')

#: endpoint templates one inbound row may remember (design §5a: "paths, capped")
MAX_PATHS = 50
#: payload classes one outbound row may remember — the same ceiling, for the same reason
MAX_CLASSES = 50

OUT_KEYS = ('name', 'system_kind', 'system_name', 'means', 'payload_classes_json', 'state', 'derived_from',
            'confirmed_by', 'confirmed_at', 'count', 'first_seen', 'last_seen')
IN_KEYS = ('name', 'source_kind', 'source', 'paths_json', 'state', 'derived_from', 'confirmed_by',
           'confirmed_at', 'count', 'first_seen', 'last_seen')

TABLES = {'outbound': ('OutboundPolicy', OUT_KEYS), 'inbound': ('InboundPolicy', IN_KEYS)}


# ---- the switches ---------------------------------------------------------------------------------------

def mode():
    """`off | advisory | enforce` — ONE knob for every gate in this codebase (`POLARI_APP_PERMISSIONS`)."""
    try:
        from accessControl.app_permissions_gate import gate_mode
        return gate_mode()
    except Exception:                       # noqa: BLE001 — an unreadable knob is off
        return 'off'


def observing(env=None):
    """Whether this instance may WRITE policy rows: dev posture only (his ruling 2026-09-18)."""
    try:
        return bool(_posture.is_dev(env))
    except Exception:                       # noqa: BLE001 — a posture that cannot be read is production
        return False


def outbound_name(system_kind, system_name, means):
    return ('%s|%s|%s' % (_clean(system_kind, 'other'), _clean(system_name, 'unnamed'),
                          _clean(means, 'send')))[:200]


def inbound_name(source_kind, source):
    return ('%s|%s' % (_clean(source_kind, 'anonymous'), _clean(source, 'anonymous')))[:200]


def _clean(value, fallback=''):
    return (str(value or '').strip() or fallback)[:120]


def _json_list(row, attr):
    try:
        v = json.loads(str(getattr(row, attr, '') or '[]'))
        return [str(x) for x in v] if isinstance(v, list) else []
    except Exception:                       # noqa: BLE001
        return []


def _find(manager, table, name):
    """THE one row named `name`, collapsing any duplicates first (§66d).

    A name is the dedup key, but nothing in the tree enforces that — two rows can end up sharing one if an
    observation writes while the class's own restore is still to come. Seen live on `polari-lean`
    2026-09-19: after a restart `anonymous|anonymous` existed TWICE, ('confirmed', 14) beside ('suggested', 7),
    because the boot-time flush found no restored row yet and made its own. Every lookup heals it, so a read
    can never show two rows with one name and a parked count can never land beside a person's ruling instead
    of on it."""
    rows = [r for r in _all_rows(manager, table) if getattr(r, 'name', '') == name]
    if len(rows) < 2:
        return rows[0] if rows else None
    return _collapse(manager, table, rows)


#: which state wins when two rows share a name — a PERSON's ruling always beats a derived suggestion
_STATE_RANK = {'confirmed': 3, 'denied': 3, 'suggested': 1, '': 0}


def _collapse(manager, table, rows):
    """Merge `rows` (all sharing one name) into the best of them and delete the rest.

    The winner is the row a PERSON ruled on — `confirmed` or `denied` — because that is the only state nothing
    may invent; ties go to the oldest row, so the identity that has been around longest survives. Counts are
    SUMMED (every observation really happened), classes and paths are unioned, and the winner's state,
    `confirmed_by` and `confirmed_at` are kept exactly as the person left them. Never raises."""
    try:
        rows = sorted(rows, key=lambda r: (-_STATE_RANK.get(str(getattr(r, 'state', '') or ''), 0),
                                           str(getattr(r, 'first_seen', '') or '9999'),
                                           -int(getattr(r, 'count', 0) or 0)))
        winner, losers = rows[0], rows[1:]
        total = sum(int(getattr(r, 'count', 0) or 0) for r in rows)
        classes, paths = set(_json_list(winner, 'payload_classes_json')), list(_json_list(winner, 'paths_json'))
        last = str(getattr(winner, 'last_seen', '') or '')
        first = str(getattr(winner, 'first_seen', '') or '')
        for row in losers:
            classes |= set(_json_list(row, 'payload_classes_json'))
            for p in _json_list(row, 'paths_json'):
                if p not in paths and len(paths) < MAX_PATHS:
                    paths.append(p)
            last = max(last, str(getattr(row, 'last_seen', '') or ''))
            other_first = str(getattr(row, 'first_seen', '') or '')
            first = min(first or other_first, other_first or first)
            _drop_row(manager, table, row)
        winner.count = total
        if last:
            winner.last_seen = last
        if first:
            winner.first_seen = first
        if hasattr(winner, 'payload_classes_json'):
            winner.payload_classes_json = json.dumps(sorted(classes)[:MAX_CLASSES])
        if hasattr(winner, 'paths_json'):
            winner.paths_json = json.dumps(paths)
        _schedule_persist(manager)
        return winner
    except Exception:                       # noqa: BLE001 — healing never raises into a read
        return rows[0] if rows else None


def _drop_row(manager, table, row):
    """Remove one row from the manager's table (and the test-double fallback), tombstoned so a persist in
    flight does not write it back — the same removal `security_trace.prune_map` does for the causal map."""
    try:
        from security.custom import security_observe as _obs
        tables = getattr(manager, 'objectTables', None) or {}
        live = tables.get(table)
        if isinstance(live, dict):
            for key, value in list(live.items()):
                if value is row:
                    live.pop(key, None)
                    try:
                        manager.noteTreeDeletion(table, key)
                    except Exception:       # noqa: BLE001
                        pass
        _obs._FALLBACK.get(id(tables), {}).get(table, {}).pop(getattr(row, 'name', ''), None)
    except Exception:                       # noqa: BLE001
        pass


def heal_duplicates(manager, direction=''):
    """Collapse every duplicated name in one or both policy tables; returns how many rows were removed.

    Called from every door read and from the flush, so an instance that ALREADY has duplicates (the live
    `polari-lean` tree does) heals itself on the next read rather than needing a migration."""
    removed = 0
    for d in ((direction,) if direction else tuple(TABLES)):
        table = TABLES[d][0]
        try:
            by_name = {}
            for row in _all_rows(manager, table):
                by_name.setdefault(getattr(row, 'name', ''), []).append(row)
            for name, rows in by_name.items():
                if len(rows) > 1:
                    _collapse(manager, table, rows)
                    removed += len(rows) - 1
        except Exception:                   # noqa: BLE001
            continue
    return removed


# ---- BEFORE THE TREE IS THE TREE: the parking lot (§66a, §66b) -------------------------------------------
# Two live findings on `polari-lean` (2026-09-19), one mechanism:
#
# §66a — outbound rows were EMPTY. `polariApiServer.outbound.process_manager()` answers None until
#        `polariServer` injects the manager at boot, and a send before that had nowhere to write.
# §66b — a CONFIRMED inbound row came back `suggested` after a redeploy. Lazy boot serves requests while the
#        definition tables are still restoring, and `_restoreDefinitionInstances` SKIPS a class that already
#        has instances ("N instances already in objectTables, skipping", polariServer.py:1820). So the first
#        request of a boot created row 1, restore then skipped `InboundPolicy` wholesale, and a person's
#        ruling was silently replaced by what the observation had just made up. An observer that writes before
#        restore does not merely lose its own row — it discards the whole class.
#
# Both answers are the same: when there is no tree to write to YET, PARK the observation, allow the traffic,
# and turn the parked observations into rows at the first verdict or door read that finds a restored tree.
# Bounded, in-process, and lost on a restart on purpose — a parked observation is an observation, and
# observations do not outlive the process that made them.

PENDING_MAX = 200
_PENDING = {}


def tree_ready(manager, table=''):
    """Is the object tree restored enough to write a policy row?

    `polariServer` sets `definitionsRestored` False in its constructor and True after
    `_restoreDefinitionInstances` (§66b). A manager that never carries the attribute is not a server's — a
    test double, or a module holding its own — and is ready by definition: only an explicit False means
    "this tree is still coming back from the database, do not touch it".

    §66 addendum 6 adds the PER-CLASS half, and it is the one that was load-bearing live. That flag is one
    boolean for the CORE restore; `InboundPolicy` belongs to the security module, whose rows come back later
    at admission (`lazy_boot._admit`). So between core-ready and security-admitted the flag said "ready" while
    this very table was still on disk unread — the swarm's anonymous health probe wrote a `suggested` row, the
    debounce persisted it over the two rows the DB held, and the restore that followed found one row where
    there had been two. Asking the manager whether THIS class is still owed a restore parks the observation
    for those few seconds instead, and the parked count then lands ON the restored row through `_find`."""
    if manager is None or getattr(manager, 'objectTables', None) is None:
        return False
    if getattr(manager, 'definitionsRestored', True) is False:
        return False
    if table:
        try:
            if table in (manager.classesPendingRestore((table,)) or ()):
                return False
        except Exception:               # noqa: BLE001 — a manager without the bookkeeping is ready
            pass
    return True


def _park(direction, name, fields):
    """Remember one observation until there is somewhere to put it. Counted, never duplicated."""
    key = (direction, name)
    entry = _PENDING.get(key)
    if entry is None:
        if len(_PENDING) >= PENDING_MAX:
            return None
        _PENDING[key] = dict(fields, count=1)
        return _PENDING[key]
    entry['count'] += 1
    entry['classes'] = sorted(set(entry.get('classes') or []) | set(fields.get('classes') or []))[:MAX_CLASSES]
    entry['paths'] = (entry.get('paths') or []) + [p for p in (fields.get('paths') or [])
                                                   if p not in (entry.get('paths') or [])]
    return entry


DERIVED_PARKED = ('observed before the tree was restored (boot-time; flushed at the first request — §66a/§66b)')


def flush_pending(manager):
    """Write the parked observations as rows, then forget them. Dev posture only (production derives nothing);
    the buffer is cleared either way so it can never grow across a long production run. Never raises."""
    if not _PENDING or not tree_ready(manager):
        return 0
    # §66 addendum 6: flush only the directions whose table is actually back.
    # Flushing an unrestored one would put the parked count in the very place
    # the restore is about to merge, which is the race this buffer exists to
    # avoid — so those entries stay parked for one more read.
    ready = {d for d in TABLES if tree_ready(manager, TABLES[d][0])}
    if not ready:
        return 0
    parked = [item for item in _PENDING.items() if item[0][0] in ready]
    for key, _entry in parked:
        _PENDING.pop(key, None)
    if not observing():
        _PENDING.clear()                # production derives nothing and parks nothing
        return 0
    heal_duplicates(manager)                # §66d: land ON the restored row, never beside it
    n = 0
    for (direction, name), entry in parked:
        try:
            table = TABLES[direction][0]
            row = _find(manager, table, name)
            for _ in range(int(entry.get('count') or 1)):
                if direction == 'outbound':
                    row = _observe_outbound(manager, name, entry['system_kind'], entry['system_name'],
                                            entry['means'], entry.get('classes') or [], row) or row
                else:
                    paths = entry.get('paths') or ['']
                    row = _observe_inbound(manager, name, entry['source_kind'], entry['source'],
                                           paths[0], row) or row
            if row is not None:
                if direction == 'inbound':
                    _merge_paths(row, entry.get('paths') or [])
                row.derived_from = DERIVED_PARKED
                n += 1
        except Exception:                   # noqa: BLE001 — a flush never raises into its caller
            continue
    if n:
        _schedule_persist(manager)
    return n


# ---- the verdict ----------------------------------------------------------------------------------------

def _answer(allowed, rule, why, name='', state='', count=0, extra=None):
    out = {'allowed': bool(allowed), 'rule': rule, 'why': why, 'knob': mode(), 'name': name,
           'state': state, 'count': int(count or 0), 'posture': _posture.posture()}
    if extra:
        out.update(extra)
    return out


#: the reading every refusal carries — closed by default is a RULE, not an accident of an empty table
WHY_UNCONFIRMED = ('closed by default (design §5a): only a CONFIRMED policy row allows traffic, and a '
                   '`suggested` row is a proposal nobody has ruled on yet')


def _verdict(manager, direction, name, observe_fn, park_fields):
    """The shared ladder. `observe_fn(row)` does the dev-posture write and returns the row (or None);
    `park_fields` is what to remember instead when there is no tree to write to yet (§66a/§66b)."""
    table, _keys = TABLES[direction]
    if not tree_ready(manager, table):
        _park(direction, name, park_fields)
        return _answer(True, 'no-security',
                       'the object tree is not restored yet (a send before the manager exists at boot, a '
                       'request served during lazy boot, or an instance carrying no security rows at all) — '
                       'the traffic proceeds exactly as it did before ct-9. The observation is PARKED and '
                       'becomes a row at the first request that finds a restored tree (§66a/§66b), so nothing '
                       'goes unlisted and nothing a person confirmed is overwritten by a half-booted guess.',
                       name=name)
    flush_pending(manager)                  # §66a/§66b: the parked observations, now that there is a tree
    row = _find(manager, table, name)
    state = _clean(getattr(row, 'state', '')) if row is not None else ''
    row = observe_fn(row) or row
    count = int(getattr(row, 'count', 0) or 0) if row is not None else 0
    if state == 'confirmed':
        return _answer(True, 'confirmed',
                       'a person confirmed this %s policy (%s)' % (direction, getattr(row, 'confirmed_at', '')),
                       name=name, state=state, count=count)
    if state == 'denied':
        ans = _answer(False, 'denied',
                      'a person DENIED this %s policy on the record (%s)' % (direction,
                                                                             getattr(row, 'confirmed_at', '')),
                      name=name, state=state, count=count)
    elif state == 'suggested':
        ans = _answer(False, 'suggested', WHY_UNCONFIRMED, name=name, state=state, count=count)
    else:
        ans = _answer(False, 'suggested-new',
                      (WHY_UNCONFIRMED + '. Nothing has ever proposed this one: '
                       + ('a `suggested` row has just been written from this observation — the suggestion list '
                          'IS the monitoring' if observing() else
                          'this instance is in production posture, so NOTHING was written (tracing does not '
                          'happen in production); the row is derived on a dev instance and carried here')),
                      name=name, state='suggested' if observing() else '', count=count)
    _note_refusal(manager, direction, name, ans)
    return ans


def _note_refusal(manager, direction, name, answer):
    """One counted `SecurityEvent` per refused subject — the ledger production DOES keep. Under `off` nothing
    is acted on and nothing is written: a verdict nobody enforces is not a security decision."""
    knob = answer.get('knob')
    if knob == 'off':
        return
    try:
        _record_event(manager, 'traffic', direction, name, reason=answer.get('why', ''),
                      outcome='denied' if knob == 'enforce' else 'observed', would_deny=True,
                      source='security.custom.security_traffic', save=True)
    except Exception:                       # noqa: BLE001 — a recorder never raises into the thing it observes
        pass


def _advise(line):
    try:
        from accessControl.traffic_middleware import advise
        advise(line)
    except Exception:                       # noqa: BLE001
        pass


def outbound_verdict(manager, system_kind, system_name, means, payload_classes=()):
    """MAY THIS SEND LEAVE? Called by `polariApiServer.outbound.send()` before it runs the call.

    Returns `{allowed, rule, why, knob, name, state, count, posture}` where `rule` is one of:

        confirmed      a person said yes — allowed
        denied         a person said no on the record — refused
        suggested      the monitoring proposed it and nobody has ruled — refused (closed by default)
        suggested-new  nothing had ever proposed it; in DEV a `suggested` row was just written from this very
                       observation, in production nothing was written at all — refused either way
        no-security    there is no policy table to consult — allowed, and says so

    `allowed` is the POLICY's answer; what happens to it is the MODE's business (`knob`). Never raises: a
    broken policy degrades to `no-security`, because a guard must not be able to take the outbound path down.
    """
    try:
        name = outbound_name(system_kind, system_name, means)
        classes = sorted({str(c) for c in (payload_classes or []) if c})[:MAX_CLASSES]
        ans = _verdict(manager, 'outbound', name,
                       lambda row: _observe_outbound(manager, name, system_kind, system_name, means,
                                                     classes, row),
                       {'system_kind': _clean(system_kind, 'other'),
                        'system_name': _clean(system_name, 'unnamed'),
                        'means': _clean(means, 'send'), 'classes': list(classes)})
        if not ans['allowed'] and ans['knob'] == 'advisory':
            _advise('would-deny outbound %s:%s' % (_clean(system_kind, 'other'), _clean(system_name, 'unnamed')))
        return ans
    except Exception:                       # noqa: BLE001
        return _answer(True, 'no-security', 'the traffic policy could not be consulted; the send proceeds')


def inbound_verdict(manager, source_kind, source, path_template=''):
    """MAY THIS CALLER IN? Called by `accessControl.traffic_middleware` on every request, with a source that is
    a NAME or a CLASS and never an address. Same shape, same ladder, same rules as `outbound_verdict`."""
    try:
        name = inbound_name(source_kind, source)
        ans = _verdict(manager, 'inbound', name,
                       lambda row: _observe_inbound(manager, name, source_kind, source, path_template, row),
                       {'source_kind': _clean(source_kind, 'anonymous'),
                        'source': _clean(source, 'anonymous'),
                        'paths': [p for p in [_clean(path_template)] if p]})
        return ans
    except Exception:                       # noqa: BLE001
        return _answer(True, 'no-security', 'the traffic policy could not be consulted; the request proceeds')


# ---- the monitoring (dev posture ONLY) ------------------------------------------------------------------

def _bump(row, now):
    row.count = int(getattr(row, 'count', 0) or 0) + 1
    row.last_seen = now
    if not getattr(row, 'first_seen', ''):
        row.first_seen = now


def _observe_outbound(manager, name, system_kind, system_name, means, classes, row):
    """Create or bump the row for one observed send. DEV POSTURE ONLY — production derives nothing."""
    if not observing():
        return row
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return row
        now = _now()
        if row is None:
            row, is_new = _plain_row(tables, 'OutboundPolicy', name, None)
            if is_new:
                from security.objects.security.OutboundPolicy import OutboundPolicy
                row = _new_row(manager, tables, 'OutboundPolicy', OutboundPolicy, {
                    'name': name, 'system_kind': _clean(system_kind, 'other'),
                    'system_name': _clean(system_name, 'unnamed'), 'means': _clean(means, 'send'),
                    'payload_classes_json': json.dumps(classes), 'state': 'suggested',
                    'derived_from': 'observed send (polariApiServer.outbound, dev posture)',
                    'confirmed_by': '', 'confirmed_at': '', 'count': 1,
                    'first_seen': now, 'last_seen': now})
                _schedule_persist(manager)
                return row
        _bump(row, now)
        known = _json_list(row, 'payload_classes_json')
        merged = sorted(set(known) | set(classes))[:MAX_CLASSES]
        if merged != known:
            row.payload_classes_json = json.dumps(merged)
        _schedule_persist(manager)
        return row
    except Exception:                       # noqa: BLE001 — a recorder never raises into the thing it observes
        return row


def _observe_inbound(manager, name, source_kind, source, path_template, row):
    """Create or bump the row for one observed request. DEV POSTURE ONLY."""
    if not observing():
        return row
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return row
        now = _now()
        paths = [p for p in [_clean(path_template)] if p][:1]
        if row is None:
            row, is_new = _plain_row(tables, 'InboundPolicy', name, None)
            if is_new:
                from security.objects.security.InboundPolicy import InboundPolicy
                row = _new_row(manager, tables, 'InboundPolicy', InboundPolicy, {
                    'name': name, 'source_kind': _clean(source_kind, 'anonymous'),
                    'source': _clean(source, 'anonymous'), 'paths_json': json.dumps(paths),
                    'state': 'suggested',
                    'derived_from': 'observed request (accessControl.traffic_middleware, dev posture)',
                    'confirmed_by': '', 'confirmed_at': '', 'count': 1,
                    'first_seen': now, 'last_seen': now})
                _schedule_persist(manager)
                return row
        _bump(row, now)
        _merge_paths(row, paths)
        _schedule_persist(manager)
        return row
    except Exception:                       # noqa: BLE001
        return row


def _merge_paths(row, paths):
    known = _json_list(row, 'paths_json')
    for p in paths:
        if p and p not in known and len(known) < MAX_PATHS:
            known.append(p)
    row.paths_json = json.dumps(known)
    return known


def note_inbound_path(manager, name, path_template):
    """Add ONE endpoint TEMPLATE to an existing inbound row, capped at `MAX_PATHS`, without bumping the count.

    Falcon routes after `process_request`, so the template is only known in `process_resource` — the same
    two-step refinement ct-0 does for the cause's `entry_ref`. Dev posture only; never raises."""
    if (not observing() or not name or not path_template
            or not tree_ready(manager, 'InboundPolicy')):
        return None
    try:
        row = _find(manager, 'InboundPolicy', name)
        if row is None:
            return None
        before = _json_list(row, 'paths_json')
        after = _merge_paths(row, [_clean(path_template)])
        if after != before:
            _schedule_persist(manager)
        return row
    except Exception:                       # noqa: BLE001
        return None


# ---- a PERSON rules (nothing confirms itself) -----------------------------------------------------------

def _confirm(manager, direction, name, user_info, decision):
    table, keys = TABLES[direction]
    sub = actor_of(user_info)
    if not sub:
        return {'ok': False, 'status': 401,
                'refusal': ('sign in first: a traffic policy is confirmed by a PERSON, and a person is a '
                            'Keycloak `sub` (D18-1). Nothing confirms itself.')}
    try:
        from security.custom.security_claims import is_admin
        admin = is_admin(user_info)
    except Exception:                       # noqa: BLE001
        admin = False
    if not admin:
        return {'ok': False, 'status': 403,
                'refusal': ('only an administrator may rule on a traffic policy (ADMIN_ROLES: admin, '
                            'polari-admin): confirming one decides what may leave this instance, or who may '
                            'call it, for every caller')}
    decision = _clean(decision)
    if decision not in DECISIONS:
        return {'ok': False, 'status': 400,
                'refusal': 'decision must be "confirmed" or "denied" — a person rules, or the row stays closed'}
    row = _find(manager, table, name)
    if row is None:
        return {'ok': False, 'status': 404,
                'refusal': ('no %s policy is named %r. Rows are DERIVED from dev monitoring — act once with the '
                            'traffic you mean to allow and the suggestion appears at GET /api/security/traffic'
                            % (direction, name))}
    row.state = decision
    row.confirmed_by = sub
    row.confirmed_at = _now()
    _schedule_persist(manager)
    _record_event(manager, 'traffic', '%s-%s' % (direction, decision), name,
                  reason='ruled %s by a person' % decision, actor=sub, outcome='allowed' if decision == 'confirmed' else 'denied',
                  would_deny=False, source='security.custom.security_traffic', save=True)
    return {'ok': True, 'status': 200, 'direction': direction, 'decision': decision,
            'policy': {k: getattr(row, k, '') for k in keys},
            'how': ('the row now applies in every posture: under `enforce` a confirmed row is the only thing '
                    'that lets traffic through, and a denied one refuses it with this ruling as the evidence')}


def confirm_outbound(manager, name, user_info, decision):
    """A person rules on one outbound policy. 401 without a `sub`, 403 without an admin role, 400 on anything
    but confirmed|denied, 404 on a row nothing proposed."""
    return _confirm(manager, 'outbound', name, user_info, decision)


def confirm_inbound(manager, name, user_info, decision):
    """A person rules on one inbound policy — same refusals, same rule."""
    return _confirm(manager, 'inbound', name, user_info, decision)


# ---- reading ---------------------------------------------------------------------------------------------

def _rows(manager, direction, state=''):
    table, keys = TABLES[direction]
    heal_duplicates(manager, direction)     # §66d: one row per name, always, on every read
    out = [{k: getattr(r, k, '') for k in keys} for r in _all_rows(manager, table)]
    if state:
        out = [r for r in out if r.get('state') == state]
    out.sort(key=lambda d: (-int(d.get('count') or 0), d.get('name') or ''))
    return out


def policies(manager):
    """Every traffic policy row, both directions, with the mode and the posture that decide what they mean."""
    flush_pending(manager)                  # §66a: a door read is as good a moment as a verdict
    out = _rows(manager, 'outbound')
    inb = _rows(manager, 'inbound')
    return {'mode': mode(), 'posture': _posture.posture(), 'observing': observing(),
            'outbound': out, 'inbound': inb,
            'counts': {d: {s: len([r for r in rows if r.get('state') == s]) for s in POLICY_STATES}
                       for d, rows in (('outbound', out), ('inbound', inb))}}


def suggestions(manager):
    """THE MONITORING: the rows derived from traffic that nobody has ruled on, busiest first.

    His ask in one list — "suggest outbound and inbounds based on our monitoring of traffic in and out of
    polari". Every row carries its count, its first/last seen and what derived it, so a person confirms on
    evidence rather than on a name."""
    flush_pending(manager)
    return {'mode': mode(), 'posture': _posture.posture(),
            'outbound': _rows(manager, 'outbound', 'suggested'),
            'inbound': _rows(manager, 'inbound', 'suggested'),
            'how': ('each row is ONE observed subject, counted. Confirm the ones that belong (POST '
                    '/api/security/traffic/outbound/<name> or /inbound/<name> {"decision": "confirmed"}) and '
                    'DENY the rest on the record — under `enforce` everything unconfirmed is refused, so the '
                    'list shrinking to nothing is what "closed by default" looks like when it is finished.')}


def declared_flows(manager):
    """The CONFIRMED rows as declared edges for the object topology (design §7) and for ct-8's `flow-declared`
    / `inbound` decision kinds.

    One dict per flow: `direction`, the counterpart (`system` outbound, `source` inbound), the `means` it
    crosses by, and the payload `classes` — which are honestly EMPTY for an inbound row, because what a caller
    sends is known only once it reaches a class, and the map records that as an object edge, not as traffic.
    `node` is the design §2 node string, so the topology builder can join these to the observed edges without
    re-deriving the vocabulary."""
    out = []
    for r in _rows(manager, 'outbound', 'confirmed'):
        kind, name = r['system_kind'], r['system_name']
        node = ('peer:%s:%s' % (name, r['means'])) if kind == 'peer' else ('external:%s:%s' % (kind, name))
        out.append({'direction': 'outbound', 'node': node, 'system': '%s:%s' % (kind, name),
                    'system_kind': kind, 'system_name': name, 'means': r['means'],
                    'classes': _load(r.get('payload_classes_json')), 'count': r['count'],
                    'confirmed_by': r['confirmed_by'], 'confirmed_at': r['confirmed_at'],
                    'provenance': 'declared'})
    for r in _rows(manager, 'inbound', 'confirmed'):
        kind, source = r['source_kind'], r['source']
        out.append({'direction': 'inbound', 'node': 'inbound:%s:%s' % (kind, source),
                    'source': '%s:%s' % (kind, source), 'source_kind': kind, 'source_name': source,
                    'means': 'request', 'classes': [], 'paths': _load(r.get('paths_json')),
                    'count': r['count'], 'confirmed_by': r['confirmed_by'],
                    'confirmed_at': r['confirmed_at'], 'provenance': 'declared'})
    return out


def _load(raw):
    try:
        v = json.loads(str(raw or '[]'))
        return [str(x) for x in v] if isinstance(v, list) else []
    except Exception:                       # noqa: BLE001
        return []


HOW_TRAFFIC = ('closed by default (his ruling 2026-09-18). A `confirmed` row is the only thing that lets '
               'traffic through under `enforce`; `suggested` rows are what the dev-posture monitoring PROPOSED '
               'and nobody has ruled on; `denied` rows are refusals a person made on the record. Rows are '
               'written only on a dev-posture instance — production carries the confirmed and denied ones and '
               'derives nothing, because tracing does not happen in production. A row never holds a raw '
               'address, a bearer or a payload: outbound rows name the configured system and the payload '
               'CLASSES, inbound rows name a peer, an Origin host or a class such as `anonymous`.')


def summary(manager):
    """What the doors and the page read: the policies, the suggestions, the mode and the reading."""
    pol = policies(manager)
    return {'ok': True, **pol, 'suggestions': suggestions(manager),
            'declared': declared_flows(manager), 'how': HOW_TRAFFIC}
