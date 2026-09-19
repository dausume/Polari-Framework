"""
accessControl.stomp_identity — WHO is on the websocket (ct-6).

Design: AI-Notes/designs/CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §10, his ruling
2026-09-18: "STOMP should just follow from the CRUDE security posture … they
should be the same." Same posture needs the same *identity*, so this module
turns a bearer arriving on a websocket into exactly the `user_info` shape the
CRUDE gate already resolves verdicts from — through the SAME validator
(`accessControl.jwt_validator.JwtValidator`), never a second implementation.

THREE places a bearer may arrive, in the order they are consulted:

  1. the WebSocket UPGRADE request's `Authorization: Bearer <token>` header
     (what a native client or a proxy that can set headers sends);
  2. the upgrade's `Sec-WebSocket-Protocol` list, as `bearer.<token>` or
     `access_token.<token>` — the browser convention, because the WebSocket
     JS API cannot set request headers;
  3. the STOMP CONNECT frame's `Authorization` header, or STOMP 1.2's own
     `passcode` (with or without a `Bearer ` prefix).

No bearer anywhere → ANONYMOUS, which is not an error: it is the same answer
the CRUDE gate gives an unauthenticated HTTP caller, and it goes down the same
verdict path.

THE PII BOUNDARY (D18-1). `JwtValidator.validate()` hands back `username` and
`email` because HTTP callers of `/api/me` need them. NOTHING of the sort is
kept on a connection: `scrub_principal()` keeps the opaque Keycloak `sub`, the
roles, and the `groups` claim — the three things
`polariapps…_shared.caller_groups()` reads — and drops the rest on the floor.
A long-lived socket is exactly the wrong place to park a person's name.
"""

#: the `Sec-WebSocket-Protocol` spellings a browser may use to smuggle a bearer
WS_PROTOCOL_PREFIXES = ('bearer.', 'access_token.', 'access-token.')

#: CONNECT-frame headers that may carry one (STOMP has no Authorization of its own)
CONNECT_TOKEN_HEADERS = ('Authorization', 'authorization', 'passcode')


class StompConnection:
    """One websocket, and what we are allowed to remember about it.

    Deliberately tiny and deliberately NOT a treeObject: it lives in the STOMP
    server's asyncio thread and never touches the object tree.

    Attributes
    ----------
    websocket    : the transport object (whatever the server handed us)
    client_id    : short opaque id used only in log lines
    user_info    : dict | None — `{'sub', 'roles', 'raw_claims': {'groups': [...]}}`
    auth_failed  : bool — a bearer WAS presented and the validator refused it
                   (an expired session is a different answer from anonymous,
                   exactly as §51 made it on the HTTP side)
    """

    __slots__ = ('websocket', 'client_id', 'user_info', 'auth_failed')

    def __init__(self, websocket=None, client_id=''):
        self.websocket = websocket
        self.client_id = client_id
        self.user_info = None
        self.auth_failed = False

    @property
    def authenticated(self):
        return self.user_info is not None

    @property
    def sub(self):
        return str((self.user_info or {}).get('sub') or '')

    @property
    def groups(self):
        """The caller's grant keys, resolved by the ONE resolution the CRUDE
        gate uses. Degrades to the roles list when polariapps is absent."""
        try:
            from polariapps.objects.apps_permissions._shared import caller_groups
            groups, _sources = caller_groups(self.user_info)
            return sorted(groups)
        except Exception:      # noqa: BLE001 — module absent: roles are still grant keys
            return sorted({str(r) for r in ((self.user_info or {}).get('roles') or [])})


def _strip_bearer(raw):
    """`Bearer <token>` → `<token>`; a bare token passes through unchanged."""
    value = str(raw or '').strip()
    if not value:
        return ''
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()
    return value


def bearer_from_upgrade(websocket):
    """The bearer on the WebSocket UPGRADE request, or ''. Never raises — a
    transport that exposes no request (a selftest double) simply has none."""
    try:
        request = getattr(websocket, 'request', None)
        headers = getattr(request, 'headers', None)
        if headers is None:
            headers = getattr(websocket, 'request_headers', None)
        if headers is None:
            return ''
        try:
            auth = headers.get('Authorization') or headers.get('authorization') or ''
        except Exception:      # noqa: BLE001
            auth = ''
        token = _strip_bearer(auth)
        if token:
            return token
        try:
            protocols = headers.get('Sec-WebSocket-Protocol') or ''
        except Exception:      # noqa: BLE001
            protocols = ''
        for entry in str(protocols).split(','):
            entry = entry.strip()
            for prefix in WS_PROTOCOL_PREFIXES:
                if entry.lower().startswith(prefix):
                    return entry[len(prefix):].strip()
        return ''
    except Exception:          # noqa: BLE001 — identity reading never breaks a socket
        return ''


def bearer_from_connect(headers):
    """The bearer on a STOMP CONNECT/STOMP frame's headers, or ''.

    `login` is NEVER read: it holds a username, and a username is not identity
    in Polari — the token is (D18-1)."""
    if not isinstance(headers, dict):
        return ''
    for key in CONNECT_TOKEN_HEADERS:
        token = _strip_bearer(headers.get(key))
        if token:
            return token
    return ''


def scrub_principal(principal):
    """The validator's principal, reduced to what a connection may keep.

    `sub` + roles + the `groups` claim — the exact inputs `caller_groups()`
    reads — and NOTHING else. Returns None for a non-principal so callers can
    assign the result straight onto `connection.user_info`."""
    if not isinstance(principal, dict):
        return None
    raw = principal.get('raw_claims') or {}
    claim = raw.get('groups') if isinstance(raw, dict) else None
    groups = [str(g) for g in claim] if isinstance(claim, list) else []
    return {
        'sub': str(principal.get('sub') or ''),
        'roles': [str(r) for r in (principal.get('roles') or [])],
        'raw_claims': {'groups': groups},
    }


def principal_for(token, validator=None):
    """Validate a bearer with the SAME validator the Falcon middleware uses,
    and return the scrubbed principal (None when there is no usable identity).

    One implementation of "is this token good" in the process, by construction:
    `JwtValidator.get()` is the middleware's own singleton."""
    if not token:
        return None
    try:
        if validator is None:
            from accessControl.jwt_validator import JwtValidator
            validator = JwtValidator.get()
        return scrub_principal(validator.validate(token))
    except Exception:          # noqa: BLE001 — an unvalidatable token is anonymous, never a crash
        return None


def adopt_identity(connection, connect_headers=None, validator=None):
    """Read the bearer for `connection` (upgrade first, CONNECT frame second),
    validate it, and stamp `user_info` / `auth_failed`.

    Returns the connection. Idempotent-ish: a CONNECT frame that carries a
    fresh, VALID token replaces an earlier identity; one that carries nothing
    leaves an identity already taken from the upgrade alone."""
    token = (bearer_from_upgrade(getattr(connection, 'websocket', None))
             or bearer_from_connect(connect_headers))
    if not token:
        return connection
    principal = principal_for(token, validator=validator)
    if principal is not None:
        connection.user_info = principal
        connection.auth_failed = False
    elif connection.user_info is None:
        connection.auth_failed = True
    return connection
