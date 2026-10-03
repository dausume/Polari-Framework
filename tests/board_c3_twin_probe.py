"""sc-3 PROBE — the ESP32-C3 twin end to end: Polari server ↔ gRPC ↔ the generated Java Hardware Bridge ↔ the pty ↔
Espressif's QEMU fork running the C3 image (ESP-IDF v5.5.5, FreeRTOS). No C3 is on hand; this is the twin-first proof with
the board's port swapped for the twin's pty link — the SAME bridge the UNO twin uses (board_uno_bridge_probe.py).

A THROWAWAY server is booted in-process (sqlite in the cwd, HTTP + the gRPC sidecar on ephemeral ports) — nothing running is
touched. Steps:
  1. SimRigState stabilized + its gRPC exposure enabled (+ set-transport both)
  2. `pol board gen c3 --variant c3-sim-rig --api <this server>` fetches the LIVE header (?target=host) → `build c3` through
     the esp engines (prf-esp-engines) → `flash c3` renders the esptool argv (DRY-RUN) → `twin c3 up` (QEMU, UART0 → pty)
  3. the pty alone: the reference parser decodes the frames after the ROM's boot text (0 bad CRC)
  4. a bridge definition {source: serial, serialDevice: <link>, grpcEnabled} → mvn package → java -jar (the generated app)
  5. the `c3-twin` SimRigState row follows (uptime_ms, status ok); a REST PUT {led_on: true, pwm_duty: 42} rides Commands down;
     the FreeRTOS rx task applies it; the row echoes status=commanded
  6. twin down; the twin's cost row is the committed one (BoardSimCost esp32-c3:qemu:esp32c3)
Skips honestly (exit 0, says why) when the esp engines image, java or mvn is missing.

  mkdir -p /tmp/x && cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_c3_twin_probe.py [--json out.json] [--no-bridge]
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
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
results = []
REPORT = {}


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra != '' and not cond else ''), flush=True)


def pty_frames(link, seconds, fm):
    """fm = the field map the firmware was generated from (THIS server's live contract — a fresh server's v1 tag order differs from
    the pinned v2 snapshot under the same contract hash: brd-1's finding)."""
    from board.custom import packet_ref
    from board.custom.compat import wire_spec
    spec = wire_spec(None, 'SimRigState', fm)
    fd = os.open(link, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    p, out, t0 = packet_ref.StreamParser(), [], time.time()
    try:
        while time.time() - t0 < seconds:
            try:
                b = os.read(fd, 4096)
            except BlockingIOError:
                b = b''
            for mt, dev, seq, payload, ver in p.feed(b):
                if mt == 1:
                    out.append((time.time(), packet_ref.decode_any(fm, payload, ver, spec)))
            time.sleep(0.02)
    finally:
        os.close(fd)
    return out, p


def main(argv):
    out_json = argv[argv.index('--json') + 1] if '--json' in argv else ''
    from board.custom import board_engines as be
    w = be.resolve('c3-run')
    bridge = '--no-bridge' not in argv
    missing = [n for n, ok in (('the C3 twin (%s)' % w['why'], w['how'] in ('local-binary', be.LOCAL_IMAGE)),
                               ('ESP-IDF (%s)' % be.resolve('idf-build')['why'], be.resolve('idf-build')['how'] != 'refused'),
                               ('java', shutil.which('java') or not bridge), ('mvn', shutil.which('mvn') or not bridge)) if not ok]
    if missing:
        print('SKIP: %s' % '; '.join(missing))
        return 0
    from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn
    from grpcbridge.custom.grpc_server import PolariGrpcServer, set_grpc_server
    from polariDataTyping.schema_stability import set_status_knob
    from grpcbridge.objects.hwsim.SimRigState import SimRigState
    from board.custom import gen_c3, build_c3, flash_c3, twin_c3
    from board_probe_boot import boot
    manager = boot(FRAMEWORK)

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
    row = SimRigState(manager=manager, name='c3-twin', uptime_ms=0, temp_c=0.0, pwm_duty=0, led_on=False, status='seeded')
    manager.db.saveInstanceInDB(row)
    st = set_status_knob(manager, 'SimRigState', 'stabilize')
    exp = _http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'enable'})
    tr = _http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'set-transport', 'transport': 'both'})
    check('SimRigState stabilized + gRPC exposure enabled (contract v%s) + set-transport both' % exp.get('version'), st.get('ok') and exp.get('ok') and tr.get('ok'))

    work = os.path.abspath('c3-work')
    link = os.path.abspath('c3-uart')
    g = gen_c3.gen_c3('c3-sim-rig', work, api=api, rig_name='c3-twin')
    cls = json.loads(g['classes_json'])[0]
    hdr = open(os.path.join(g['project_dir'], 'main', 'simrigstate_packets.h')).read()
    check('gen c3 --api: the LIVE header from this server, target=host (8-byte double), contract hash %s' % cls['contract_hash'],
          cls['source'] == 'live' and 'polari_avr_double_t' not in hdr and 'double temp_c;' in hdr)
    t0 = time.time()
    b = build_c3.build('c3', work)
    REPORT['build'] = {k: b.get(k) for k in ('name', 'state', 'size_text', 'size_data', 'size_bss', 'flash_bytes', 'ram_bytes', 'artifact_sha256', 'cache', 'build_cost')}
    check('build c3 through the esp engines (%s, %.0f s): app %s B, DRAM %s B, image sha256 %s' % (b.get('cache'), time.time() - t0, b.get('flash_bytes'),
                                                                                                b.get('ram_bytes'), (b.get('artifact_sha256') or '')[:16]),
          b['state'] == 'built')
    f = flash_c3.flash(work, '/dev/ttyACM0')
    REPORT['flash_dry_run'] = f['text']
    check('flash c3 DRY-RUN: %s' % f['text'][:110], f['dry_run'] and f['argv'][:8] == ['esptool.py', '--chip', 'esp32c3', '--port', '/dev/ttyACM0', '--baud', '460800', 'write_flash'])
    tcp = int(os.environ.get('C3_TWIN_TCP', '9839'))
    s = twin_c3.up(work, tcp=tcp, link=link)
    java = None
    try:
        check('twin c3 up (%s %s): QEMU esp32c3, UART0 at %s' % (s['how'], s.get('container') or s.get('pid'), link), s['alive'])
        from board.custom import compat
        fm = compat.server_header(manager, 'SimRigState', 1, 'host')['field_map']
        warm, _ = pty_frames(link, 4.0, fm)   # -icount shift=auto runs AHEAD for its first seconds (measured: ~35 s of uptime in ~2 s), then settles
        REPORT['warmup'] = {'frames': len(warm), 'uptime_ms_first_last': [warm[0][1]['uptime_ms'], warm[-1][1]['uptime_ms']] if warm else None}
        frames, p = pty_frames(link, 4.0, fm)
        ups = [v['uptime_ms'] for _, v in frames]
        hz = len(frames) / 4.0
        rate = ((ups[-1] - ups[0]) / 1000.0) / (frames[-1][0] - frames[0][0]) if len(frames) > 2 else 0
        REPORT['pty'] = {'frames_4s': len(frames), 'hz': hz, 'virtual_per_wall': round(rate, 3), 'bad_crc': p.bad_crc, 'last': frames[-1][1] if frames else None}
        check('the pty alone (after a 4 s warm-up: %s frames, uptime %s ms): %d SimRigState frames in 4 s (%.1f Hz), virtual/wall %.2f '
              '(-icount shift=auto), 0 bad CRC, name c3-twin, status ok' % (REPORT['warmup']['frames'], REPORT['warmup']['uptime_ms_first_last'], len(frames), hz, rate), 5 <= hz <= 12 and 0.6 <= rate <= 1.3 and p.bad_crc == 0 and frames[-1][1].get('name') == 'c3-twin'
              and frames[-1][1].get('status') == 'ok', REPORT['pty'])
        if not bridge:
            return _done(out_json)
        r = _http('POST', api + '/api/grpc/bridges', {'bridgeName': 'c3-twin', 'classes': ['SimRigState'], 'source': 'serial', 'serialDevice': link,
                                                     'grpcEnabled': True, 'grpcTarget': '127.0.0.1:%d' % grpc_srv.port, 'deviceId': 7})
        tgz = _http('GET', api + '/api/grpc/bridges/c3-twin/download')
        proj = os.path.abspath('bridge')
        shutil.rmtree(proj, ignore_errors=True)
        tarfile.open(fileobj=io.BytesIO(tgz)).extractall(proj)
        root = next(os.path.join(proj, d) for d in os.listdir(proj)) if not os.path.exists(os.path.join(proj, 'pom.xml')) else proj
        props = open(os.path.join(root, 'bridge.properties')).read()
        check('the bridge definition is serial at the C3 twin\'s link, gRPC on', r.get('ok') and 'source=serial' in props and 'serial.device=%s' % link in props)
        t0 = time.time()
        mvn = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=900)
        if mvn.returncode != 0:
            mvn = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=1200)
        jar = os.path.join(root, 'target', 'polari-hw-bridge.jar')
        check('mvn package of the generated bridge (%.0f s) — the same generator as the UNO\'s' % (time.time() - t0), mvn.returncode == 0 and os.path.isfile(jar),
              (mvn.stdout + mvn.stderr)[-800:])
        java = subprocess.Popen(['java', '-jar', jar, 'bridge.properties'], cwd=root, stdout=open('bridge.log', 'w'), stderr=subprocess.STDOUT)
        time.sleep(6)

        def row_now():
            for v in (manager.objectTables.get('SimRigState') or {}).values():
                if getattr(v, 'name', '') == 'c3-twin':
                    return {k: getattr(v, k) for k in ('uptime_ms', 'pwm_duty', 'led_on', 'status')}, v
            return {}, None
        a, _ = row_now(); ta = time.time()
        time.sleep(3)
        z, obj = row_now(); tz = time.time()
        rr = (int(z.get('uptime_ms') or 0) - int(a.get('uptime_ms') or 0)) / 1000.0 / (tz - ta) if a and z else 0
        check('the c3-twin SimRigState ROW follows the C3 firmware through the generated Java bridge: uptime_ms %s → %s over %.1f s (virtual/wall %.2f), '
              'status %s' % (a.get('uptime_ms'), z.get('uptime_ms'), tz - ta, rr, z.get('status')),
              z and int(z['uptime_ms']) > int(a.get('uptime_ms') or 0) > 0 and 0.6 <= rr <= 1.3 and z['status'] == 'ok', (a, z))
        pid = getattr(obj, 'id', '') or getattr(obj, 'polariId', '')
        body, ctype = _multipart({'polariId': pid, 'updateData': json.dumps({'led_on': True, 'pwm_duty': 42})})
        _http('PUT', api + '/SimRigState', body, ctype)
        tp = time.time()
        echo = {}
        while time.time() - tp < 8:
            echo, _ = row_now()
            if echo.get('status') == 'commanded' and int(echo.get('uptime_ms') or 0) > int(z['uptime_ms']):
                break
            time.sleep(0.1)
        t_echo = time.time() - tp
        check('REST PUT {led_on: true, pwm_duty: 42} → Commands → the bridge → UART0 → the FreeRTOS rx task → the row echoes status=commanded, led_on, '
              'pwm 42 (%.2f s)' % t_echo, echo.get('status') == 'commanded' and str(echo.get('led_on')).lower() in ('true', '1')
              and int(echo.get('pwm_duty') or 0) == 42, echo)
        REPORT.update(row=z, echo=echo, put_echo_s=round(t_echo, 2), row_virtual_per_wall=round(rr, 3), contract=cls)
    finally:
        if java is not None:
            java.terminate()
            try:
                java.wait(10)
            except Exception:
                java.kill()
        d = twin_c3.down(work)
        check('twin c3 down (the trace tail: %s)' % ' | '.join(d.get('trace_tail') or [])[:120], d['state'] == 'down')
        grpc_srv.stop() if hasattr(grpc_srv, 'stop') else None
        httpd.shutdown()
    from board.board_seed import BOARD_SEED_PAIRS
    c3 = [x for x in next(r for n, _, r in BOARD_SEED_PAIRS if n == 'BoardSimCost') if x['board'] == 'esp32-c3']
    check('BoardSimCost esp32-c3:qemu:esp32c3 seeded from the committed measurement: %s' % (c3[0]['notes'][:120] if c3 else '—'), len(c3) == 1)
    return _done(out_json)


def _done(out_json):
    if out_json:
        json.dump(REPORT, open(out_json, 'w'), indent=1, default=str)
    print('\n%d/%d C3 twin probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


def _http(method, url, body=None, ctype='application/json', timeout=60):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': ctype} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _multipart(fields):
    b = '----polari-c3-probe'
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    out.write(('--%s--\r\n' % b).encode())
    return out.getvalue(), 'multipart/form-data; boundary=%s' % b


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
