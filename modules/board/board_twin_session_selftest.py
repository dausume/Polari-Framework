"""board_twin_session_selftest - sim-0 / sim-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md section 8): twin SESSIONS.

OFFLINE half (always runs): the TwinSession class and its registration, the derived token, the worker resolution in words, the backend (start / inject /
events fan-out / stop / reaped-on-the-worker) against a FAKE worker + FAKE twin control port (custom.twin_session_fakes.py), the doors on a real falcon.App
(including the SSE stream), the CLI's request shapes, and the Hardware System participant.

LIVE half (runs when a worker that lists sessions is reachable: BOARD_ENGINES_URL, else the topology provider; SKIPPED in words otherwise): the REAL twin on the
REAL worker - start uno-light, press the button (PD2 0 then 1, 60 ms of wall time apart = ~960 000 cycles at 16 MHz, past the 30 ms debounce), see PD6 rise on the
events stream and the USART report say source=button (decoded with board.custom.light_twin.decode), hold ADC0 at 1200 mV and read it in the next status, pause and
resume, and see an abandoned session reaped at its TTL. Every session this file starts is stopped in a finally block.

    PYTHONPATH=.:modules python3 -m board.board_twin_session_selftest      # from polari-framework/ (standalone: both halves)
    (board.board_selftest calls run_twin_session(check, live=False): the offline half)
"""
import contextlib
import hashlib
import json
import os
import socket
import tempfile
import time
import types

HEX = b':020000040000FA\n:00000001FF\n'


@contextlib.contextmanager
def _env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    os.environ.update({k: v for k, v in kv.items() if v is not None})
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _mgr():
    return types.SimpleNamespace(objectTables={}, db=None, idList=[])


def run_twin_session(check, live=True):
    with tempfile.TemporaryDirectory(prefix='twin-session-test-') as td, _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret'), POLARI_TWIN_TOKEN_SECRET=None):
        offline(check)
        if live:
            live_half(check)


# ---------------------------------------------------------------------------------------------------------------- offline
def offline(check):
    from board.board_basis import BOARD_CLASSES, TwinSession
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import board_engines as be, twin_sessions as TS, twin_token as TT, twin_ctl_hub as HUB
    from board.custom.twin_session_fakes import FakeWorker

    check('sim-1: TwinSession is a BOARD_CLASSES member with plain_words, seeded with no rows (observed, never seeded)',
          TwinSession in BOARD_CLASSES and TwinSession.plain_words and [r for n, _c, r in BOARD_SEED_PAIRS if n == 'TwinSession'] == [[]])
    a, b = TT.derive('uno-light-aaaaaa'), TT.derive('uno-light-bbbbbb')
    check('sim-1: the control token is derived (HMAC of the server secret and the name): stable, 32 hex, different per session, kept in a 0600 file',
          a == TT.derive('uno-light-aaaaaa') and a != b and len(a) == 32 and int(a, 16) >= 0
          and oct(os.stat(os.environ['POLARI_TWIN_TOKEN_FILE']).st_mode & 0o777) == '0o600')

    old, new = FakeWorker(sessions=False), FakeWorker(sessions=True)
    try:
        with _env(BOARD_ENGINES_URL=old.url):
            r = be.resolve_sessions()
        check('sim-0: a worker without /sessions (an older image) is REFUSED in words, never silently skipped: %s' % r['why'][:110],
              r['how'] == 'refused' and 'does not list sessions' in r['why'] and 'roll the board-engines service' in r['why'])
        with _env(BOARD_ENGINES_URL='http://127.0.0.1:9'):
            r = be.resolve_sessions()
        check('sim-0: an unreachable declared worker is a refusal naming the knob (no fallback to local)', r['how'] == 'refused' and 'unreachable' in r['why'] and 'BOARD_ENGINES_URL' in r['why'])
        with _env(BOARD_ENGINES_URL=None):
            r = be.resolve_sessions()
        check('sim-0: with no knob and no topology provider the refusal says what to set', r['how'] == 'refused' and 'no worker lists twin sessions' in r['why'])
        # ti-3a: an isle-app deploy (`--engine board`) writes an EngineProviderBinding row; it is the row form of the knob
        from topology import provider_registry as PR
        prev_mgr = getattr(PR, 'MANAGER', None)
        PR.MANAGER = types.SimpleNamespace(objectTables={'EngineProviderBinding': {'1': types.SimpleNamespace(name='board', url=new.url + '/')}})
        try:
            with _env(BOARD_ENGINES_URL=None):
                r = be.resolve_sessions()
                bound = be.topology_url('avr')
            check('ti-3a: with no knob, a binding row for family board resolves to its URL (trailing slash stripped) and the sessions door uses it',
                  bound == new.url and r['how'] == 'remote' and r['where'] == new.url, (bound, r))
            with _env(BOARD_ENGINES_URL='http://127.0.0.1:9'):
                r = be.resolve_sessions()
            check('ti-3a: a set knob still wins over a binding row (unreachable knob = refusal, never the bound worker)',
                  r['how'] == 'refused' and 'unreachable' in r['why'] and r['where'] == 'http://127.0.0.1:9', r)
            check('ti-3a: the esp family reads its own row (esp), not the board row', be.topology_url('esp') != new.url)
        finally:
            PR.MANAGER = prev_mgr
        mgr = _mgr()
        with _env(BOARD_ENGINES_URL=old.url):
            try:
                TS.start(mgr, 'uno-light', hex_bytes=HEX)
                why, st = '', 0
            except TS.SessionRefused as e:
                why, st = str(e), e.status
        check('sim-1: start against a worker that lists no sessions refuses in words (HTTP 424, never a 503 the proxy masks) and writes no row', st == 424 and 'does not list sessions' in why and not TS._rows(mgr))

        with _env(BOARD_ENGINES_URL=new.url):
            _backend(check, mgr, new, TS, HUB)
            _doors(check, mgr, new, TS)
    finally:
        for s in list(TS._rows(mgr)):
            if s.state == 'running':
                with _env(BOARD_ENGINES_URL=new.url):
                    TS.stop(mgr, s.name)
        old.close()
        new.close()
        TS.HUBS.clear()


