"""
Falcon middleware that populates `req.context.user_info` and
`req.context.roles` from a Bearer token, if one is present and valid.

Phase 1: lenient. Missing/invalid token → user_info=None, roles=[].
The middleware never rejects a request — gating happens later in
polariCRUDE when the permission matrix is wired up.

Authorization header is the only token source we accept. Cookies,
query params, and STOMP frames are out of scope here.

§51 (2026-09-17): "lenient" used to be SILENT, and an EXPIRED bearer was
therefore indistinguishable from no bearer at all — the caller read as
anonymous and every act grew a would-deny advisory (a 403 storm under
enforce) with nothing anywhere saying "your token expired". A request that
CARRIED a Bearer which validate() refused now answers with

    X-Polari-Auth: invalid-or-expired

and `req.context.auth_failed = True` for the gate, which then says
`unauthenticated` rather than `would-deny`. Still no rejection here: the
header is the diagnosis, not a policy.
"""

from typing import Optional

from accessControl.jwt_validator import JwtValidator


class AuthContextMiddleware:
    """Attaches identity info to every request's context.

    Reads:
        req.headers['AUTHORIZATION']   (Falcon uppercases header names)

    Writes (always — even on anonymous requests, so downstream code can
    rely on the attributes existing):
        req.context.user_info    : dict | None
        req.context.roles        : list[str] (empty when unauthenticated)
        req.context.auth_failed  : bool      (a Bearer was sent and REFUSED)
    """

    #: set on the response when a Bearer was present but did not validate
    AUTH_HEADER = 'X-Polari-Auth'
    AUTH_INVALID = 'invalid-or-expired'

    def __init__(self, validator: Optional[JwtValidator] = None):
        self.validator = validator or JwtValidator.get()

    def process_request(self, req, resp):
        token = self._extract_bearer(req)
        principal = self.validator.validate(token) if token else None

        if principal is not None:
            req.context.user_info = principal
            req.context.roles = principal.get('roles', [])
            req.context.auth_failed = False
        else:
            req.context.user_info = None
            req.context.roles = []
            # A token WAS sent and was refused (expired, wrong issuer, bad
            # signature, JWKS unreachable) — say so, once, on the response.
            # Without it an expired session looks exactly like anonymous
            # browsing and the caller chases a permission problem that
            # isn't one.
            req.context.auth_failed = bool(token)
            if token:
                try:
                    resp.set_header(self.AUTH_HEADER, self.AUTH_INVALID)
                except Exception:      # noqa: BLE001 — diagnosis, never a failure mode
                    pass

    @staticmethod
    def _extract_bearer(req) -> Optional[str]:
        header = req.get_header('Authorization')
        if not header:
            return None
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        return parts[1].strip() or None
