"""
@module odooconnect.odoo_selftest

od-3 selftests against a STUB JSON-RPC server (stdlib http.server on an
ephemeral port — no live Odoo anywhere near CI): auth, search_read
paging, refusal shapes, the write guards (read_only / push_enabled /
operations typed-confirm), and sim/ops handle separation.

Run from polari-framework/: python3 -m odooconnect.odoo_selftest
(with modules/ on the import path, as the pol modules runner does).
"""

import json
import os
import types

from odooconnect.custom.odoo_analysis import odoo_status
from odooconnect.custom.odoo_client import (
    OdooHandle, jsonrpc, ops_confirm_phrase,
)
from odooconnect.odoo_seed import SEED_ODOO_INSTANCES
from odooconnect.custom.stub_odoo import start_stub

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _cfg(name, mode, push_enabled, read_only, base_url,
         auth_password_env='STUB_ODOO_PASS'):
    return types.SimpleNamespace(
        name=name, display_name=name, base_url=base_url,
        db=f'odoo_{name.split("-")[-1]}', mode=mode, url_env='',
        auth_login='stub', auth_password_env=auth_password_env,
        push_enabled=push_enabled, read_only=read_only,
        is_prior=True, provenance_id='od-3-test', notes='')


if __name__ == '__main__':
    server, URL = start_stub()
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
