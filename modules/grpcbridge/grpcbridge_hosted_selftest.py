"""grpcbridge_hosted_selftest - brg-0 / sim-2 (HARDWARE_BENCH_CONVERGENCE_PLAN.md sections 3, 4): the generated bridge's TcpDevicePort and the HOSTED bridge.

OFFLINE half (always runs; no worker, no docker): HostedBridge registration; the engines seam in words; the REAL worker logic (prf-bridge-engines/bridge_hosted.py)
with fake mvn / java (custom.hosted_checks); brg-0 on the JVM - the generated uno-light core run with source=twin-tcp against a fake USART port, the proof being the
LightState frames it decoded (custom.hosted_checks, skipped in words without a JDK); the backend (start / list / logs / stop / an ended session ends its bridge)
against fakes of both workers; the doors on a falcon.App over real HTTP; `pol grpc hosted` (hosted_cli) against them.

LIVE half (runs when BOARD_ENGINES_URL and BRIDGE_ENGINES_URL name workers that answer; SKIPPED in words otherwise): a REAL uno-light session, a REAL hosted bridge
beside it in log-only mode, a press injected on PD2, and the bridge's own log shows the LightState it decoded (led_on, toggles=1, source button).

BOTH-DIRECTIONS proof against a Polari server (runs when HOSTED_PROOF_API names one - the test node; skipped in words otherwise): start a session, a hosted bridge
pointed at that server, press (PD2 0 then 1) and read the server's LightState row `uno-light` (led_on, toggles=1, source=button) within 2 s; then run
`light-toggle` on the server and see the twin's PD6 fall on the events stream and the next report say source=command. Everything it starts is stopped in a finally.

    PYTHONPATH=.:modules python3 -m grpcbridge.grpcbridge_hosted_selftest      # from polari-framework/
    (pol modules selftest grpcbridge runs it; `pol deploy selftest isle-core --ref dev-brg-0 --modules grpcbridge.grpcbridge_hosted_selftest`)
"""
import contextlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import types
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

HEX = b':020000040000FA\n:00000001FF\n'
_results, _skips = [], []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(('PASS: ' if cond else 'FAIL: ') + label + ('' if cond else '  -> ' + str(extra)))


def skip(label, why):
    _skips.append(label)
    print('SKIP: %s - %s' % (label, why))


@contextlib.contextmanager
def _env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
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


# ---------------------------------------------------------------------------------------------------------------- offline
def offline():
    from grpcbridge.custom import bridge_engines as be, hosted_bridges as HB, hosted_checks as HC
    from grpcbridge.custom.hosted_fakes import FakeBridgeWorker
    from board.custom import twin_sessions as TS
    from board.custom.twin_session_fakes import FakeWorker

    _registration(check)
    old, new = FakeBridgeWorker(bridges=False), FakeBridgeWorker()
    try:
        with _env(BRIDGE_ENGINES_URL=old.url):
            be.forget()
            r = be.resolve()
        check('sim-2: a worker that does not host bridges (an older image) is REFUSED in words naming the image', r['how'] == 'refused' and 'does not host bridges' in r['why'] and 'prf-bridge-engines' in r['why'])
        with _env(BRIDGE_ENGINES_URL='http://127.0.0.1:9'):
            be.forget()
            r = be.resolve()
        check('sim-2: an unreachable declared worker is a refusal naming the knob (never a silent fallback)', r['how'] == 'refused' and 'unreachable' in r['why'] and 'BRIDGE_ENGINES_URL' in r['why'])
        with _env(BRIDGE_ENGINES_URL=None):
            be.forget()
            r = be.resolve()
        check('sim-2: with no knob and no topology provider the refusal names the knob, the image and `pol allocate grpcbridge.engines`', r['how'] == 'refused'
              and 'BRIDGE_ENGINES_URL' in r['why'] and 'pol allocate grpcbridge.engines' in r['why'])
        with _env(BRIDGE_ENGINES_URL=new.url):
            be.forget()
            r = be.resolve()
        check('sim-2: a worker that hosts bridges resolves (the knob)', r['how'] == 'remote' and r['where'] == new.url)

        HC.worker_logic(check, skip)
        HC.jvm_twin_mode(check, skip)

        with tempfile.TemporaryDirectory(prefix='hosted-selftest-') as td, _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret'), POLARI_TWIN_TOKEN_SECRET=None):
            board = FakeWorker(sessions=True)
            mgr = _mgr()
            try:
                with _env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=new.url):
                    be.forget()
                    _backend(mgr, TS, HB, new, board)
                    _doors(mgr, TS, new)
            finally:
                for s in list(TS._rows(mgr)):
                    if s.state == 'running':
                        with _env(BOARD_ENGINES_URL=board.url):
                            TS.stop(mgr, s.name)
                TS.HUBS.clear()
                board.close()
    finally:
        old.close()
        new.close()


