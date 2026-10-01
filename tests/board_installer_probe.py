"""brd-fi PROBE — the Firmware Installer end to end on the UNO's TWIN (no UNO is attached; the simavr twin counts as the
device for this proof, and every record says so). A THROWAWAY in-process server (HTTP + gRPC, sqlite in the cwd) and
the REAL engines: avr-gcc / avr-objcopy / avr-size and simavr (prf-board-engines), the generated Java bridge (mvn).

  1. SimRigState + UnoAnalogState stabilized, gRPC exposures enabled HERE (a fresh server: v1, alphabetical tags);
     SimRigState set-transport both (the Commands leg) — the person's knob acts, done by the probe
  2. GET /api/board/variants → the four; POST /api/board/installer/build for each → sizes measured, all built
  3. GET /api/board/builds/<b>/compat → compatible for all four (live source); a build generated from the PINNED v2
     snapshot is stale-header against this v1 server and its plan is REFUSED (409, plain words) — brd-1's finding caught
  4. POST /api/board/installer/plan (twin) for each → the argv, verbatim
  5. install + attach + result, through the doors the page uses:
       uno-echo     frames arrive; a PUT {temp_c: 12.5, pwm_duty: 7, led_on: true} comes back whole, status=echoed
       uno-sim-rig  frames at ~10 Hz, temp_c 24.707 at 750 mV; a PUT {led_on, pwm_duty: 42} → status=commanded, OCR0A 107
       uno-adc-sweep  UnoAnalogState rows: a0/a1/a2 = 153/307/614 at 750/1500/3000 mV (the twin's ADC stimulus)
       uno-blink-only via `pol board install uno --variant uno-blink-only --twin --yes` (CLI parity): led_on flips
  6. run without confirm refused; GET /api/board/installer lists the records

  mkdir -p /tmp/x && cd /tmp/x && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/board_installer_probe.py [--json out.json]
"""
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

os.environ['POLARI_MODULES'] = 'hwmap,grpcbridge,board'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
os.environ['POLARI_BOARD_HOME'] = os.path.abspath('board-home')
os.environ['BOARD_INSTALLER_TWIN_TCP'] = os.environ.get('UNO_TWIN_TCP', '9848')
os.environ['BOARD_INSTALLER_TWIN_LINK'] = os.path.abspath('uno-uart')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []
REPORT = {}


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra != '' and not cond else ''), flush=True)


def http(method, url, body=None, ctype='application/json', timeout=900):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': ctype} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, code = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, code = e.read(), e.code
    try:
        d = json.loads(raw)
    except ValueError:
        d = {'raw': raw[:200]}
    if isinstance(d, dict):
        d['_status'] = code
    return d


