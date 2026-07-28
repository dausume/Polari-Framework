"""
@module odooconnect.selftest_odoo

od-3 selftests against a STUB JSON-RPC server (stdlib http.server on an
ephemeral port — no live Odoo anywhere near CI): auth, search_read
paging, refusal shapes, the write guards (read_only / push_enabled /
operations typed-confirm), and sim/ops handle separation.

Run from polari-framework/: python3 -m odooconnect.selftest_odoo
(with modules/ on the import path, as the pol modules runner does).
"""

import json
import os
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from odooconnect.odoo_analysis import odoo_status
from odooconnect.odoo_client import (
    OdooHandle, jsonrpc, ops_confirm_phrase,
)
from odooconnect.odoo_seed import SEED_ODOO_INSTANCES

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


# ---------------------------------------------------------------------------
# Stub Odoo: /jsonrpc with common.version / common.authenticate /
# object.execute_kw over 25 fake partners. Auth: login 'stub' +
# password 'stub-pass' -> uid 7.
# ---------------------------------------------------------------------------
PARTNERS = [{'id': i, 'name': f'partner-{i:02d}'} for i in range(1, 26)]
CREATED = []


class _StubOdoo(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, result=None, error=None):
        body = {'jsonrpc': '2.0', 'id': 1}
        if error is not None:
            body['error'] = error
        else:
            body['result'] = result
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != '/jsonrpc':
            self.send_error(404)
            return
        req = json.loads(self.rfile.read(
            int(self.headers.get('Content-Length', 0))))
        params = req.get('params', {})
        service, method = params.get('service'), params.get('method')
        args = params.get('args', [])
        if service == 'common' and method == 'version':
            self._reply({'server_version': '18.0-stub'})
        elif service == 'common' and method == 'authenticate':
            db, login, password = args[0], args[1], args[2]
            ok = (db.startswith('odoo_') and login == 'stub'
                  and password == 'stub-pass')
            self._reply(7 if ok else False)
        elif service == 'object' and method == 'execute_kw':
            _db, uid, password, model, obj_method = args[:5]
            if uid != 7 or password != 'stub-pass':
                self._reply(error={'message': 'Access Denied'})
                return
            m_args = args[5] if len(args) > 5 else []
            m_kwargs = args[6] if len(args) > 6 else {}
            if model == 'res.partner' and obj_method == 'search_read':
                offset = int(m_kwargs.get('offset', 0))
                limit = int(m_kwargs.get('limit', 0)) or len(PARTNERS)
                self._reply(PARTNERS[offset:offset + limit])
            elif model == 'res.partner' and obj_method == 'create':
                CREATED.append(m_args[0])
                self._reply(1000 + len(CREATED))
            else:
                self._reply(error={'message':
                                   f'stub: no {model}.{obj_method}'})
        else:
            self._reply(error={'message': 'stub: unknown service'})