def _registration(check):
    here = os.path.dirname(os.path.abspath(__file__))
    fw = os.path.normpath(os.path.join(here, '..', '..'))
    app = json.load(open(os.path.join(here, 'polari-app.json')))
    from grpcbridge.hosted_basis import HostedBridge
    check('sim-2: HostedBridge is a row class with plain_words, registered in the module manifest (object, basis, doors, custom, selftest) and in the server', HostedBridge.plain_words
          and 'objects/hosted/HostedBridge' in app['files']['objects'] and 'hosted_basis' in app['files']['basis'] and 'hosted_bridges_api' in app['files']['api']
          and {'custom/bridge_engines', 'custom/hosted_bridges', 'custom/hosted_worker', 'custom/hosted_cli', 'custom/hosted_fakes', 'custom/hosted_checks', 'custom/hosted_proof'} <= set(app['files']['custom'])
          and 'grpcbridge_hosted_selftest' in app['selftests'] and 'HostedBridge' in app['classes']
          and "'HostedBridge'" in open(os.path.join(fw, 'polariApiServer', 'feature_imports.py')).read()
          and 'HostedBridge' in open(os.path.join(fw, 'polariApiServer', 'polariServer.py')).read()
          and 'HostedBridgesAPI' in open(os.path.join(fw, 'polariApiServer', 'module_endpoints.py')).read())
    from topology import provider_registry as PR
    check('sim-2: the topology knows the worker - PROVIDER_PORTS prf-bridge-engines:9870, the engine module grpcbridge.engines resolves to it', PR.PROVIDER_PORTS.get('prf-bridge-engines') == 9870
          and 'grpcbridge.engines' in open(os.path.join(fw, 'modules', 'resources', 'custom', 'profile_analysis.py')).read())


def _backend(mgr, TS, HB, bworker, board):
    ts = TS.start(mgr, 'uno-light', ttl_s=300, owner='tester', hex_bytes=HEX)
    try:
        HB.start(mgr, 'no-such-session')
        why = ''
    except HB.HostedRefused as e:
        why, st = str(e), e.status
    check('sim-2: start for an unknown session is refused in words (404), no row', 'no twin session' in why and st == 404 and not HB._rows(mgr))
    v = HB.start(mgr, ts['name'], api_host='https://testnode.example:8443/', owner='tester')
    sent = bworker.items[v['worker_bridge']]['body']
    check('sim-2: start -> a HostedBridge row beside the session; the worker got the session\'s host + USART port, the generated project (pom, TcpDevicePort, bridge.properties), '
          'and the gRPC target derived from the host asked (testnode.example:3002, the demo bundle\'s derivation)', v['state'] == 'running' and v['session'] == ts['name']
          and sent['twin_host'] == ts['host'] and sent['twin_port'] == ts['tcp_port'] and 'src/main/java/org/polari/bridge/TcpDevicePort.java' in sent['files'] and 'pom.xml' in sent['files']
          and sent['grpc_target'] == 'testnode.example:3002' and v['grpc'] and 'twin.port=' in sent['files']['bridge.properties'], str(v)[:300])
    check('sim-2: the project comes from the code-owned uno-light rows when the server has none, and says so', 'code-owned rows' in v['project_source'], v.get('project_source'))
    v2 = HB.start(mgr, ts['name'], grpc_target_='other.example:4000')
    v3 = HB.start(mgr, ts['name'], log_only=True, api_host='ignored.example')
    check('sim-2: an explicit grpc_target wins; log_only sends none (the bridge only logs what it decodes)', bworker.items[v2['worker_bridge']]['body']['grpc_target'] == 'other.example:4000'
          and bworker.items[v3['worker_bridge']]['body']['grpc_target'] == '' and not v3['grpc'])
    try:
        HB.start(mgr, ts['name'], bridge_name='nonesuch')
        why = ''
    except HB.HostedRefused as e:
        why, st = str(e), e.status
    check('sim-2: an unknown bridge is refused in words (404)', 'no bridge' in why and st == 404)
    check('sim-2: the bridge row\'s ttl follows the session\'s remaining time (<= 300 s), listing shows three, the view carries no files',
          0 < v['ttl_s'] <= 300 and len(HB.listing(mgr)) == 3 and 'files' not in json.dumps(HB.listing(mgr)))
    out = HB.logs(mgr, v['name'], tail=5)
    check('sim-2: logs come from the worker', out['ok'] and any('twin-tcp' in ln for ln in out['lines']))
    s = HB.stop(mgr, v2['name'])
    check('sim-2: stop -> the worker is told (DELETE), the row is ended', s['state'] == 'ended' and v2['worker_bridge'] not in bworker.items and ('DELETE', '/bridges/%s' % v2['worker_bridge']) in bworker.requests)
    TS.stop(mgr, ts['name'])
    ls = {b['name']: b for b in HB.listing(mgr)}
    check('sim-2: when the SESSION ends, its bridges end with it (the next look stops them on the worker and says why)', ls[v['name']]['state'] == 'ended'
          and 'session' in ls[v['name']]['end_reason'] and ls[v3['name']]['state'] == 'ended' and not bworker.items)
    try:
        HB.start(mgr, ts['name'])
        why = ''
    except HB.HostedRefused as e:
        why, st = str(e), e.status
    check('sim-2: a bridge for an ended session is refused (409)', st == 409 and 'has ended' in why)


