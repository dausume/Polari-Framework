"""grpcbridge.custom.bridge_link_checks - checks for grpcbridge_hosted_selftest: a bridge reaches its Polari node from its PolariBridgeInstance (bridge_link),
the same way for a cabled board and for its twin.

    link_rules(check)                       the pure rules: the node's isle gRPC name, verified TLS, the refusals in words
    worker_tls(check, skip)                 the REAL worker (prf-bridge-engines/bridge_hosted.py): grpc_tls replaces the generated grpc.tls line and is repeated
    backend_instance(check, mgr, TS, HB, env, hex_bytes)   hosted_bridges.start(instance=...) against fake workers (one older than the link)
"""
import os
import time


def link_rules(check):
    from grpcbridge.custom import bridge_link as BL, bridge_paths as BP
    seeds = {r['name']: r for r in BP.SEED_POLARI_BRIDGES}
    uno, c3 = BL.link(dict(seeds[BP.UNO_BRIDGE])), BL.link(dict(seeds[BP.C3_BRIDGE]))
    check('link: an instance\'s bridge pushes to its node\'s gRPC name on the isle (grpc.<node>.isle:443, TLS verified), beside its api name; the same rule for the '
          'cabled UNO and the C3 twin', uno['target'] == 'grpc.polari-pol.isle:443' and uno['tls'] == 'verified' and uno['node_url'] == 'https://api.polari-pol.isle'
          and c3['target'] == uno['target'] and uno['definition'] == 'uno-light' and c3['definition'] == 'esp32c3-light' and uno['mode'] == 'serial' and c3['mode'] == 'simulated',
          str((uno, c3))[:300])
    check('link: the link carries the instance\'s struct-to-object maps (StructObjectMap names) and says them', uno['maps'] == 'LightState_t->LightState'
          and 'LightState_t->LightState' in uno['why'] and 'grpc.polari-pol.isle' in uno['why'])
    row = dict(seeds[BP.UNO_BRIDGE], name='renamed-node', polari_node='polari-other', polari_node_url=BP.node_url('polari-other'))
    check('link: the target follows the node name (nothing hard-coded): polari-other -> grpc.polari-other.isle:443', BL.link(row)['target'] == 'grpc.polari-other.isle:443')

    def refused(r):
        try:
            BL.link(r)
            return None
        except BL.LinkRefused as e:
            return e

    e1 = refused(dict(seeds[BP.UNO_BRIDGE], polari_node='', polari_node_url=''))
    e2 = refused(dict(seeds[BP.UNO_BRIDGE], polari_node_url='https://api.somewhere-else.isle'))
    e3 = refused(dict(seeds[BP.UNO_BRIDGE], bridge_definition=''))
    check('link: an instance with no node, or a url that is not its node\'s isle name, is refused in words (409); no bridge_definition is a 422',
          e1 and e1.status == 409 and 'names no polari_node' in str(e1) and e2 and 'not polari-pol' in str(e2) and e3 and e3.status == 422 and 'no bridge_definition' in str(e3),
          '%s | %s | %s' % (e1, e2, e3))
    try:
        BL.instance(None, 'nonesuch-bridge')
        e4 = None
    except BL.LinkRefused as e:
        e4 = e
    check('link: an unknown instance is a 404 listing the known ones', e4 and e4.status == 404 and BP.UNO_BRIDGE in str(e4))
    import types
    mgr = types.SimpleNamespace(objectTables={'PolariBridgeInstance': {'x': types.SimpleNamespace(**dict(seeds[BP.UNO_BRIDGE], polari_node='polari-live',
                                                                                                       polari_node_url=BP.node_url('polari-live')))}})
    check('link: the server\'s own PolariBridgeInstance row wins over the seed of the same name', BL.instance(mgr, BP.UNO_BRIDGE)['polari_node'] == 'polari-live')


def worker_tls(check, skip):
    from grpcbridge.custom import hosted_checks as HC
    HC.worker_logic(check, skip, checks=_worker_tls, label='link worker grpc_tls')


