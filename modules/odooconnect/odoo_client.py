"""
@module odooconnect.odoo_client

Stdlib JSON-RPC client for Odoo (/jsonrpc; no third-party dependency)
with the honest-refusal shape {ok: False, refusal, suggestion} on every
failure — connection, auth, permission, guard. NEVER raises, and NEVER
retries a write (a retried create/write could double-post real business
data; idempotency arrives with x_polari_ref bindings in od-4).

Write guards are DATA-driven from the OdooInstanceConfig row a handle
was built from:
  - read_only=True            -> every write refuses, naming the field
  - push_enabled=False        -> every write refuses, naming the knob
  - mode='operations'         -> writes ALSO need the typed phrase
                                 'PUSH TO OPERATIONS <name>' per call
Anything not in READ_SAFE_METHODS counts as a write — unknown methods
are guarded, not waved through.

Duck-typed: handles are built from any object with the config fields
(a treeObject row or a SimpleNamespace in selftests).
"""

import json
import os
import urllib.error
import urllib.request

#: execute_kw methods that cannot mutate — everything else is a write.
READ_SAFE_METHODS = frozenset({
    'search', 'search_read', 'search_count', 'read', 'read_group',
    'fields_get', 'name_search', 'name_get', 'check_access_rights',
})

#: gm-6 typed-confirmation phrase for operations writes.
def ops_confirm_phrase(config_name):
    return f'PUSH TO OPERATIONS {config_name}'


def _suggestion(evidence, knob, action):
    return {'evidence': evidence, 'knob': knob, 'action': action}


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def jsonrpc(base_url, service, method, args, timeout=15):
    """One raw JSON-RPC call. Returns {ok, result} or a refusal —
    never raises."""
    if not base_url:
        return _refuse('no Odoo base_url configured',
                       _suggestion('empty base_url on the config row',
                                   'OdooInstanceConfig.base_url / url_env',
                                   'set the row base_url or its url_env'))
    payload = {'jsonrpc': '2.0', 'method': 'call', 'id': 1,
               'params': {'service': service, 'method': method,
                          'args': list(args)}}
    req = urllib.request.Request(
        base_url.rstrip('/') + '/jsonrpc',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except Exception as exc:  # noqa: BLE001 — refusals, not crashes
        return _refuse(f'odoo unreachable at {base_url}: {exc}',
                       _suggestion(f'{type(exc).__name__} on POST /jsonrpc',
                                   'pol odoo status',
                                   'pol odoo up (is the odoo profile running?)'))
    if body.get('error'):
        err = body['error'] or {}
        msg = ((err.get('data') or {}).get('message')
               or err.get('message') or 'unknown odoo error')
        return _refuse(f'odoo error: {msg}')
    return {'ok': True, 'result': body.get('result')}


class OdooHandle:
    """A client bound to ONE OdooInstanceConfig row. The row's mode and
    knobs travel with the handle — sim and ops can never blur inside a
    single object."""

    def __init__(self, config, timeout=15):
        self.config = config
        self.timeout = timeout
        self._uid = None

    # -- config resolution ------------------------------------------
    @property
    def name(self):
        return getattr(self.config, 'name', '')

    @property
    def mode(self):
        return getattr(self.config, 'mode', 'simulation')

    def base_url(self):
        env_name = getattr(self.config, 'url_env', '') or ''
        if env_name and os.environ.get(env_name, ''):
            return os.environ[env_name].rstrip('/')
        return (getattr(self.config, 'base_url', '') or '').rstrip('/')

    def _password(self):
        env_name = getattr(self.config, 'auth_password_env', '') or ''
        if not env_name:
            return None, _refuse(
                f'config "{self.name}" names no auth_password_env',
                _suggestion('auth_password_env is empty on the row',
                            'OdooInstanceConfig.auth_password_env',
                            'set it to the NAME of the env var holding '
                            'the RPC password'))
        secret = os.environ.get(env_name, '')
        if not secret:
            return None, _refuse(
                f'env var {env_name} is not set (config "{self.name}")',
                _suggestion(f'os.environ[{env_name!r}] is empty',
                            env_name,
                            f'export {env_name}=<rpc password/api-key> '
                            'on the backend'))
        return secret, None

    # -- calls ------------------------------------------------------
    def version(self):
        """Unauthenticated server probe (common.version)."""
        return jsonrpc(self.base_url(), 'common', 'version', [],
                       timeout=self.timeout)

    def authenticate(self):
        """Resolve uid once per handle; refusal if auth fails."""
        if self._uid is not None:
            return {'ok': True, 'result': self._uid}
        secret, refusal = self._password()
        if refusal:
            return refusal
        login = getattr(self.config, 'auth_login', '') or ''
        db = getattr(self.config, 'db', '') or ''
        out = jsonrpc(self.base_url(), 'common', 'authenticate',
                      [db, login, secret, {}], timeout=self.timeout)
        if not out.get('ok'):
            return out
        if not out.get('result'):
            return _refuse(
                f'authentication failed for "{login}" on {db} '
                f'(config "{self.name}")',
                _suggestion('common.authenticate returned false',
                            getattr(self.config, 'auth_password_env', ''),
                            'check the login + the env-var secret'))
        self._uid = out['result']
        return {'ok': True, 'result': self._uid}

    def _write_guard(self, method, confirm):
        cfg = self.config
        if getattr(cfg, 'read_only', False):
            return _refuse(
                f'"{self.name}" is read_only — refusing {method}',
                _suggestion('read_only=True on the OdooInstanceConfig row',
                            f'OdooInstanceConfig[{self.name}].read_only',
                            'flip read_only deliberately (ops rows: od-6 '
                            'guardrails first)'))
        if not getattr(cfg, 'push_enabled', False):
            return _refuse(
                f'push_enabled is False on "{self.name}" — refusing '
                f'{method}',
                _suggestion('writes are knob-gated, never implicit',
                            f'OdooInstanceConfig[{self.name}].push_enabled',
                            'enable the knob on the row (ops rows also '
                            'need the typed confirmation per call)'))
        if self.mode == 'operations':
            phrase = ops_confirm_phrase(self.name)
            if confirm != phrase:
                return _refuse(
                    f'operations write to "{self.name}" needs the typed '
                    f'confirmation phrase',
                    _suggestion('mode=operations (REAL business data)',
                                'confirm=<typed phrase>',
                                f'pass confirm={phrase!r} on this call'))
        return None

    def execute_kw(self, model, method, args=None, kwargs=None,
                   confirm=''):
        """Authenticated object call. Writes (any method not in
        READ_SAFE_METHODS) pass the data-driven guards first."""
        if method not in READ_SAFE_METHODS:
            refusal = self._write_guard(method, confirm)
            if refusal:
                return refusal
        auth = self.authenticate()
        if not auth.get('ok'):
            return auth
        secret, refusal = self._password()
        if refusal:
            return refusal
        db = getattr(self.config, 'db', '') or ''
        return jsonrpc(self.base_url(), 'object', 'execute_kw',
                       [db, self._uid, secret, model, method,
                        list(args or []), dict(kwargs or {})],
                       timeout=self.timeout)

    def search_read(self, model, domain=None, fields=None, limit=0,
                    offset=0, order=''):
        kwargs = {}
        if fields:
            kwargs['fields'] = list(fields)
        if limit:
            kwargs['limit'] = int(limit)
        if offset:
            kwargs['offset'] = int(offset)
        if order:
            kwargs['order'] = order
        return self.execute_kw(model, 'search_read',
                               [list(domain or [])], kwargs)
