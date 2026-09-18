"""
accessControl.cause_context — the CAUSE that travels with execution (ct-0).

CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2: a `CauseContext` is a small dict that
rides synchronous execution from the entry point down to every seam that
records something:

    {trace_id, parent_id, entry_kind, entry_ref, actor, groups, roleplay, depth}

`entry_kind` is one of ENTRY_KINDS below. `entry_ref` names the door:
`PUT /api/MealEntry/{id}`, `trigger:daily-rollup`, `solution:score-article`.

Modelled exactly on `simulationLocks/run_context.py` (`push_run`/`pop_run`/
`current_run`), which the tree already reads from deep inside
`objectTreeDecorators.py` and `polariCRUDE.py`. A CHILD cause is pushed at
every seam crossing: it inherits `trace_id`, takes the current cause's id as
`parent_id` and `depth + 1`, so a chain is recoverable with no global registry.

DEV POSTURE ONLY (his ruling 2026-09-18, design §2/§10: "tracing should not
occur in production, only finalized security posture rows derived from them").
When `moduleService.posture` does not say `dev`, `root_cause()` returns None
and NOTHING is pushed — not the ledgers, not the target, not even the context.
`child_cause()` is likewise a no-op when there is no current cause, so a
production request never mints one on the way down either.

THE PII BOUNDARY (D18-1): `actor` holds the caller's opaque Keycloak `sub` and
nothing else — never a preferred_username, never an e-mail, never a display
name. `actor_of()` here is the same rule as
`security.custom.security_observe.actor_of` (imported lazily when the security
module is present, replicated verbatim when it is not, so this module has no
import-time dependency on a module bundle).

THE THREAD BOUNDARY (design §4, the one honest limitation): contextvars follow
SYNCHRONOUS execution and nothing else. A `threading.Thread` / `threading.Timer`
does NOT inherit the cause — every background worker must mint its own root
cause or be handed one by argument. `selftest_cause_context.py` keeps the
inventory of thread sites and fails when a new one appears un-listed.
"""

import contextvars
import uuid
from typing import Dict, Optional, Sequence

#: design §2 — the entry kinds a chain can start from.
ENTRY_KINDS = ('api', 'trigger', 'schedule', 'solution', 'simulation',
               'peer', 'ai', 'boot')

_CAUSE_CONTEXT: contextvars.ContextVar = contextvars.ContextVar(
    'polari_cause_context', default=None)

#: the header a Polari instance sends another so the two maps join
#: (`<trace_id>/<parent_id>` — trace ids ONLY, never the sub — design §10).
TRACE_HEADER = 'X-Polari-Trace'


# ---- the posture switch -------------------------------------------------

def tracing_enabled() -> bool:
    """True only in dev posture. Never raises: an unreadable posture is
    production, which is the safe answer (no tracing)."""
    try:
        from moduleService import posture
        return bool(posture.is_dev())
    except Exception:       # noqa: BLE001 — a switch that cannot be read is off
        return False


# ---- the PII boundary ---------------------------------------------------

def actor_of(user_info) -> str:
    """The caller's opaque Keycloak `sub`, or '' when there is nobody.

    Prefers `security.custom.security_observe.actor_of` (the ONE resolution)
    and replicates its rule when the security module is not installed."""
    try:
        from security.custom.security_observe import actor_of as _actor_of
        return _actor_of(user_info)
    except Exception:       # noqa: BLE001 — the rule, replicated
        if not isinstance(user_info, dict):
            return ''
        return str(user_info.get('sub') or '')


# ---- the contextvar -----------------------------------------------------

def current_cause() -> Optional[Dict]:
    """The cause riding this call stack, or None."""
    return _CAUSE_CONTEXT.get()


def push_cause(**fields):
    """Push a cause dict built from `fields`; returns the reset token.

    Missing fields are filled with their defaults, so a caller may push a
    partial cause (the selftests do) without the readers learning a shape."""
    cause = {
        'trace_id': fields.get('trace_id') or new_trace_id(),
        'parent_id': fields.get('parent_id') or '',
        'entry_kind': fields.get('entry_kind') or 'api',
        'entry_ref': str(fields.get('entry_ref') or '')[:400],
        'actor': str(fields.get('actor') or ''),
        'groups': tuple(fields.get('groups') or ()),
        'roleplay': fields.get('roleplay') or '',
        'depth': int(fields.get('depth') or 0),
    }
    cause['id'] = fields.get('id') or new_trace_id()
    return _CAUSE_CONTEXT.set(cause)


