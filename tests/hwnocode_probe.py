"""hn-0 PROBE — the split app `uno-temp-split` END TO END on the UNO's simavr twin (HARDWARE_NOCODE_PLAN.md §7 hn-0). No UNO is
attached: the twin runs the SAME .hex a board would be flashed with; the real-UNO replay is his.

  1. `pol hwnocode render uno-temp-split` → the board half through cmod-glue: files_sha256 EQUAL to cmod-1's record (unchanged
     output); `pol hwnocode build` → make alone → the .hex byte-identical to cmod-1's (4188f6ae…)
  2. a THROWAWAY server in-process (sqlite in the cwd, HTTP + gRPC on ephemeral ports; modules hwmap, grpcbridge, board, cmod,
     hwnocode): GET /stateSpaceClasses lists the three hardware node kinds WITH their palette metadata (D-hn-2: the palette as data)
  3. the contract ledger the firmware was generated from (the pinned SimRigState v2 — the glue's header is built offline from it)
     restored as this server's ProtoContractVersion v1, exposure enabled → v2 with the SAME tag order: the server's own header for
     bridge uno-temp-split is byte-identical to the glue's simrigstate_packets.h
  4. `pol board twin uno up --work <hwnocode work>` (that build; ADC0 a 700→800 mV triangle = 20→30 °C), the generated Java bridge
     at the twin's pty (the seeded binding uno-temp-split/SimRigState/0 is the hw-interface node)
  5. the backend half: SimRigState frames at ~10 Hz → the EventTrigger → the engine (AnalysisCall → ConditionalChain →
     StateChangeCommit) → SimRigTempSample rows at ~10 Hz + SimRigTempDerived (moving average, over_threshold seen false AND true as
     the ramp crosses 25 °C)
  6. GET /api/hwnocode/solutions/uno-temp-split/chart → both series; a REST PUT {led_on: true} on the row → Commands → the firmware →
     the next frame echoes status=commanded; GET …/placement (every node, where, why); GET …/suggest (bare-c, SUGGEST ONLY)
  7. costs: the twin, the bridge, the server, the engine per frame (the cost rule); --record writes the proof into the split record
Skips honestly when the twin, java or mvn is missing.

  mkdir -p /tmp/h && cd /tmp/h && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/hwnocode_probe.py [--db tmpfs|disk] [--json out.json]
        [--record] [--record-costs]
  --db: where the throwaway sqlite lives (default tmpfs when /dev/shm exists) — see the comment at the boot
"""
import io
import json
import os
import resource
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request

os.environ['POLARI_MODULES'] = 'hwmap,grpcbridge,board,cmod,hwnocode'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []
REPORT = {}
SOL = 'uno-temp-split'


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra != '' and not cond else ''), flush=True)


def http(method, url, body=None, ctype='application/json', timeout=120):
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
    b = '----polari-hwnocode-probe'
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    out.write(('--%s--\r\n' % b).encode())
    return out.getvalue(), 'multipart/form-data; boundary=%s' % b


def rss_kb(pid):
    try:
        for line in open('/proc/%d/status' % pid):
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    except Exception:
        return 0
    return 0


