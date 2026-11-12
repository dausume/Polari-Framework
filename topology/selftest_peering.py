"""
Selftest for tpl-2 (AI-Notes/designs/TOPOLOGY_PEERING_DESIGN.md, decisions taken 2026-11-07): Polari backends see each other
without an isle.

Two in-memory backends shaped like the live ones (A = 'polari' on isle-core, B = 'polari-pol' on pol-core), each describing
itself with the REAL tpl-0/tpl-1 code. Only the external boundary is replaced: `fetch(name, url)` returns the other
backend's real self_description() through a JSON round trip (as the wire would), or raises (a dead peer). The default fetch
is checked separately to go through outbound.http_request(kind 'peer'), with no TLS override of its own.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m topology.selftest_peering
"""
import json
import os
import tempfile
import types

from topology import selftest_example_retire_durable as D
from topology import selftest_example_retire as T

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('%s: %s%s' % ('PASS' if cond else 'FAIL', label, (' - %r' % (extra,)) if extra and not cond else ''))


def _env(**kw):
    for k in ('POLARI_INSTANCE_NAME', 'POLARI_INSTANCE_ID', 'CORS_ORIGINS', 'POLARI_MACHINE_NAME', 'ISLE_HOSTNAME',
              'POLARI_TOPOLOGY_SEED', 'POLARI_TOPOLOGY_PEERS', 'POLARI_TOPOLOGY_PEERS_FILE', 'POLARI_TOPOLOGY_PEER_PULL_S',
              'POLARI_TOPOLOGY_VERIFY'):
        os.environ.pop(k, None)
    os.environ.update(kw)


AS_A = dict(CORS_ORIGINS='https://polari.isle', ISLE_HOSTNAME='isle-core', POLARI_TOPOLOGY_VERIFY='off')
AS_B = dict(CORS_ORIGINS='https://polari-pol.isle,https://electronics.isle', ISLE_HOSTNAME='pol-core', POLARI_TOPOLOGY_VERIFY='off')


def _backend(as_env, live, bindings=()):
    from topology import topology_self as S
    from topology.topology_modules import EngineProviderBinding
    _env(**as_env)
    store = D.Store()
    m = T._manager()
    m.db = store
    S.describe_self(m, live, 'selftest')
    for kind, url in bindings:
        store.saveInstanceInDB(EngineProviderBinding(name=kind, url=url, manager=m))
    S.describe_links(m, live, 'selftest', fetch=lambda u: {})
    return m, store


def _as(env, fn, *a, **k):
    _env(**env)
    return fn(*a, **k)


