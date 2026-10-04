"""brd-wire PROBE (grpc-j4, his ruling 2026-10-02) — N simavr UNO twins on ONE bridge, the computer↔firmware mapping
end to end: the SAME firmware built N times (instance_index 0..N-1), one HardwareInterfaceBinding per twin, the GENERATED
Java bridge opening one pty per binding, the index in the frame, the identity only in the gRPC message.

  n = 2  bridge uno-pair (the SEEDED bindings: rows uno-twin-0 / uno-twin-1)      → a 1-bit index
  n = 3  bridge uno-trio (three bindings made here: rows trio-twin-0..2)          → a 2-bit index (his clarification:
                                                                                      "if we have 3 we should change")
For each: every row follows ITS twin (each twin's ADC0 is held at a different voltage, so each row's temp_c names the
board it came from) — index routing UP; a PUT to row k changes ONLY twin k's PWM (simavr's OCR0A) — index routing DOWN;
led_on set true then false → the row returns to false (the presence mask, brd-fi finding (1)); the binding chain of a
twin answers from GET /api/board/instances/<instance>/interface. n = 4..257 is proven at the unit level (board selftest
`mapping`, c_twin, javabridge — fakes, said so there).

A THROWAWAY server is booted in-process (tests/board_probe_boot.py: the framework as cwd for the boot, the sqlite DB in
./data of the throwaway dir). Skips honestly without the twin, java or mvn.

  mkdir -p /tmp/p && cd /tmp/p && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_pair_probe.py [--only 2|3] [--json out.json]
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.parse
import urllib.request

os.environ['POLARI_MODULES'] = 'hwmap,grpcbridge,board'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK)
sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
results = []
REPORT = {}
CLS = 'SimRigState'


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra != '' and not cond else ''), flush=True)


def http(method, url, body=None, ctype='application/json', timeout=60):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': ctype} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def multipart(fields):
    b = '----polari-pair-probe'
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    out.write(('--%s--\r\n' % b).encode())
    return out.getvalue(), 'multipart/form-data; boundary=%s' % b


def temp_at(mv):
    """What the firmware reports for ADC0 held at mv on the twin (simavr: count = mV·1023/5000; TMP36: (mV − 500)/10)."""
    return (int(mv * 1023 / 5000) * 5000.0 / 1024.0 - 500.0) / 10.0


def run_bridge(manager, api, grpc_port, bridge, n, prefix, here):
    from grpcbridge.mapping_basis import HardwareInterfaceBinding
    from grpcbridge.custom import wire_contract as W
    from board.custom import gen, build, twin
    tag = '%s(n=%d)' % (bridge, n)
    rep = REPORT.setdefault(bridge, {'n': n})
    # ---- the bindings (seeded for uno-pair; made here for uno-trio)
    rows = W.bindings(manager, bridge, CLS)
    if not rows:
        for k in range(n):
            b = HardwareInterfaceBinding(manager=manager, name='%s/%s/%d' % (bridge, CLS, k), bridge_name=bridge, object_class=CLS,
                                         object_name='%s-%d' % (prefix, k), board_instance='twin:arduino-uno-r3#%s%d' % (prefix[0], k),
                                         board_definition='arduino-uno-r3', interface_kind='twin-pty', interface_name='usart0',
                                         port=os.path.join(here, '%s-%d-uart' % (bridge, k)), instance_index=k, origin='probe')
            manager.db.saveInstanceInDB(b)
        rows = W.bindings(manager, bridge, CLS)
    spec = W.spec_for(manager, CLS, bridge)
    check('%s: %d bindings, indexes %s, ports %s → the index is %s, %d bit(s) (suggested %d) — width = f(n), never a constant'
          % (tag, len(rows), [r.instance_index for r in rows], [os.path.basename(r.port) for r in rows], spec['index_repr'],
             spec['index_width'], spec['suggested_index_width']),
          len(rows) == n and [r.instance_index for r in rows] == list(range(n)) and spec['index_width'] == W.index_width(n) and spec['index_repr'] == 'bits')
    # ---- the same firmware built n times
    builds, twins = [], []
    for k in range(n):
        work = os.path.join(here, '%s-work-%d' % (bridge, k))
        g = gen.gen('uno', work=work, variant='uno-pair', manager=manager, instance_index=k, bridge=bridge)
        b = build.build('uno', work)
        builds.append((g, b))
    hdr = {json.loads(g['classes_json'])[0]['header_sha256'] for g, _ in builds}
    v2 = {g['contract_hash_v2'] for g, _ in builds}
    check('%s: uno-pair built %d times (instance_index 0..%d): ONE header sha + ONE hash v2 %s, %d different .hex (%s B flash each)'
          % (tag, n, n - 1, list(v2)[0], len({b['artifact_sha256'] for _, b in builds}), '/'.join(str(b['flash_bytes']) for _, b in builds)),
          all(b['state'] == 'built' for _, b in builds) and len(hdr) == 1 and len(v2) == 1 and len({b['artifact_sha256'] for _, b in builds}) == n)
    rep['builds'] = [{'instance_index': g['instance_index'], 'flash_bytes': b['flash_bytes'], 'ram_bytes': b['ram_bytes'],
                      'artifact_sha256': b['artifact_sha256'], 'contract_hash_v2': g['contract_hash_v2']} for g, b in builds]
    mvs = [700 + 50 * k for k in range(n)]
    java = None
    try:
        for k, r in enumerate(rows):
            s = twin.up('uno', os.path.join(here, '%s-work-%d' % (bridge, k)), tcp=9850 + 10 * (n - 2) + k, link=r.port, adc0_mv=mvs[k],
                        tag='%s%d' % (bridge, k))
            twins.append(s)
        check('%s: %d simavr twins up, each its own container + pty at its binding\'s port' % (tag, n),
              all(s['alive'] for s in twins) and len({s.get('container') or s.get('pid') for s in twins}) == n)
        # ---- the bridge: one definition, generated from the bindings
        http('POST', api + '/api/grpc/bridges', {'bridgeName': bridge, 'classes': [CLS], 'source': 'serial', 'serialDevice': rows[0].port,
                                                 'grpcEnabled': True, 'grpcTarget': '127.0.0.1:%d' % grpc_port, 'deviceId': 3})
        tgz = http('GET', api + '/api/grpc/bridges/%s/download' % bridge)
        proj = os.path.join(here, 'bridge-%s' % bridge)
        shutil.rmtree(proj, ignore_errors=True)
        tarfile.open(fileobj=io.BytesIO(tgz)).extractall(proj)
        root = os.path.join(proj, os.listdir(proj)[0])
        props = open(os.path.join(root, 'bridge.properties')).read()
        codec = open(os.path.join(root, 'src/main/java/org/polari/bridge/codec/%sCodec.java' % CLS)).read()
        check('%s: the generated bridge carries the %d bindings (bridge.properties) and a %d-bit index codec; the WireContract row is derived'
              % (tag, n, spec['index_width']),
              'binding.count=%d' % n in props and 'INDEX_WIDTH = %d;' % spec['index_width'] in codec
              and any(getattr(w, 'name', '') == '%s@%s' % (CLS, bridge) for w in (manager.objectTables.get('WireContract') or {}).values()), props[-400:])
        t0 = time.time()
        mvn = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=900)
        if mvn.returncode != 0:
            mvn = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=1200)
        jar = os.path.join(root, 'target', 'polari-hw-bridge.jar')
        check('%s: mvn package of the generated bridge (%.0f s)' % (tag, time.time() - t0), mvn.returncode == 0 and os.path.isfile(jar), (mvn.stdout + mvn.stderr)[-600:])
        log_path = os.path.join(here, 'bridge-%s.log' % bridge)
        java = subprocess.Popen(['java', '-jar', jar, 'bridge.properties'], cwd=root, stdout=open(log_path, 'w'), stderr=subprocess.STDOUT)
        names = ['%s-%d' % (prefix, k) for k in range(n)] if bridge != 'uno-pair' else ['uno-twin-%d' % k for k in range(n)]

        def row(name):
            return next((o for o in (manager.objectTables.get(CLS) or {}).values() if getattr(o, 'name', '') == name), None)

        def wait(pred, s=8.0):
            t = time.time()
            while time.time() - t < s:
                if pred():
                    return time.time() - t
                time.sleep(0.1)
            return None

        dt = wait(lambda: all(row(nm) is not None and abs(float(getattr(row(nm), 'temp_c', 0) or 0) - temp_at(mvs[k])) < 1e-3
                              for k, nm in enumerate(names)), 20)
        temps = {nm: round(float(getattr(row(nm), 'temp_c', 0) or 0), 3) for nm in names if row(nm) is not None}
        check('%s: UP — each row follows ITS twin: %s (ADC0 held at %s mV → expected %s); the firmware sends no name, the binding is '
              'the identity' % (tag, temps, mvs, [round(temp_at(m), 3) for m in mvs]), dt is not None, temps)
        lines = [l for l in open(log_path) if l.startswith('[bridge] seq=')]
        idx_seen = sorted({int(l.split('index=')[1].split()[0]) for l in lines if 'index=' in l})
        check('%s: the bridge decoded frames carrying index %s in the prelude (and no name field)' % (tag, idx_seen),
              idx_seen == list(range(n)) and not any('name=' in l for l in lines[-20:]), lines[-2:])
        # ---- DOWN: a PUT to the LAST row reaches only the last twin
        last, first = names[-1], names[0]

        def put(name, values):
            o = row(name)
            body, ctype = multipart({'polariId': getattr(o, 'id', ''), 'updateData': json.dumps(values)})
            return http('PUT', api + '/' + CLS, body, ctype)

        def ocr(k):
            st = [json.loads(l) for l in open(twins[k]['log']) if l.startswith('{') and '"status"' in l]
            return st[-1]['ocr0a'] if st else None

        put(last, {'pwm_duty': 42})
        dt_last = wait(lambda: int(getattr(row(last), 'pwm_duty', 0) or 0) == 42 and getattr(row(last), 'status', '') == 'commanded')
        time.sleep(1.3)
        o_after = [ocr(k) for k in range(n)]
        check('%s: DOWN — PUT {pwm_duty: 42} on %s (index %d) → its row echoes commanded in %s s; simavr OCR0A per twin %s (only twin %d = 107)'
              % (tag, last, n - 1, round(dt_last, 2) if dt_last else 'never', o_after, n - 1),
              dt_last is not None and o_after[-1] == 107 and all(x == 0 for x in o_after[:-1]), o_after)
        put(first, {'pwm_duty': 10})
        dt_first = wait(lambda: int(getattr(row(first), 'pwm_duty', 0) or 0) == 10)
        time.sleep(1.3)
        o_after2 = [ocr(k) for k in range(n)]
        check('%s: DOWN the other way — PUT {pwm_duty: 10} on %s (index 0) → OCR0A per twin %s (twin 0 = 25, twin %d keeps 107)'
              % (tag, first, o_after2, n - 1), dt_first is not None and o_after2[0] == 25 and o_after2[-1] == 107, o_after2)
        cmd_lines = [l.strip() for l in open(log_path) if l.startswith('[grpc] %s command ->' % CLS)]
        check('%s: the bridge logged each command routed to ONE binding by index: %s' % (tag, cmd_lines[-2:]),
              any('index %d' % (n - 1) in l for l in cmd_lines) and any('index 0' in l for l in cmd_lines))
        # ---- the presence mask (brd-fi finding (1)): the device's led_on=false must reach the ROW
        def pb5(k):
            ev = [json.loads(l) for l in open(twins[k]['log']) if l.startswith('{') and '"t":"pb5"' in l]
            return ev[-1]['v'] if ev else None

        put(last, {'led_on': True})
        d_on = wait(lambda: pb5(n - 1) == 1)
        put(last, {'led_on': False})
        d_off = wait(lambda: pb5(n - 1) == 0)

        def drained(s=1.0):   # frames already in flight from the high window land first — wait for 1 s of steady false
            t = time.time()
            while time.time() - t < s:
                if str(getattr(row(last), 'led_on', '')).lower() not in ('false', '0'):
                    return False
                time.sleep(0.05)
            return True
        d_drain = wait(drained, 15)
        stale = row(last)
        stale.led_on = True            # the row says true, NO command sent; the board (D13 low) keeps reporting false
        d_back = wait(lambda: str(getattr(row(last), 'led_on', '')).lower() in ('false', '0'), 3)
        held = []
        for _ in range(10):
            held.append(str(getattr(row(last), 'led_on', '')).lower())
            time.sleep(0.1)
        check('%s: presence mask — led_on PUT true → twin %d D13 high (%s s), PUT false → low (%s s), the row steady false (frames in '
              'flight drained); then the ROW is set true '
              'in-process with NO command: the next frame (led_on=false, present) brings it back to false in %s s and it stays %s '
              '(before brd-wire a false never reached the row)' % (tag, n - 1, round(d_on, 2) if d_on else 'never',
                                                                  round(d_off, 2) if d_off else 'never', round(d_back, 2) if d_back else 'never',
                                                                  sorted(set(held))),
              d_on is not None and d_off is not None and d_drain is not None and d_back is not None and d_back < 1.0
              and set(held) <= {'false', '0'})
        # ---- the analysis side
        inst = rows[-1].board_instance
        ch = http('GET', api + '/api/board/instances/%s/interface' % urllib.parse.quote(inst, safe=''))
        lk = (ch.get('links') or [{}])[0] if isinstance(ch, dict) else {}
        check('%s: GET /api/board/instances/%s/interface → %s (index %s, %s frames applied, wire %s %s-bit, the UNO, %d facts)'
              % (tag, inst, lk.get('object', {}).get('name'), lk.get('binding', {}).get('instance_index'), lk.get('binding', {}).get('frames_seen'),
                 lk.get('wire', {}).get('contract_hash_v2'), lk.get('wire', {}).get('index_width'), len(lk.get('datasheet_facts') or [])),
              isinstance(ch, dict) and ch.get('ok') and lk['object']['name'] == last and lk['binding']['instance_index'] == n - 1
              and lk['binding']['frames_seen'] > 0 and lk['wire']['index_width'] == spec['index_width'] and lk['hash_agrees']
              and lk['object']['fields'].get('pwm_duty') == 42, ch if not isinstance(ch, dict) else ch.get('error'))
        rep.update(temps=temps, mvs=mvs, index_seen=idx_seen, ocr_after_put_last=o_after, ocr_after_put_first=o_after2,
                   put_echo_s=[round(dt_last or -1, 2), round(dt_first or -1, 2)], led_back_to_false_s=round(d_back or -1, 2), commands=cmd_lines[-4:],
                   chain=ch.get('plain') if isinstance(ch, dict) else None, wire=spec['hash_v2'], index_width=spec['index_width'])
    finally:
        if java is not None:
            java.terminate()
            try:
                java.wait(10)
            except Exception:  # noqa: BLE001
                java.kill()
        for k in range(len(twins)):
            twin.down('uno', os.path.join(here, '%s-work-%d' % (bridge, k)))


def main(argv):
    out_json = argv[argv.index('--json') + 1] if '--json' in argv else ''
    only = int(argv[argv.index('--only') + 1]) if '--only' in argv else 0
    from board.custom import board_engines as be
    tw = be.resolve('avr-twin')
    missing = [x for x, ok in (('the simavr twin (%s)' % tw['why'], tw['how'] in ('local-binary', be.LOCAL_IMAGE)),
                               ('java', shutil.which('java')), ('mvn', shutil.which('mvn'))) if not ok]
    if missing:
        print('SKIP: %s' % '; '.join(missing))
        return 0
    from board_probe_boot import boot
    here = os.getcwd()
    manager = boot(FRAMEWORK, here)
    os.environ['POLARI_BOARD_HOME'] = os.path.join(here, 'board-home')
    from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn
    from grpcbridge.custom.grpc_server import PolariGrpcServer, set_grpc_server
    from polariDataTyping.schema_stability import set_status_knob
    from grpcbridge.objects.hwsim.SimRigState import SimRigState

    class TS(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class Quiet(WSGIRequestHandler):
        def log_message(self, *a):
            pass
    httpd = make_server('127.0.0.1', 0, manager.polServer.falconServer, server_class=TS, handler_class=Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    api = 'http://127.0.0.1:%d' % httpd.server_port
    grpc_srv = PolariGrpcServer(manager, port=0)
    grpc_srv.start()
    set_grpc_server(grpc_srv)
    try:
        seed = SimRigState(manager=manager, name='pair-seed', uptime_ms=1, temp_c=1.5, pwm_duty=1, led_on=True, status='seeded')
        manager.db.saveInstanceInDB(seed)
        st = set_status_knob(manager, CLS, 'stabilize')
        exp = http('POST', api + '/api/grpc/exposures/%s' % CLS, {'action': 'enable'})
        tr = http('POST', api + '/api/grpc/exposures/%s' % CLS, {'action': 'set-transport', 'transport': 'both'})
        check('a throwaway server (HTTP %s, gRPC :%s); SimRigState stabilized, exposed (contract v%s), Commands leg on'
              % (api, grpc_srv.port, exp.get('version')), st.get('ok') and exp.get('ok') and tr.get('ok'), (exp, tr))
        if only in (0, 2):
            run_bridge(manager, api, grpc_srv.port, 'uno-pair', 2, 'uno-twin', here)
        if only in (0, 3):
            run_bridge(manager, api, grpc_srv.port, 'uno-trio', 3, 'trio-twin', here)
    finally:
        grpc_srv.stop()
        httpd.shutdown()
    if out_json:
        json.dump(REPORT, open(out_json, 'w'), indent=1, default=str)
    print('\n%d/%d pair probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
