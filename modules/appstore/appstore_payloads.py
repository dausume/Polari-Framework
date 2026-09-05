"""
@module appstore.appstore_payloads

Builders for the shared shell contracts (plan S1-S3):
  - registration document v1 (canonical schema:
    polari-app-shell/config/polari-shell.schema.json)
  - the /api/appstore/identity probe payload
  - the polari://register deep link (QR payload = the same string)

URL resolution ladder: InstanceDefinition.public_base_url /
api_base_url -> env POLARI_PUBLIC_BASE_URL / POLARI_API_BASE_URL ->
honest refusal naming the knob. The CA travels IN the payload
(tls.caPem + caSha256) so a shell can pin the suite's self-signed
root without OS trust-store surgery; POLARI_SHELL_CA_PATH is the
knob, absence is honest (empty caPem + note), never fatal.
"""

import hashlib
import json
import os
from urllib.parse import quote

from appstore.appstore_tokens import now_iso

#: Where the suite CA lands when the deploy mounts it. First
#: readable wins; the env knob overrides.
CA_PATH_ENV = 'POLARI_SHELL_CA_PATH'
CA_FALLBACK_PATHS = ('/app/certs/root_ca.crt', '/app/ca/root_ca.crt')

SCHEMA_KIND = 'polari-shell-registration'
SCHEMA_VERSION = 1

#: The dedicated public Keycloak client for shells (A6). Phase-1
#: desktop auth actually rides the SPA's own polari-frontend flow
#: inside the embedded browser; this block is what phase-2 native
#: auth (and mobile) uses.
SHELL_CLIENT_ID = 'polari-shell'
SHELL_REDIRECT_URI = 'polari://oauth/callback'
SHELL_SCOPES = 'openid profile email roles offline_access'


def _env(name):
    return (os.environ.get(name) or '').strip()


def instance_row(manager):
    """The InstanceDefinition row for THIS instance. Ladder: env
    POLARI_INSTANCE_NAME -> 'prf-<POLARI_INSTANCE_ID>' (id defaults
    to 'a', matching peers_api) -> a 'prf'-kind row that actually
    DECLARES public_base_url -> first 'prf'-kind row -> None
    (identity still answers from env — the probe must never 500).
    Caught live: prf-b iterated before prf-a, so plain first-match
    answered for the twin."""
    tables = getattr(manager, 'objectTables', None) or {}
    rows = list((tables.get('InstanceDefinition') or {}).values())
    wanted = _env('POLARI_INSTANCE_NAME') \
        or 'prf-' + (_env('POLARI_INSTANCE_ID') or 'a')
    for row in rows:
        if getattr(row, 'name', '') == wanted:
            return row
    prf_rows = [r for r in rows
                if getattr(r, 'kind', '') == 'prf']
    for row in prf_rows:
        if getattr(row, 'public_base_url', ''):
            return row
    return prf_rows[0] if prf_rows else None


def resolve_urls(manager):
    """{'ok', webUrl, apiUrl} or an honest refusal naming the knob."""
    row = instance_row(manager)
    web = (getattr(row, 'public_base_url', '') or '' if row else '') \
        or _env('POLARI_PUBLIC_BASE_URL')
    api = (getattr(row, 'api_base_url', '') or '' if row else '') \
        or _env('POLARI_API_BASE_URL')
    if not web or not api:
        return {'ok': False,
                'error': 'instance URLs are not declared',
                'suggestion': {
                    'knob': 'InstanceDefinition.public_base_url / '
                            'api_base_url (or env '
                            'POLARI_PUBLIC_BASE_URL / '
                            'POLARI_API_BASE_URL)',
                    'action': 'declare how a shell reaches this '
                              'instance; a downloadable app cannot '
                              'guess its own address'}}
    return {'ok': True, 'webUrl': web.rstrip('/'),
            'apiUrl': api.rstrip('/')}


def reachability_block(manager):
    """The instance's declared reachability, shaped for the wire.
    Hints are ADVISORY — the authoritative probe is identityUrl."""
    row = instance_row(manager)
    scope = (getattr(row, 'accessibility_scope', '') or 'local'
             if row else 'local')
    hint = {}
    if row:
        try:
            hint = json.loads(
                getattr(row, 'network_hint_json', '{}') or '{}')
        except ValueError:
            hint = {}
    urls = resolve_urls(manager)
    probe = (urls['apiUrl'] + '/api/appstore/identity'
             if urls.get('ok') else '')
    return {'scope': scope,
            'networkKind': (getattr(row, 'network_kind', '') or ''
                            if row else ''),
            'networkName': (getattr(row, 'network_display_name', '')
                            or '' if row else ''),
            'hint': {'cidrs': hint.get('expectedCidrs', []) or [],
                     'probeUrl': probe}}


