"""
polariApiServer.outbound — the ONE seam every call to another system passes
(ct-3, CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2 "The outbound wrapper", §5).

Before this file the outbound surface was twenty ad-hoc `requests` / `urllib`
sites with nothing in common: no shared timeout, no shared header, and — the
point of the ct arc — nowhere to say **what left, to which system, by which
wire**. This module is that one place.

    outbound.send(kind, name, means, fn, payload_classes=(...))
    outbound.http_request(kind, name, 'POST', url, lib='urllib', ...)
    with outbound.wrap(kind, name, 'sdk', payload_classes=(...)):
        client.do_something()

THREE RULES, all of them load-bearing:

1. **The payload never leaves this process in a row.** The wrapper records the
   system, the wire and the payload CLASSES — never a body, never a field, and
   in the audio case (`voiceAPI`) never the bytes. `payload_classes` is a tuple
   of Polari class names; `()` means "nothing of ours crossed" (a token fetch,
   a capability probe).

2. **The actor never crosses the wire.** `X-Polari-Trace` carries
   `<trace_id>/<parent_id>` and nothing else (design §10) — no `sub`, no
   groups, no name. It is added ONLY when `system_kind == 'peer'` (another
   Polari instance, which has a map to join) and ONLY when the current cause
   yields a non-empty value, which in production posture it never does because
   ct-0 mints no cause there at all.

3. **Recording can never raise and can never change the result.** The recorder
   lives in the security module (`security.custom.security_trace`, ct-1) and
   may simply not be installed. Every call into it is lazy, wrapped, and its
   outcome discarded. A send fails or succeeds exactly as it did before this
   module existed; behaviour-preserving migration is the whole contract.

The straggler guard (`selftest_outbound.py`) greps the tree for bare
`requests.` / `urllib.request.urlopen` outside this file and fails on any site
that is neither migrated nor listed with a reason — the migration is visible
rather than assumed.

ct-9 (2026-09-19) added the fourth rule: **the policy is consulted BEFORE the
call runs.** `security.custom.security_traffic.outbound_verdict` answers from
the `OutboundPolicy` rows — closed by default, derived in dev from these very
observations, confirmed by a person — and the mode (`POLARI_APP_PERMISSIONS`)
decides what happens to the answer: `off` nothing, `advisory` a `would-deny`
line on `X-Polari-Traffic-Advisory`, `enforce` an `OutboundRefused`. Rule 3
still holds: an absent or broken policy allows the send, exactly as before.
"""

import functools
import inspect


class OutboundRefused(RuntimeError):
    """This send was refused by the ct-9 traffic policy before it ran.

    Raised from `send()` / `wrap.__enter__()` ONLY when the gate mode is
    `enforce` and no `confirmed` `OutboundPolicy` row allows the edge — his
    "closed by default" (design §5a). It is a plain exception on the send
    path, which every call site already handles: a refused send fails the way
    an unreachable system fails, and says which row would have allowed it.
    Under `advisory` nothing is raised and the send proceeds; under `off` the
    verdict is not acted on at all."""

#: design §2 — the external node kinds a `kind:ref` edge can name.
SYSTEM_KINDS = ('keycloak', 'odoo', 'livekit', 'reticulum', 'engine',
                'provider', 'peer', 'self', 's3', 'mqtt', 'profiler',
                'other')

#: design §2 — the wire an edge was crossed by (`means`, `detail` on a `send`).
MEANS = ('rest', 'json-rpc', 's3', 'grpc', 'mqtt', 'sdk', 'probe')


# ---- the manager the recorder writes rows through -----------------------

def process_manager():
    """The process-wide object manager, or None.

    `polariServer` injects it at boot through
    `topology.provider_registry.set_manager` (polariServer.py:768) — the ONE
    existing accessor for core code that has no manager in hand. Read the
    ATTRIBUTE, never an imported copy, so a later injection is seen."""
    try:
        from topology import provider_registry
        return getattr(provider_registry, 'MANAGER', None)
    except Exception:       # noqa: BLE001 — no manager is a fine answer
        return None


# ---- the trace header (peers only, ids only) ----------------------------