def _backend(check, mgr, worker, TS, HUB):
    v = TS.start(mgr, 'uno-light', ttl_s=120, owner='tester', hex_bytes=HEX)
    sha = hashlib.sha256(HEX).hexdigest()
    check('sim-1: start -> a running TwinSession row: participant twin:arduino-uno-r3#0, the LOCKED firmware sha256 %s, ports from the worker, a token shown ONCE (and in no row)'
          % sha[:12], v['state'] == 'running' and v['participant'] == 'twin:arduino-uno-r3#0' and v['firmware'] == {'sha256': sha, 'bytes': len(HEX), 'locked': True, 'config': 'uno-light'}
          and v['ctl_port'] and len(v['token']) == 32 and v['token'] not in json.dumps(TS.one(mgr, v['name'])) and v['token'] not in json.dumps([vars(r) for r in TS._rows(mgr)], default=str))
    sent = worker.twins and next(iter(worker.twins.values()))['body']
    check('sim-1: the worker was asked with the hex (base64), the derived token and the ttl; the token it was given is the one derived for this name',
          sent['token'] == v['token'] == __import__('board.custom.twin_token', fromlist=['x']).derive(v['name']) and sent['ttl_s'] == 120 and sent['owner'] == 'tester')
    v2 = TS.start(mgr, 'uno-light', ttl_s=60, hex_bytes=HEX)
    check('sim-1: a second session of the same board is twin:arduino-uno-r3#1 (the lowest free index among the RUNNING ones)', v2['participant'] == 'twin:arduino-uno-r3#1')
    name = v['name']
    sub, sub2 = TS.events(mgr, name), TS.events(mgr, name)
    r = TS.inject(mgr, name, {'set': 'PD2', 'level': 1})
    evs = [sub.get(2), sub.get(2)]
    evs2 = [sub2.get(2), sub2.get(2)]
    check('sim-1: inject set PD2 1 -> the twin acks with its cycle; the watched pins\' edges are FANNED OUT to every subscriber (PD2, then PD6 rising)',
          r['ok'] and r['reply']['t'] == 'ack' and r['reply']['cycle'] > 0 and [(e['pin'], e['level']) for e in evs] == [('PD2', 1), ('PD6', 1)] == [(e['pin'], e['level']) for e in evs2],
          (r, evs))
    r = TS.inject(mgr, name, {'set': 'PX9', 'level': 1})
    check('sim-1: a bad pin comes back as the twin\'s words, ok false: %s' % r['reply'].get('why'), not r['ok'] and r['reply']['why'] == 'PX9 is not a pin of atmega328p')
    r = TS.inject(mgr, name, {'adc': 0, 'mv': 1200})
    st = TS.inject(mgr, name, {'status': 1})
    check('sim-1: inject adc 0 1200 is acked and the next status says adc0_mv 1200', r['ok'] and st['reply']['adc0_mv'] == 1200 and json.loads(TS._find(mgr, name).last_status_json)['adc0_mv'] == 1200)
    r = TS.inject(mgr, name, {'reset': 1})
    check('sim-1: inject reset -> acked at cycle 0', r['ok'] and r['reply'] == {'t': 'ack', 'of': 'reset', 'cycle': 0})
    bad = []
    for body in ({}, {'set': 'PD2'}, {'set': 'PD2', 'level': 7}, {'adc': 'x', 'mv': 1}, {'watch': 'PD6'}, {'nonsense': 1}):
        try:
            TS.inject(mgr, name, body)
            bad.append(body)
        except TS.SessionRefused as e:
            if e.status != 400:
                bad.append(body)
    check('sim-1: malformed injects are refused in words with HTTP 400 (6 shapes)', not bad, bad)
    s = HUB.Subscription(types.SimpleNamespace(unsubscribe=lambda s: None))
    for i in range(HUB.QUEUE_MAX + 25):
        s.put({'t': 'pin', 'i': i})
    first = s.get(0.1)
    check('sim-1: a slow subscriber is BOUNDED: its queue keeps %d, it is told how many it lost (%s) and the others are unaffected' % (HUB.QUEUE_MAX, first),
          first == {'t': 'lost', 'events': 25} and s.get(0.1)['i'] == 25)
    sub.close()
    sub2.close()
    del worker.twins[next(k for k, t in worker.twins.items() if t['body']['ttl_s'] == 60)]   # the worker reaped session #1 at its TTL
    listed = {x['name']: x for x in TS.listing(mgr)}
    check('sim-1: a session the worker no longer has is marked ENDED with the reason in words (never left "running")',
          listed[v2['name']]['state'] == 'ended' and 'reaped at its TTL' in listed[v2['name']]['end_reason'] and listed[name]['state'] == 'running')
    check('sim-1: the Hardware System lists only RUNNING sessions as participants (twin:arduino-uno-r3#0)',
          [p['variant'] for p in TS.participants(mgr)] == ['twin:arduino-uno-r3#0'] and TS.participants(mgr)[0]['ref'] == 'TwinSession:%s' % name)
    out = TS.stop(mgr, name)
    check('sim-1: stop -> the worker got DELETE, the row is ended, the connection closed; inject afterwards is refused with 409 in words',
          out['state'] == 'ended' and ('DELETE', '/sessions/%s' % TS._find(mgr, name).worker_session) in worker.requests and name not in TS.HUBS and _refused(TS, mgr, name, 409))