def pop_cause(token) -> None:
    """Reset to whatever was current before the matching push. A None token
    (the push was declined by posture) is a no-op, so every caller can write
    the same balanced try/finally."""
    if token is None:
        return
    try:
        _CAUSE_CONTEXT.reset(token)
    except ValueError:      # a token from another context — nothing to reset
        pass


def new_trace_id() -> str:
    return uuid.uuid4().hex


# ---- the two mints ------------------------------------------------------

def root_cause(entry_kind: str, entry_ref: str, actor: Optional[str] = None,
               groups: Sequence[str] = (), roleplay: Optional[str] = None,
               trace_id: str = '', parent_id: str = ''):
    """Start a NEW chain (depth 0). Returns the push token, or None in
    production posture, where no cause is minted at all.

    `trace_id`/`parent_id` are given only when adopting a peer's chain from
    an inbound `X-Polari-Trace` header (design §3, the peer root)."""
    if not tracing_enabled():
        return None
    if entry_kind not in ENTRY_KINDS:
        entry_kind = 'api'
    return push_cause(trace_id=trace_id or new_trace_id(),
                      parent_id=parent_id or '',
                      entry_kind=entry_kind, entry_ref=entry_ref,
                      actor=actor or '', groups=groups,
                      roleplay=roleplay or '', depth=0)


def child_cause(entry_kind: str, entry_ref: str):
    """Cross a seam inside an existing chain: same `trace_id`, `parent_id` =
    the current cause's id, `depth + 1`. Returns None (and pushes nothing)
    when there is no current cause — production, or a path nobody traced."""
    parent = current_cause()
    if parent is None:
        return None
    if entry_kind not in ENTRY_KINDS:
        entry_kind = 'solution'
    return push_cause(trace_id=parent.get('trace_id', ''),
                      parent_id=parent.get('id', ''),
                      entry_kind=entry_kind, entry_ref=entry_ref,
                      actor=parent.get('actor', ''),
                      groups=parent.get('groups', ()),
                      roleplay=parent.get('roleplay', ''),
                      depth=int(parent.get('depth', 0)) + 1)


def child_or_root_cause(entry_kind: str, entry_ref: str):
    """A child when a chain is running, a root of the same kind when one is
    not (the dispatcher tick, an engine called straight from a selftest)."""
    token = child_cause(entry_kind, entry_ref)
    if token is None and current_cause() is None:
        token = root_cause(entry_kind, entry_ref)
    return token


# ---- what the ledgers stamp (ct-1 writes them; ct-0 only supplies them) --

def trace_ids() -> Dict[str, str]:
    """`{'trace_id', 'parent_id'}` of the current cause — '' / '' when there
    is none, so a row always has the columns and never a None."""
    cause = current_cause()
    if not cause:
        return {'trace_id': '', 'parent_id': ''}
    return {'trace_id': cause.get('trace_id', ''),
            'parent_id': cause.get('id', '')}


def parse_trace_header(value) -> Dict[str, str]:
    """`<trace_id>/<parent_id>` → the two ids ('' / '' when malformed)."""
    raw = str(value or '').strip()
    if not raw:
        return {'trace_id': '', 'parent_id': ''}
    head, _, tail = raw.partition('/')
    head = ''.join(c for c in head if c.isalnum() or c in '-_')[:64]
    tail = ''.join(c for c in tail if c.isalnum() or c in '-_')[:64]
    return {'trace_id': head, 'parent_id': tail}


def trace_header_value() -> str:
    """What to put on an outbound request to another Polari instance
    (ct-3 adopts it; ct-0 only defines the spelling)."""
    ids = trace_ids()
    if not ids['trace_id']:
        return ''
    return f"{ids['trace_id']}/{ids['parent_id']}"
