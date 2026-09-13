"""
@module security.custom.security_app_rows

The App domain's rows, DERIVED: TrustChannel from the proxy templates (user → app over TLS), the Keycloak
realms (public clients = asymmetric user channels, confidential clients = symmetric app ↔ Keycloak),
ServiceConnection rows and the isle protocol matrix when a manager is present; AuthzRule as a view over
the accessControl permission sets, roles and the CRUDE gate; ContentPolicy per class from the typing
(a JSON Schema + limits, mode derived); BrowserPolicy per frontend host from what it loads.
His point: users hold asymmetric material (signed tokens, TLS certs), servers may share symmetric
material between themselves — a symmetric key on a USER channel is a finding.
"""
import glob
import json
import os
import re

from security.custom.security_facts import SUITE

PROXY = os.path.join(SUITE, 'pol-proxy')
REALMS = os.path.join(SUITE, 'pol-keycloak', 'realm-imports')
HIDDEN_CLIENTS = ('account', 'account-console', 'admin-cli', 'broker', 'realm-management', 'security-admin-console')


def trust_channel_rows(manager=None):
    rows = []
    # user → app through the proxy: every server block is a user-facing TLS channel
    for p in sorted(glob.glob(os.path.join(PROXY, 'nginx.*.conf.template'))):
        env = os.path.basename(p).split('.')[1]
        txt = open(p, encoding='utf-8', errors='replace').read()
        for block in re.findall(r'server\s*\{(.*?)\n\s*\}', txt, flags=re.S):
            names = re.findall(r'server_name\s+([^;]+);', block)
            ups = re.findall(r'proxy_pass\s+\$?(\w+)', block)
            if not names or not ups:
                continue
            host = names[0].split()[0].replace('${PROD_DOMAIN}', '<domain>').replace('${BASE_DOMAIN}', '<domain>')
            tls = 'listen 443' in block or 'ssl' in block
            auth = 'oidc-bearer' if env == 'prod' and ('api' in host) else ('none' if env == 'lean' else 'oidc-bearer' if 'api' in host else 'none (page)')
            rows.append({'name': f'{env}:user→{host}', 'from_kind': 'user', 'to_kind': 'backend' if 'api' in host or 'backend' in ups[0] else 'frontend',
                         'from_app': 'a browser', 'to_app': ups[0], 'direction': 'to', 'transport': 'tls' if tls else 'plain', 'auth': auth,
                         'key_kind': 'asymmetric', 'key_source': 'letsencrypt / suite-ca (server cert) + keycloak (token)' if 'oidc' in auth else 'letsencrypt / suite-ca',
                         'scenario': {'lean': 'swarm-lean', 'prod': 'swarm-full', 'staging': 'dev'}.get(env, env), 'verified': False,
                         'finding': '' if tls else 'plain HTTP on a user channel', 'evidence': f'{os.path.basename(p)}: server_name {host} → proxy_pass {ups[0]}'})
    # Keycloak clients
    for rp in sorted(glob.glob(os.path.join(REALMS, '*.json'))):
        try:
            realm = json.load(open(rp, encoding='utf-8'))
        except Exception:
            continue
        for c in realm.get('clients', []):
            cid = c.get('clientId', '')
            if cid in HIDDEN_CLIENTS or not cid:
                continue
            public = bool(c.get('publicClient'))
            rows.append({'name': f"keycloak:{realm.get('realm')}:{cid}", 'from_kind': 'user' if public else 'backend', 'to_kind': 'service',
                         'from_app': cid, 'to_app': 'keycloak', 'direction': 'to', 'transport': 'tls', 'auth': 'oidc-code+pkce (public client)' if public else 'client-secret (confidential client)',
                         'key_kind': 'asymmetric' if public else 'symmetric', 'key_source': 'keycloak', 'scenario': 'swarm-full', 'verified': False,
                         'finding': '' if public or c.get('serviceAccountsEnabled') is not None else '', 'evidence': f"{os.path.basename(rp)}: publicClient={public}"})
    # app ↔ app from the live tables
    if manager is not None:
        tables = getattr(manager, 'objectTables', None) or {}
        for row in (tables.get('ServiceConnection') or {}).values():
            rows.append({'name': f"service:{getattr(row, 'name', '')}", 'from_kind': getattr(row, 'from_kind', 'service'), 'to_kind': getattr(row, 'to_kind', 'service'),
                         'from_app': getattr(row, 'from_instance_name', ''), 'to_app': getattr(row, 'to_instance_name', getattr(row, 'interconnect_key', '')),
                         'direction': 'to', 'transport': 'overlay-encrypted', 'auth': 'hmac-secret / api-key', 'key_kind': 'symmetric', 'key_source': 'docker-secret',
                         'scenario': 'any', 'verified': False, 'finding': '', 'evidence': 'ServiceConnection row'})
        for row in (tables.get('IsleProtocolPermit') or {}).values():
            rows.append({'name': f"isle:{getattr(row, 'name', '')}", 'from_kind': getattr(row, 'from_kind', 'service'), 'to_kind': getattr(row, 'to_kind', 'service'),
                         'from_app': getattr(row, 'from_instance_name', ''), 'to_app': getattr(row, 'interconnect_key', ''), 'direction': 'to', 'transport': 'tls (isle CA)',
                         'auth': 'per protocol', 'key_kind': 'both', 'key_source': 'isle-ca', 'scenario': 'isle', 'verified': False, 'finding': '', 'evidence': 'IsleProtocolPermit row'})
    for r in rows:
        if r['from_kind'] == 'user' and r['key_kind'] == 'symmetric':
            r['finding'] = 'symmetric key on a user channel'
    return rows


