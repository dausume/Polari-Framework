"""
Falcon middleware that populates `req.context.user_info` and
`req.context.roles` from a Bearer token, if one is present and valid.

Phase 1: lenient. Missing/invalid token → user_info=None, roles=[].
The middleware never rejects a request — gating happens later in
polariCRUDE when the permission matrix is wired up.

Authorization header is the only token source we accept. Cookies,
query params, and STOMP frames are out of scope here.
"""

from typing import Optional

from accessControl.jwt_validator import JwtValidator


class AuthContextMiddleware:
    """Attaches identity info to every request's context.

    Reads:
        req.headers['AUTHORIZATION']   (Falcon uppercases header names)

    Writes (always — even on anonymous requests, so downstream code can
    rely on the attributes existing):
        req.context.user_info  : dict | None
        req.context.roles      : list[str]   (empty list when unauthenticated)
    """

    def __init__(self, validator: Optional[JwtValidator] = None):
        self.validator = validator or JwtValidator.get()

    def process_request(self, req, resp):
        token = self._extract_bearer(req)
        principal = self.validator.validate(token) if token else None

        if principal is not None:
            req.context.user_info = principal
            req.context.roles = principal.get('roles', [])
        else:
            req.context.user_info = None
            req.context.roles = []

    @staticmethod
    def _extract_bearer(req) -> Optional[str]:
        header = req.get_header('Authorization')
        if not header:
            return None
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        return parts[1].strip() or None