def load_ca():
    """{'caPem': [...], 'caSha256': hex} — or empty-with-note when no
    CA is mounted (a public-CA deployment needs none)."""
    paths = [p for p in (_env(CA_PATH_ENV),) if p] \
        + list(CA_FALLBACK_PATHS)
    for path in paths:
        try:
            with open(path, 'rb') as fh:
                pem = fh.read()
        except OSError:
            continue
        return {'caPem': [pem.decode('utf-8', 'replace')],
                'caSha256': hashlib.sha256(pem).hexdigest(),
                'source': path}
    return {'caPem': [], 'caSha256': '',
            'note': f'no CA file readable (knob: {CA_PATH_ENV}); '
                    'shells will use OS trust'}


def identity_payload(manager):
    """S3: the unauthenticated probe body. Cheap, no writes; the
    shell distinguishes wrong-network (unreachable) / down (/api/
    health 503) / wrong-instance (instanceId mismatch) with it."""
    urls = resolve_urls(manager)
    return {
        'ok': True,
        'instanceName': _env('POLARI_INSTANCE_NAME') or 'local',
        'instanceId': _env('POLARI_INSTANCE_ID') or 'a',
        'realm': _env('POLARI_KEYCLOAK_REALM') or 'Polari',
        'keycloakIssuer': _env('POLARI_KEYCLOAK_ISSUER_URI'),
        'frontendUrl': urls.get('webUrl', ''),
        'apiUrl': urls.get('apiUrl', ''),
        'reachability': reachability_block(manager),
        'serverTime': now_iso(),
    }


def registration_document(manager, shell_row, enrollment_wire=None,
                          enrollment_expires_at='', username=''):
    """S1: the one document every delivery path carries (baked into
    tarballs, served by /registration, returned by redeem).
    Credential-free except the single-use enrollment token."""
    urls = resolve_urls(manager)
    if not urls.get('ok'):
        return urls
    branding = {}
    try:
        branding = json.loads(
            getattr(shell_row, 'branding_json', '{}') or '{}')
    except ValueError:
        pass
    capabilities = []
    try:
        parsed = json.loads(
            getattr(shell_row, 'capabilities_json', '[]') or '[]')
        if isinstance(parsed, list):
            capabilities = [str(c) for c in parsed]
    except ValueError:
        pass
    ca = load_ca()
    api = urls['apiUrl']
    instance = {
        'id': _env('POLARI_INSTANCE_NAME') or 'local',
        'displayName': getattr(shell_row, 'title', '') or 'Polari',
        'webUrl': urls['webUrl'],
        'apiUrl': api,
        'identityUrl': api + '/api/appstore/identity',
        'instanceId': _env('POLARI_INSTANCE_ID') or 'a',
        'auth': {
            'authority': _env('POLARI_KEYCLOAK_ISSUER_URI'),
            'realm': _env('POLARI_KEYCLOAK_REALM') or 'Polari',
            'clientId': SHELL_CLIENT_ID,
            'pkce': 'S256',
            'scope': SHELL_SCOPES,
            'shellRedirectUri': SHELL_REDIRECT_URI,
            'loginHint': username or '',
        },
        'tls': {'caPem': ca['caPem'], 'caSha256': ca['caSha256']},
        'reachability': reachability_block(manager),
    }
    enrollment = None
    if enrollment_wire:
        enrollment = {'token': enrollment_wire,
                      'redeemUrl': api + '/api/appstore/enroll/redeem',
                      'expiresAt': enrollment_expires_at}
    return {
        'ok': True,
        'kind': SCHEMA_KIND,
        'schemaVersion': SCHEMA_VERSION,
        'app': {
            'name': getattr(shell_row, 'name', ''),
            'title': getattr(shell_row, 'title', ''),
            'scope': getattr(shell_row, 'scope', 'instance'),
            'appName': getattr(shell_row, 'app_name', ''),
            'startRoute': getattr(shell_row, 'start_route', ''),
            'brandColor': branding.get('brandColor', ''),
            'icon': branding.get('icon', ''),
            # sep-2: references to edge-behavior rows (sep-5), never
            # the definitions themselves.
            'capabilities': capabilities,
        },
        'instances': [instance],
        'enrollment': enrollment,
    }


def deep_link(manager, enrollment_wire):
    """S2 short form. Carries the CA fingerprint (TOFU pin for the
    first trusted fetch) AND the reachability scope — so a shell can
    phrase the wrong-network advisory before it ever reaches the
    instance."""
    urls = resolve_urls(manager)
    if not urls.get('ok'):
        return urls
    reach = reachability_block(manager)
    ca = load_ca()
    link = (f"polari://register?api={quote(urls['apiUrl'], safe='')}"
            f"&t={quote(enrollment_wire, safe='')}")
    if ca['caSha256']:
        link += f"&ca={ca['caSha256']}"
    link += f"&scope={quote(reach['scope'], safe='')}"
    if reach['networkKind']:
        link += f"&nk={quote(reach['networkKind'], safe='')}"
    if reach['networkName']:
        link += f"&nn={quote(reach['networkName'], safe='')}"
    return {'ok': True, 'deepLink': link, 'qrPayload': link}