class _Quiet(WSGIRequestHandler):
    def log_message(self, *a):
        pass


def _doors(mgr, TS, bworker):
    import falcon
    from grpcbridge.hosted_bridges_api import HostedBridgesAPI
    ts = TS.start(mgr, 'uno-light', ttl_s=300, owner='tester', hex_bytes=HEX)
    app = falcon.App()
    HostedBridgesAPI(polServer=types.SimpleNamespace(falconServer=app), manager=mgr)
    httpd = make_server('127.0.0.1', 0, app, handler_class=_Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    api = 'http://127.0.0.1:%d' % httpd.server_address[1]

    def call(method, path, body=None):
        req = urllib.request.Request(api + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                     headers={'Content-Type': 'application/json'} if body is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    try:
        c0, _ = call('POST', '/api/grpc/hosted-bridges', {})
        c1, d1 = call('POST', '/api/grpc/hosted-bridges', {'session': ts['name'], 'owner': 'door'})
        name = d1.get('name', '')
        c2, d2 = call('GET', '/api/grpc/hosted-bridges')
        c3, d3 = call('GET', '/api/grpc/hosted-bridges/%s' % name)
        c4, d4 = call('GET', '/api/grpc/hosted-bridges/%s/logs?tail=3' % name)
        c5, d5 = call('GET', '/api/grpc/hosted-bridges/nope')
        c6, d6 = call('GET', '/api/grpc/hosted-engines')
        check('sim-2 doors: POST 201 (and 400 with no session), GET list (rows for a table), GET one (+ the tail of the output), logs, 404 in words, the engines placement',
              c0 == 400 and c1 == 201 and d1['ok'] and d1['grpc_target'] == '127.0.0.1:3002' and c2 == 200 and d2['count'] >= 1 and c3 == 200 and 'output_tail' in d3 and c4 == 200
              and d4['lines'] and c5 == 404 and 'no hosted bridge' in d5['error'] and c6 == 200 and d6['resolved']['how'] == 'remote', str([c0, c1, c2, c3, c4, c5, c6]))
        from grpcbridge.custom import hosted_cli as CLI
        import io
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = [CLI.main(['start', ts['name'], '--api', api, '--owner', 'cli']), CLI.main(['list', '--api', api]), CLI.main(['engines', '--api', api]), CLI.main(['show', 'nope', '--api', api])]
        finally:
            sys.stdout = old
        text = buf.getvalue()
        cli_name = re.search(r'hosted bridge (\S+) ', text)
        rc += [CLI.main(['logs', cli_name.group(1), '--api', api]) if cli_name else 9, CLI.main(['stop', cli_name.group(1), '--api', api]) if cli_name else 9]
        check('pol grpc hosted: start (waits for running, prints where it reads and pushes), list, engines, show/logs/stop; a refusal prints the words and exits 1',
              rc == [0, 0, 0, 1, 0, 0] and 'beside' in text and 'refused: no hosted bridge' in text and 'knob BRIDGE_ENGINES_URL=' in text, '%s %s' % (rc, text[-500:]))
        c7, d7 = call('DELETE', '/api/grpc/hosted-bridges/%s' % name)
        check('sim-2 doors: DELETE stops it', c7 == 200 and d7['state'] == 'ended')
    finally:
        httpd.shutdown()
        httpd.server_close()


# ---------------------------------------------------------------------------------------------------------------- live
def _get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def live():
    board, bridge = os.environ.get('BOARD_ENGINES_URL', '').rstrip('/'), os.environ.get('BRIDGE_ENGINES_URL', '').rstrip('/')
    for label, url, need in (('board worker', board, 'sessions'), ('bridge worker', bridge, 'bridges')):
        try:
            ok = bool(url) and (_get(url + '/capability', 5).get(need) or {}).get('available')
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            return skip('sim-2 live half', 'no %s answering at %s (set BOARD_ENGINES_URL and BRIDGE_ENGINES_URL)' % (label, url or '(unset)'))
    from board.custom import twin_sessions as TS
    from grpcbridge.custom import hosted_bridges as HB
    from board.custom import board_engines as bce
    from grpcbridge.custom import bridge_engines as be
    bce._CAP_CACHE.clear()
    be.forget()
    mgr = _mgr()
    with tempfile.TemporaryDirectory(prefix='hosted-live-') as td, _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret')):
        s = h = None
        try:
            s = TS.start(mgr, 'uno-light', ttl_s=300, owner='hosted-selftest')
            h = HB.start(mgr, s['name'], log_only=True, ttl_s=240, owner='hosted-selftest')
            end = time.time() + 300
            while h['state'] == 'building' and time.time() < end:
                time.sleep(1)
                h = dict(h, **{k: v for k, v in HB.one(mgr, h['name']).items() if k in ('state', 'jar_sha256', 'end_reason')})
            check('sim-2 live: a REAL hosted bridge (built or from the cache, then run as a detached JVM) is running beside a REAL uno-light session', h['state'] == 'running', str(h)[:300])
            time.sleep(2.0)
            TS.inject(mgr, s['name'], {'set': 'PD2', 'level': 0})
            time.sleep(0.07)
            TS.inject(mgr, s['name'], {'set': 'PD2', 'level': 1})
            text, end = '', time.time() + 5
            while time.time() < end:
                text = '\n'.join(HB.logs(mgr, h['name'], tail=200)['lines'])
                if re.search(r'LightState.*toggles=1', text):
                    break
                time.sleep(0.2)
            m = re.search(r'LightState\{[^}]*\}', text)
            check('sim-2 live (brg-0 twin-session mode): the bridge decoded the report of the press from the twin\'s serial port - the LightState frame says led_on=true toggles=1 source=button',
                  bool(re.search(r'LightState.*led_on=true.*toggles=1', text) and re.search(r'LightState.*source=button', text)), (m.group(0) if m else text[-600:]))
        finally:
            for fn, row in ((HB.stop, h), (TS.stop, s)):
                if row:
                    try:
                        fn(mgr, row['name'])
                    except Exception as e:  # noqa: BLE001
                        print('cleanup:', e)


def proof_against_server():
    api = os.environ.get('HOSTED_PROOF_API', '').rstrip('/')
    if not api:
        return skip('sim-2 both-directions proof', 'HOSTED_PROOF_API is not set (a Polari server whose backend reaches the board + bridge workers)')
    from grpcbridge.custom import hosted_proof
    hosted_proof.run(check, api)


def main():
    offline()
    live()
    proof_against_server()
    failed = [label for label, ok in _results if not ok]
    print('\n%d/%d checks passed%s%s' % (len(_results) - len(failed), len(_results), '; %d skipped' % len(_skips) if _skips else '', '; FAILED: %s' % failed if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