def authz_rule_rows(manager=None):
    rows = []
    gate = 'off (crude_permission_gate default; accessControl.app_permissions_gate)'
    try:
        from accessControl import app_permissions_gate as g
        for attr in ('GATE_ENABLED', 'ENABLED', 'gate_enabled'):
            if hasattr(g, attr):
                gate = f"{attr}={getattr(g, attr)}"
                break
    except Exception:
        pass
    if manager is not None:
        tables = getattr(manager, 'objectTables', None) or {}
        for row in (tables.get('polariPermissionSet') or {}).values():
            rows.append({'name': f"permset:{getattr(row, 'Name', '')}", 'app': 'core', 'resource': str(getattr(row, 'setAccessQueries', ''))[:200], 'role': '',
                         'verbs': str(getattr(row, 'setPermissionQuery', ''))[:200], 'source': 'accessControl.polariPermissionSet', 'gate': gate, 'notes': ''})
        for row in (tables.get('Role') or {}).values():
            rows.append({'name': f"role:{getattr(row, 'name', getattr(row, 'Name', ''))}", 'app': 'core', 'resource': '*', 'role': getattr(row, 'name', getattr(row, 'Name', '')),
                         'verbs': 'per permission set', 'source': 'accessControl.Role', 'gate': gate, 'notes': ''})
    if not rows:
        rows.append({'name': 'crude-gate', 'app': 'core', 'resource': 'every class (CRUDE)', 'role': 'any', 'verbs': 'CRUDE',
                     'source': 'accessControl.app_permissions_gate', 'gate': gate, 'notes': 'no permission-set rows on this instance: with the gate off and no logins (lean), every caller may CRUDE'})
    return rows


def _schema_for(typing_obj):
    props = {}
    for v in getattr(typing_obj, 'polyTypedVars', None) or []:
        n = getattr(v, 'name', None)
        if not n or n in ('manager', 'id', 'branch'):
            continue
        t = (getattr(v, 'typeList', None) or getattr(v, 'pythonTypeDefault', None) or 'str')
        t = t[0] if isinstance(t, (list, tuple)) and t else t
        js = {'str': 'string', 'int': 'integer', 'float': 'number', 'bool': 'boolean', 'list': 'array', 'dict': 'object'}.get(str(t).replace("<class '", '').replace("'>", ''), 'string')
        props[n] = {'type': js}
    return props


def content_policy_rows(manager=None):
    rows = []
    if manager is None:
        return rows
    typing = getattr(manager, 'objectTypingDict', None) or {}
    for cls, t in typing.items():
        props = _schema_for(t)
        schema = {'type': 'object', 'properties': props, 'additionalProperties': False}
        rows.append({'name': f'class:{cls}', 'app': getattr(t, 'module', '') or 'core', 'target': cls, 'mode': 'derived', 'schema_json': json.dumps(schema)[:2000],
                     'fields': len(props), 'max_body_bytes': 1048576, 'max_array': 10000, 'max_string': 65536, 'content_types': 'application/json',
                     'violations_observed': 0, 'last_tested': '', 'test_verdict': ''})
    return rows


def browser_policy_rows():
    rows = []
    for host, env, api, auth in (('prf', 'lean', 'api.prf', False), ('hub', 'lean', '', False), ('prf', 'prod', 'api.prf', True), ('psc', 'prod', 'api.psc', True), ('hub', 'prod', '', False), ('polari.isle', 'isle', 'api.polari.isle', False)):
        origins = ["'self'"] + ([f'https://{api}.<domain>' if env != 'isle' else f'https://{api}'] if api else []) + (['https://auth.<domain>'] if auth else [])
        csp = f"default-src 'self'; connect-src {' '.join(origins)}{' wss://' + api + '.<domain>' if api and env != 'isle' else ''}; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        rows.append({'name': f'{env}:{host}', 'host': f'{host}.<domain>' if env != 'isle' else host, 'env': env, 'mode': 'derived', 'csp': csp, 'frame': 'DENY',
                     'referrer': 'strict-origin-when-cross-origin', 'report_to': '/api/security/csp-report (not built)', 'violations': 0})
    return rows