def main():
    from topology import topology_peering as P
    from topology import topology_example_retire as R
    from topology import topology_self as S
    P._LAST.clear()
    A, sa = _backend(AS_A, {'cmod', 'islemesh'}, [('board', 'https://board-engines.isle')])
    B, sb = _backend(AS_B, {'board', 'cmod'}, [('board', 'https://board-engines.isle')])
    peers = {'polari': (A, AS_A), 'polari-pol': (B, AS_B)}
    calls = []

    def fetch_from(caller_env):
        def fetch(name, url):
            target = next(v for k, v in peers.items() if '/api.%s.isle/' % k in url + '/' or url.startswith('https://api.%s.isle' % k))
            fn = P.self_digest if url.endswith('/self/digest') else P.self_description
            calls.append(url)
            desc = _as(target[1], fn, target[0])
            _env(**caller_env)                       # back to the caller's identity after the "remote" call
            return json.loads(json.dumps(desc))      # the wire
        return fetch

    # -- the self-description
    dB = _as(AS_B, P.self_description, B)
    check('self: B describes itself (instance, machine)', dB['kind'] == 'polari-topology-self' and dB['instance'] == 'polari-pol'
          and dB['machine'] == 'pol-core')
    names = {c: {r['name'] for r in rows} for c, rows in dB['rows'].items()}
    check('self: its instance, machine, live modules, engine link and frontend', 'polari-pol' in names['InstanceDefinition']
          and 'pol-core' in names['PolariNodeMachine'] and {'board@polari-pol', 'cmod@polari-pol'} <= names['ModuleAssignment']
          and 'board-engines' in names['InstanceDefinition'] and 'electronics' in names['InstanceDefinition'], names)
    check('self: the board edge it consumes', any(n.startswith('board@polari-pol->') for n in names['ModuleDependencyEdge']))
    check('self: no topology_name travels (each side files copies under its own)',
          all('topology_name' not in r for rows in dB['rows'].values() for r in rows))
    check('self: JSON-serializable', json.loads(json.dumps(dB)) == dB)

    # -- peer sources: both (D-tpl2-b)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
        json.dump([{'name': 'lab', 'url': 'https://api.lab.isle/'}, 'https://api.polari-pol.isle'], fh)
        pfile = fh.name
    try:
        from polariPeers.peer_node import PeerNode
        sa.saveInstanceInDB(PeerNode(name='polari-pol', base_url='https://api.polari-pol.isle', manager=A))
        envs = dict(AS_A, POLARI_TOPOLOGY_PEERS='polari-pol=https://api.polari-pol.isle,https://api.polari.isle,https://api.extra.isle',
                    POLARI_TOPOLOGY_PEERS_FILE=pfile)
        src = _as(envs, P.peer_sources, A)
        by = {s['url']: s for s in src}
        check('sources: agreed + env + file for the same peer, deduplicated by URL',
              by['https://api.polari-pol.isle']['sources'] == ['agreed', 'configured-env', 'configured-file'])
        check('sources: a bare URL names the peer from api.<name>.isle', by['https://api.extra.isle']['name'] == 'extra')
        check('sources: a file entry (trailing slash normalized)', by['https://api.lab.isle']['sources'] == ['configured-file'])
        check('sources: this backend is never its own peer', 'https://api.polari.isle' not in by)
        _env(**dict(AS_A, POLARI_TOPOLOGY_PEERS_FILE='/nonexistent/peers.json'))
        bad = P.peer_sources(A)
        check('sources: an unreadable file is reported in words, the agreed peer still listed',
              any('unreadable' in s.get('error', '') for s in bad) and any(s.get('url') == 'https://api.polari-pol.isle' for s in bad))
    finally:
        os.unlink(pfile)
    # from here on A names B by its agreement row only
    # -- A pulls B
    _env(**AS_A)
    r = P.pull_peers(A, fetch=fetch_from(AS_A))
    p = r['peers'][0]
    check('pull: ok, B created as copies', r['ok'] and p['ok'] and p['instance'] == 'polari-pol' and p['created'], r.get('words'))
    copy = T._find(A, 'InstanceDefinition', 'polari-pol')
    check('pull: B\'s instance is a peer copy on A, filed under A\'s active topology', copy is not None
          and '(tpl-2 peer:polari-pol ' in copy.notes and copy.topology_name == 'polari' and '(tpl-0)' not in copy.notes)
    check('pull: B\'s machine is a copy with source peer:polari-pol', T._find(A, 'PolariNodeMachine', 'pol-core').source == 'peer:polari-pol')
    check('pull: provenance reads copies as peer (tpl-6 never retires them)', R.provenance(A)['InstanceDefinition']['polari-pol']['kind']
          == 'peer' and not any(d['name'] == 'polari-pol' for d in R.plan(A)['retire']))
    shared = [c for c in p['conflicts'] if c['name'] == 'board-engines']
    check('pull: the shared engine worker A already has is KEPT (a conflict with the same values), not overwritten',
          shared and 'same values' in shared[0]['why'] and '(tpl-2' not in T._find(A, 'InstanceDefinition', 'board-engines').notes)
    check('pull: memory == database on A', D._coherent(A, sa))

    # -- the graph labels every row with where it came from (the page marks peer copies and the July example)
    from topology.topology_analysis import graph_payload
    g = _as(AS_A, graph_payload, A, 'polari')
    gi = {r['name']: r['provenance'] for r in g['instances']}
    check('graph: a peer copy is labelled peer, with the peer and when it was pulled', gi['polari-pol']['kind'] == 'peer'
          and gi['polari-pol']['peer'] == 'polari-pol' and gi['polari-pol']['at'].startswith('20'), gi.get('polari-pol'))
    check('graph: this backend\'s own instance is labelled self', gi['polari']['kind'] == 'self')
    check('graph: assignments and machines carry labels too', all('provenance' in r for r in g['assignments'] + g['machines']))
    E = T._manager(); T._seed(E)
    ge = _as(dict(AS_A), graph_payload, E, 'staging-a')
    check('graph: the July snapshot rows are labelled example', {r['provenance']['kind'] for r in ge['instances']} == {'example'})

    # -- no echo: B pulls A; A's description excludes its copies of B, even a B row that names A
    from topology.topology_links import ServiceConnection
    _env(**AS_B)
    sb.saveInstanceInDB(ServiceConnection(name='polari-pol->polari:peer-token', interconnect_key='peer-token', from_kind='prf-backend',
                                          to_kind='prf-backend', from_instance_name='polari-pol', to_instance_name='polari', manager=B))
    _env(**AS_A)
    P.pull_peers(A, fetch=fetch_from(AS_A))
    check('no echo setup: A holds B\'s connection to A as a copy', '(tpl-2 peer:polari-pol' in
          (T._find(A, 'ServiceConnection', 'polari-pol->polari:peer-token').notes or ''))
    dA = _as(AS_A, P.self_description, A)
    check('no echo: a copied row that names A is still not A\'s to publish', 'polari-pol->polari:peer-token' not in
          {x['name'] for x in dA['rows']['ServiceConnection']})
    check('no echo: A\'s self-description carries none of its copies of B', 'polari-pol' not in
          {x['name'] for x in dA['rows']['InstanceDefinition']} and not any('(tpl-2' in str(x.get('notes')) for rows in dA['rows'].values() for x in rows))
    sb.saveInstanceInDB(PeerNode(name='polari', base_url='https://api.polari.isle', manager=B))
    _env(**AS_B)
    rb = P.pull_peers(B, fetch=fetch_from(AS_B))
    check('no echo: B pulls A and gets A, never a copy of itself', rb['ok'] and T._find(B, 'InstanceDefinition', 'polari') is not None
          and '(tpl-2 peer:' not in (T._find(B, 'InstanceDefinition', 'polari-pol').notes or ''))

    # -- B changes: a module goes live, another goes away; A follows at the next pull
    _env(**AS_B)
    from topology.placement_truth import sync_assignment_row
    sync_assignment_row(B, 'instruments', 'enabled', 'selftest')
    gone = T._find(B, 'ModuleAssignment', 'cmod@polari-pol')
    from topology.topology_example_retire import _delete
    _delete(B, 'ModuleAssignment', gone)
    _env(**AS_A)
    r = P.pull_peers(A, fetch=fetch_from(AS_A))
    p = r['peers'][0]
    check('change: B\'s new module appears on A', 'ModuleAssignment:instruments@polari-pol' in p['created'])
    check('change: B\'s removed module is retired on A', 'ModuleAssignment:cmod@polari-pol' in p['retired']
          and T._find(A, 'ModuleAssignment', 'cmod@polari-pol') is None and D._coherent(A, sa))
    r = P.pull_peers(A, fetch=fetch_from(AS_A))
    check('idempotent: a pull with nothing new creates, updates and retires nothing',
          not r['peers'][0]['created'] and not r['peers'][0]['updated'] and not r['peers'][0]['retired'])

    # -- B goes down: copies kept, state says so
    def dead(name, url):
        raise OSError('connection refused')
    before = D._state(A)
    r = P.pull_peers(A, fetch=dead)
    check('dead peer: pull not ok, words say unreachable, copies kept', not r['ok'] and 'unreachable' in r['peers'][0]['words']
          and D._state(A) == before)
    rep = P.peers_report(A)
    rp = rep['peers'][0]
    check('dead peer: the report says failed with the last GOOD pull time and the copy count',
          rp['state'] == 'failed' and rp['pulledAt'] and rp['copies'] > 0, rp)
    os.environ['POLARI_ISLE_EVIDENCE_MAX_AGE_S'] = '1'
    from datetime import datetime, timedelta, timezone
    rep = P.peers_report(A, now=datetime.now(timezone.utc) + timedelta(seconds=30))
    check('stale: a last good pull older than POLARI_ISLE_EVIDENCE_MAX_AGE_S reads stale', rep['peers'][0]['state'] == 'stale')
    os.environ.pop('POLARI_ISLE_EVIDENCE_MAX_AGE_S', None)

    # -- D-tpl2-c: a person's local row with a peer's name is kept
    from topology.topology_basis import InstanceDefinition
    _delete(A, 'InstanceDefinition', T._find(A, 'InstanceDefinition', 'electronics'))      # say a person wrote it first
    sa.saveInstanceInDB(InstanceDefinition(name='electronics', kind='prf', notes='written here by a person', manager=A))
    r = P.pull_peers(A, fetch=fetch_from(AS_A))
    hit = [c for c in r['peers'][0]['conflicts'] if c['name'] == 'electronics']
    check('conflict: a person\'s row named like the peer\'s is kept, reported', hit and 'kept' in hit[0]['why']
          and T._find(A, 'InstanceDefinition', 'electronics').notes == 'written here by a person')

    # -- malformed or hostile descriptions are refused, copies kept
    for label, desc in (('wrong kind', {'kind': 'x', 'rows': {}}), ('claims to be A', dict(dA, kind='polari-topology-self'))):
        snap = D._state(A)
        r = P.pull_peers(A, fetch=lambda n, u, d=desc: json.loads(json.dumps(d)))
        check('refused description (%s): not ok, nothing changed' % label, not r['ok'] and 'refused' in r['peers'][0]['words']
              and D._state(A) == snap)
    hostile = json.loads(json.dumps(_as(AS_B, P.self_description, B)))
    hostile['rows']['InstanceDefinition'].append({'name': 'polari', 'kind': 'prf', 'machine_name': 'evil'})
    _env(**AS_A)
    r = P.pull_peers(A, fetch=lambda n, u: hostile)
    check('a peer row describing THIS backend is ignored, said', T._find(A, 'InstanceDefinition', 'polari').machine_name == 'isle-core'
          and any(c['name'] == 'polari' and 'describes this backend' in c['why'] for c in r['peers'][0]['conflicts']))

    # -- durable first: a refused save leaves no copy in memory
    sa.fail('save', 'ModuleAssignment', 'board@polari-pol', 'false')
    _delete(A, 'ModuleAssignment', T._find(A, 'ModuleAssignment', 'board@polari-pol'))
    r = P.pull_peers(A, fetch=fetch_from(AS_A))
    check('refused save: pull not ok, the problem named, no copy left in memory, memory == database',
          not r['ok'] and any('board@polari-pol' in x for x in r['problems']) and T._find(A, 'ModuleAssignment', 'board@polari-pol') is None
          and D._coherent(A, sa))
    sa.rules.clear()

    # -- tpl-1 takes over a peer's copy of a shared worker (local truth outranks a copy)
    C, sc = _backend(dict(AS_A, CORS_ORIGINS='https://lab.isle', ISLE_HOSTNAME='lab-host'), {'cmod'})
    sc.saveInstanceInDB(PeerNode(name='polari-pol', base_url='https://api.polari-pol.isle', manager=C))
    _env(**dict(AS_A, CORS_ORIGINS='https://lab.isle', ISLE_HOSTNAME='lab-host'))
    P.pull_peers(C, fetch=fetch_from(dict(AS_A, CORS_ORIGINS='https://lab.isle', ISLE_HOSTNAME='lab-host')))
    check('takeover setup: C holds B\'s board-engines worker as a copy', '(tpl-2 peer:polari-pol' in T._find(C, 'InstanceDefinition', 'board-engines').notes)
    from topology.topology_modules import EngineProviderBinding
    EngineProviderBinding(name='board', url='https://board-engines.isle', manager=C)
    S.describe_links(C, {'cmod'}, 'selftest', fetch=lambda u: {})
    w = T._find(C, 'InstanceDefinition', 'board-engines')
    check('takeover: C binds the same engine; its tpl-1 pass makes the worker row its own', '(tpl-1)' in w.notes and '(tpl-2' not in w.notes)

    # -- the change signal: digest, cheap checks, nudges, the loop step, the wake hook
    _env(**AS_A)
    sa.rules.clear()
    P.pull_peers(A, fetch=fetch_from(AS_A))
    d1, d2 = _as(AS_B, P.self_digest, B), _as(AS_B, P.self_digest, B)
    check('digest: stable while nothing changes, and equals the description\'s', d1['digest'] == d2['digest']
          == _as(AS_B, P.self_description, B)['digest'] and d1['kind'] == 'polari-topology-self-digest')
    _env(**AS_A)
    del calls[:]
    c = P.check_peers(A, fetch=fetch_from(AS_A))
    check('check: nothing changed -> only the digest was fetched, no pull', not c['changed'] and c['pulled'] is None
          and calls and all(u.endswith('/self/digest') for u in calls), calls)
    _env(**AS_B)
    sb.saveInstanceInDB(T._find(B, 'InstanceDefinition', 'polari-pol'))
    sync_assignment_row(B, 'scope', 'enabled', 'selftest')
    check('digest: changes when B changes', _as(AS_B, P.self_digest, B)['digest'] != d1['digest'])
    _env(**AS_A)
    del calls[:]
    c = P.check_peers(A, fetch=fetch_from(AS_A))
    check('check: B changed -> B pulled, the new module is here', c['changed'] == ['https://api.polari-pol.isle'] and c['pulled']['ok']
          and T._find(A, 'ModuleAssignment', 'scope@polari-pol') is not None and any(u.endswith('/api/topology/self') for u in calls))
    c = P.check_peers(A, fetch=lambda n, u: {'title': '404 Not Found'})
    check('check: an older backend without the digest door is said, nothing pulled', 'no digest door' in c['words'] and not c['changed'])

    from datetime import datetime, timedelta, timezone
    r = P.nudge(A, 'stranger', fetch=fetch_from(AS_A))
    check('nudge: from a backend this one does not name -> nothing pulled', not r['ok'] and r['pulled'] is None)
    later = datetime.now(timezone.utc) + timedelta(seconds=10)
    r = P.nudge(A, 'polari-pol', fetch=fetch_from(AS_A), now=later)
    check('nudge: from a named peer -> pulled now', r['ok'] and r['pulled'] and r['pulled']['peers'])
    r = P.nudge(A, 'polari-pol', fetch=fetch_from(AS_A), now=datetime.now(timezone.utc))
    check('nudge: again within NUDGE_MIN_S -> not pulled twice', r['ok'] and r['pulled'] is None and 'less than' in r['words'])

    sent = []
    out = P.notify_peers(A, send=lambda n, u, b: sent.append((u, b)))
    check('notify: each named peer gets POST .../peers/nudge {"from": this instance}', sent ==
          [('https://api.polari-pol.isle/api/topology/peers/nudge', {'from': 'polari'})] and out == ['polari-pol nudged'])

    state, sent = {'own': None, 'full': None}, []
    send = lambda n, u, b: sent.append(u)
    t1 = P.tick(A, state, fetch=fetch_from(AS_A), send=send, now=1000.0)
    check('tick 1: a full pull, own digest recorded, nobody notified', 'pull' in t1 and 'notified' not in t1 and state['own'])
    t2 = P.tick(A, state, fetch=fetch_from(AS_A), send=send, now=1015.0)
    check('tick 2: a cheap check, nothing changed', 'check' in t2 and not t2['check']['changed'] and not sent)
    _env(**AS_A)
    P._WAKE.clear()
    sync_assignment_row(A, 'instruments', 'enabled', 'selftest')
    check('wake: a module going live here wakes the loop at once', P._WAKE.is_set())
    t3 = P.tick(A, state, fetch=fetch_from(AS_A), send=send, now=1016.0)
    check('tick 3: own change -> peers nudged', t3.get('notified') == ['polari-pol nudged'] and sent)
    t4 = P.tick(A, state, fetch=fetch_from(AS_A), send=send, now=1000.0 + 300)
    check('tick at PULL_S: a full pull again (recovers anything a check missed)', 'pull' in t4)
    _env(**dict(AS_A, POLARI_TOPOLOGY_PEER_CHECK_S='0'))
    t5 = P.tick(A, state, fetch=fetch_from(AS_A), send=send, now=1000.0 + 301)
    check('CHECK_S=0: no cheap checks between full pulls', 'check' not in t5 and 'pull' not in t5)
    _env(**AS_A)

    # -- the default transport is the outbound seam, kind peer, no TLS override
    import polariApiServer.outbound as OB
    seen = {}
    real = OB.http_request

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({'kind': 'x'}).encode()

    def fake(kind, name, method, url, **kw):
        seen.update(kind=kind, name=name, method=method, url=url, kw=kw)
        return _Resp()
    OB.http_request = fake
    try:
        P._default_fetch('polari-pol', 'https://api.polari-pol.isle/api/topology/self')
    finally:
        OB.http_request = real
    check('transport: outbound.http_request kind peer, GET, the peer\'s /api/topology/self', seen.get('kind') == 'peer'
          and seen.get('method') == 'GET' and seen.get('url', '').endswith('/api/topology/self'))
    check('transport: no TLS context of its own (the shared policy decides; verified by default)', 'context' not in seen.get('kw', {}))

    # -- the timer
    _env(POLARI_TOPOLOGY_PEER_PULL_S='0')
    check('timer: POLARI_TOPOLOGY_PEER_PULL_S=0 starts nothing', 'off' in P.start_peer_puller(A))
    _env()
    passed = sum(_results)
    print('\n%d/%d passed' % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
