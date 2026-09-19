"""
accessControl.cause_middleware — where an API chain gets its cause (ct-0).

Design §3, first row: the root cause is minted right after
`AuthContextMiddleware` (so `req.context.user_info` / `roles` exist) and
BEFORE `RoleplayObserverMiddleware` (so the roleplay observer, the CRUDE gate
and everything downstream run inside the chain).

    api  root — entry_ref = `METHOD <path-template>` (the template, never an
                instance id: `PUT /api/MealEntry/{id}`, so the map stays
                class-level — design §2)
    peer root — an inbound `X-Polari-Trace: <trace_id>/<parent_id>` adopts the
                sender's chain, so the two instances' maps join (design §3,
                "inbound from a peer"). The header carries trace ids ONLY; the
                actor never crosses the wire (design §10).

`req.context.cause` is the dict handlers read. Production posture mints
nothing at all (`root_cause` returns None) and `req.context.cause` is None —
the attribute always exists so downstream code never needs a getattr default.

Never raises and never touches the response body: a cause is diagnosis, not
policy (the `AuthContextMiddleware` idiom).
"""

from accessControl.cause_context import (
    TRACE_HEADER, actor_of, current_cause, parse_trace_header, pop_cause,
    root_cause,
)
from accessControl.roleplay_observer import roleplay_of
from accessControl.traffic_middleware import (TRAFFIC_ADVISORY_HEADER,
                                              drain_advisories)


class CauseContextMiddleware:
    """Mints the root cause of an API chain and pops it on the way out."""

    #: where the push token is parked between request and response
    TOKEN_ATTR = 'cause_token'

    def process_request(self, req, resp):
        try:
            req.context.cause = None
            setattr(req.context, self.TOKEN_ATTR, None)
            inbound = parse_trace_header(req.get_header(TRACE_HEADER))
            entry_ref = f'{req.method} {self._path_template(req)}'
            user_info = getattr(req.context, 'user_info', None)
            groups = tuple(getattr(req.context, 'roles', ()) or ())
            token = root_cause(
                'peer' if inbound['trace_id'] else 'api',
                entry_ref,
                actor=actor_of(user_info),
                groups=groups,
                roleplay=roleplay_of(req),
                trace_id=inbound['trace_id'],
                parent_id=inbound['parent_id'],
            )
            setattr(req.context, self.TOKEN_ATTR, token)
            req.context.cause = current_cause() if token is not None else None
        except Exception:      # noqa: BLE001 — never a failure mode
            try:
                req.context.cause = None
                setattr(req.context, self.TOKEN_ATTR, None)
            except Exception:
                pass

    def process_resource(self, req, resp, resource, params):
        """Falcon routes AFTER `process_request`, so `req.uri_template` is
        only known here. Refine the entry_ref in place (same cause, same ids —
        no second push) so the map node is the TEMPLATE and not one instance's
        path. Nothing downstream has read it yet: the CRUDE gate and the
        responders all run after this hook."""
        try:
            cause = current_cause()
            if cause is None:
                return
            template = getattr(req, 'uri_template', None)
            if template:
                cause['entry_ref'] = f'{req.method} {template}'[:400]
        except Exception:      # noqa: BLE001
            pass

    def process_response(self, req, resp, resource, req_succeeded):
        """Pop the cause, and emit ct-9's traffic advisories.

        A `would-deny` from the outbound wrapper happens deep inside a send
        with no response in reach, and one from the inbound gate happens
        before the responder runs; both park a line through
        `traffic_middleware.advise()` (on the cause dict when there is one,
        and always on a contextvar, because production posture mints no cause
        at all). Draining here is the ONE place they reach the caller."""
        try:
            pop_cause(getattr(req.context, self.TOKEN_ATTR, None))
            setattr(req.context, self.TOKEN_ATTR, None)
        except Exception:      # noqa: BLE001
            pass
        try:
            lines = drain_advisories()
            if lines:
                resp.set_header(TRAFFIC_ADVISORY_HEADER,
                                '; '.join(lines)[:400])
        except Exception:      # noqa: BLE001 — an advisory is never a failure mode
            pass

    @staticmethod
    def _path_template(req) -> str:
        """The ROUTE template when falcon resolved one (`/api/{class}/{id}`),
        the raw path otherwise — the class-level node of design §2."""
        try:
            return getattr(req, 'uri_template', None) or req.path
        except Exception:      # noqa: BLE001
            return ''
