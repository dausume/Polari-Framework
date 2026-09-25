"""
THE CALLER'S OWN KEYS TO THE FILE STORE (fs-2, plan FILE_STORE_PLAN.md §5).

The store's browser UI is closed (it had no login, plan §4); the store is reached only through S3, and the ONE
Keycloak door on it is STS in claim mode (prf-file-store/README.md): a realm access token is exchanged for
temporary S3 keys whose policies ARE the token's realm roles. This seam does that exchange FOR the caller of a
Polari route — the backend never lends its root keys to a browser:

    client, who = caller_store_client(manager, request)
        → a Minio client holding the caller's temporary keys (cached per token until they expire), and a
          record of who is acting + which side enforces
        → falcon.HTTPUnauthorized when no Bearer came (anonymous never browses the store)
        → falcon.HTTPServiceUnavailable when the store is down / not configured

Enforcement is the STORE's when the exchange works (`enforced_by: store`): a viewer can list and get, a
developer can also write, a caller can never hold more than its token says, and the realm is the sole authority.
When the store has NO OIDC door (dev without POLARI_KEYCLOAK_ISSUER_URI, a bare `weed` with only s3.json) the
exchange fails, and the fallback is the BACKEND's gate over the same table (`enforced_by: backend`): the
caller must carry a realm role the table knows, and the root connection performs only what that role allows —
the browse routes are read-only, so `read` is the verb they ask for.
"""
import hashlib
import os
import threading
import time
import xml.etree.ElementTree as ET

import falcon

# the same table the store renders (prf-file-store/entrypoint.sh): realm role → what it may do
ROLE_ALLOWS = {
    'polari-admin': ('read', 'write', 'buckets', 'admin'),
    'polari-developer': ('read', 'write', 'buckets'),
    'polari-user': ('read', 'write'),
    'polari-viewer': ('read',),
    'default-roles-polari': ('read',),
}

_CACHE = {}
_LOCK = threading.Lock()
_MARGIN_S = 60


def _bearer(request):
    header = request.get_header('Authorization') or ''
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1].strip() or None


def allowed(roles, verb):
    """The backend-side reading of the table: does any of these realm roles allow `verb`?"""
    return any(verb in ROLE_ALLOWS.get(r, ()) for r in (roles or []))


def _sts_exchange(store, token, duration_s=3600):
    """AssumeRoleWithWebIdentity in claim mode against the store's S3 endpoint. Returns
    {'access_key','secret_key','session_token','expires_at'} or raises RuntimeError(reason)."""
    import urllib3
    scheme = 'https' if store.secure else 'http'
    body = {'Action': 'AssumeRoleWithWebIdentity', 'Version': '2011-06-15', 'WebIdentityToken': token,
            'DurationSeconds': str(int(duration_s)), 'RoleSessionName': 'polari-' + hashlib.sha256(token.encode()).hexdigest()[:12]}
    http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=3.0, read=10.0), cert_reqs='CERT_NONE' if not store.secure else None)
    try:
        r = http.request('POST', '%s://%s/' % (scheme, store.endpoint), fields=body, encode_multipart=False,
                         headers={'Content-Type': 'application/x-www-form-urlencoded'})
    except Exception as exc:
        raise RuntimeError('store unreachable for STS: %s' % exc)
    text = r.data.decode('utf-8', 'replace') if r.data else ''
    if r.status != 200:
        raise RuntimeError('STS refused (%s): %s' % (r.status, text[:200].replace('\n', ' ')))
    found = {}
    try:
        for el in ET.fromstring(text).iter():
            tag = el.tag.rsplit('}', 1)[-1]
            if tag in ('AccessKeyId', 'SecretAccessKey', 'SessionToken', 'Expiration'):
                found[tag] = (el.text or '').strip()
    except ET.ParseError as exc:
        raise RuntimeError('STS answer unreadable: %s' % exc)
    if not all(found.get(k) for k in ('AccessKeyId', 'SecretAccessKey', 'SessionToken')):
        raise RuntimeError('STS answer lacked credentials: %s' % text[:200])
    expires_at = time.time() + duration_s
    exp = found.get('Expiration', '')
    if exp:
        try:
            import datetime
            expires_at = datetime.datetime.fromisoformat(exp.replace('Z', '+00:00')).timestamp()
        except Exception:
            pass
    return {'access_key': found['AccessKeyId'], 'secret_key': found['SecretAccessKey'], 'session_token': found['SessionToken'], 'expires_at': expires_at}


def _client_for(store, creds, public=False):
    from minio import Minio
    endpoint = store.public_endpoint if public else store.endpoint
    secure = store.public_secure if public else store.secure
    return Minio(endpoint, access_key=creds['access_key'], secret_key=creds['secret_key'], session_token=creds['session_token'], secure=secure, region='us-east-1')


class CallerStore:
    """What a route gets back: the client to act with, a presign client (public host), and who/how."""

    def __init__(self, client, presign_client, who):
        self.client = client
        self.presign_client = presign_client
        self.who = who


def caller_store_client(manager, request, verb='read'):
    store = getattr(manager, 'objectStore', None)
    if store is None or not getattr(store, 'connected', False):
        raise falcon.HTTPServiceUnavailable(title='file store not connected', description='the backend holds no connection to the object store (MINIO_ENDPOINT / credentials)')
    token = _bearer(request)
    ctx = getattr(request, 'context', None)
    user_info = getattr(ctx, 'user_info', None)
    roles = list(getattr(ctx, 'roles', None) or [])
    if not token:
        raise falcon.HTTPUnauthorized(title='sign in to browse the file store', description='the file store is reached only as a signed-in person: the realm token is exchanged for temporary store keys (claim-mode STS)')
    if user_info is None:
        raise falcon.HTTPUnauthorized(title='session invalid or expired', description='the Bearer token was refused by the realm')
    sub = str(user_info.get('sub') or user_info.get('preferred_username') or '?')
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and hit['expires_at'] - _MARGIN_S > now:
            return hit['caller']
        for k in [k for k, v in _CACHE.items() if v['expires_at'] <= now]:
            _CACHE.pop(k, None)
    who = {'sub': sub, 'roles': roles}
    try:
        creds = _sts_exchange(store, token)
        caller = CallerStore(_client_for(store, creds), _client_for(store, creds, public=True), dict(who, enforced_by='store', note='temporary keys minted from your realm token; the store applies your roles'))
        with _LOCK:
            _CACHE[key] = {'expires_at': creds['expires_at'], 'caller': caller}
        return caller
    except RuntimeError as exc:
        reason = str(exc)
    # no OIDC door on the store → the backend's gate over the same table, with the root connection
    if os.environ.get('FILE_STORE_BACKEND_GATE', 'yes').strip().lower() in ('no', '0', 'false', 'off'):
        raise falcon.HTTPServiceUnavailable(title='the store did not accept the realm token', description=reason)
    if not allowed(roles, verb):
        raise falcon.HTTPForbidden(title='no realm role allows %r on the file store' % verb, description='roles seen: %s; the table: %s' % (', '.join(roles) or 'none', ', '.join(sorted(ROLE_ALLOWS))))
    return CallerStore(store.client, store._presign_client(), dict(who, enforced_by='backend', note='the store has no OIDC door here (%s); the backend applied the same role table with its own connection' % reason))
