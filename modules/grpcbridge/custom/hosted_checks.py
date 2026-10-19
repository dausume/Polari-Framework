"""grpcbridge.custom.hosted_checks - checks for grpcbridge_hosted_selftest that need no live worker:

  worker_logic(check)   the REAL prf-bridge-engines/bridge_hosted.py driven through falcon's test client with FAKE mvn / java executables: build cached by the
                        project's sha, the properties it writes, TTL reaper, stop, a dead process noticed, refusals in words, the cap, nothing left running
  jvm_twin_mode(check)  brg-0 on the JVM: the generated uno-light core compiled with javac, run with source=twin-tcp against a FAKE twin USART port that sends real
                        LightState frames (the independent Python reference codec) - the proof is the LightState frames the bridge decoded, the snapshot it sent
                        down on attach, and the reconnect after the port closed

Both skip in words (never silently) when the worker source or a JDK is not on this machine."""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER_DIR = os.path.normpath(os.path.join(HERE, *['..'] * 4, 'prf-bridge-engines'))

FAKE_MVN = '''#!/bin/sh
# fake mvn: counts runs, fails when the pom says FAIL, else "builds" target/polari-hw-bridge.jar
echo run >> "$FAKE_COUNT"
grep -q FAIL pom.xml && { echo "BUILD FAILURE (fake)"; exit 1; }
mkdir -p target
cat pom.xml > target/polari-hw-bridge.jar
echo "built $(wc -c < target/polari-hw-bridge.jar) bytes"
'''
FAKE_JAVA = '''#!/bin/sh
# fake java -Xmx.. -XX.. -Xss.. -jar JAR PROPS: prints the properties it was given and stays alive (the command line carries the .jar)
exec python3 -c "import sys,time; print(open(sys.argv[2]).read(), flush=True); time.sleep(300)" "$5" "$6"
'''


def _script(path, text):
    with open(path, 'w') as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


