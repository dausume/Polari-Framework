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
    return next((r for r in _all_rows(manager, table) if getattr(r, 'name', '') == name), None)


# ---- the sends that happen before there IS a manager (§66a) -----------------------------------------------
# Found by the live proof on `polari-lean` (2026-09-19): outbound rows were EMPTY on an instance whose
# Keycloak and JWKS sends demonstrably happen. `polariApiServer.outbound.process_manager()` answers None until
# `polariServer` injects the manager at boot (polariServer.py:780), and a send before that had nowhere to write
# — so the very sends that run earliest, which are exactly the ones a person most wants to rule on, were the
# ones that never appeared. They are PARKED here instead, counted, and flushed into rows the first time any
# verdict or door is asked with a real manager. Bounded, in-process, and lost on a restart on purpose: a parked
# send is an observation, and observations do not outlive the process that made them.

PENDING_MAX = 200
_PENDING = {}


def _park(name, system_kind, system_name, means, classes):
    entry = _PENDING.get(name)
    if entry is None:
        if len(_PENDING) >= PENDING_MAX:
            return None
        _PENDING[name] = {'system_kind': system_kind, 'system_name': system_name, 'means': means,
                          'classes': list(classes), 'count': 1}
        return _PENDING[name]
    entry['count'] += 1
    entry['classes'] = sorted(set(entry['classes']) | set(classes))[:MAX_CLASSES]
    return entry


def flush_pending(manager):
    """Write the parked sends as rows, then forget them. Dev posture only (production derives nothing); the
    buffer is cleared either way so it can never grow across a long production run. Never raises."""
    if not _PENDING:
        return 0
    parked = list(_PENDING.items())
    _PENDING.clear()
    if not observing():
        return 0
    n = 0
    for name, entry in parked:
        try:
            row = _find(manager, 'OutboundPolicy', name)
            for _ in range(int(entry.get('count') or 1)):
                row = _observe_outbound(manager, name, entry['system_kind'], entry['system_name'],
                                        entry['means'], entry['classes'], row) or row
            if row is not None:
                row.derived_from = ('observed send before the manager existed (boot-time, flushed at the first '
                                    'request — §66a)')
                n += 1
        except Exception:                   # noqa: BLE001 — a flush never raises into its caller
            continue
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


def _verdict(manager, direction, name, observe_fn):
    """The shared ladder. `observe_fn(row)` does the dev-posture write and returns the row (or None)."""
    table, _keys = TABLES[direction]
    tables = getattr(manager, 'objectTables', None) if manager is not None else None
    if tables is None:
        return _answer(True, 'no-security',
                       'there is no object tree to consult yet (a send before the manager exists at boot, or an '
                       'instance carrying no security rows at all) — the traffic proceeds exactly as it did '
                       'before ct-9. A boot-time OUTBOUND send is PARKED and becomes a row at the first request '
                       '(§66a), so nothing that leaves goes unlisted.',
                       name=name)
    flush_pending(manager)                  # §66a: the boot-time sends, now that there is somewhere to write
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
        if manager is None or getattr(manager, 'objectTables', None) is None:
            # §66a: no tree yet (a boot-time send). Park it so the first request turns it into a row.
            _park(name, _clean(system_kind, 'other'), _clean(system_name, 'unnamed'), _clean(means, 'send'),
                  classes)
        ans = _verdict(manager, 'outbound', name,
                       lambda row: _observe_outbound(manager, name, system_kind, system_name, means,
                                                     classes, row))
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
                       lambda row: _observe_inbound(manager, name, source_kind, source, path_template, row))
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
    if not observing() or not name or not path_template:
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
