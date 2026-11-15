"""grpcbridge.custom.hosted_door_checks - td-3 / td-4 (AI-Notes/plans/TWIN_DOOR_PLAN.md): the hosted bridge reaching a twin session's serial stream through
the board worker's twin door. Checks for grpcbridge_hosted_selftest, all offline:

  worker_door(check, skip)    the REAL prf-bridge-engines/bridge_hosted.py with fake mvn / java: a `twin_uart` door writes source=twin-door + twin.uart, the
                              session token reaches the bridge's process by the environment variable TWIN_TOKEN and is found NOWHERE else (no file under the
                              worker's directories, not the command line, not an answer); refusals in words
  jvm_door_mode(check, skip)  the generated uno-light core on the JVM with source=twin-door against a FAKE door (a real WebSocket server over TLS with a test
                              certificate): the LightState frames it decoded, the reconnect, and the refusals that must END the bridge instead of looping
                              (wrong token, unknown session, a certificate that is not trusted, no token, a door that is not wss://)
  grpc_tls_mode(check, skip)  D5: the WHOLE generated jar (built with `mvn -o package` where the repository is warmed; skipped in words elsewhere) pushing to a
                              gRPC recorder under the grpc.tls knob: verified against the bundle, verified by default, an untrusted certificate and a
                              plaintext port get nothing, plaintext only by the explicit knob, any other value refused
  backend_door(check, ...)    hosted_bridges.start for a session that went through a door: the worker is sent the session's own uart URL and its token; the
                              token is in no row, view or listing; a bridge worker older than the door is refused (D4), the bridge stopped, no row left

Skips are said in words (no worker source beside this checkout, no JDK, no openssl)."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time

from grpcbridge.custom import hosted_checks as HC

DOOR = 'wss://twin.board-engines.isle/sessions/f00001/uart'
TOKEN = 'c0ffee5e55107e57c0ffee5e55107e57'     # the shape of twin_token.derive (32 hex); a test value, not a secret


def test_cert(dirname, name='door'):
    """A self-signed certificate for `localhost` (openssl) -> (crt, key), or (None, why)."""
    if not shutil.which('openssl'):
        return None, 'no openssl on this device to make a test certificate'
    crt, key = os.path.join(dirname, name + '.crt'), os.path.join(dirname, name + '.key')
    made = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                           '-keyout', key, '-out', crt], capture_output=True, text=True)
    return (crt, key) if made.returncode == 0 else (None, 'openssl could not make a test certificate (%s)' % made.stderr.strip()[-80:])


# ---------------------------------------------------------------------------------------------------------------- the worker
def worker_door(check, skip):
    HC.worker_logic(check, skip, checks=_worker_door, label='td-4 worker door')


def _holders(root, needle):
    """Every file under `root` whose bytes contain `needle`."""
    found = []
    for dp, _d, fns in os.walk(root):
        for fn in fns:
            try:
                if needle in open(os.path.join(dp, fn), 'rb').read():
                    found.append(os.path.relpath(os.path.join(dp, fn), root))
            except OSError:
                pass
    return found


def _worker_door(check, bh, falcon, FT, tmp, count):
    app = falcon.App(middleware=[bh.Reaper()])
    bh.add_routes(app)
    cl = FT.TestClient(app)
    files = {'pom.xml': '<project>ok</project>', 'src/main/java/A.java': 'class A {}',
             'bridge.properties': 'source=serial\nserial.device=/dev/ttyACM0\ntwin.uart=tcp://stale:1\ngrpc.enabled=false\nbaud=1\n'}
    body = dict(session_id='uno-light-abc123', bridge_name='uno-light', files=files, ttl_s=60, twin_uart=DOOR, token=TOKEN)

    def wait(bid, secs=15):
        end, r = time.time() + secs, {}
        while time.time() < end:
            r = cl.simulate_get('/bridges/%s' % bid).json
            if r.get('state') in ('running', 'failed'):
                return r
            time.sleep(0.1)
        return r

    def printed(bid, needle, secs=5):
        end, out = time.time() + secs, ''
        while time.time() < end:
            out = ''.join(cl.simulate_get('/bridges/%s/logs' % bid, params={'tail': 50}).json['lines'])
            if needle in out:
                break
            time.sleep(0.1)
        return out

    try:
        r = cl.simulate_post('/bridges', json=body)
        a = wait(r.json.get('id'))
        lines = open(os.path.join(bh.DIR, '%s.properties' % a['id'])).read().splitlines()
        check('td-4 worker: a twin_uart door starts the bridge with source=twin-door and twin.uart=<the door> (the generated twin.uart line replaced), with NO twin host / port '
              'asked for or written - a door session is reached at the door alone; the answer repeats twin_uart', r.status_code == 200 and a.get('state') == 'running'
              and 'source=twin-door' in lines and 'twin.uart=%s' % DOOR in lines and not [x for x in lines if x.startswith(('twin.host', 'twin.port', 'twin.uart=tcp'))]
              and 'serial.device=/dev/ttyACM0' in lines and r.json.get('twin_uart') == DOOR, '%s %s' % (str(r.json)[:200], lines))
        out = printed(a['id'], 'token-env=')
        check('td-4 worker: the session token reaches the bridge\'s process in the environment variable TWIN_TOKEN (the process reports its sha256)',
              'token-env=%s' % hashlib.sha256(TOKEN.encode()).hexdigest() in out, out[-200:])
        held = _holders(tmp, TOKEN.encode())
        cmdline = open('/proc/%d/cmdline' % a['pid'], 'rb').read()
        said = json.dumps([r.json, cl.simulate_get('/bridges/%s' % a['id']).json, cl.simulate_get('/bridges').json, cl.simulate_get('/bridges/%s/logs' % a['id']).json,
                           cl.simulate_get('/bridges/%s/logs' % a['id'], params={'which': 'build'}).json])
        check('td-4 worker: the token is kept NOWHERE else - no file under the worker\'s directories (state, properties, logs, jars, builds), not the command line, no answer '
              '(start, detail, listing, logs)', not held and TOKEN.encode() not in cmdline and TOKEN not in said, 'files %s' % held)
        cl.simulate_delete('/bridges/%s' % a['id'])

        r = cl.simulate_post('/bridges', json=dict(body, twin_uart='tcp://127.0.0.1:9999', twin_host='127.0.0.1', twin_port=9999))
        b = wait(r.json.get('id'))
        lines = open(os.path.join(bh.DIR, '%s.properties' % b['id'])).read().splitlines()
        out = printed(b['id'], 'token-env=')
        check('td-4 worker: a tcp:// twin_uart stays source=twin-tcp and a token sent with it is NOT handed to the process (the raw port is not token-gated)',
              b.get('state') == 'running' and 'source=twin-tcp' in lines and 'twin.uart=tcp://127.0.0.1:9999' in lines and 'twin.port=9999' in lines and 'token-env=unset' in out,
              '%s %s' % (lines, out[-120:]))
        cl.simulate_delete('/bridges/%s' % b['id'])

        r = cl.simulate_post('/bridges', json=dict(body, twin_uart='ws://127.0.0.1:9864/sessions/f00001/uart'))
        c = wait(r.json.get('id'))
        check('td-4 worker: ws:// without TLS is accepted for loopback only (a test door on the same device)', r.status_code == 200 and c.get('state') == 'running', str(r.json)[:200])
        cl.simulate_delete('/bridges/%s' % c['id'])

        bad = {'a door with no token': dict(body, token=None), 'a token too short to be one': dict(body, token='abc'),
               'a token that is not text': dict(body, token={'x': 1}), 'ws:// off this device': dict(body, twin_uart='ws://twin.board-engines.isle/sessions/f00001/uart'),
               'another scheme': dict(body, twin_uart='https://twin.board-engines.isle/sessions/f00001/uart'), 'a door with no path': dict(body, twin_uart='wss://twin.board-engines.isle'),
               'a second line smuggled into the properties': dict(body, twin_uart=DOOR + '\nsource=serial'), 'a query string': dict(body, twin_uart=DOOR + '?token=' + TOKEN),
               'not text': dict(body, twin_uart=['x']), 'no door and no host / port': {k: v for k, v in body.items() if k not in ('twin_uart', 'token')}}
        got = {k: cl.simulate_post('/bridges', json=v) for k, v in bad.items()}
        wrong = {k: (x.status_code, x.json) for k, x in got.items() if x.status_code != 400 or not x.json.get('error')}
        check('td-4 worker: refused in words with a 400 - %s' % ', '.join(bad), not wrong and not [x for x in bh._all() if x['state'] in ('building', 'running')], str(wrong)[:400])
    finally:
        for s in bh._all():
            try:
                if s['state'] in ('building', 'running'):
                    bh._kill(s)
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------------------------------------------- the JVM
def jvm_door_mode(check, skip):
    javac, java = shutil.which('javac'), shutil.which('java')
    if not (javac and java):
        return skip('td-4 JVM twin-door mode', 'no JDK on PATH')
    from grpcbridge.custom.hosted_fakes import FakeUartDoor
    frame = HC.light_frame
    with tempfile.TemporaryDirectory(prefix='polari-td4-') as tmp:
        tls, other = test_cert(tmp), test_cert(tmp, 'other')
        if tls[0] is None or other[0] is None:
            return skip('td-4 JVM twin-door mode', tls[1] if tls[0] is None else other[1])
        rep, comp = HC.light_core(tmp)
        if comp is None or comp.returncode != 0:
            return check('td-4: the generated uno-light core (with IsleTrust, WsDevicePort, TwinPort) compiles with javac', False, str(rep.get('error')) if comp is None else comp.stderr[:600])
        base = [ln for ln in rep['files']['bridge.properties'].splitlines()
                if ln.split('=', 1)[0] not in ('source', 'twin.host', 'twin.port', 'twin.uart', 'twin.connect_timeout_s', 'grpc.enabled', 'serial.device')]

        def run(name, uart, token=TOKEN, bundle=tls[0], source='twin-door', timeout=40):
            props = os.path.join(tmp, name + '.properties')
            with open(props, 'w') as f:
                f.write('\n'.join(base + ['source=' + source, 'twin.connect_timeout_s=6', 'grpc.enabled=false'] + (['twin.uart=' + uart] if uart else [])) + '\n')
            env = {k: v for k, v in os.environ.items() if k not in ('TWIN_TOKEN', 'ISLE_TRUST_BUNDLE')}
            env.update({k: v for k, v in (('TWIN_TOKEN', token), ('ISLE_TRUST_BUNDLE', bundle)) if v})
            t0 = time.time()
            try:
                p = subprocess.run([java, '-cp', os.path.join(tmp, 'out'), 'org.polari.bridge.BridgeMain', props, '--max-frames=3'], capture_output=True, text=True,
                                   timeout=timeout, env=env)
                return p.returncode, p.stdout + p.stderr, time.time() - t0
            except subprocess.TimeoutExpired as e:
                text = b''.join(x for x in (e.stdout, e.stderr) if isinstance(x, bytes)).decode(errors='replace')
                return 124, text + '\n(still running after %d s: it did not end)' % timeout, time.time() - t0

        door = FakeUartDoor([[frame(1), frame(2, True, 1, 'button')], [frame(3, False, 2, 'command')]], TOKEN, tls=tls, host='localhost')
        try:
            rc, out, _s = run('door', door.url)
            door.finished.wait(5)
            got = [ln for ln in out.splitlines() if 'LightState' in ln and '[bridge] seq=' in ln]
            check('td-4: source=twin-door - the bridge dialled the door over wss:// (certificate checked against ISLE_TRUST_BUNDLE), sent the token first and DECODED the '
                  'LightState frames carried as binary WebSocket frames (led_on / toggles / source as sent, in order)', rc == 0 and len(got) == 3
                  and 'on twin-door %s' % door.url in out and 'toggles=1' in got[1] and 'toggles=2' in got[2] and not door.refused, out[-900:])
            check('td-4: the door closing the stream (4410, the twin closed it) is a RECONNECT, not a crash: ws-lost, then ws-open attempt 2 with the token sent again, no gap '
                  'in the sequence, reconnects=1', '"t":"ws-lost"' in out and '"t":"ws-open"' in out and '"attempt":2' in out and bool(got) and 'gaps=0' in got[-1]
                  and 'reconnects=1' in got[-1] and door.connections == 2, out[-600:])
            check('td-4: the token is in nothing the bridge prints, and nothing but the token frame went up (LightState has no snapshot to ask for): no serial bytes on either '
                  'connection', TOKEN not in out and len(door.received) == 2 and not any(door.received), str([len(b) for b in door.received]))

            before = door.connections
            rc, out, secs = run('wrong-token', door.url, token='not-this-sessions-token')
            check('td-4: a WRONG token ends the bridge with the reason in words (the door closed 4403) instead of dialling again forever: %s' % _last(out, 'refused the token'),
                  rc != 124 and secs < 15 and 'refused the token' in out and 'TWIN_TOKEN' in out and door.refused.count(4403) == 1 and door.connections == before
                  and 'not-this-sessions-token' not in out, '%s %.1fs %s %s' % (rc, secs, door.refused, out[-500:]))
            rc, out, secs = run('unknown-session', door.url.replace('/f00001/', '/f99999/'))
            check('td-4: a session the door does not know (4404) ends the bridge in words too: %s' % _last(out, 'knows no'),
                  rc != 124 and secs < 15 and 'knows no' in out and door.refused.count(4404) == 1, '%s %.1fs %s %s' % (rc, secs, door.refused, out[-500:]))
            seen = len(door.refused) + door.connections
            rc, out, secs = run('untrusted', door.url, bundle=other[0])
            check('td-4 TLS: a door whose certificate is NOT in the bundle this bridge trusts is refused at once, naming the bundle (verification is never skipped; no token '
                  'left this process): %s' % _last(out), rc not in (0, 124) and secs < 6 and 'certificate was not accepted' in out and other[0] in out
                  and len(door.refused) + door.connections == seen, '%s %.1fs %s' % (rc, secs, out[-500:]))
            rc, out, secs = run('other-name', door.url.replace('localhost', '127.0.0.1'))
            check('td-4 TLS: the NAME is checked too - the same certificate under another host name is refused: %s' % _last(out),
                  rc not in (0, 124) and secs < 6 and 'certificate was not accepted' in out and len(door.refused) + door.connections == seen, '%s %.1fs %s' % (rc, secs, out[-500:]))
            rc, out, secs = run('no-bundle', door.url, bundle=os.path.join(tmp, 'no-such-bundle.pem'))
            check('td-4 TLS: ISLE_TRUST_BUNDLE naming a file that cannot be read is a refusal in words, never a quiet fall back to another trust store: %s' % _last(out),
                  rc not in (0, 124) and 'no-such-bundle.pem' in out and len(door.refused) + door.connections == seen, '%s %s' % (rc, out[-500:]))
            rc, out, secs = run('no-token', door.url, token='')
            check('td-4: with no TWIN_TOKEN in the environment the bridge refuses to dial the door, naming the variable: %s' % _last(out),
                  rc not in (0, 124) and 'TWIN_TOKEN' in out and len(door.refused) + door.connections == seen, '%s %s' % (rc, out[-400:]))
            rc, out, secs = run('no-uart', '')
            rc2, out2, _s = run('tcp-as-door', 'tcp://127.0.0.1:9')
            rc3, out3, _s = run('plain-ws', 'ws://twin.board-engines.isle/sessions/f00001/uart')
            check('td-4 (D4): source=twin-door never falls back to TCP - no twin.uart, a tcp:// twin.uart and a ws:// door off this device are each refused in words',
                  rc not in (0, 124) and 'needs twin.uart' in out.replace('\n', ' ') and rc2 not in (0, 124) and 'a door is wss://' in out2 and rc3 not in (0, 124)
                  and 'must be wss://' in out3, '%s | %s | %s' % (out[-200:], out2[-200:], out3[-200:]))
        finally:
            door.close()


def _last(out, about=''):
    """The line a person would read: the one that says `about`, else the last one that is not a stack frame."""
    said = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.strip().startswith(('at ', '...', 'Caused by'))]
    hit = [ln for ln in said if about and about in ln]
    return (hit[0] if hit else said[-1] if said else '')[:170].replace('Exception in thread "main" ', '')


# ---------------------------------------------------------------------------------------------------------------- gRPC over TLS (D5)
class _Recorder:
    """A gRPC server on loopback that takes ANY service's Push (client stream) and Commands (server stream) and counts what arrives - the Polari backend's
    side of the bridge link, protocol only. tls=(crt, key) serves TLS."""

    def __init__(self, tls=None):
        from concurrent import futures
        import grpc
        self.pushed, self.calls = 0, []
        outer = self

        class Any(grpc.GenericRpcHandler):
            def service(self, details):
                outer.calls.append(details.method.rsplit('/', 1)[-1])
                if details.method.endswith('/Push'):
                    def push(frames, _ctx):
                        for _f in frames:
                            outer.pushed += 1
                        return b''
                    return grpc.stream_unary_rpc_method_handler(push)
                if details.method.endswith('/Commands'):
                    def commands(_req, ctx):
                        end = time.time() + 20
                        while ctx.is_active() and time.time() < end:
                            time.sleep(0.05)
                        return iter(())
                    return grpc.unary_stream_rpc_method_handler(commands)
                return None

        self.srv = grpc.server(futures.ThreadPoolExecutor(8))
        self.srv.add_generic_rpc_handlers((Any(),))
        if tls:
            self.port = self.srv.add_secure_port('127.0.0.1:0', grpc.ssl_server_credentials([(open(tls[1], 'rb').read(), open(tls[0], 'rb').read())]))
        else:
            self.port = self.srv.add_insecure_port('127.0.0.1:0')
        self.srv.start()

    def close(self):
        self.srv.stop(0)


def grpc_tls_mode(check, skip):
    """D5 on the JVM: the generated bridge's gRPC link under the grpc.tls knob. Needs the WHOLE jar (the gRPC half has Maven dependencies), so it runs where
    `mvn -o package` can build it from a warmed repository (the bridge worker's image, a developer's machine) and is skipped in words elsewhere."""
    label = 'td-4 gRPC TLS (D5)'
    mvn, java = shutil.which('mvn'), shutil.which('java')
    if not (mvn and java):
        return skip(label, 'no mvn / java on PATH to build the whole bridge jar')
    os.environ.setdefault('GRPC_VERBOSITY', 'NONE')    # the refused handshakes below are the point, not noise for the selftest's output
    try:
        import grpc  # noqa: F401
    except ImportError:
        return skip(label, 'no grpcio here to stand in for the backend\'s gRPC server')
    from grpcbridge.custom.hosted_fakes import FakeUsart
    from hwnocode.custom import offline_project as OP
    with tempfile.TemporaryDirectory(prefix='polari-d5-') as tmp:
        tls, other = test_cert(tmp), test_cert(tmp, 'other')
        if tls[0] is None or other[0] is None:
            return skip(label, tls[1] if tls[0] is None else other[1])
        rep = OP.light_project(grpc_target='localhost:3002')
        proj = os.path.join(tmp, 'project')
        for path, text in rep.get('files', {}).items():
            dest = os.path.join(proj, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w') as f:
                f.write(text)
        try:
            built = subprocess.run([mvn, '-o', '-q', '-B', 'package', '-DskipTests'], cwd=proj, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return skip(label, 'mvn -o package did not finish in 600 s')
        jar = os.path.join(proj, 'target', 'polari-hw-bridge.jar')
        if built.returncode != 0 or not os.path.isfile(jar):
            said = (built.stdout + built.stderr)
            if 'offline' in said.lower() or 'could not resolve' in said.lower() or 'not been downloaded' in said.lower():
                return skip(label, 'mvn -o package cannot build the jar here: the Maven repository on this device does not hold the bridge\'s dependencies')
            return check('td-4 (D5): the WHOLE generated bridge (GrpcForwarder with the grpc.tls knob and IsleTrust) builds with mvn', False, said[-700:])
        check('td-4 (D5): the generated properties say grpc.tls=plaintext out loud (today\'s backend gRPC port is plaintext; the knob is never left to a default)',
              'grpc.tls=plaintext' in rep['files']['bridge.properties'].splitlines())
        base = [ln for ln in rep['files']['bridge.properties'].splitlines()
                if ln.split('=', 1)[0] not in ('source', 'twin.host', 'twin.port', 'twin.uart', 'grpc.enabled', 'grpc.target', 'grpc.tls', 'serial.device')]

        def run(name, server_tls, knob, bundle):
            rec = _Recorder(tls if server_tls else None)
            usart = FakeUsart([[HC.light_frame(1), HC.light_frame(2, True, 1, 'button'), HC.light_frame(3, False, 2, 'command')]])
            props = os.path.join(tmp, name + '.properties')
            with open(props, 'w') as f:
                f.write('\n'.join(base + ['source=twin-tcp', 'twin.host=127.0.0.1', 'twin.port=%d' % usart.port, 'grpc.enabled=true', 'grpc.target=localhost:%d' % rec.port]
                                  + (['grpc.tls=' + knob] if knob else [])) + '\n')
            env = {k: v for k, v in os.environ.items() if k != 'ISLE_TRUST_BUNDLE'}
            if bundle:
                env['ISLE_TRUST_BUNDLE'] = bundle
            try:
                p = subprocess.run([java, '-jar', jar, props, '--max-frames=3'], capture_output=True, text=True, timeout=60, env=env)
                rc, out = p.returncode, p.stdout + p.stderr
            except subprocess.TimeoutExpired as e:
                rc, out = 124, b''.join(x for x in (e.stdout, e.stderr) if isinstance(x, bytes)).decode(errors='replace')
            time.sleep(0.3)
            usart.close()
            rec.close()
            return rc, out, rec

        rc, out, rec = run('verified', True, 'verified', tls[0])
        check('td-4 (D5): grpc.tls=verified - the bridge pushed the 3 LightState frames to a TLS gRPC server whose certificate is in ISLE_TRUST_BUNDLE, and opened the '
              'Commands stream; it says which bundle it trusts and prints the server\'s answer before it ends', rc == 0 and rec.pushed == 3 and 'Commands' in rec.calls and 'push ack' in out and 'is TLS, verified against the certificates in %s' % tls[0] in out,
              '%s pushed=%s %s %s' % (rc, rec.pushed, rec.calls, _grpc(out)))
        rc, out, rec = run('default', True, '', tls[0])
        check('td-4 (D5): a properties file with NO grpc.tls key is verified TLS (the jar\'s default is the safe one)', rc == 0 and rec.pushed == 3 and 'is TLS, verified' in out,
              '%s pushed=%s %s' % (rc, rec.pushed, _grpc(out)))
        rc, out, rec = run('other-bundle', True, 'verified', other[0])
        check('td-4 (D5): a server whose certificate is NOT in the bundle gets nothing - no frame, no call - and the bridge says the push failed: %s' % _last(out, 'push error'),
              rec.pushed == 0 and not rec.calls and 'push error' in out, '%s pushed=%s %s %s' % (rc, rec.pushed, rec.calls, _grpc(out)))
        rc, out, rec = run('tls-to-plain', False, 'verified', tls[0])
        check('td-4 (D5): verified TLS against a PLAINTEXT gRPC port (today\'s backend, port 3002) delivers nothing and says so - it never drops to plaintext by itself',
              rec.pushed == 0 and not rec.calls and 'push error' in out, '%s pushed=%s %s' % (rc, rec.pushed, _grpc(out)))
        rc, out, rec = run('plain', False, 'plaintext', None)
        check('td-4 (D5): grpc.tls=plaintext is the explicit knob for that port: the 3 frames arrive and the bridge prints that nothing on the link is encrypted or checked',
              rc == 0 and rec.pushed == 3 and 'is PLAINTEXT (grpc.tls=plaintext)' in out, '%s pushed=%s %s' % (rc, rec.pushed, _grpc(out)))
        rc, out, rec = run('bogus', False, 'off', None)
        check('td-4 (D5): any other grpc.tls value is refused in words (not read as "no TLS")', rc not in (0, 124) and 'grpc.tls=off is neither verified nor plaintext' in out
              and rec.pushed == 0, '%s %s' % (rc, out[-300:]))


def _grpc(out):
    return ' | '.join(ln.strip()[:160] for ln in out.splitlines() if '[grpc]' in ln)[:700]


# ---------------------------------------------------------------------------------------------------------------- the backend
def backend_door(check, mgr, TS, HB, env, hex_bytes):
    """A session that went through a door, then its hosted bridge. `env` = the selftest's environment context manager."""
    from board.custom import board_engines as bce, twin_token
    from board.custom.twin_session_fakes import FakeDoor, FakeWorker
    from grpcbridge.custom import bridge_engines as be
    from grpcbridge.custom.hosted_fakes import FakeBridgeWorker
    board = FakeWorker(sessions=True)
    door = FakeDoor(board)
    board.transports = door.transports
    new, old = FakeBridgeWorker(), FakeBridgeWorker(knows_door=False)
    try:
        with env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=new.url):
            bce._CAP_CACHE.clear()
            be.forget()
            ts = TS.start(mgr, 'uno-light', ttl_s=300, owner='tester', hex_bytes=hex_bytes)
            v = HB.start(mgr, ts['name'], log_only=True, owner='tester')
            sent = new.items[v['worker_bridge']]['body']
            token = twin_token.derive(ts['name'])
            check('td-3: a session that went through the worker\'s twin door hands its bridge the SAME choice - the worker is sent twin_uart = the session\'s own uart URL '
                  '(%s) and the session\'s token in the POST body' % ts.get('uart_url'), ts.get('transport') == 'door' and sent.get('twin_uart') == ts['uart_url']
                  and ts['uart_url'].endswith('/sessions/%s/uart' % ts['worker_session']) and sent.get('token') == token and v['twin'] == ts['uart_url'], str(v)[:300])
            row = [r for r in HB._rows(mgr) if r.name == v['name']][0]
            said = json.dumps([v, HB.listing(mgr), HB.one(mgr, v['name']), {k: str(x) for k, x in vars(row).items()}, new.items[v['worker_bridge']]['view'],
                               HB.logs(mgr, v['name'], tail=20)])
            check('td-3: the token is in NO row, view, listing or log of the hosted bridge (only the POST body carried it); the row keeps the uart URL',
                  token not in said and row.twin_uart == ts['uart_url'] and any('twin-door' in ln for ln in HB.logs(mgr, v['name'], tail=5)['lines']))
            HB.stop(mgr, v['name'])
        with env(BOARD_ENGINES_URL=board.url, BRIDGE_ENGINES_URL=old.url):
            be.forget()
            rows = len(HB._rows(mgr))
            try:
                HB.start(mgr, ts['name'], log_only=True)
                why, st = '', 0
            except HB.HostedRefused as e:
                why, st = str(e), e.status
            check('td-3 (D4): a bridge worker OLDER than the twin door (its answer does not repeat twin_uart, so it would read a TCP port the session\'s worker does not publish) '
                  'is refused in words (424), the bridge it started is stopped, no row is left: %s' % why[:120], st == 424 and 'WITHOUT the twin door' in why
                  and ts['uart_url'] in why and not old.items and [m for m, _p in old.requests].count('DELETE') == 1 and len(HB._rows(mgr)) == rows, '%s %s %s' % (st, why, old.requests))
            TS.stop(mgr, ts['name'])
    finally:
        be.forget()
        bce._CAP_CACHE.clear()
        for w in (old, new, door, board):
            w.close()