def _load_worker(tmp):
    spec = importlib.util.spec_from_file_location('bridge_hosted_under_test', os.path.join(WORKER_DIR, 'bridge_hosted.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def worker_logic(check, skip):
    if not os.path.isfile(os.path.join(WORKER_DIR, 'bridge_hosted.py')):
        return skip('sim-2 worker logic', 'the prf-bridge-engines source is not beside this framework checkout')
    import falcon
    import falcon.testing as FT
    with tempfile.TemporaryDirectory(prefix='bridge-worker-test-') as tmp:
        count = os.path.join(tmp, 'mvn.count')
        _script(os.path.join(tmp, 'mvn'), FAKE_MVN)
        _script(os.path.join(tmp, 'java'), FAKE_JAVA)
        env = dict(BRIDGES_DIR=os.path.join(tmp, 'bridges'), JARS_DIR=os.path.join(tmp, 'jars'), BUILDS_DIR=os.path.join(tmp, 'builds'), BRIDGE_MVN=os.path.join(tmp, 'mvn'),
                   BRIDGE_JAVA=os.path.join(tmp, 'java'), BRIDGES_MAX='3', FAKE_COUNT=count)
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            sys.path.insert(0, WORKER_DIR)
            try:
                bh = _load_worker(tmp)
            finally:
                sys.path.remove(WORKER_DIR)
            _worker_checks(check, bh, falcon, FT, tmp, count)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _runs(count):
    try:
        return len(open(count).read().split())
    except OSError:
        return 0


def _worker_checks(check, bh, falcon, FT, tmp, count):
    bh.TTL_MIN = 1
    app = falcon.App(middleware=[bh.Reaper()])
    bh.add_routes(app)
    cl = FT.TestClient(app)
    base = {'pom.xml': '<project>ok</project>', 'src/main/java/A.java': 'class A {}', 'bridge.properties': 'source=serial\nserial.device=/dev/ttyACM0\nmax_frames=0\ngrpc.enabled=false\nbaud=1\n',
            'install-ubuntu.sh': 'ignored'}
    body = dict(session_id='uno-light-abc123', twin_host='127.0.0.1', twin_port=9999, bridge_name='uno-light', files=base, grpc_target='backend.example:3002', ttl_s=60)

    def wait(bid, states, secs=15):
        end = time.time() + secs
        while time.time() < end:
            r = cl.simulate_get('/bridges/%s' % bid).json
            if r.get('state') in states:
                return r
            time.sleep(0.1)
        return r

    pids = []
    try:
        r = cl.simulate_post('/bridges', json=body)
        a = wait(r.json['id'], ('running', 'failed'))
        pids.append(a.get('pid'))
        props = open(os.path.join(bh.DIR, '%s.properties' % a['id'])).read()
        check('sim-2 worker: POST /bridges builds the project (mvn ran once), starts the jar as a detached process and answers running with the jar sha', r.status_code == 200
              and a['state'] == 'running' and a['jar_sha256'] and a['build']['cached'] is False and _runs(count) == 1 and a['pid'] and os.path.exists('/proc/%d' % a['pid']), str(a)[:200])
        lines = props.splitlines()
        check('sim-2 worker: the properties it writes keep the generated ones and override ONLY its own keys: source=twin-tcp, the session\'s host + port, gRPC on with the target; '
              'the generated source=serial line is gone', 'source=twin-tcp' in lines and 'source=serial' not in lines and 'twin.host=127.0.0.1' in lines and 'twin.port=9999' in lines
              and 'grpc.enabled=true' in lines and 'grpc.target=backend.example:3002' in lines and 'serial.device=/dev/ttyACM0' in lines and 'baud=1' in lines
              and 'grpc.enabled=false' not in lines, props)
        out = ''.join(cl.simulate_get('/bridges/%s/logs' % a['id'], params={'tail': 50}).json['lines'])
        check('sim-2 worker: GET /bridges/{id}/logs returns what the bridge printed; the build log is reachable too', 'source=twin-tcp' in out
              and any('mvn' in ln for ln in cl.simulate_get('/bridges/%s/logs' % a['id'], params={'which': 'build'}).json['lines']))
        d = cl.simulate_get('/bridges/%s' % a['id']).json
        check('sim-2 worker: the detail carries the live process cost (RSS kB, CPU seconds)', d.get('rss_kb') and d.get('cpu_s') is not None, str(d)[:160])

        r2 = cl.simulate_post('/bridges', json=dict(body, grpc_target='', session_id='uno-light-def456'))
        b = wait(r2.json['id'], ('running', 'failed'))
        pids.append(b.get('pid'))
        props2 = open(os.path.join(bh.DIR, '%s.properties' % b['id'])).read().splitlines()
        check('sim-2 worker: the second bridge of the SAME code starts from the jar cache (no second mvn run) and, with no grpc_target, is LOG-ONLY (grpc.enabled=false, no target)',
              b['state'] == 'running' and b['build']['cached'] is True and _runs(count) == 1 and 'grpc.enabled=false' in props2 and not [x for x in props2 if x.startswith('grpc.target')], str(b)[:200])
        fp1 = a['build_fp']
        r3 = cl.simulate_post('/bridges', json=dict(body, files=dict(base, **{'src/main/java/A.java': 'class A { int x; }'}), session_id='uno-light-789'))
        c = wait(r3.json['id'], ('running', 'failed'))
        pids.append(c.get('pid'))
        check('sim-2 worker: changed code = a different fingerprint = a second build (cached by the project sha, not by the bridge name)', c['build_fp'] != fp1 and _runs(count) == 2, '%s %s' % (c.get('build_fp'), _runs(count)))
        r4 = cl.simulate_post('/bridges', json=dict(body, session_id='x'))
        check('sim-2 worker: the cap is enforced in words (3 live, the 4th is a 503 naming the limit)', r4.status_code == 503 and 'limit' in r4.json['error'], str(r4.json))
        lst = cl.simulate_get('/bridges').json
        check('sim-2 worker: GET /bridges lists the three (no files, no properties in the listing)', len(lst['bridges']) == 3 and 'files' not in str(lst) and lst['max'] == 3)
        for pid in pids:
            os.kill(pid, 0)
        dele = cl.simulate_delete('/bridges/%s' % a['id'])
        time.sleep(0.3)
        gone = not os.path.exists('/proc/%d' % a['pid']) or open('/proc/%d/stat' % a['pid']).read().split(')')[1].split()[0] == 'Z'
        check('sim-2 worker: DELETE stops the process and removes its state', dele.json.get('stopped') and gone and cl.simulate_get('/bridges/%s' % a['id']).status_code == 404
              and not os.path.exists(os.path.join(bh.DIR, '%s.properties' % a['id'])))
        os.kill(b['pid'], 9)
        time.sleep(0.3)
        bh.reap()
        e = cl.simulate_get('/bridges/%s' % b['id']).json
        check('sim-2 worker: a bridge process that dies by itself is noticed and marked ended with the reason', e['state'] == 'ended' and 'exited' in e['end_reason'], str(e)[:200])
        t = cl.simulate_post('/bridges', json=dict(body, ttl_s=1, session_id='ttl'))
        tw = wait(t.json['id'], ('running',))
        time.sleep(1.4)
        bh.reap()
        te = cl.simulate_get('/bridges/%s' % tw['id']).json
        check('sim-2 worker: the TTL reaper ends a bridge past its TTL and kills the process', te['state'] == 'ended' and 'TTL' in te['end_reason'] and not os.path.exists('/proc/%d/cmdline' % tw['pid']), str(te)[:200])
        f = cl.simulate_post('/bridges', json=dict(body, files=dict(base, **{'pom.xml': '<project>FAIL</project>'}), session_id='bad'))
        fe = wait(f.json['id'], ('failed', 'running'))
        check('sim-2 worker: a build that fails is reported failed with a pointer to the build log (no process, no jar cached)', fe['state'] == 'failed' and 'mvn package failed' in fe['end_reason']
              and any('BUILD FAILURE' in ln for ln in cl.simulate_get('/bridges/%s/logs' % fe['id'], params={'which': 'build'}).json['lines']), str(fe)[:200])
        bad = [cl.simulate_post('/bridges', json={k: v for k, v in body.items() if k != 'files'}),
               cl.simulate_post('/bridges', json=dict(body, files=dict(base, **{'src/../../etc/x': 'y'}))),
               cl.simulate_post('/bridges', json=dict(body, twin_port=0)),
               cl.simulate_post('/bridges', json=dict(body, ttl_s=99999)),
               cl.simulate_post('/bridges', json=dict(body, grpc_target='no port here')),
               cl.simulate_post('/bridges', json=dict(body, twin_host='a b; rm'))]
        check('sim-2 worker: bad input is refused in words with a 400 (no files, a path outside the project, port 0, a huge ttl, a bad gRPC target, a bad host)',
              all(x.status_code == 400 and x.json['error'] for x in bad), str([x.json for x in bad])[:300])
        cap = bh.info()
        check('sim-2 worker: info() reports available when java + mvn are found, with the cached jar count', cap['available'] and cap['cached_jars'] == 2 and cap['max'] == 3, str(cap))
    finally:
        for s in bh._all():
            try:
                if s['state'] in ('building', 'running'):
                    bh._kill(s)
            except Exception:  # noqa: BLE001
                pass
        for pid in pids:
            try:
                os.kill(pid, 9)
            except (OSError, TypeError):
                pass
    left = [pid for pid in pids if pid and os.path.exists('/proc/%d/cmdline' % pid) and open('/proc/%d/cmdline' % pid).read()]
    check('sim-2 worker: no bridge process left running after the checks', not left, str(left))


# ---------------------------------------------------------------------------------------------------------------- the JVM
def jvm_twin_mode(check, skip):
    javac, java = shutil.which('javac'), shutil.which('java')
    if not (javac and java):
        return skip('brg-0 JVM twin mode', 'no JDK on PATH')
    from board.custom import light_twin as LT
    from grpcbridge.custom import wire_ref
    from hwnocode.custom import offline_project as OP
    from grpcbridge.custom.hosted_fakes import FakeUsart
    rep = OP.light_project(grpc_target='localhost:3002')
    if not rep.get('ok'):
        return check('brg-0: the uno-light project generates', False, str(rep.get('error')))
    fmap, spec = LT._spec()

    def frame(seq, led_on=False, toggles=0, source='command'):
        vals = dict(name='uno-light', seq=seq, status='idle', boot_session=77, led_on=led_on, toggles=toggles, source=source)
        return wire_ref.frame(1, 1, seq, wire_ref.encode(spec, vals), version=spec['wire_version'])

    usart = FakeUsart([[frame(1), frame(2, True, 1, 'button')], [frame(3, False, 2, 'command')]])
    with tempfile.TemporaryDirectory(prefix='polari-brg0-') as tmp:
        for path, text in rep['files'].items():
            dest = os.path.join(tmp, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w') as f:
                f.write(text)
        core = [os.path.join(dp, fn) for dp, _d, fns in os.walk(os.path.join(tmp, 'src/main/java')) for fn in fns if fn.endswith('.java') and '/grpc' not in dp]
        comp = subprocess.run([javac, '--release', '17', '-d', os.path.join(tmp, 'out')] + core, capture_output=True, text=True)
        check('brg-0: the generated uno-light core (with TcpDevicePort) compiles with javac', comp.returncode == 0, comp.stderr[:600])
        if comp.returncode != 0:
            return
        props = [ln for ln in rep['files']['bridge.properties'].splitlines() if ln.split('=', 1)[0] not in ('source', 'twin.host', 'twin.port', 'grpc.enabled', 'serial.device')]
        props += ['source=twin-tcp', 'twin.host=127.0.0.1', 'twin.port=%d' % usart.port, 'grpc.enabled=false']
        with open(os.path.join(tmp, 'twin.properties'), 'w') as f:
            f.write('\n'.join(props) + '\n')
        try:
            run = subprocess.run([java, '-cp', os.path.join(tmp, 'out'), 'org.polari.bridge.BridgeMain', os.path.join(tmp, 'twin.properties'), '--max-frames=3'],
                                 capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as e:
            run = subprocess.CompletedProcess(e.cmd, 124, (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''), 'timeout')
        usart.finished.wait(5)
        usart.close()
        out = run.stdout
        got = [ln for ln in out.splitlines() if 'LightState' in ln and '[bridge] seq=' in ln]
        check('brg-0: source=twin-tcp - the bridge connected to the twin\'s USART port and DECODED the LightState frames (led_on / toggles / source as sent, in order), the proof '
              'of the twin-session mode', run.returncode == 0 and len(got) == 3 and 'on twin-tcp 127.0.0.1:%d' % usart.port in out and 'toggles=1' in got[1]
              and 'toggles=2' in got[2], out[-900:] + run.stderr[-300:])
        check('brg-0: the port closing is a RECONNECT, not a crash: tcp-lost, then tcp-open attempt 2, no gap in the sequence, reconnects=1 on the last frame', '"t":"tcp-lost"' in out
              and '"t":"tcp-open"' in out and '"attempt":2' in out and 'gaps=0' in got[-1] and 'reconnects=1' in got[-1] and usart.connections == 2, out[-600:])
        check('brg-0: LightState declares no snapshot field, so NOTHING is sent down on attach (the serial port\'s rule, kept): no bytes reached the port on either connection',
              len(usart.received) == 2 and not any(usart.received) and 'snapshot-requested' not in out, str([len(b) for b in usart.received]))
