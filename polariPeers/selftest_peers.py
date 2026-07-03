"""
Self-test for the peers + modules handshake (twin-Polari).

Run from polari-framework/:
    python3 -m polariPeers.selftest_peers

Pure python — fake manager + fake falcon plumbing + mocked peer HTTP.
"""

import json
import os
from types import SimpleNamespace

import polariPeers.peers_api as peers_api_mod
from polariPeers.peers_api import (
    PeersAPI, instance_identity, peer_token, _parse_crude_rows,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


class _Resp:
    def __init__(self):
        self.media, self.status = None, '200 OK'


def _req(body=None):
    return SimpleNamespace(media=body or {})


def _api(peers=(), modules=(), sims=0):
    api = PeersAPI.__new__(PeersAPI)  # bypass treeObjectInit (needs polServer)
    api.manager = SimpleNamespace(objectTables={
        'PeerNode': {p.name: p for p in peers},
        'PolariModule': {m.name: m for m in modules},
        'SimulationDefinition': {f's{i}': SimpleNamespace(name=f's{i}')
                                 for i in range(sims)},
    }, db=None)
    return api


def _peer(name='b', base='http://prf-b-backend:3000'):
    return SimpleNamespace(name=name, base_url=base, status='unknown',
                           last_seen='', identity_json='{}')


def main():
    print('Twin-Polari — peers + modules handshake\n')

    # Identity + token resolution.
    os.environ['POLARI_INSTANCE_ID'] = 'b'
    os.environ['POLARI_INSTANCE_NAME'] = 'polari-b'
    ident = instance_identity()
    check('identity from env', ident['instanceId'] == 'b'
          and ident['instanceName'] == 'polari-b')
    os.environ.pop('POLARI_INSTANCE_ID'); os.environ.pop('POLARI_INSTANCE_NAME')
    check('identity defaults without env',
          instance_identity()['instanceId'] == 'a')
    os.environ['POLARI_PEER_TOKEN'] = 'sekrit'
    check('token from env', peer_token() == 'sekrit')
    os.environ.pop('POLARI_PEER_TOKEN')

    # Registration: token gate + upsert idempotency.
    api = _api()
    resp = _Resp()
    os.environ['POLARI_PEER_TOKEN'] = 'tok'
    api.on_post_register(_req({'name': 'b', 'baseUrl': 'http://x:3000',
                               'token': 'WRONG'}), resp)
    check('wrong token rejected 403', resp.status.startswith('403'))
    # Create path: stub the PeerNode class (the real treeObject needs the
    # full manager machinery; construction wiring is not under test here).
    import polariPeers.peer_node as pn_mod
    real_peer_node = pn_mod.PeerNode
    pn_mod.PeerNode = lambda **kw: SimpleNamespace(
        identity_json='{}', last_seen='', **kw)
    try:
        resp = _Resp()
        api.on_post_register(_req({'name': 'b', 'baseUrl': 'http://x:3000/',
                                   'token': 'tok'}), resp)
        created_ok = resp.status.startswith('201')
    finally:
        pn_mod.PeerNode = real_peer_node
    # Upsert path: the fake manager has no real PeerNode class wiring, so
    # emulate the found-peer branch directly.
    peer = _peer()
    api2 = _api(peers=[peer])
    resp2 = _Resp()
    api2.on_post_register(_req({'name': 'b', 'baseUrl': 'http://new:3000',
                                'token': 'tok'}), resp2)
    check('register: valid token creates/updates (201, url updated)',
          created_ok and resp2.status.startswith('201')
          and peer.base_url == 'http://new:3000')
    os.environ.pop('POLARI_PEER_TOKEN')
    resp3 = _Resp()
    api2.on_post_register(_req({'name': 'b', 'baseUrl': 'http://n:1',
                                'token': ''}), resp3)
    check('no token configured -> registration disabled 403',
          resp3.status.startswith('403')
          and 'no peer token' in resp3.media['error'])

    # Ping payload shape.
    api = _api(modules=[SimpleNamespace(name='m1')], sims=3)
    resp = _Resp()
    api.on_get_ping(_req(), resp)
    d = resp.media['data']
    check('ping carries identity + counts',
          d['framework'] == 'polari' and d['moduleCount'] == 1
          and d['simulationCount'] == 3 and 'instanceId' in d)

    # Peer listing with mocked liveness.
    real_get = peers_api_mod._http_get_json
    peers_api_mod._http_get_json = lambda url: (
        {'success': True, 'data': {'instanceName': 'polari-b'}}
        if 'ping' in url else {'_error': 'nope'})
    try:
        peer = _peer()
        api = _api(peers=[peer])
        resp = _Resp()
        api.on_get(_req(), resp)
        row = resp.media['data'][0]
        check('peer list live-pings and reports alive',
              row['status'] == 'alive' and row['lastSeen']
              and row['identity'].get('instanceName') == 'polari-b')

        # Peer-simulations proxy parsing (CRUDE envelope).
        peers_api_mod._http_get_json = lambda url: [
            {'SimulationDefinition': [{'data': [
                {'name': 'wind-field-3d', 'intent': 'observe',
                 'description': 'wind'},
                {'name': 'material-condensation', 'intent': 'search',
                 'description': 'materials'},
            ]}]}]
        resp = _Resp()
        api.on_get_peer_simulations(_req(), resp, 'b')
        sims = resp.media['data']['simulations']
        check('peer simulations proxied + summarized',
              len(sims) == 2 and sims[1]['intent'] == 'search',
              f'sims={[s["name"] for s in sims]}')

        peers_api_mod._http_get_json = lambda url: {'_error': 'down'}
        resp = _Resp()
        api.on_get_peer_simulations(_req(), resp, 'b')
        check('unreachable peer -> structured 502',
              resp.status.startswith('502'))
        resp = _Resp()
        api.on_get_peer_simulations(_req(), resp, 'ghost')
        check('unknown peer -> 404', resp.status.startswith('404'))
    finally:
        peers_api_mod._http_get_json = real_get

    # Modules skeleton.
    mod = SimpleNamespace(name='pendulum-samples', version='abc123',
                          source_kind='peer', source_ref='a',
                          status='installing',
                          manifest_json=json.dumps({'objects': 12}),
                          bundle_json='')
    api = _api(modules=[mod])
    resp = _Resp()
    api.on_get_modules(_req(), resp)
    check('modules list shows installing modules to probing peers',
          resp.media['data'][0]['status'] == 'installing'
          and resp.media['data'][0]['manifest']['objects'] == 12)
    resp = _Resp()
    api.on_get_module_one(_req(), resp, 'pendulum-samples')
    check('module fetch returns manifest (bundle None until Track 3)',
          resp.media['data']['bundle'] is None
          and resp.media['data']['version'] == 'abc123')
    resp = _Resp()
    api.on_get_module_one(_req(), resp, 'nope')
    check('missing module -> clear Track-3 404',
          resp.status.startswith('404') and 'Track 3' in resp.media['error'])

    # CRUDE envelope parser edge cases.
    check('crude parser tolerates junk',
          _parse_crude_rows({'weird': 1}, 'X') == []
          and _parse_crude_rows([], 'X') == [])

    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