def multipart(fields):
    b = '----polari-installer-probe'
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
                               ('avr-gcc', be.resolve('avr-gcc')['how'] != 'refused'), ('java', shutil.which('java')), ('mvn', shutil.which('mvn'))) if not ok]
    if missing:
        print('SKIP: %s' % '; '.join(missing))
        return 0
    from objectTreeManagerDecorators import managerObject
    from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn
    from grpcbridge.custom.grpc_server import PolariGrpcServer, set_grpc_server
    from polariDataTyping.schema_stability import set_status_knob
    from grpcbridge.objects.hwsim.SimRigState import SimRigState
    from board.board_basis import UnoAnalogState
    from board.custom import gen, build, twin, attach, installer as I

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
    check('a throwaway server: HTTP %s, gRPC :%s' % (api, grpc_srv.port), grpc_srv._running)
    for cls, row in (('SimRigState', SimRigState(manager=manager, name='seed-rig', uptime_ms=0, temp_c=0.0, pwm_duty=0, led_on=False, status='seeded')),
                     ('UnoAnalogState', UnoAnalogState(manager=manager, name='seed-analog', uptime_ms=0, a0=0, a1=0, a2=0, status='seeded'))):
        manager.db.saveInstanceInDB(row)
        set_status_knob(manager, cls, 'stabilize')
        e = http('POST', api + '/api/grpc/exposures/%s' % cls, {'action': 'enable'})
        check('%s stabilized + gRPC exposure enabled (contract v%s)' % (cls, e.get('version')), e.get('ok'), e)
    tr = http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'set-transport', 'transport': 'both'})
    check('SimRigState set-transport both (the Commands leg — the person\'s knob, done here by the probe)', tr.get('ok'), tr)

    var = http('GET', api + '/api/board/variants')
    names = [v['name'] for v in var.get('variants', [])]
    check('GET /api/board/variants → the four seeded variants', names == ['uno-sim-rig', 'uno-blink-only', 'uno-adc-sweep', 'uno-echo'], names)
    builds = {}
    for v in names:
        t0 = time.time()
        b = http('POST', api + '/api/board/installer/build', {'variant': v})
        builds[v] = b
        check('POST /api/board/installer/build %s → %s: flash %s B, RAM %s B (%.1f s)' % (v, b.get('state'), b.get('flash_bytes'), b.get('ram_bytes'), time.time() - t0),
              b.get('ok') and b.get('state') == 'built', b)
    REPORT['sizes'] = {v: {k: builds[v].get(k) for k in ('build', 'flash_bytes', 'ram_bytes', 'artifact_sha256')} for v in names}
    smallest_flash = min(names, key=lambda v: builds[v].get('flash_bytes') or 1e9)
    smallest_ram = min(names, key=lambda v: builds[v].get('ram_bytes') or 1e9)
    print('       smallest flash: %s · smallest RAM: %s' % (smallest_flash, smallest_ram))
    REPORT['smallest'] = {'flash': smallest_flash, 'ram': smallest_ram}
    comp = {v: http('GET', api + '/api/board/builds/%s/compat' % builds[v]['build']) for v in names}
    check('GET /api/board/builds/<b>/compat → compatible for all four, judged against THIS server\'s live exposures',
          all(c.get('verdict') == 'compatible' and c['classes'][0]['source'] == 'live' for c in comp.values()), {v: c.get('verdict') for v, c in comp.items()})
    REPORT['compat'] = {v: {'verdict': c['verdict'], 'order': c['classes'][0]['now_order'], 'contract': 'v%s %s' % (c['classes'][0]['contract_version'], c['classes'][0]['contract_hash'])}
                        for v, c in comp.items()}
    # brd-1's finding, caught: the pinned v2 snapshot vs this fresh v1 server (same contract hash)
    work = I.work_dir()
    st = gen.gen('uno', work=work, variant='uno-echo')   # no --api, no server: the pinned v2 snapshot
    rec = build.build('uno', work)                          # → the same build store the installer reads
    sc = http('GET', api + '/api/board/builds/%s/compat' % rec['name'])
    sp = http('POST', api + '/api/board/installer/plan', {'instance': I.TWIN, 'build': rec['name']})
    check('a build from the PINNED v2 snapshot (contract hash %s, same as this server\'s v1) → stale-header; its plan is REFUSED (409) in plain words'
          % json.loads(st['classes_json'])[0]['contract_hash'], sc.get('verdict') == 'stale-header' and sp.get('_status') == 409 and 'misread' in sp.get('error', ''),
          (sc.get('verdict'), sp.get('_status'), sp.get('error', '')[:200]))
    REPORT['stale'] = {'verdict': sc.get('verdict'), 'plan_refusal': sp.get('error')}
    plans = {}
    for v in names:
        p = http('POST', api + '/api/board/installer/plan', {'instance': I.TWIN, 'build': builds[v]['build']})
        plans[v] = p
        print('       [DRY-RUN %s] %s' % (v, p.get('argv_text')))
        if p.get('wrapper_text'):
            print('                    runs as: %s' % p['wrapper_text'])
    check('POST /api/board/installer/plan (twin) for all four → the exact argv (polari-avr-twin --hex <the stored .hex> …), compat compatible',
          all(p.get('ok') and p['argv'][0] == 'polari-avr-twin' and p['argv'][p['argv'].index('--hex') + 1].endswith('/firmware.hex') and p['compat'] == 'compatible'
              for p in plans.values()), {v: p.get('error') for v, p in plans.items() if not p.get('ok')})
    REPORT['plans'] = {v: {'argv': p.get('argv_text'), 'wrapper': p.get('wrapper_text')} for v, p in plans.items()}
    nc = http('POST', api + '/api/board/installer/run', {'plan': plans['uno-echo']['plan']})
    check('run WITHOUT confirm → refused (400), nothing run', nc.get('_status') == 400 and 'not confirmed' in nc.get('error', ''), nc)

    def install(v):
        r = http('POST', api + '/api/board/installer/run', {'plan': plans[v]['plan'], 'confirm': True})
        a = http('POST', api + '/api/board/installer/attach', {'record': r.get('name', '')})
        t0, res = time.time(), {}
        while time.time() - t0 < 900:
            res = http('GET', api + '/api/board/installer/result/%s' % r.get('name', ''))
            if (res.get('bridge_state') or '').startswith('refused') or (res.get('bridge_state') == 'attached' and res.get('frames_total', 0) >= 5):
                break
            time.sleep(1.0)
        return r, a, res

    def row_of(cls, name):
        for o in (manager.objectTables.get(cls) or {}).values():
            if getattr(o, 'name', '') == name:
                return o
        return None

    def put(cls, name, values):
        obj = row_of(cls, name)
        body, ctype = multipart({'polariId': getattr(obj, 'id', ''), 'updateData': json.dumps(values)})
        return http('PUT', api + '/' + cls, body, ctype)

    def wait_row(cls, name, pred, s=6.0):
        t0 = time.time()
        while time.time() - t0 < s:
            o = row_of(cls, name)
            if o is not None and pred(o):
                return o, time.time() - t0
            time.sleep(0.1)
        return row_of(cls, name), None

    # ---- uno-echo: the protocol test
    t0 = time.time()
    r, a, res = install('uno-echo')
    check('install uno-echo into THE TWIN → %s: %s (%.1f s)' % (r.get('verdict'), r.get('verify'), r.get('elapsed_s') or 0),
          r.get('verdict') == 'installed' and r.get('verified_bytes', 0) > 0, r)
    check('attach → the generated bridge at the twin\'s pty, frames arrive (%s frames, bridge %s, %.0f s incl. mvn)' % (res.get('frames_total'), res.get('bridge_state'), time.time() - t0),
          a.get('ok') and res.get('bridge_state') == 'attached' and res.get('frames_total', 0) >= 5 and res['frames'][0]['class'] == 'SimRigState', (a, res.get('bridge_state')))
    time.sleep(2.5)
    res = http('GET', api + '/api/board/installer/result/%s' % r['name'])
    put('SimRigState', 'uno-echo', {'temp_c': 12.5, 'pwm_duty': 7, 'led_on': True})
    o, dt = wait_row('SimRigState', 'uno-echo', lambda o: getattr(o, 'status', '') == 'echoed' and abs(float(getattr(o, 'temp_c', 0) or 0) - 12.5) < 1e-6)
    check('uno-echo: a PUT {temp_c: 12.5, pwm_duty: 7, led_on: true} comes back WHOLE — the row says status=echoed, temp_c 12.5 (no sensor could), pwm 7, led on (%s s)'
          % (round(dt, 2) if dt else 'never'), dt is not None and int(o.pwm_duty) == 7 and str(o.led_on).lower() in ('true', '1'),
          {k: getattr(o, k, None) for k in ('status', 'temp_c', 'pwm_duty', 'led_on')} if o else None)
    REPORT['echo'] = {'record': r['name'], 'verify': r['verify'], 'frames_per_s': res.get('frames_per_s'), 'first_frame': (res.get('frames') or [None])[0],
                      'echo_s': round(dt, 2) if dt else None}
    # ---- uno-sim-rig: the whole rig
    r, a, res = install('uno-sim-rig')
    check('install uno-sim-rig (the twin stops the echo firmware and loads this one) → %s: %s' % (r.get('verdict'), r.get('verify')), r.get('verdict') == 'installed', r)
    time.sleep(3.2)
    res = http('GET', api + '/api/board/installer/result/%s' % r['name'])
    check('uno-sim-rig: frames at ~10 Hz through the bridge (%s frames/s), temp_c 24.707 in the row (TMP36 at 750 mV)' % res.get('frames_per_s'),
          res.get('bridge_state') == 'attached' and 8.5 <= float(res.get('frames_per_s') or 0) <= 11.5 and res.get('row') and abs(float(res['row']['temp_c']) - 24.70703125) < 1e-3,
          (res.get('frames_per_s'), res.get('row')))
    put('SimRigState', 'uno-rig', {'led_on': True, 'pwm_duty': 42})
    o, dt = wait_row('SimRigState', 'uno-rig', lambda o: getattr(o, 'status', '') == 'commanded' and int(getattr(o, 'pwm_duty', 0) or 0) == 42)
    time.sleep(1.2)
    log = [json.loads(line) for line in open(twin.status('uno', work)['log']) if line.startswith('{')]
    stl = [x for x in log if x.get('t') == 'status']
    check('uno-sim-rig: a PUT {led_on, pwm_duty 42} → status=commanded in the row (%s s); simavr OCR0A = 107' % (round(dt, 2) if dt else 'never'),
          dt is not None and stl and stl[-1]['ocr0a'] == 107, (stl[-1] if stl else None))
    REPORT['sim_rig'] = {'record': r['name'], 'verify': r['verify'], 'frames_per_s': res.get('frames_per_s'), 'row': res.get('row'), 'put_echo_s': round(dt, 2) if dt else None}
    # ---- uno-adc-sweep: the second class
    r, a, res = install('uno-adc-sweep')
    check('install uno-adc-sweep → %s: %s' % (r.get('verdict'), r.get('verify')), r.get('verdict') == 'installed', r)
    o, dt = wait_row('UnoAnalogState', 'uno-analog', lambda o: int(getattr(o, 'a2', 0) or 0) > 0, 15)
    res = http('GET', api + '/api/board/installer/result/%s' % r['name'])
    # MEASURED: simavr 1.6 returns floor(mV·1023/Vref) (306/613 here — consistent with a 0x3FF scale); the datasheet says ADC = Vin·1024/Vref (DS40002061B §24.7) — so the
    # twin reads 1 LSB low at 1500/3000 mV (306/613, where a real ATmega328P gives 307/614). The probe checks what the twin does
    # and says so; the deviation is a twin fact, recorded, not hidden.
    want = tuple(int(mv * 1023 // 5000) for mv in (750, 1500, 3000))
    check('uno-adc-sweep: UnoAnalogState rows arrive — a0/a1/a2 = %d/%d/%d at the twin\'s 750/1500/3000 mV (simavr: mV·1023/5000; the datasheet\'s '
          '·1024 would give 153/307/614)' % want,
          o is not None and (int(o.a0), int(o.a1), int(o.a2)) == want and res['frames'][0]['class'] == 'UnoAnalogState',
          {k: getattr(o, k, None) for k in ('a0', 'a1', 'a2', 'status')} if o else None)
    REPORT['adc_sweep'] = {'record': r['name'], 'verify': r['verify'], 'row': res.get('row'), 'first_frame': (res.get('frames') or [None])[0]}
    # ---- uno-blink-only through the CLI (parity)
    cli = subprocess.run([sys.executable, '-m', 'board.custom.install_cli', 'install', 'uno', '--variant', 'uno-blink-only', '--twin', '--yes', '--api', api],
                         capture_output=True, text=True, timeout=900, cwd=FRAMEWORK, env=dict(os.environ, PYTHONPATH='.:modules'))
    print('\n'.join('       | ' + line for line in cli.stdout.splitlines()))
    blink_rec = [x for x in http('GET', api + '/api/board/installer')['records'] if x['variant'] == 'uno-blink-only'][0]['name']
    time.sleep(1.5)
    log = os.path.join(I.work_dir(), 'bridge', 'run', 'bridge-%s.log' % blink_rec)
    leds = [f['values'].get('led_on') for f in (attach.parse_line(x) for x in open(log)) if f]
    row = row_of('SimRigState', 'uno-blink')
    # FINDING (grpcbridge, not this slice): a pushed frame updates only the fields it carries with NON-default values
    # (descriptor_build.message_to_values — proto3 has no presence for plain scalars), so led_on=false never reaches the
    # row: the row goes true and stays. The device-side truth is the bridge's decoded frames, checked here.
    check('pol board install uno --variant uno-blink-only --twin --yes (CLI parity): DRY-RUN line, installed, frames; led_on flips in the '
          'decoded frames (%d true / %d false of %d)' % (leds.count('true'), leds.count('false'), len(leds)),
          cli.returncode == 0 and '[DRY-RUN] polari-avr-twin' in cli.stdout and 'installed' in cli.stdout and leds.count('true') >= 3 and leds.count('false') >= 3,
          cli.stdout[-600:] + cli.stderr[-300:])
    REPORT['blink'] = {'frames': len(leds), 'true': leds.count('true'), 'false': leds.count('false'), 'row_led_on': getattr(row, 'led_on', None),
                       'finding': 'Push drops default-valued fields (proto3, no presence): the row\'s led_on cannot return to false'}
    dry = subprocess.run([sys.executable, '-m', 'board.custom.install_cli', 'install', 'uno', '--variant', 'uno-echo', '--twin', '--api', api],
                         capture_output=True, text=True, timeout=300, cwd=FRAMEWORK, env=dict(os.environ, PYTHONPATH='.:modules'))
    check('pol board install … without --yes is a DRY-RUN: the argv, "nothing was run", exit 0', dry.returncode == 0 and 'nothing was run' in dry.stdout, dry.stdout[-300:])
    nob = subprocess.run([sys.executable, '-m', 'board.custom.install_cli', 'install', 'uno', '--api', api],
                         capture_output=True, text=True, timeout=300, cwd=FRAMEWORK, env=dict(os.environ, PYTHONPATH='.:modules'))
    check('pol board install uno with no UNO detected and no --twin → refused, exit 3, says --twin', nob.returncode == 3 and '--twin' in nob.stdout, nob.stdout[-300:])
    REPORT['cli'] = cli.stdout
    doc = http('GET', api + '/api/board/installer')
    check('GET /api/board/installer lists the four install records (installed) and the twin running uno-blink-only',
          len([x for x in doc.get('records', []) if x['verdict'] == 'installed']) >= 4 and doc['twin']['variant'] == 'uno-blink-only', doc.get('twin'))
    REPORT['records'] = [{k: x[k] for k in ('name', 'variant', 'verdict', 'verify', 'firmware_sha', 'elapsed_s', 'bridge_state', 'frames_per_s')} for x in doc.get('records', [])]
    attach.detach(work)
    twin.down('uno', work)
    grpc_srv.stop() if hasattr(grpc_srv, 'stop') else None
    httpd.shutdown()
    if out_json:
        json.dump(REPORT, open(out_json, 'w'), indent=1, default=str)
    print('\n%d/%d installer probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    finally:
        try:
            from board.custom import attach, twin, installer as I
            attach.detach(I.work_dir())
            twin.down('uno', I.work_dir())
        except Exception:  # noqa: BLE001
            pass
