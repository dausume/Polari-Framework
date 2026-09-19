"""
@module cicd.custom.cicd_auth

WHO MAY DO WHAT on the cicd doors — two credentials, deliberately different in kind.

1. **A PERSON, to change a setting.** `ADMIN_ROLES` ({'admin', 'polari-admin'}), read from
   `polariapps.objects.apps_permissions._shared` so there is one definition, with the same literal fallback
   `security.custom.security_claims` uses when polariapps is not admitted. The caller is identified by their
   opaque Keycloak `sub` and nothing else (his PII rule D18-1) — no username, no e-mail, no display name
   reaches a row.

2. **THE PIPELINE, to mirror a run in.** A POSTING-ONLY per-device token. `POST /api/cicd/device/token`
   (admin) mints one, shows it ONCE in that response, and stores only `sha256(token)` in
   `PipelineDevice.ingest_token_hash`. The token may reach `POST /api/cicd/ingest` and nothing else: it
   cannot read a setting, cannot change one, cannot mint another, and is not a Jenkins credential of any
   kind. The device keeps it under the same secrets posture as every other secret
   (`/etc/polari-jenkins/secrets/polari/cicd_ingest_token`, root:polari-ci 0640).

WHY A TOKEN AND NOT A KEYCLOAK SERVICE ACCOUNT: the pipeline device commonly runs against a core in the
LEAN posture, where `POL_PROD_AUTH=off` and there is no Keycloak at all (docker-compose.lean.yml). A
credential that only exists when Keycloak does would make the mirror work on one deployment and silently
not on another. A per-device token works in both, and is checked with `hmac.compare_digest` so a wrong one
cannot be found a byte at a time.

The comparison is against the hash of the device's own token only — there is no global token, so a device
whose token leaks is revoked by re-minting that one device's, and every other device is untouched.
"""
import hashlib
import hmac

#: the header the pipeline sends. Bearer is accepted too, so `curl -H "Authorization: Bearer $TOK"` works.
TOKEN_HEADER = 'X-Polari-CICD-Token'
#: where the device keeps it (the ci-7 secrets posture) — a NAME, never a value
TOKEN_SECRET = 'polari/cicd_ingest_token'
#: bytes of randomness behind a minted token
TOKEN_BYTES = 32


def admin_roles():
    try:
        from polariapps.objects.apps_permissions._shared import ADMIN_ROLES
        return set(ADMIN_ROLES)
    except Exception:
        return {'admin', 'polari-admin'}


def caller_sub(user_info):
    """The caller's opaque Keycloak id — the ONLY identifier this module writes into a row (D18-1)."""
    return str(user_info.get('sub') or '') if isinstance(user_info, dict) else ''


def caller_groups(user_info):
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups as _cg
        return set(_cg(user_info))
    except Exception:
        if not isinstance(user_info, dict):
            return set()
        raw = (user_info.get('raw_claims') or {}).get('groups') or []
        return {str(g).lstrip('/') for g in raw} | {str(r) for r in (user_info.get('roles') or [])}


def is_admin(user_info):
    return bool(admin_roles() & caller_groups(user_info))


def hash_token(token):
    """sha256 hex of the token. The ONLY form that is ever stored, logged or compared."""
    return hashlib.sha256((token or '').encode('utf-8')).hexdigest()


def mint_token():
    """A fresh posting-only token. Returned ONCE to the minting admin; only its hash is kept."""
    import secrets
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_from_request(request):
    """The presented token, from the dedicated header or a Bearer authorization."""
    get = getattr(request, 'get_header', None)
    if not callable(get):
        return ''
    tok = get(TOKEN_HEADER) or ''
    if tok:
        return str(tok).strip()
    auth = str(get('Authorization') or '')
    if auth[:7].lower() == 'bearer ':
        return auth[7:].strip()
    return ''


def device_for_token(devices, token):
    """The PipelineDevice whose `ingest_token_hash` matches — or None.

    Constant-time per candidate (`hmac.compare_digest`), and a device with no hash set NEVER matches: an
    empty stored hash must not be satisfiable by an empty presented token.
    """
    if not token:
        return None
    presented = hash_token(token)
    for row in devices or []:
        stored = str(getattr(row, 'ingest_token_hash', '') or '')
        if stored and hmac.compare_digest(stored, presented):
            return row
    return None