def _refused(TS, mgr, name, status):
    try:
        TS.inject(mgr, name, {'status': 1})
    except TS.SessionRefused as e:
        return e.status == status and 'has ended' in str(e)
    return False


def _doors(check, mgr, worker, TS):
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    server = types.SimpleNamespace(falconServer=falcon.App(), manager=mgr)
    real_build = TS.build_hex
    TS.build_hex = lambda config: (HEX, hashlib.sha256(HEX).hexdigest())
    try:
        with contextlib.redirect_stdout(open(os.devnull, 'w')):
            construct_board_endpoints(server)
        cl = ft.TestClient(server.falconServer)
        post = cl.simulate_post('/api/board/twins', json={'config': 'uno-light', 'ttl_s': 90, 'owner': 'door'})
        name = post.json['name']
        lst = cl.simulate_get('/api/board/twins').json
        one = cl.simulate_get('/api/board/twins/%s' % name).json
        check('sim-1 DOORS: POST /api/board/twins -> 201 with the token once; GET lists (rows, count) and shows one; the routes ADD next to every existing /api/board route',
              post.status_code == 201 and len(post.json['token']) == 32 and lst['ok'] and lst['count'] >= 1 and one['ok'] and one['firmware']['locked'] and 'token' not in one)
        inj = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'PD2', 'level': 1})
        bad = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'PX9', 'level': 1})
        check('sim-1 DOORS: POST .../inject -> 200 with the twin\'s ack; a pin the chip does not have -> 409 with the twin\'s words', inj.status_code == 200 and inj.json['reply']['t'] == 'ack'
              and bad.status_code == 409 and 'not a pin' in bad.json['reply']['why'])
        sse = cl.simulate_get('/api/board/twins/%s/events?replay=10&limit=2&seconds=5' % name)
        datas = [json.loads(ln[5:]) for ln in sse.text.splitlines() if ln.startswith('data:')]
        check('sim-1 DOORS: GET .../events is text/event-stream: hello, then the replayed pin edges (PD2 1, PD6 1), ends at ?limit', sse.headers['content-type'].startswith('text/event-stream')
              and datas[0]['t'] == 'hello' and [(d['pin'], d['level']) for d in datas[1:]] == [('PD2', 1), ('PD6', 1)])
        e400 = cl.simulate_post('/api/board/twins', json={}).status_code
        e404 = [cl.simulate_get('/api/board/twins/nope').status_code, cl.simulate_post('/api/board/twins/nope/inject', json={'status': 1}).status_code,
                cl.simulate_get('/api/board/twins/nope/events').status_code, cl.simulate_delete('/api/board/twins/nope').status_code]
        old_pin = cl.simulate_get('/api/board/arduino-uno-r3/pin-roles').status_code
        check('sim-1 DOORS: no config -> 400 in words; an unknown session -> 404 on all four doors; the existing /api/board/{board}/pin-roles door still answers (%s)' % old_pin,
              e400 == 400 and e404 == [404, 404, 404, 404] and old_pin == 200)
        gone = cl.simulate_delete('/api/board/twins/%s' % name)
        after = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'status': 1})
        check('sim-1 DOORS: DELETE stops it; inject afterwards is 409 "has ended"', gone.status_code == 200 and gone.json['state'] == 'ended' and after.status_code == 409 and 'has ended' in after.json['error'])
    finally:
        TS.build_hex = real_build
    from board.custom import twin_sessions_cli as CLI
    check('sim-1 CLI: inject words become the request bodies (set PD2 0 / adc 0 750 / reset / watch / run / status) and a wrong shape is refused',
          [CLI._inject_body(w) for w in (['set', 'PD2', '0'], ['adc', '0', '750'], ['reset'], ['watch', 'PD6,PB5'], ['run', 'false'], ['status'])]
          == [{'set': 'PD2', 'level': 0}, {'adc': 0, 'mv': 750}, {'reset': 1}, {'watch': ['PD6', 'PB5']}, {'run': False}, {'status': 1}]
          and all(_raises(CLI._inject_body, w) for w in (['set', 'PD2', '2'], ['adc', '0'], ['run', 'maybe'], [])))


