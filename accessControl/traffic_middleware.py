"""
accessControl.traffic_middleware — WHO IS CALLING, and the advisory channel both halves of ct-9 speak through
(design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §5a).

Two things live here, both CORE-resident so nothing in the request path depends on the security module being
installed:

1. **The advisory sink.** A `would-deny` from the outbound wrapper happens deep inside a send, with no falcon
   response in reach; a `would-deny` from the inbound gate happens before the responder runs. Both call
   `advise()`, which parks the line on a contextvar (and, when a cause is riding the chain, on the cause dict
   too, so it travels with the trace), and `CauseContextMiddleware.process_response` drains it into
   `X-Polari-Traffic-Advisory`. The contextvar is the load-bearing half: production posture mints NO cause at
   all (ct-0), and an advisory-mode production instance must still be able to say what it would have denied.

2. **The inbound gate.** `TrafficPolicyMiddleware` classifies every caller into one of design §5a's four
   source kinds — and NEVER into an address:

       peer        an `X-Polari-Trace` header, or an Origin/Host matching a registered `PeerNode.base_url`
                   → the peer's NAME
       origin      an `Origin` header → `scheme://host` ONLY (no path, no query). An IP-LITERAL host is
                   recorded as the class `ip-literal`: Polari does not put a raw address in a row
       anonymous   neither — a class, not an identity
       external    reserved for a CONFIGURED external caller's name; nothing configures one yet (stated)

   It then asks `security.custom.security_traffic.inbound_verdict` and follows the SAME ladder every other
   gate in this package follows (`app_permissions_gate.gate_mode()`):

       off        nothing at all
       advisory   the request proceeds; the would-deny rides the advisory header
       enforce    403 BEFORE the responder runs, with the evidence

   His "closed by default in production" is realised when the production answer is `enforce`: an unconfirmed
   source is refused exactly as an unknown one is. The home stack runs `advisory` by his standing rule
   (security WARN-ONLY in deployments, §17), so on it this gate warns and never blocks.

Never raises into a request: a broken gate degrades to proceed-with-nothing, the `AuthContextMiddleware` idiom.
"""

import contextvars

#: the response header the drained advisories are emitted on (added to the CORS expose list in polariServer)
TRAFFIC_ADVISORY_HEADER = 'X-Polari-Traffic-Advisory'

#: the peer trace header (ct-0). Imported by name rather than from cause_context so this module stays usable
#: when the cause context is not installed.
TRACE_HEADER = 'X-Polari-Trace'

#: doors the inbound gate NEVER refuses, whatever the mode. `/api/health` is how an orchestrator learns the
#: instance is alive, and `/api/security/traffic` is where a person CONFIRMS a source — gating the confirmation
#: door behind the confirmations would lock an administrator out of their own instance on the first enforce.
#: Both are already behind Keycloak (or deliberately public, in health's case), so the exemption opens nothing
#: a bearer does not already open. Stated rather than silent.
NEVER_REFUSED = ('/api/health', '/api/security/traffic')

#: how many advisory lines one response may carry (a burst of sends must not grow a header without bound)
MAX_ADVISORIES = 8

_ADVISORIES = contextvars.ContextVar('polari_traffic_advisories', default=())


# ---- the advisory sink --------------------------------------------------

def advise(line):
    """Park one `would-deny …` line for this request's response. Never raises, never duplicates."""
    text = str(line or '').strip()[:200]
    if not text:
        return
    try:
        current = tuple(_ADVISORIES.get() or ())
        if text in current or len(current) >= MAX_ADVISORIES:
            return
        _ADVISORIES.set(current + (text,))
    except Exception:      # noqa: BLE001 — an advisory is diagnosis, never a failure mode
        pass
    try:
        from accessControl.cause_context import current_cause
        cause = current_cause()
        if cause is not None:
            cause.setdefault('advisories', []).append(text)
    except Exception:      # noqa: BLE001 — no cause (production posture) is the normal case
        pass


def advisories():
    """What is parked right now, without clearing it (the selftests and the gate read it)."""
    try:
        return list(_ADVISORIES.get() or ())
    except Exception:      # noqa: BLE001
        return []


def drain_advisories():
    """Take the parked lines and clear them. Called once per response, and again at the start of the next
    request, so a line can never leak from one caller's response into another's."""
    out = advisories()
    try:
        if out:
            _ADVISORIES.set(())
    except Exception:      # noqa: BLE001
        pass
    return out


# ---- classifying the caller (never an address) --------------------------

def _header(req, name):
    try:
        return (req.get_header(name) or '').strip()
    except Exception:      # noqa: BLE001
        return ''


def _is_ip_literal(host):
    """A bare IPv4/IPv6 host. Polari does not store a raw address in a row (design §5a), so these collapse to
    the single class `ip-literal`."""
    h = str(host or '').split(':')[0] if str(host or '').count(':') <= 1 else str(host or '')
    if h.startswith('[') or ':' in h:
        return True                                   # bracketed or bare IPv6
    parts = h.split('.')
    return len(parts) == 4 and all(p.isdigit() and len(p) <= 3 for p in parts)


def normalise_origin(value):
    """`https://app.example:4200` → `https://app.example` — scheme + host, no port, no path, no query, and
    never a raw address. Returns '' when there is nothing usable."""
    raw = str(value or '').strip()
    if not raw or raw.lower() == 'null':
        return ''
    scheme, _, rest = raw.partition('://')
    if not rest:
        scheme, rest = 'http', raw
    host = rest.split('/')[0].split('?')[0].strip()
    if not host:
        return ''
    if _is_ip_literal(host):
        return 'ip-literal'
    host = host.split(':')[0] if not host.startswith('[') else host.split(']')[0] + ']'
    return ('%s://%s' % (scheme.lower(), host.lower()))[:200]


