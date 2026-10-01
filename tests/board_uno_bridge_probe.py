"""brd-1 PROBE — the FULL loop on the UNO twin: Polari server ↔ gRPC ↔ the generated Java Hardware Bridge ↔ the pty ↔
simavr running the UNO .hex. No UNO is attached; this is the plan's brd-1 proof with the board's serialDevice swapped
for the twin's pty link (plan §0 step 5: "the only difference is serialDevice").

A THROWAWAY server is booted in-process (sqlite in the cwd, HTTP on an ephemeral port, the gRPC sidecar on an
ephemeral port) — nothing running is touched. Steps:
  1. SimRigState stabilized + its gRPC exposure enabled (+ set-transport both) → a contract generated HERE
  2. `pol board gen uno --api <this server>` fetches the LIVE header (?target=avr) → build → twin up (pty link)
  3. a bridge definition {source: serial, serialDevice: <link>, grpcEnabled} → the project downloaded → mvn package →
     java -jar (the generated app, unchanged)
  4. the `uno-twin` SimRigState row updates at ~10 Hz (uptime_ms, temp_c from the TMP36 stimulus)
  5. a REST PUT {led_on: true, pwm_duty: 42} rides the Commands stream down; the firmware applies it; the row echoes
     status=commanded; simavr shows PORTB5 high and OCR0A = 107
Skips honestly when the twin, java or mvn is missing.

  mkdir -p /tmp/x && cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_uno_bridge_probe.py [--json out.json]
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
import urllib.request

os.environ['POLARI_MODULES'] = 'hwmap,grpcbridge,board'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []
REPORT = {}


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra != '' else ''), flush=True)


def http(method, url, body=None, ctype='application/json', timeout=60):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': ctype} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def multipart(fields):
    b = '----polari-board-probe'
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    out.write(('--%s--\r\n' % b).encode())
    return out.getvalue(), 'multipart/form-data; boundary=%s' % b


def main(argv):
    out_json = argv[argv.index('--json') + 1] if '--json' in argv else ''
    from board.custom import board_engines as be
    tw = be.resolve('avr-twin')
    missing = [n for n, ok in (('the simavr twin (%s)' % tw['why'], tw['how'] in ('local-binary', be.LOCAL_IMAGE)),
                               ('java', shutil.which('java')), ('mvn', shutil.which('mvn'))) if not ok]
    if missing:
        print('SKIP: %s' % '; '.join(missing))
        return 0
    from objectTreeManagerDecorators import managerObject
    from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn
    from grpcbridge.custom.grpc_server import PolariGrpcServer, set_grpc_server
    from polariDataTyping.schema_stability import set_status_knob
    from grpcbridge.objects.hwsim.SimRigState import SimRigState
    from board.custom import gen, build, twin

    manager = managerObject(hasServer=True, hasDB=True)

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
    check('a throwaway server: HTTP %s, gRPC :%s (in-process, sqlite in the cwd)' % (api, grpc_srv.port), grpc_srv._running)

    row = SimRigState(manager=manager, name='uno-twin', uptime_ms=0, temp_c=0.0, pwm_duty=0, led_on=False, status='seeded')
    manager.db.saveInstanceInDB(row)
    st = set_status_knob(manager, 'SimRigState', 'stabilize')
    exp = http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'enable'})
    tr = http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'set-transport', 'transport': 'both'})
    check('SimRigState stabilized + gRPC exposure enabled (contract v%s) + set-transport both (the Commands leg)' % exp.get('version'),
          st.get('ok') and exp.get('ok') and tr.get('ok'), (exp, tr))

    work = os.path.abspath('uno-work')
    link = os.path.abspath('uno-uart')
    g = gen.gen('uno', ['SimRigState'], work, api=api, rig_name='uno-twin')
    cls = json.loads(g['classes_json'])[0]
    check('gen --api: the LIVE header (target=avr) from this server, contract hash %s' % cls['contract_hash'], cls['source'] == 'live' and cls['contract_hash'])
    b = build.build('uno', work)
    check('build: %s, flash %s B / RAM %s B' % (b['state'], b.get('flash_bytes'), b.get('ram_bytes')), b['state'] == 'built')
    s = twin.up('uno', work, tcp=int(os.environ.get('UNO_TWIN_TCP', '9838')), link=link, adc0_mv=750)
    java = None
    try:
        check('twin up (%s) with its UART at %s' % (s['how'], link), s['alive'])
        r = http('POST', api + '/api/grpc/bridges', {'bridgeName': 'uno-twin', 'classes': ['SimRigState'], 'source': 'serial', 'serialDevice': link,
                                                    'grpcEnabled': True, 'grpcTarget': '127.0.0.1:%d' % grpc_srv.port, 'deviceId': 3})
        tgz = http('GET', api + '/api/grpc/bridges/uno-twin/download')
        proj = os.path.abspath('bridge')
        shutil.rmtree(proj, ignore_errors=True)
        tarfile.open(fileobj=io.BytesIO(tgz)).extractall(proj)
        root = next(os.path.join(proj, d) for d in os.listdir(proj)) if not os.path.exists(os.path.join(proj, 'pom.xml')) else proj
        props = open(os.path.join(root, 'bridge.properties')).read()
        check('the bridge definition is serial at the twin\'s link, gRPC on (the generated bridge.properties)',
              r.get('ok') and 'source=serial' in props and 'serial.device=%s' % link in props and 'grpc.enabled=true' in props, props)
        t0 = time.time()
        mvn = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=900)
        if mvn.returncode != 0:   # the offline repo may lack a plugin: one online attempt
            mvn = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=1200)
        jar = os.path.join(root, 'target', 'polari-hw-bridge.jar')
        check('mvn package of the generated bridge (%.0f s)' % (time.time() - t0), mvn.returncode == 0 and os.path.isfile(jar), (mvn.stdout + mvn.stderr)[-800:])
        java = subprocess.Popen(['java', '-jar', jar, 'bridge.properties'], cwd=root, stdout=open('bridge.log', 'w'), stderr=subprocess.STDOUT)
        time.sleep(6)

        def row_now():
            for v in (manager.objectTables.get('SimRigState') or {}).values():
                if getattr(v, 'name', '') == 'uno-twin':
                    return {k: getattr(v, k) for k in ('uptime_ms', 'temp_c', 'pwm_duty', 'led_on', 'status')}, v
            return {}, None
        seqs = lambda: sum(1 for l in open('bridge.log') if l.startswith('[bridge] seq='))  # noqa: E731
        a, _ = row_now(); ta = time.time(); na = seqs()
        time.sleep(3)
        z, obj = row_now(); tz = time.time(); nz = seqs()
        hz = (nz - na) / (tz - ta)
        check('the generated Java bridge decodes %.2f SimRigState frames/s from the pty (10 Hz expected)' % hz, 9.0 <= hz <= 11.0, nz - na)
        REPORT['bridge_frames_per_s'] = round(hz, 3)
        rate = (int(z.get('uptime_ms') or 0) - int(a.get('uptime_ms') or 0)) / 1000.0 / (tz - ta) if a and z else 0
        check('the uno-twin SimRigState ROW follows the firmware: uptime_ms %s → %s over %.1f s wall (sim/wall %.2f), status %s'
              % (a.get('uptime_ms'), z.get('uptime_ms'), tz - ta, rate, z.get('status')),
              z and int(z['uptime_ms']) > int(a.get('uptime_ms') or 0) > 0 and 0.8 <= rate <= 1.2 and z['status'] == 'ok', (a, z))
        check('temp_c in the row = the TMP36 formula at 750 mV (24.707 °C)', z and abs(float(z['temp_c']) - 24.70703125) < 1e-3, z.get('temp_c'))
        REPORT['row_before_put'] = z
        pid = getattr(obj, 'id', '') or getattr(obj, 'polariId', '')
        body, ctype = multipart({'polariId': pid, 'updateData': json.dumps({'led_on': True, 'pwm_duty': 42})})
        put = http('PUT', api + '/SimRigState', body, ctype)
        tp = time.time()
        echo = {}
        while time.time() - tp < 5:
            echo, _ = row_now()
            if echo.get('status') == 'commanded' and int(echo.get('uptime_ms') or 0) > int(z['uptime_ms']):
                break
            time.sleep(0.1)
        t_echo = time.time() - tp
        check('REST PUT {led_on: true, pwm_duty: 42} → Commands → the bridge → the firmware → the row echoes status=commanded, led_on, pwm 42 (%.2f s)' % t_echo,
              echo.get('status') == 'commanded' and str(echo.get('led_on')).lower() in ('true', '1') and int(echo.get('pwm_duty') or 0) == 42, (put if not isinstance(put, dict) else put.get('ok', put), echo))
        time.sleep(1.2)
        log = [json.loads(l) for l in open(s['log']) if l.startswith('{')]
        pb5 = [x for x in log if x.get('t') == 'pb5' and x.get('v') == 1]
        stl = [x for x in log if x.get('t') == 'status']
        check('simavr: PORTB5 (D13) high, OCR0A = 107 (42 % of 255)', bool(pb5) and stl and stl[-1]['ocr0a'] == 107, (pb5[:1], stl[-1]['ocr0a'] if stl else None))
        REPORT.update(echo_row=echo, put_echo_s=round(t_echo, 2), rate_sim_per_wall=round(rate, 3), pb5=pb5[:1], last_status=stl[-1] if stl else None,
                      contract=cls, build={k: b[k] for k in ('size_text', 'size_data', 'size_bss', 'artifact_sha256')})
    finally:
        if java is not None:
            java.terminate()
            try:
                java.wait(10)
            except Exception:
                java.kill()
        twin.down('uno', work)
        grpc_srv.stop() if hasattr(grpc_srv, 'stop') else None
        httpd.shutdown()
    if out_json:
        json.dump(REPORT, open(out_json, 'w'), indent=1, default=str)
    print('\n%d/%d bridge probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