def trace_headers(system_kind):
    """`{X-Polari-Trace: <trace_id>/<parent_id>}` for a peer, else `{}`.

    Empty for every other kind (an external system has no Polari map to join)
    and empty when there is no cause — production posture mints none, so a
    production request carries no header at all."""
    if system_kind != 'peer':
        return {}
    try:
        from accessControl.cause_context import (TRACE_HEADER,
                                                 trace_header_value)
        value = trace_header_value()
    except Exception:       # noqa: BLE001 — ct-0 absent: send nothing
        return {}
    return {TRACE_HEADER: value} if value else {}


# ---- the recorder (lazy, tolerant, never load-bearing) ------------------

def _detail_accepted(recorder):
    """Whether `record_outbound` takes an outcome `detail` kwarg.

    Inspected ONCE per call rather than probed by a retry: a `TypeError`
    raised from INSIDE the recorder must never be mistaken for a signature
    mismatch and turned into a second, duplicate row."""
    try:
        params = inspect.signature(recorder).parameters
    except Exception:       # noqa: BLE001 — unintrospectable: assume not
        return False
    if 'detail' in params:
        return True
    return any(p.kind == p.VAR_KEYWORD for p in params.values())


def _record(system_kind, system_name, means, payload_classes, manager,
            outcome):
    """One `external:`/`peer:` edge. Swallows everything, including an
    absent security module — ct-1 owns `security_trace`, and this wrapper
    must work before it lands."""
    try:
        from security.custom.security_trace import record_outbound
    except Exception:       # noqa: BLE001 — recorder not installed yet
        return
    try:
        mgr = manager if manager is not None else process_manager()
        classes = list(payload_classes or ())
        if _detail_accepted(record_outbound):
            record_outbound(mgr, system_kind, system_name, means, classes,
                            detail=outcome)
        else:
            record_outbound(mgr, system_kind, system_name, means, classes)
    except Exception:       # noqa: BLE001 — recording is never load-bearing
        pass


# ---- the ct-9 traffic policy (lazy, tolerant, closed by default) --------

def _policy_check(system_kind, system_name, means, payload_classes, manager):
    """Consult `OutboundPolicy` BEFORE the send. Returns the verdict dict, or
    None when there is no policy to consult (the module is not installed, or
    it failed) — in which case the send proceeds exactly as it did in ct-3.

    Refusing is the CALLER's job (`_refuse_if_enforced`) so that `send` and
    `wrap` share one rule; recording the advisory under `advisory` mode is
    done inside the verdict, which is the only frame that knows the reason."""
    try:
        from security.custom.security_traffic import outbound_verdict
    except Exception:       # noqa: BLE001 — no security module: no policy
        return None
    try:
        mgr = manager if manager is not None else process_manager()
        return outbound_verdict(mgr, system_kind, system_name, means,
                                list(payload_classes or ()))
    except Exception:       # noqa: BLE001 — a broken gate never blocks a send
        return None


def _refuse_if_enforced(verdict, system_kind, system_name, means):
    """Raise `OutboundRefused` when the policy says no AND the mode is
    `enforce`. Every other combination returns None and the send proceeds."""
    if not verdict or verdict.get('allowed'):
        return None
    if str(verdict.get('knob') or 'off') != 'enforce':
        return None
    raise OutboundRefused(
        'outbound refused by policy: %s:%s over %s — %s '
        '(POLARI_APP_PERMISSIONS=enforce, policy row %r is %s). An '
        'administrator confirms it at POST /api/security/traffic/outbound/%s '
        '{"decision": "confirmed"}.'
        % (system_kind, system_name, means, verdict.get('why', ''),
           verdict.get('name', ''), verdict.get('state') or 'absent',
           verdict.get('name', '')))


# ---- the seam -----------------------------------------------------------

def send(system_kind, system_name, means, fn, *, payload_classes=(), url='',
         manager=None):
    """Run `fn()` and return exactly what it returns; record the edge either
    way. An exception from `fn` propagates unchanged after being recorded by
    its type name — a failed send is still a send, and the map must show it.

    `url` is accepted so call sites can pass what they are dialling without
    stashing it anywhere: it is NOT recorded (a URL can carry a key — see
    `polariApiProfiler.endpoint_fetch.redact`) and never leaves this frame.

    ct-9: the traffic policy is consulted FIRST. Under `enforce` a send no
    confirmed row allows raises `OutboundRefused` and `fn` is never called —
    the refusal is recorded as its own edge outcome, so the map shows the
    send that did not happen."""
    verdict = _policy_check(system_kind, system_name, means, payload_classes,
                            manager)
    try:
        _refuse_if_enforced(verdict, system_kind, system_name, means)
    except OutboundRefused:
        _record(system_kind, system_name, means, payload_classes, manager,
                'refused-by-policy')
        raise
    try:
        result = fn()
    except BaseException as exc:
        _record(system_kind, system_name, means, payload_classes, manager,
                type(exc).__name__)
        raise
    _record(system_kind, system_name, means, payload_classes, manager, 'ok')
    return result


