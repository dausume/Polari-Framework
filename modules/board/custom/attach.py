"""
@module board.custom.attach

After an install, "the bridge attaching, the first rows arriving" (brd-fi, plan §7a step 5): the GENERATED Java Hardware
Bridge — the same app brd-1 proved at the twin's pty — is pointed at the installed board's port (or the twin's pty link)
with `source=serial` (grpcbridge/custom/renode_twin/README.md), its project rendered from THIS server's bridge definition
and contracts, packaged once per code fingerprint (mvn; the jar is cached), and started on THIS host. Frames then push
the class row (Push matches on `name` = the variant's rig_name) and fan out over STOMP like any REST change, so the page
watches the row live.

  attach(manager, record)   POST /api/board/installer/attach — starts in a background thread; the record's bridge_state
                            goes attaching → attached | refused: <why>
  result(manager, record)   GET  /api/board/installer/result/<record> — the first frames the bridge logged, frames/s,
                            and the row's fields now

Refusals (plain words): the record did not install; a class's gRPC exposure is not enabled (nothing auto-enables — the
exposure is a knob, POST /api/grpc/exposures/<class> {action: enable}); java/mvn missing on this host. A class whose
exposure transport has no gRPC leg still attaches (telemetry flows) with a warning: commands need `set-transport both`.
One bridge per board: a new attach stops the previous one (the port is exclusive).
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time

from board.custom import installer as I

BRIDGE = 'fi-uno'
#: brd-wire: a wire v2 frame's line carries `index=K` (its instance index) before the class
LINE_RE = re.compile(r'^\[bridge\] seq=(\d+) device=(\d+) (?:index=(\d+) )?(\w+)\{(.*)\}\s*$')
KV_RE = re.compile(r'(\w+)=([^,]*)(?:, |$)')
_THREADS = {}


class AttachRefused(I.InstallRefused):
    pass


def _bridge_root(work):
    return os.path.join(work or I.work_dir(), 'bridge')


def parse_line(line):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    vals = {k: v.strip() for k, v in KV_RE.findall(m.group(5))}
    return {'seq': int(m.group(1)), 'device': int(m.group(2)), 'index': int(m.group(3) or 0), 'class': m.group(4), 'values': vals}


def frames(log_path, limit=5):
    """(first `limit` frames, total frames, frames per DEVICE second) from the bridge's stdout log. The rate comes from
    the frames' own uptime_ms (first → last): the device's clock, which is wall time on a board and on the real-time
    twin — never from file timestamps (the JVM flushes its stdout in bursts)."""
    out, total, first_up, last_up = [], 0, None, None
    try:
        for line in open(log_path, errors='replace'):
            f = parse_line(line)
            if not f:
                continue
            total += 1
            if len(out) < limit:
                out.append(f)
            try:
                up = int(f['values'].get('uptime_ms', ''))
            except ValueError:
                continue
            first_up = up if first_up is None else first_up
            last_up = up
    except OSError:
        pass
    rate = round((total - 1) * 1000.0 / (last_up - first_up), 2) if total > 1 and last_up and first_up is not None and last_up > first_up else 0.0
    return out, total, rate


def _stop(pid):
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except Exception:  # noqa: BLE001
        try:
            os.kill(int(pid), signal.SIGTERM)
        except Exception:  # noqa: BLE001
            pass


def detach(work=None):
    st = os.path.join(_bridge_root(work), 'running.json')
    try:
        d = json.load(open(st))
    except Exception:  # noqa: BLE001
        return {'state': 'none'}
    _stop(d.get('pid', 0))
    os.remove(st)
    return {'state': 'stopped', 'pid': d.get('pid')}


def preflight(manager, rec):
    """What attach needs, checked before anything starts. Returns (classes, warnings) or raises AttachRefused."""
    from grpcbridge.custom.proto_gen import get_exposure
    if getattr(rec, 'verdict', '') != 'installed':
        raise AttachRefused('install %s did not install (%s) — nothing to attach to' % (rec.name, rec.verdict or 'no verdict'))
    b = I.find_build(manager, rec.build)
    classes = [c['class'] for c in json.loads(b.get('classes_json') or '[]')]
    off = [c for c in classes if get_exposure(manager, c) is None or not int(getattr(get_exposure(manager, c), 'proto_version', 0) or 0)]
    if off:
        raise AttachRefused('the gRPC exposure of %s is not enabled on this server — enable it (POST /api/grpc/exposures/%s {"action": "enable"}), '
                            'then attach again; the installer never flips that knob itself' % (', '.join(off), off[0]))
    for tool in ('java', 'mvn'):
        if not shutil.which(tool):
            raise AttachRefused('%s is not installed on %s — the bridge is a Java app built with Maven' % (tool, I.this_host()))
    warn = []
    feats = (json.loads(b.get('repro_json') or '{}').get('knobs') or {}).get('features') or {}
    for c in classes:
        tp = getattr(get_exposure(manager, c), 'transport_preference', 'stomp')
        if feats.get('commands') and tp not in ('grpc', 'both'):
            warn.append('%s\'s exposure transport is %r — telemetry flows, but commands need the gRPC leg (set-transport both)' % (c, tp))
    return classes, warn


def attach(manager, record_name, work=None, grpc_target='', background=True):
    rec = I._by_name(manager, 'InstallRecord', record_name)
    if rec is None:
        raise AttachRefused('no install record %r' % record_name, '404 Not Found')
    classes, warn = preflight(manager, rec)
    p = I._by_name(manager, 'InstallPlan', rec.plan)
    port = getattr(p, 'port', '') or I.TWIN_LINK
    if not grpc_target:
        from grpcbridge.custom.grpc_server import get_grpc_server
        srv = get_grpc_server()
        if srv is None or not getattr(srv, 'port', 0):
            raise AttachRefused('this server has no gRPC sidecar running — the bridge pushes rows over gRPC')
        grpc_target = '127.0.0.1:%d' % srv.port
    b = I.find_build(manager, rec.build)
    knobs = json.loads(b.get('repro_json') or '{}').get('knobs') or {}
    rec.bridge_name, rec.bridge_state = BRIDGE, 'attaching'
    rec.notes = (rec.notes + ' | ' if rec.notes else '') + '; '.join(warn) if warn else rec.notes
    I._save(manager, rec)
    try:   # contextvars do not cross a thread: the request's cause is HANDED to the worker (accessControl.cause_context)
        from accessControl.cause_context import current_cause
        cause = current_cause()
    except Exception:  # noqa: BLE001
        cause = None
    args = (manager, rec, classes, port, grpc_target, int(knobs.get('device_id') or 3), work, cause)
    if background:
        t = threading.Thread(target=_attach_run, args=args, daemon=True)
        _THREADS[rec.name] = t
        t.start()
    else:
        _attach_run(*args)
    return {'record': rec.name, 'bridge': BRIDGE, 'state': rec.bridge_state, 'port': port, 'classes': classes, 'grpcTarget': grpc_target, 'warnings': warn}


def _definition(manager, classes, port, grpc_target, device_id):
    from grpcbridge.custom.java_bridge import get_bridge
    from grpcbridge.java_bridge_basis import HardwareBridgeDefinition
    row = get_bridge(manager, BRIDGE)
    if row is None:
        row = HardwareBridgeDefinition(manager=manager, name='%s-hw-bridge' % BRIDGE, bridge_name=BRIDGE)
    row.source, row.serial_device, row.baud = 'serial', port, 115200
    row.exposed_classes_json, row.grpc_enabled, row.grpc_target, row.device_id = json.dumps(classes), True, grpc_target, device_id
    I._save(manager, row)
    return row


def _attach_run(manager, rec, classes, port, grpc_target, device_id, work, cause=None):
    token = None
    if cause:
        try:
            from accessControl.cause_context import push_cause
            token = push_cause(**cause)
        except Exception:  # noqa: BLE001
            token = None
    try:
        _attach_body(manager, rec, classes, port, grpc_target, device_id, work)
    finally:
        if token is not None:
            from accessControl.cause_context import pop_cause
            pop_cause(token)


def _attach_body(manager, rec, classes, port, grpc_target, device_id, work):
    from grpcbridge.custom.java_bridge import generate_project, stamp_generation
    root = _bridge_root(work)
    try:
        detach(work)
        bridge = _definition(manager, classes, port, grpc_target, device_id)
        rep = generate_project(manager, bridge)
        if not rep.get('ok'):
            raise RuntimeError(rep.get('error'))
        stamp_generation(manager, bridge, rep)
        code = {p: t for p, t in rep['files'].items() if p != 'bridge.properties'}
        fp = hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest()[:16]
        proj = os.path.join(root, 'build-%s' % fp)
        jar = os.path.join(proj, 'target', 'polari-hw-bridge.jar')
        if not os.path.isfile(jar):
            shutil.rmtree(proj, ignore_errors=True)
            for path, text in code.items():
                os.makedirs(os.path.dirname(os.path.join(proj, path)) or proj, exist_ok=True)
                open(os.path.join(proj, path), 'w').write(text)
            m = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=proj, capture_output=True, text=True, timeout=900)
            if m.returncode != 0:
                m = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=proj, capture_output=True, text=True, timeout=1200)
            if m.returncode != 0 or not os.path.isfile(jar):
                raise RuntimeError('mvn package failed: %s' % (m.stdout + m.stderr)[-600:])
        run_dir = os.path.join(root, 'run')
        os.makedirs(run_dir, exist_ok=True)
        open(os.path.join(run_dir, 'bridge.properties'), 'w').write(rep['files']['bridge.properties'])
        log = os.path.join(run_dir, 'bridge-%s.log' % rec.name)
        proc = subprocess.Popen(['java', '-jar', jar, 'bridge.properties'], cwd=run_dir, stdout=open(log, 'w'), stderr=subprocess.STDOUT,
                                start_new_session=True)
        json.dump({'pid': proc.pid, 'record': rec.name, 'log': log, 'port': port, 'jar': jar, 'started': time.time()},
                  open(os.path.join(root, 'running.json'), 'w'))
        rec.bridge_state = 'attached'
        rec.notes = (rec.notes + ' | ' if rec.notes else '') + 'bridge %s (pid %d, jar %s) at %s' % (BRIDGE, proc.pid, fp, port)
    except Exception as e:  # noqa: BLE001
        rec.bridge_state = 'refused: %s' % str(e)[:400]
    I._save(manager, rec)


def result(manager, record_name, work=None, limit=5):
    rec = I._by_name(manager, 'InstallRecord', record_name)
    if rec is None:
        raise AttachRefused('no install record %r' % record_name, '404 Not Found')
    run = {}
    try:
        run = json.load(open(os.path.join(_bridge_root(work), 'running.json')))
    except Exception:  # noqa: BLE001
        pass
    log = run.get('log') if run.get('record') == rec.name else os.path.join(_bridge_root(work), 'run', 'bridge-%s.log' % rec.name)
    first, total, fps = frames(log or '', limit)
    if first:
        rec.first_frames_json = json.dumps(first)
        rec.frames_per_s = fps
        I._save(manager, rec)
    row = None
    if rec.row_class:
        obj = next((r for r in I._rows(manager, rec.row_class) if getattr(r, 'name', '') == rec.row_name), None)
        if obj is not None:
            row = {k: v for k, v in vars(obj).items() if not k.startswith('_') and isinstance(v, (str, int, float, bool)) and k not in ('manager',)}
    return {'ok': True, 'record': rec.name, 'verdict': rec.verdict, 'verify': rec.verify, 'variant': rec.variant, 'target_kind': rec.target_kind,
            'bridge_state': rec.bridge_state, 'frames': first, 'frames_total': total, 'frames_per_s': fps, 'row_class': rec.row_class,
            'row_name': rec.row_name, 'row': row, 'firmware_sha': rec.firmware_sha}