def _peer_names(manager):
    """{host: peer name} from the registered `PeerNode` rows — the ONE place an address is turned back into a
    name, and the address itself never leaves this function."""
    out = {}
    try:
        rows = ((getattr(manager, 'objectTables', None) or {}).get('PeerNode') or {}).values()
    except Exception:      # noqa: BLE001
        return out
    for row in rows:
        base = str(getattr(row, 'base_url', '') or '')
        name = str(getattr(row, 'name', '') or '')
        if not base or not name:
            continue
        host = base.partition('://')[2] or base
        host = host.split('/')[0].strip().lower()
        if host:
            out[host] = name
            out[host.split(':')[0]] = name
    return out


def classify(manager, req):
    """(source_kind, source) for one request. NEVER an IP, never a bearer, never a header value."""
    try:
        origin = _header(req, 'Origin')
        host = _header(req, 'Host')
        peers = _peer_names(manager)
        for candidate in (origin.partition('://')[2] or origin, host):
            key = str(candidate or '').split('/')[0].strip().lower()
            if key and (key in peers or key.split(':')[0] in peers):
                return 'peer', peers.get(key) or peers[key.split(':')[0]]
        if _header(req, TRACE_HEADER):
            # a Polari chain is being adopted, but nothing registered the sender: it is still a peer, and the
            # row says it is an unregistered one rather than inventing a name or storing where it came from
            return 'peer', 'unregistered'
        if origin:
            norm = normalise_origin(origin)
            return ('origin', norm) if norm else ('anonymous', 'anonymous')
        return 'anonymous', 'anonymous'
    except Exception:      # noqa: BLE001
        return 'anonymous', 'anonymous'


def path_template(req):
    """The ROUTE template falcon resolved, or '' — and NEVER the raw path.

    ct-0 falls back to `req.path` for a cause's `entry_ref` because a cause is diagnosis; a policy row is not.
    `/api/MealEntry/m-1` carries an instance id, so falling back to it would put one in a row that outlives the
    request. Falcon routes AFTER `process_request`, so this is empty there and the template is added in
    `process_resource` — the same two-step refinement, with the unsafe half left out."""
    try:
        return str(getattr(req, 'uri_template', None) or '')[:200]
    except Exception:      # noqa: BLE001
        return ''


# ---- the gate -----------------------------------------------------------

class TrafficPolicyMiddleware:
    """The inbound half of ct-9. Registered immediately AFTER `CauseContextMiddleware`, so a refusal is still
    inside a cause (in dev) and the advisory drain in that middleware's `process_response` sees what this one
    parked."""

    CONTEXT_ATTR = 'traffic'

    def __init__(self, server=None):
        self.server = server

    def _manager(self):
        manager = getattr(self.server, 'manager', None)
        if manager is not None:
            return manager
        try:
            from polariApiServer.outbound import process_manager
            return process_manager()
        except Exception:      # noqa: BLE001
            return None

    def process_request(self, req, resp):
        """Classify, record, and refuse under `enforce` — before routing, so a source nobody confirmed gets
        nothing at all rather than a 404 that tells it which doors exist."""
        refusal = None
        try:
            req.context.traffic = None
            drain_advisories()                   # a previous response's lines never leak into this one
            manager = self._manager()
            kind, source = classify(manager, req)
            answer = self._verdict(manager, kind, source, path_template(req))
            if answer is None:
                return
            req.context.traffic = answer
            path = str(getattr(req, 'path', '') or '')
            mode = str(answer.get('knob') or 'off')
            if (answer.get('allowed') or mode == 'off'
                    or any(path.startswith(p) for p in NEVER_REFUSED)):
                return
            line = 'would-deny inbound %s:%s' % (kind, source)
            advise(line)
            if mode == 'advisory':
                return
            refusal = ('%s. %s (POLARI_APP_PERMISSIONS=enforce; the policy row is %s). A person confirms a '
                       'source at POST /api/security/traffic/inbound/{name} — nothing confirms itself.'
                       % (line, answer.get('why', ''), answer.get('state') or 'absent'))
        except Exception:      # noqa: BLE001 — a broken gate must never take the API down
            try:
                req.context.traffic = None
            except Exception:      # noqa: BLE001
                pass
            return
        if refusal:
            import falcon
            raise falcon.HTTPForbidden(title='inbound traffic policy', description=refusal)

    def process_resource(self, req, resp, resource, params):
        """Falcon routes AFTER `process_request`, so the TEMPLATE is only known here. Add it to the row's
        observed paths (dev posture only) — the raw path never lands in a row."""
        try:
            answer = getattr(req.context, self.CONTEXT_ATTR, None)
            if not answer or not answer.get('name'):
                return
            template = getattr(req, 'uri_template', None)
            if not template:
                return
            from security.custom.security_traffic import note_inbound_path
            note_inbound_path(self._manager(), answer['name'],
                              '%s %s' % (req.method, template))
        except Exception:      # noqa: BLE001 — a recorder never raises into the thing it observes
            pass

    @staticmethod
    def _verdict(manager, kind, source, template):
        try:
            from security.custom.security_traffic import inbound_verdict
        except Exception:      # noqa: BLE001 — the security module is not installed: no policy, no gate
            return None
        try:
            return inbound_verdict(manager, kind, source, template)
        except Exception:      # noqa: BLE001
            return None