class wrap:
    """Context manager / decorator for SDK sends — the OpenAI client, minio,
    paho — where there is no URL of ours to build and the library owns the
    wire. Records on the way out, success or exception, and never suppresses
    one (`__exit__` returns False, always)."""

    def __init__(self, system_kind, system_name, means, payload_classes=(),
                 *, manager=None):
        self.system_kind = system_kind
        self.system_name = system_name
        self.means = means
        self.payload_classes = tuple(payload_classes or ())
        self.manager = manager

    def __enter__(self):
        """ct-9: the policy is consulted on the way IN, so an SDK send no
        confirmed row allows never reaches the library under `enforce`."""
        verdict = _policy_check(self.system_kind, self.system_name, self.means,
                                self.payload_classes, self.manager)
        try:
            _refuse_if_enforced(verdict, self.system_kind, self.system_name,
                                self.means)
        except OutboundRefused:
            _record(self.system_kind, self.system_name, self.means,
                    self.payload_classes, self.manager, 'refused-by-policy')
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        _record(self.system_kind, self.system_name, self.means,
                self.payload_classes, self.manager,
                'ok' if exc_type is None else getattr(exc_type, '__name__',
                                                      'error'))
        return False

    def __call__(self, fn):
        spec = (self.system_kind, self.system_name, self.means,
                self.payload_classes)
        manager = self.manager

        @functools.wraps(fn)
        def inner(*args, **kwargs):
            with wrap(*spec, manager=manager):
                return fn(*args, **kwargs)
        return inner


# ---- the HTTP helpers (same library, same timeout, same return type) ----

def http_request(system_kind, system_name, method, url, *, means='rest',
                 payload_classes=(), headers=None, data=None, timeout=None,
                 lib='requests', manager=None, **kw):
    """One HTTP send through the seam, using the SAME library the site used.

    `lib='requests'` returns the `requests.Response` the site expected and
    raises `requests.RequestException` as before. `lib='urllib'` returns the
    open `urlopen` result — still a context manager, so `with
    http_request(...) as resp:` reads exactly like the line it replaced — and
    raises `urllib.error.HTTPError` / `URLError` as before.

    `url` may be a pre-built `urllib.request.Request` (several sites build one
    to set a body and a content type); the trace header is then ADDED to it
    rather than a second request being built, so nothing about the site's own
    headers changes. `**kw` passes through untouched (`context=` for a dev TLS
    context, `data=`/`json=` for requests)."""
    hdrs = dict(headers or {})
    hdrs.update(trace_headers(system_kind))

    if lib == 'requests':
        import requests as _requests

        def _call():
            return _requests.request(method, url, headers=hdrs or None,
                                     timeout=timeout, data=data, **kw)
    elif lib == 'urllib':
        import urllib.request as _urlreq

        def _call():
            target = url
            if isinstance(target, _urlreq.Request):
                for key, value in hdrs.items():
                    target.add_header(key, value)
            else:
                target = _urlreq.Request(target, data=data, headers=hdrs,
                                         method=method)
            if timeout is None:
                return _urlreq.urlopen(target, **kw)
            return _urlreq.urlopen(target, timeout=timeout, **kw)
    else:
        raise ValueError(f"outbound.http_request: unknown lib {lib!r} "
                         f"(expected 'requests' or 'urllib')")

    return send(system_kind, system_name, means, _call,
                payload_classes=payload_classes, manager=manager)


def urlopen(system_kind, system_name, target, *, means='rest',
            payload_classes=(), timeout=None, manager=None, **kw):
    """`urllib.request.urlopen(target, timeout=...)` through the seam, for the
    many sites that already hold a `Request` (or a plain URL) and want nothing
    else changed. Thin sugar over `http_request(lib='urllib')`."""
    return http_request(system_kind, system_name, 'GET', target, means=means,
                        payload_classes=payload_classes, timeout=timeout,
                        lib='urllib', manager=manager, **kw)