def _worker_tls(check, bh, falcon, FT, tmp, count):
    base = 'source=serial\nmax_frames=0\ngrpc.enabled=false\ngrpc.tls=plaintext\nbaud=1\n'
    s = {'id': 'x', 'session_id': 's', 'twin_host': '127.0.0.1', 'twin_port': 9999, 'twin_uart': '', 'grpc_target': 'grpc.polari-pol.isle:443'}
    on = bh._properties(base, dict(s, grpc_tls='verified')).splitlines()
    off = bh._properties(base, s).splitlines()
    check('link worker: grpc_tls=verified replaces the generated grpc.tls=plaintext line (once); without grpc_tls the generated line is kept as it was',
          on.count('grpc.tls=verified') == 1 and 'grpc.tls=plaintext' not in on and 'grpc.target=grpc.polari-pol.isle:443' in on
          and 'grpc.tls=plaintext' in off and not [x for x in off if x == 'grpc.tls=verified'], str((on, off)))
    app = falcon.App(middleware=[bh.Reaper()])
    bh.add_routes(app)
    cl = FT.TestClient(app)
    files = {'pom.xml': '<project>ok</project>', 'src/main/java/A.java': 'class A {}', 'bridge.properties': base}
    body = dict(session_id='uno-light-tls', twin_host='127.0.0.1', twin_port=9999, bridge_name='uno-light', files=files, grpc_target='grpc.polari-pol.isle:443', ttl_s=60)
    bad = cl.simulate_post('/bridges', json=dict(body, grpc_tls='insecure'))
    check('link worker: a grpc_tls that is neither verified nor plaintext is a 400 in words (there is no "TLS without checking")', bad.status_code == 400 and 'grpc_tls' in bad.json['error'])
    r = cl.simulate_post('/bridges', json=dict(body, grpc_tls='verified'))
    bid = r.json.get('id')
    end, a = time.time() + 15, r.json
    while bid and a.get('state') == 'building' and time.time() < end:
        time.sleep(0.1)
        a = cl.simulate_get('/bridges/%s' % bid).json
    try:
        props = open(os.path.join(bh.DIR, '%s.properties' % bid)).read().splitlines() if bid else []
        check('link worker: the answer repeats grpc_tls (how a caller tells this worker applied it) and the running bridge\'s properties say verified',
              r.status_code == 200 and r.json.get('grpc_tls') == 'verified' and a.get('grpc_tls') == 'verified' and 'grpc.tls=verified' in props, str(a)[:200])
    finally:
        if bid:
            cl.simulate_delete('/bridges/%s' % bid)


def backend_instance(check, mgr, TS, HB, env, hex_bytes):
    from grpcbridge.custom import bridge_engines as be, bridge_paths as BP
    from grpcbridge.custom.hosted_fakes import FakeBridgeWorker
    from board.custom.twin_session_fakes import FakeWorker
    board, new, old = FakeWorker(sessions=True), FakeBridgeWorker(), FakeBridgeWorker(knows_tls=False)
    try:
        with env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=new.url):
            be.forget()
            ts = TS.start(mgr, 'uno-light', ttl_s=300, owner='tester', hex_bytes=hex_bytes)
            v = HB.start(mgr, ts['name'], instance=BP.UNO_BRIDGE, api_host='https://ignored.example/', owner='tester')
            sent = new.items[v['worker_bridge']]['body']
            check('link backend: start(instance=uno-1-bridge) runs the instance\'s own bridge (uno-light, the one the cabled UNO runs) on its twin, pushing to '
                  'grpc.polari-pol.isle:443 with grpc_tls=verified; the host the request came to is NOT used', sent['bridge_name'] == 'uno-light'
                  and sent['grpc_target'] == 'grpc.polari-pol.isle:443' and sent.get('grpc_tls') == 'verified' and 'ignored' not in str(v)
                  and v['instance'] == BP.UNO_BRIDGE and v['grpc_tls'] == 'verified' and v['link']['maps'] == 'LightState_t->LightState', str(v)[:400])
            lo = HB.start(mgr, ts['name'], instance=BP.UNO_BRIDGE, log_only=True)
            check('link backend: log_only with an instance sends no target and no grpc_tls', new.items[lo['worker_bridge']]['body']['grpc_target'] == ''
                  and 'grpc_tls' not in new.items[lo['worker_bridge']]['body'])

            def why(**kw):
                try:
                    HB.start(mgr, ts['name'], **kw)
                    return None
                except HB.HostedRefused as e:
                    return e

            e1, e2 = why(instance=BP.UNO_BRIDGE, grpc_target_='other.example:4000'), why(instance=BP.UNO_BRIDGE, bridge_name='uno-pair')
            e3 = why(instance='nonesuch-bridge')
            check('link backend: a grpc_target or another bridge_name beside an instance is refused (409); an unknown instance is a 404', e1 and e1.status == 409
                  and 'one source' in str(e1) and e2 and e2.status == 409 and 'uno-pair' in str(e2) and e3 and e3.status == 404, '%s | %s | %s' % (e1, e2, e3))
            plain = HB.start(mgr, ts['name'], grpc_target_='dev-stack.example:3002')
            check('link backend: without an instance nothing changes - an explicit target is sent as given and no grpc_tls (the generated line stays)',
                  new.items[plain['worker_bridge']]['body']['grpc_target'] == 'dev-stack.example:3002' and 'grpc_tls' not in new.items[plain['worker_bridge']]['body']
                  and plain['instance'] == '')
        with env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=old.url):
            be.forget()
            before = len(HB._rows(mgr))
            e4 = None
            try:
                HB.start(mgr, ts['name'], instance=BP.UNO_BRIDGE)
            except HB.HostedRefused as e:
                e4 = e
            check('link backend: a worker older than the link (its answer does not repeat grpc_tls) has its bridge STOPPED and the start refused (424) - never '
                  'left to reach the isle in plaintext; no row', e4 and e4.status == 424 and 'plaintext' in str(e4) and not old.items
                  and any(m == 'DELETE' for m, _ in old.requests) and len(HB._rows(mgr)) == before, str(e4))
        with env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=new.url):
            for b in HB._rows(mgr):
                if b.state in ('building', 'running'):
                    HB.stop(mgr, b.name)
            TS.stop(mgr, ts['name'])
    finally:
        be.forget()
        board.close()
        new.close()
        old.close()