def _raises(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


# ---------------------------------------------------------------------------------------------------------------- live
def _tcp_read(host, port, seconds):
    s = socket.create_connection((host, port), timeout=5)
    s.settimeout(0.2)
    data, end = b'', time.time() + seconds
    while time.time() < end:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            pass
    s.close()
    return data


def live_half(check):
    from board.custom import board_engines as be, twin_sessions as TS, light_twin as LT
    where = be.resolve_sessions()
    if where['how'] != be.REMOTE:
        check('sim-0 live: SKIPPED - no engines worker that lists sessions is reachable here (%s)' % where['why'][:150], True)
        return
    mgr = _mgr()
    started = []
    try:
        t0 = time.time()
        hexb, _sha = TS.build_hex('uno-light')   # the shipped pipeline once; both starts below load these exact bytes
        built_s = time.time() - t0
        t0 = time.time()
        v = TS.start(mgr, 'uno-light', ttl_s=300, owner='selftest', hex_bytes=hexb)
        started.append(v['name'])
        up_s = time.time() - t0
        host, name = v['host'], v['name']
        check('sim-0 live: started uno-light on %s (build %.1f s; POST to ready %.2f s): %s, firmware sha256 %s locked, tcp :%s ctl :%s' % (where['why'], built_s, up_s, v['participant'], v['firmware']['sha256'][:12], v['tcp_port'], v['ctl_port']),
              v['state'] == 'running' and v['firmware']['locked'] and v['tcp_port'] and v['ctl_port'] and v['firmware']['bytes'] > 1000)
        # the report: attach to the USART port FIRST (bytes are dropped with nobody attached), then press
        import threading
        got = {}
        reader = threading.Thread(target=lambda: got.update(data=_tcp_read(host, v['tcp_port'], 4.0)), daemon=True)
        reader.start()
        sub = TS.events(mgr, name)
        time.sleep(0.8)
        a = TS.inject(mgr, name, {'set': 'PD2', 'level': 0})
        time.sleep(0.06)
        b = TS.inject(mgr, name, {'set': 'PD2', 'level': 1})
        cycles = b['reply'].get('cycle', 0) - a['reply'].get('cycle', 0)
        pd6 = None
        end = time.time() + 3.0
        while time.time() < end and pd6 is None:
            ev = sub.get(0.3)
            if ev and ev.get('t') == 'pin' and ev['pin'] == 'PD6' and ev['level'] == 1:
                pd6 = ev
        check('sim-0 live: inject set PD2 0 then 1, %d cycles apart (%.1f ms of sim time; >= the 30 ms debounce = 480 000 cycles) -> the events stream shows PD6 rising at cycle %s'
              % (cycles, cycles / 16000.0, pd6 and pd6['cycle']), a['ok'] and b['ok'] and cycles >= 480000 and pd6 is not None, (a, b))
        reader.join(6)
        frames, bad = LT.decode(got.get('data', b''))
        last = frames[-1] if frames else {}
        check('sim-0 live: the USART report (%d bytes, %d frames, decoded by the LightState reference decoder) says led_on=%s toggles=%s source=%s' % (len(got.get('data', b'')), len(frames), last.get('led_on'), last.get('toggles'), last.get('source')),
              bool(frames) and bad == 0 and last.get('source') == 'button' and last.get('led_on') is True and last.get('toggles') == 1, last)
        TS.inject(mgr, name, {'adc': 0, 'mv': 1200})
        st = TS.inject(mgr, name, {'status': 1})['reply']
        check('sim-0 live: inject adc 0 1200 -> the next status says adc0_mv %s, adc_mv %s' % (st.get('adc0_mv'), st.get('adc_mv')), st.get('adc0_mv') == 1200 and (st.get('adc_mv') or [0])[0] == 1200, st)
        TS.inject(mgr, name, {'run': False})
        c1 = TS.inject(mgr, name, {'status': 1})['reply']
        time.sleep(0.5)
        c2 = TS.inject(mgr, name, {'status': 1})['reply']
        TS.inject(mgr, name, {'run': True})
        time.sleep(0.5)
        c3 = TS.inject(mgr, name, {'status': 1})['reply']
        check('sim-0 live: run false pauses stepping (cycle %d -> %d over 0.5 s), run true resumes (-> %d)' % (c1['cycle'], c2['cycle'], c3['cycle']),
              c1['paused'] == 1 and c2['cycle'] == c1['cycle'] and c3['paused'] == 0 and c3['cycle'] > c2['cycle'])
        rst = TS.inject(mgr, name, {'reset': 1})
        check('sim-0 live: inject reset is acked (avr_reset at cycle %s)' % rst['reply'].get('cycle'), rst['ok'] and rst['reply'].get('of') == 'reset')
        sub.close()
        refused = TS.inject(mgr, name, {'set': 'PX9', 'level': 1})
        check('sim-0 live: a pin the chip does not have is refused in the twin\'s words: %s' % refused['reply'].get('why'), not refused['ok'] and 'PX9 is not a pin of atmega328p' in refused['reply']['why'])
        # a second client on the control port is refused (one at a time)
        c = socket.create_connection((host, v['ctl_port']), timeout=3)
        c.settimeout(3)
        second = c.recv(512).decode()
        c.close()
        check('sim-0 live: a SECOND control client is refused in words while one is attached: %s' % second.strip()[:90], 'another control client is attached' in second)
        # a wrong token is refused and hung up (a fresh port: stop the backend hub first)
        TS.HUBS.pop(name).close('selftest: probing the token')
        time.sleep(0.4)
        c = socket.create_connection((host, v['ctl_port']), timeout=3)
        c.sendall(b'{"token":"wrong-token-value"}\n')
        c.settimeout(3)
        why = c.recv(512).decode()
        c.close()
        check('sim-0 live: a wrong token is refused and the connection closed: %s' % why.strip()[:80], 'the token is wrong' in why)
        # an abandoned session is reaped at its TTL (10 s is the worker's floor); nothing stops it
        short = TS.start(mgr, 'uno-light', ttl_s=10, owner='selftest-abandoned', hex_bytes=hexb)
        started.append(short['name'])
        time.sleep(22)
        gone = TS.one(mgr, short['name'])
        listing = [s['id'] for s in __import__('board.custom.twin_session_worker', fromlist=['x']).listing(where['where'])['sessions'] if s['state'] == 'running']
        check('sim-0 live: the abandoned 10 s session was reaped by the worker (%s); the worker lists no running session of ours but the first' % gone['end_reason'],
              gone['state'] == 'ended' and short['worker_session'] not in listing)
    finally:
        for n in started:
            with contextlib.suppress(Exception):
                TS.stop(mgr, n)
        TS.HUBS.clear()
        left = [s for s in __import__('board.custom.twin_session_worker', fromlist=['x']).listing(where['where'])['sessions'] if s['state'] == 'running' and s['owner'].startswith('selftest')]
        check('sim-0 live: no twin process of this test is left on the worker (stop + reaper)', not left, left)


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_twin_session(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