def _cfg(name, mode, push_enabled, read_only, base_url,
         auth_password_env='STUB_ODOO_PASS'):
    return types.SimpleNamespace(
        name=name, display_name=name, base_url=base_url,
        db=f'odoo_{name.split("-")[-1]}', mode=mode, url_env='',
        auth_login='stub', auth_password_env=auth_password_env,
        push_enabled=push_enabled, read_only=read_only,
        is_prior=True, provenance_id='od-3-test', notes='')


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 0), _StubOdoo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    URL = f'http://127.0.0.1:{server.server_address[1]}'
    os.environ['STUB_ODOO_PASS'] = 'stub-pass'

    print('== suite: raw jsonrpc + probes ==')
    out = jsonrpc(URL, 'common', 'version', [])
    check('version probe ok', out.get('ok')
          and out['result']['server_version'] == '18.0-stub')
    check('empty base_url refuses with suggestion',
          not jsonrpc('', 'common', 'version', []).get('ok')
          and jsonrpc('', 'common', 'version', [])['suggestion'])
    dead = jsonrpc('http://127.0.0.1:9', 'common', 'version', [],
                   timeout=2)
    check('unreachable server refuses (never raises)',
          not dead.get('ok') and 'unreachable' in dead['refusal'])

    print('== suite: authentication ==')
    sim = OdooHandle(_cfg('odoo-sim', 'simulation', True, False, URL))
    check('authenticate resolves uid',
          sim.authenticate().get('result') == 7)
    bad = OdooHandle(_cfg('odoo-sim', 'simulation', True, False, URL,
                          auth_password_env='STUB_ODOO_WRONG'))
    os.environ['STUB_ODOO_WRONG'] = 'nope'
    check('bad password -> auth refusal',
          'authentication failed' in bad.authenticate().get('refusal', ''))
    unset = OdooHandle(_cfg('odoo-sim', 'simulation', True, False, URL,
                            auth_password_env='STUB_ODOO_UNSET'))
    out = unset.authenticate()
    check('missing env var refusal NAMES the var',
          'STUB_ODOO_UNSET' in out.get('refusal', '')
          and out['suggestion']['knob'] == 'STUB_ODOO_UNSET')

    print('== suite: search_read paging ==')
    pages = [sim.search_read('res.partner', limit=10, offset=o)
             for o in (0, 10, 20)]
    check('three pages ok', all(p.get('ok') for p in pages))
    check('page sizes 10/10/5',
          [len(p['result']) for p in pages] == [10, 10, 5])
    ids = [r['id'] for p in pages for r in p['result']]
    check('pages disjoint + complete', sorted(ids) == list(range(1, 26)))

    print('== suite: write guards (the sim/ops invariant) ==')
    out = sim.execute_kw('res.partner', 'create', [{'name': 'from-sim'}])
    check('sim write lands (push_enabled=True)',
          out.get('ok') and out['result'] >= 1000)
    ops = OdooHandle(_cfg('odoo-ops', 'operations', False, True, URL))
    check('ops read is fine',
          ops.search_read('res.partner', limit=1).get('ok'))
    out = ops.execute_kw('res.partner', 'create', [{'name': 'x'}])
    check('ops write refuses naming read_only',
          not out.get('ok') and 'read_only' in out['refusal'])
    ops2 = OdooHandle(_cfg('odoo-ops', 'operations', False, False, URL))
    out = ops2.execute_kw('res.partner', 'create', [{'name': 'x'}])
    check('push_enabled=False refusal NAMES the knob',
          not out.get('ok') and 'push_enabled' in out['refusal']
          and 'push_enabled' in out['suggestion']['knob'])
    ops3 = OdooHandle(_cfg('odoo-ops', 'operations', True, False, URL))
    out = ops3.execute_kw('res.partner', 'create', [{'name': 'x'}])
    check('ops write without typed phrase refuses',
          not out.get('ok') and 'typed' in out['refusal'])
    check('refusal action carries the exact phrase',
          ops_confirm_phrase('odoo-ops') in out['suggestion']['action'])
    out = ops3.execute_kw('res.partner', 'create', [{'name': 'real'}],
                          confirm=ops_confirm_phrase('odoo-ops'))
    check('knob + typed phrase together allow the ops write',
          out.get('ok') and out['result'] >= 1000)
    out = ops3.execute_kw('res.partner', 'action_confirm', [[1]])
    check('unknown method counts as a write (guarded)',
          not out.get('ok') and 'typed' in out['refusal'])
    sim_ro = OdooHandle(_cfg('odoo-sim', 'simulation', True, True, URL))
    check('read_only wins even on a sim row',
          'read_only' in sim_ro.execute_kw(
              'res.partner', 'create', [{}]).get('refusal', ''))

    print('== suite: handle separation ==')
    check('handles carry their mode',
          sim.mode == 'simulation' and ops.mode == 'operations')
    check('refusals name THEIR row, not a global',
          'odoo-ops' in ops2.execute_kw(
              'res.partner', 'create', [{}])['refusal'])

    print('== suite: status endpoint over a fake manager ==')
    live = _cfg('odoo-sim', 'simulation', True, False, URL)
    down = _cfg('odoo-ops', 'operations', False, True,
                'http://127.0.0.1:9')
    mgr = types.SimpleNamespace(objectTables={
        'OdooInstanceConfig': {'a': live, 'b': down}})
    st = odoo_status(mgr, timeout=2)
    rows = {r['name']: r for r in st['statuses']}
    check('status ok with mixed reachability', st.get('ok')
          and st['configCount'] == 2)
    check('live row reports version',
          rows['odoo-sim']['reachable']
          and rows['odoo-sim']['serverVersion'] == '18.0-stub')
    check('down row refuses honestly, endpoint still answers',
          not rows['odoo-ops']['reachable']
          and rows['odoo-ops']['refusal'])
    check('knob states visible in status',
          rows['odoo-ops']['readOnly'] is True
          and rows['odoo-ops']['pushEnabled'] is False)

    print('== suite: seeds ==')
    names = {s['name'] for s in SEED_ODOO_INSTANCES}
    check('seeds = odoo-sim + odoo-ops',
          names == {'odoo-sim', 'odoo-ops'})
    ops_seed = next(s for s in SEED_ODOO_INSTANCES
                    if s['name'] == 'odoo-ops')
    check('ops seed is read_only + push-disabled',
          ops_seed['read_only'] and not ops_seed['push_enabled'])
    check('no secret-shaped values in seeds',
          all('pass' not in json.dumps(s).lower()
              .replace('auth_password_env', '')
              .replace('rpc_password', '')
              for s in SEED_ODOO_INSTANCES))

    server.shutdown()
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