def main(argv):
    out_json = argv[argv.index('--json') + 1] if '--json' in argv else ''
    from board.custom import board_engines as be
    tw = be.resolve('avr-twin')
    missing = [n for n, ok in (('the simavr twin (%s)' % tw['why'], tw['how'] in ('local-binary', be.LOCAL_IMAGE)),
                               ('java', shutil.which('java')), ('mvn', shutil.which('mvn'))) if not ok]
    if missing:
        print('SKIP: %s' % '; '.join(missing))
        return 0
    here = os.path.abspath(os.getcwd())
    work = os.path.join(here, 'hwnocode-work')
    link = os.path.join(here, 'uno-uart')
    tcp = int(os.environ.get('UNO_TWIN_TCP', '9858'))
    cli = [sys.executable, '-m', 'hwnocode.custom.hwnocode_cli']
    env = dict(os.environ, PYTHONPATH='%s:%s' % (FRAMEWORK, os.path.join(FRAMEWORK, 'modules')))

    # ---- 1. render + build (the CLI, as a person runs it)
    t0 = time.time()
    r = subprocess.run(cli + ['render', SOL, '--work', work], cwd=FRAMEWORK, env=env, capture_output=True, text=True, timeout=300)
    REPORT['render'] = {'stdout': r.stdout, 'wall_s': round(time.time() - t0, 2)}
    print(r.stdout, end='')
    from cmod.custom import glue as GL
    crec = GL.load_record('uno-sim-rig-graph')
    from hwnocode.custom import split as SP
    srec = SP.load_record(SOL) or {}
    check('pol hwnocode render: the board half = cmod-glue\'s output, files_sha256 %s = cmod-1\'s record (unchanged)' % crec['files_sha256'][:16],
          r.returncode == 0 and 'UNCHANGED OUTPUT' in r.stdout and (srec.get('board_half') or {}).get('files_sha256') == crec['files_sha256'],
          r.stdout[-300:] + r.stderr[-300:])
    t0 = time.time()
    r = subprocess.run(cli + ['build', SOL, '--work', work], cwd=FRAMEWORK, env=env, capture_output=True, text=True, timeout=600)
    print(r.stdout, end='')
    srec = SP.load_record(SOL) or {}
    b = srec.get('build') or {}
    REPORT['build'] = dict(b, wall_s_cli=round(time.time() - t0, 2))
    check('pol hwnocode build: make alone → .hex %s BYTE-IDENTICAL to cmod-1\'s (flash %s B, RAM %s B)' % (b.get('hex_sha256', '')[:16],
          b.get('flash_bytes'), b.get('ram_bytes')), r.returncode == 0 and b.get('hex_sha256') == crec['build']['hex_sha256'], r.stdout[-300:] + r.stderr[-300:])

    # ---- 2. the throwaway server
    from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn
    from grpcbridge.custom.grpc_server import PolariGrpcServer, set_grpc_server
    from polariDataTyping.schema_stability import set_status_knob
    sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
    from board_probe_boot import boot
    # --db tmpfs (default when /dev/shm exists) | disk: where the throwaway sqlite lives. Measured on pol-core 2026-10-03: one
    # sqlite commit = 10.8 ms on the disk vs 0.06 ms on tmpfs, and every gated engine run commits ~10 rows (queue entry, lease,
    # lock rows — xsim-2's single-writer gate) — so the disk run measures this HOST's fsync, the tmpfs run the solution's own path.
    db_mode = argv[argv.index('--db') + 1] if '--db' in argv else ('tmpfs' if os.path.isdir('/dev/shm') else 'disk')
    db_here = here if db_mode == 'disk' else '/dev/shm/hwnocode-probe-%d' % os.getpid()
    REPORT['db_mode'] = db_mode
    t0 = time.time()
    manager = boot(FRAMEWORK, here=db_here)
    os.chdir(here)
    boot_s = time.time() - t0

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
    t = manager.objectTables
    # cost instrumentation (no behaviour change): the wall time of every trigger firing and every row save while the twin runs
    from polariNoCode import event_dispatcher as ED
    TIMES = {'fire': [], 'save': [], 'push': []}
    _fire, _save = ED.EventDispatcher.fire, manager.db.saveInstanceInDB

    def timed_fire(self, *a, **k):
        t0_ = time.perf_counter()
        try:
            return _fire(self, *a, **k)
        finally:
            TIMES['fire'].append(time.perf_counter() - t0_)

    def timed_save(*a, **k):
        t0_ = time.perf_counter()
        try:
            return _save(*a, **k)
        finally:
            TIMES['save'].append(time.perf_counter() - t0_)
            TIMES.setdefault('by_class', {}).setdefault(type(a[0]).__name__ if a else '?', []).append(time.perf_counter() - t0_)
    ED.EventDispatcher.fire = timed_fire
    manager.db.saveInstanceInDB = timed_save
    check('a throwaway server booted in %.1f s (HTTP %s, gRPC :%s); hwnocode seeded: HardwareSolution %s, %d placements, the binding, '
          'the trigger, the backend half' % (boot_s, api, grpc_srv.port, SOL, len(t.get('HardwareNodePlacement') or {})),
          any(x.name == SOL for x in (t.get('HardwareSolution') or {}).values())
          and any(x.name == 'uno-temp-split/SimRigState/0' for x in (t.get('HardwareInterfaceBinding') or {}).values())
          and any(x.name == 'uno-temp-split.backend' for x in (t.get('SolutionDefinition') or {}).values())
          and any(x.name == 'uno-temp-split-on-temp' for x in (t.get('EventTrigger') or {}).values()))
    ssc = http('GET', api + '/stateSpaceClasses')
    kinds = {c['className']: (c.get('palette') or {}).get('nodeKind') for c in (ssc.get('stateSpaceClasses') or []) if c.get('palette')}
    check('GET /stateSpaceClasses (the existing endpoint) lists the hardware node kinds WITH palette metadata: %s' % kinds,
          kinds == {'HardwareSubgraph': 'hardware-subgraph', 'HardwareInterface': 'hw-interface', 'CAtom': 'c-atom'}, kinds)
    REPORT['palette'] = kinds

    # ---- 3. the contract ledger the firmware speaks
    from grpcbridge.objects.hwsim.SimRigState import SimRigState
    from grpcbridge.contract_basis import ProtoContractVersion
    from board.custom import compat
    pinned, _p = compat.pinned_contract('SimRigState')
    v1 = ProtoContractVersion(manager=manager, name='SimRigState-proto-v1', subject_class='SimRigState', version=1,
                              contract_hash=pinned['contract_hash'], proto_text='', field_map_json=json.dumps(pinned['field_map']),
                              generated_at='', reason='initial', notes='restored from the pinned v2 snapshot the firmware was generated from (hn-0 probe)')
    manager.db.saveInstanceInDB(v1)
    row = SimRigState(manager=manager, name='uno-twin', uptime_ms=0, temp_c=0.0, pwm_duty=0, led_on=False, status='seeded')
    manager.db.saveInstanceInDB(row)
    st = set_status_knob(manager, 'SimRigState', 'stabilize')
    exp = http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'enable'})
    tr = http('POST', api + '/api/grpc/exposures/SimRigState', {'action': 'set-transport', 'transport': 'both'})
    hdr = compat.server_header(manager, 'SimRigState', bridge='uno-temp-split')
    glue_hdr = crec['files']['simrigstate_packets.h']
    check('the ledger: pinned v2 restored as v1 → enable → contract v%s hash %s, tag order %s; THIS server\'s header for bridge '
          'uno-temp-split = the glue\'s simrigstate_packets.h (%s)' % (exp.get('version'), hdr and hdr['contract_hash'], hdr and hdr['tag_order'],
                                                                      glue_hdr[:16]),
          st.get('ok') and exp.get('ok') and tr.get('ok') and hdr and hdr['sha256'] == glue_hdr, (exp, hdr and hdr['sha256']))
    for bnd in (t.get('HardwareInterfaceBinding') or {}).values():
        if bnd.name == 'uno-temp-split/SimRigState/0':
            bnd.port = link    # the knob the binding keeps per instance: this probe's twin link
            manager.db.saveInstanceInDB(bnd)

    # ---- 4. the twin (the CLI) + the bridge
    java = None
    twin_env = dict(env)
    up = subprocess.run([sys.executable, '-m', 'board.custom.twin', 'uno', 'up', '--work', work, '--tcp', str(tcp), '--link', link,
                         '--adc0-ramp', '700,800,8000'], cwd=FRAMEWORK, env=twin_env, capture_output=True, text=True, timeout=120)
    print(up.stdout, end='')
    try:
        from board.custom import twin
        s = twin.status('uno', work)
        check('pol board twin uno up --work <hwnocode work>: that build (%s) in simavr (%s), UART at %s, ADC0 a 700→800 mV triangle'
              % (s.get('hex_sha256', '')[:16], s.get('how'), link), up.returncode == 0 and s.get('alive') and s.get('hex_sha256') == b.get('hex_sha256'),
              up.stdout[-400:] + up.stderr[-400:])
        r = http('POST', api + '/api/grpc/bridges', {'bridgeName': 'uno-temp-split', 'classes': ['SimRigState'], 'source': 'serial',
                                                    'serialDevice': link, 'grpcEnabled': True, 'grpcTarget': '127.0.0.1:%d' % grpc_srv.port,
                                                    'deviceId': 3})
        tgz = http('GET', api + '/api/grpc/bridges/uno-temp-split/download')
        proj = os.path.abspath('bridge')
        shutil.rmtree(proj, ignore_errors=True)
        tarfile.open(fileobj=io.BytesIO(tgz)).extractall(proj)
        root = next(os.path.join(proj, d) for d in os.listdir(proj)) if not os.path.exists(os.path.join(proj, 'pom.xml')) else proj
        props = open(os.path.join(root, 'bridge.properties')).read()
        check('the generated bridge carries the hw-interface binding (binding.count=1, its port = the twin link)',
              r.get('ok') and 'binding.count=1' in props and link in props, props[:400])
        t0 = time.time()
        mvn = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=900)
        if mvn.returncode != 0:
            mvn = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=root, capture_output=True, text=True, timeout=1200)
        jar = os.path.join(root, 'target', 'polari-hw-bridge.jar')
        mvn_s = time.time() - t0
        check('mvn package of the generated bridge (%.0f s)' % mvn_s, mvn.returncode == 0 and os.path.isfile(jar), (mvn.stdout + mvn.stderr)[-600:])
        java = subprocess.Popen(['java', '-jar', jar, 'bridge.properties'], cwd=root, stdout=open('bridge.log', 'w'), stderr=subprocess.STDOUT)
        time.sleep(6)

        # ---- 5. the backend half at 10 Hz
        def row_now():
            for v in (manager.objectTables.get('SimRigState') or {}).values():
                if getattr(v, 'name', '') == 'uno-twin':
                    return {k: getattr(v, k) for k in ('uptime_ms', 'temp_c', 'pwm_duty', 'led_on', 'status')}, v
            return {}, None

        def derived_now():
            for v in (manager.objectTables.get('SimRigTempDerived') or {}).values():
                if v.name == 'uno-twin':
                    return {k: getattr(v, k) for k in ('temp_avg', 'over_threshold', 'samples', 'last_temp_c', 'last_uptime_ms', 'window', 'threshold_c')}
            return {}

        def firings():
            return [f for f in (manager.objectTables.get('TriggerFiring') or {}).values() if f.trigger_name == 'uno-temp-split-on-temp']
        seqs = lambda: sum(1 for l in open('bridge.log') if l.startswith('[bridge] seq='))  # noqa: E731

        def bridge_uptime():
            import re
            last = [l for l in open('bridge.log') if l.startswith('[bridge] seq=')][-1:]
            m_ = re.search(r'uptime_ms=(\d+)', last[0]) if last else None
            return int(m_.group(1)) if m_ else 0

        def lag_ms():
            rr_, _ = row_now()
            return bridge_uptime() - int(rr_.get('uptime_ms') or 0)
        # the bridge's first seconds (mvn-built JVM warm-up, the first lock/ring rows) queue frames: wait until the server has
        # caught up with what the bridge decoded, THEN measure (a backlog drain would read as > 10 Hz)
        tw0 = time.time()
        while time.time() - tw0 < 40 and lag_ms() > 300:
            time.sleep(0.2)
        REPORT['catch_up_s'] = round(time.time() - tw0, 1)
        a, _ = row_now(); da = derived_now(); fa = firings(); na = seqs(); ta = time.time()
        seen = []
        while time.time() - ta < 9.0:
            d = derived_now()
            rr, _ = row_now()
            if d:
                seen.append((round(time.time() - ta, 2), rr.get('temp_c'), round(float(d['temp_avg']), 4), bool(d['over_threshold']), d['samples']))
            time.sleep(0.1)
        z, obj = row_now(); dz = derived_now(); fz = firings(); nz = seqs(); tz = time.time()
        span = tz - ta
        hz_frames = (nz - na) / span
        hz_rows = (int(dz.get('samples') or 0) - int(da.get('samples') or 0)) / span
        fired = [f for f in fz if f not in fa]
        ok_fired = sum(1 for f in fired if f.status == 'fired')
        fw_s = (int(z.get('uptime_ms') or 0) - int(a.get('uptime_ms') or 0)) / 1000.0
        per_fw_s = (int(dz.get('samples') or 0) - int(da.get('samples') or 0)) / fw_s if fw_s else 0
        lag_end = lag_ms()
        check('the bridge decodes %.2f SimRigState frames/s from the twin (10 Hz expected); the row follows (uptime_ms %s → %s, status %s)'
              % (hz_frames, a.get('uptime_ms'), z.get('uptime_ms'), z.get('status')), 9.0 <= hz_frames <= 11.0 and z and int(z['uptime_ms']) > int(a.get('uptime_ms') or 0),
              (nz - na, a, z))
        check('the backend half receives temp_c at %.2f Hz: %d TriggerFiring rows in %.1f s (%d fired, %d failed), SimRigTempSample written '
              'at %.2f rows/s = %.2f per firmware-second (every frame, none dropped); lag behind the bridge at the end %d ms (caught up '
              'after %.1f s)' % (len(fired) / span, len(fired), span, ok_fired, len(fired) - ok_fired, hz_rows, per_fw_s, lag_end,
                                 REPORT['catch_up_s']),
              9.0 <= hz_rows <= 11.0 and 9.5 <= per_fw_s <= 10.5 and lag_end <= 500 and ok_fired >= 0.95 * len(fired) > 0,
              ([(f.status, f.error[:120]) for f in fired if f.status != 'fired'][:3], per_fw_s, lag_end))
        flags = {s_[3] for s_ in seen}
        lo = min((s_[2] for s_ in seen), default=None)
        hi = max((s_[2] for s_ in seen), default=None)
        check('SimRigTempDerived: the moving average follows the 20→30 °C ramp (%.2f … %.2f °C) and over_threshold (avg > 25 °C) is seen '
              'FALSE and TRUE: %s' % (lo or 0, hi or 0, sorted(flags)), flags == {False, True} and lo is not None and lo < 25 < hi, seen[::10])
        mean = lambda xs: round(1000 * sum(xs) / len(xs), 2) if xs else 0  # noqa: E731
        REPORT['dispatch_cost'] = {'firing_mean_ms': mean(TIMES['fire']), 'firing_max_ms': round(1000 * max(TIMES['fire'] or [0]), 1),
                                   'firings_timed': len(TIMES['fire']), 'save_mean_ms': mean(TIMES['save']), 'saves': len(TIMES['save']),
                                   'saves_by_class': {k: (len(v), mean(v)) for k, v in sorted((TIMES.get('by_class') or {}).items())}}
        print('dispatch cost: %s' % REPORT['dispatch_cost'], flush=True)
        REPORT['backend'] = {'frames_per_s': round(hz_frames, 3), 'derived_rows_per_s': round(hz_rows, 3), 'firings': len(fired),
                             'rows_per_firmware_s': round(per_fw_s, 3), 'lag_end_ms': lag_end, 'catch_up_s': REPORT['catch_up_s'],
                             'fired_ok': ok_fired, 'span_s': round(span, 2), 'samples_seen': seen[::5], 'derived_last': dz,
                             'firing_errors': sorted({f.error[:160] for f in fired if f.status != 'fired'})[:3]}
        # the avg is the 5-sample moving average of the samples the ring holds
        ring = sorted((x for x in (manager.objectTables.get('SimRigTempSample') or {}).values() if x.source_object == 'uno-twin'), key=lambda x: x.seq)
        last5 = ring[-5:]
        want = sum(x.temp_c for x in last5) / len(last5) if last5 else None
        check('the newest sample\'s temp_avg = the mean of the last 5 temp_c in the ring (%s)' % (want and round(want, 4)),
              last5 and abs(last5[-1].temp_avg - want) < 1e-9, [(x.seq, x.temp_c, x.temp_avg) for x in last5])

        # ---- 6. the chart, the PUT, the placement, the suggestion
        ch = http('GET', api + '/api/hwnocode/solutions/%s/chart' % SOL)
        rows = ch.get('rows') or []
        check('GET …/chart → %d rows with BOTH series (temp_c, temp_avg) over uptime_s, oldest first' % len(rows),
              ch.get('ok') and len(rows) >= 50 and all({'uptime_s', 'temp_c', 'temp_avg'} <= set(x) for x in rows)
              and rows == sorted(rows, key=lambda x: x['seq']), str(ch)[:300])
        REPORT['chart'] = {'rows': len(rows), 'first': rows[:2], 'last': rows[-2:]}
        z, obj = row_now()
        pid = getattr(obj, 'id', '') or getattr(obj, 'polariId', '')
        body, ctype = multipart({'polariId': pid, 'updateData': json.dumps({'led_on': True})})
        http('PUT', api + '/SimRigState', body, ctype)
        tp = time.time()
        echo = {}
        while time.time() - tp < 5:
            echo, _ = row_now()
            if echo.get('status') == 'commanded' and int(echo.get('uptime_ms') or 0) > int(z['uptime_ms']):
                break
            time.sleep(0.05)
        t_echo = time.time() - tp
        check('REST PUT {led_on: true} on the hw-interface\'s row → Commands → the bridge → the firmware → the next frame echoes '
              'status=commanded, led_on true (%.2f s)' % t_echo, echo.get('status') == 'commanded' and str(echo.get('led_on')).lower() in ('true', '1'), echo)
        time.sleep(1.2)
        log = [json.loads(l) for l in open(s['log']) if l.startswith('{')]
        pb5 = [x for x in log if x.get('t') == 'pb5' and x.get('v') == 1]
        check('simavr: PORTB5 (D13) went high — the LED the PUT asked for', bool(pb5), log[-3:])
        REPORT['put'] = {'echo_row': echo, 'echo_s': round(t_echo, 2), 'pb5': pb5[:1]}
        pl = http('GET', api + '/api/hwnocode/solutions/%s/placement' % SOL)
        check('GET …/placement: %s — every node with where and why, no refusal' % pl.get('summary'),
              pl.get('ok') and pl.get('summary') == 'twin 19, bridge 1, backend 6, browser 1' and all(n.get('why') for n in pl.get('nodes') or []), str(pl)[:300])
        REPORT['placement'] = [{k: n[k] for k in ('layer', 'node', 'kind', 'placement', 'why')} for n in pl.get('nodes') or []]
        sg = http('GET', api + '/api/hwnocode/solutions/%s/suggest' % SOL)
        check('GET …/suggest: %s by rule %s — applied %s (SUGGEST ONLY)' % (sg.get('suggested'), sg.get('decisive_rule'), sg.get('applied')),
              sg.get('suggested') == 'bare-c' and sg.get('applied') is False)
        REPORT['suggest'] = {k: sg.get(k) for k in ('suggested', 'decisive_rule', 'reasons', 'policy')}

        # ---- 7. costs
        tw_mem = ''
        if s.get('container'):
            ds = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}}', s['container']], capture_output=True, text=True, timeout=30)
            tw_mem = ds.stdout.strip()
        from polariNoCode.graph_builder import execute
        backend = next(x for x in t['SolutionDefinition'].values() if x.name == 'uno-temp-split.backend')
        bdef = json.loads(backend.definition)
        t0 = time.time()
        for i in range(50):
            execute(bdef, manager=manager, params={'instance.name': 'cost-probe', 'instance.temp_c': 24.0 + i % 3, 'instance.uptime_ms': 100 * i,
                                                    'window': 5, 'threshold_c': 25.0, 'keep': 600})
        per_run_ms = (time.time() - t0) / 50 * 1000
        REPORT['costs'] = {'board_half': {'flash_bytes': b.get('flash_bytes'), 'ram_bytes': b.get('ram_bytes'), 'make_alone_s': b.get('wall_s')},
                           'twin_container_mem': tw_mem, 'bridge_rss_kb': rss_kb(java.pid), 'server_peak_rss_kb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                           'server_boot_s': round(boot_s, 1), 'mvn_package_s': round(mvn_s, 1),
                           'engine_per_frame_ms': round(per_run_ms, 2), 'engine_cpu_at_10hz_pct': round(per_run_ms / 100.0 * 100, 1),
                           'put_echo_s': round(t_echo, 2), 'new_image_mb': 0}
        check('costs measured: engine %.2f ms per frame (%.1f %% of one core at 10 Hz), bridge RSS %d MB, twin %s, server peak RSS %d MB'
              % (per_run_ms, per_run_ms / 100.0 * 100, rss_kb(java.pid) // 1024, tw_mem or '-', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024),
              per_run_ms > 0)
    finally:
        if java is not None:
            java.terminate()
            try:
                java.wait(10)
            except Exception:
                java.kill()
        subprocess.run([sys.executable, '-m', 'board.custom.twin', 'uno', 'down', '--work', work], cwd=FRAMEWORK, env=twin_env,
                       capture_output=True, text=True, timeout=120)
        grpc_srv.stop() if hasattr(grpc_srv, 'stop') else None
        httpd.shutdown()
    if db_mode == 'tmpfs':
        shutil.rmtree(db_here, ignore_errors=True)
    n_ok, n = sum(results), len(results)
    if '--record-costs' in argv and REPORT.get('backend'):
        rec = SP.load_record(SOL) or {}
        rec.setdefault('costs_by_db', {})[db_mode] = dict(REPORT.get('costs') or {}, backend_rows_per_s=REPORT['backend']['derived_rows_per_s'],
                                                          frames_per_s=REPORT['backend']['frames_per_s'], dispatch=REPORT.get('dispatch_cost'),
                                                          checks='%d/%d' % (n_ok, n))
        SP.save_record(SOL, rec)
        print('recorded the %s-db costs into %s' % (db_mode, SP.record_path(SOL)))
    if '--record' in argv and all(results):
        rec = SP.load_record(SOL) or {}
        bk = REPORT['backend']
        rec['proof'] = {'ok': True, 'checks': '%d/%d' % (n_ok, n), 'proven_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'db': db_mode,
                        'twin': 'polari-avr-twin (libsimavr, prf-board-engines:trixie), ADC0 700→800 mV triangle over 8 s',
                        'frames_per_s': bk['frames_per_s'], 'derived_rows_per_s': bk['derived_rows_per_s'],
                        'firings': '%d fired of %d' % (bk['fired_ok'], bk['firings']), 'derived_last': bk['derived_last'],
                        'chart_rows': REPORT['chart']['rows'], 'put_echo': REPORT['put']['echo_row'], 'put_echo_s': REPORT['put']['echo_s'],
                        'summary': ('twin: %.2f frames/s through the bridge → the backend half %.2f derived rows/s (%d/%d firings ok); '
                                    'over_threshold seen false and true on the 20→30 °C ramp; chart %d rows (temp_c, temp_avg); PUT led_on '
                                    '→ status=commanded in %.2f s' % (bk['frames_per_s'], bk['derived_rows_per_s'], bk['fired_ok'], bk['firings'],
                                                                     REPORT['chart']['rows'], REPORT['put']['echo_s']))}
        rec['costs'] = REPORT['costs']
        SP.save_record(SOL, rec)
        print('recorded the proof into %s' % SP.record_path(SOL))
    if out_json:
        json.dump(REPORT, open(out_json, 'w'), indent=1, default=str)
    print('\n%d/%d hwnocode probe checks passed' % (n_ok, n))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
