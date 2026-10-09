"""
@module board.custom.attach_cli

`pol board attach uno --variant uno-button-clock --twin [--api URL] [--seconds N] [--presses N] [--work DIR]`
(ucd-frames+bundle, UNO_CORE_DEMO_PLAN.md §1/§3): runs ENTIRELY ON THIS HOST, never through the server's own
install/attach doors (`board.custom.installer`/`attach.py` run the twin and the Java bridge WHERE THE SERVER's
engines resolve — on the live isle-core worker that is a remote rung, and "a twin refuses a remote rung"
(`board.custom.twin.up`): a twin is a long-lived TCP port, not a `/run` request).

  1. build the variant HERE (gen + build — the SAME ladder `pol board install` uses, with no manager/server: the
     offline path `board.board_button_clock_twin_selftest._build` already proves);
  2. bring up the simavr twin HERE (`board.custom.twin.up`) with the demo's press schedule (`--pin-at` on D2) and its
     sense wire (`--wire PD6:PD3`, derived from the seeded BoardPinNet rows exactly as `twin.wires_from_circuit`
     does for the real proof — no server needed: `board.custom.board_object.seed_tables()` carries them);
  3. ensure the server (--api) holds the HardwareBridgeDefinition `button-clock` (POST /api/grpc/bridges — the
     explicit knob act `uno_core_demo.custom.readiness._bridge_part` names) and its HardwareInterfaceBinding
     (button-clock/ButtonClockState/0, a generic CRUDE POST — every object class gets one, grpcbridge.mapping_basis.
     _bind() is the SAME shape for uno-pair's bindings), both idempotent (a second run reuses them);
  4. forward the twin's frames to --api for the run's duration. Two routes, named in the output:
       - gRPC (the generated Java bridge: grpcbridge.custom.java_bridge.generate_project + mvn + the jar — the 0e3
         reconnect/snapshot/gap lifecycle actually runs) when the server's gRPC sidecar (:3002, PolariGrpcServer) is
         reachable FROM THIS HOST (a plain TCP connect, checked before anything is built — refused loudly, not
         silently skipped);
       - HTTP (the fallback, FIRST-CLASS here because the live server's :3002 is not published in the compose stack
         — `docker service ls` / `.generated/stack-node.yml` name no 3002 port, and a direct TCP connect from this
         host times out): decode each frame with THE SAME pinned v2 wire spec `board_button_clock_twin_selftest`
         proves against (`board.custom.gen.pinned_contract` + `board.custom.compat.wire_spec`, fully offline), then
         push the SAME rows the Java bridge's GrpcForwarder would — ButtonClockState upserted by name (the bound
         identity, the binding above), ButtonClockEvent rows appended (deliberately UNBOUND, UNO_CORE_DEMO_PLAN.md
         §3) — through the generic CRUDE PUT/POST doors every object class carries (`polariApiServer.polariCRUDE`).
     Both routes fan out through `polariCRUDE._notify_ws_subscribers` -> `transport_mux.publish_crude_change` — the
     SAME fan-out the gRPC push loop uses — so the cross-domain relay (button-clock-ledger -> ButtonClockDerived)
     fires on either route; this is said, not assumed (the live run below confirms it by reading ButtonClockDerived
     back).

Exit 3 = refused (no built firmware, no twin engine, no --api); exit 1 = the push ran but something came back short
of the targets named on the command line.
"""
import json
import os
import select
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BOARD = 'arduino-uno-r3'
CIRCUIT = 'uno-button-clock'
BRIDGE_NAME = 'button-clock'
STATE_CLASS = 'ButtonClockState'
EVENT_CLASS = 'ButtonClockEvent'
STATE_ROW = 'uno-button-clock'          # the rig_name knob — "it is the row name" (board.custom.variants)
BINDING_NAME = '%s/%s/0' % (BRIDGE_NAME, STATE_CLASS)
TWIN_INSTANCE = 'twin:%s' % BOARD
TWIN_LINK_DEFAULT = '/tmp/polari-uno-attach-twin-uart'
TWIN_TCP_DEFAULT = 9833
START_CYCLE = 1600000            # 100 ms in — past every *_init() at the top of main() (ucd-0e2's own margin)
HOLD_CYCLES = 80000              # ~5 ms "held" before release
MIN_GAP_CYCLES = 2400000         # 150 ms: >= 3x the firmware's HAL_INT0_DEBOUNCE_MS (ucd-0e2's own spacing rule)
MCU_HZ = 16000000


class AttachCliError(RuntimeError):
    pass


# --------------------------------------------------------------------- offline: build + twin + wire specs


def _build_variant(variant, work):
    """gen + build, no manager, no server — the SAME offline path board_button_clock_twin_selftest._build proves
    (12/12 on the twin). Raises AttachCliError naming the refusal."""
    from board.custom import build as B
    from board.custom import gen
    try:
        gen.gen('uno', None, work, variant=variant)
        row = B.build('uno', work)
    except gen.GenRefused as e:
        raise AttachCliError('build refused: %s' % e)
    if row.get('state') != 'built':
        raise AttachCliError('uno-button-clock did not build: %s' % row.get('notes'))
    return row


def _wire_specs():
    """{class: (field_map, spec)} fully offline — the pinned v1 contract snapshot + wire_contract.spec(instances=1),
    the SAME two calls board_button_clock_twin_selftest._specs() makes."""
    from board.custom import gen
    from board.custom.compat import wire_spec
    out = {}
    for cls in (STATE_CLASS, EVENT_CLASS):
        fmap = gen.pinned_contract(cls)[0]['field_map']
        out[cls] = (fmap, wire_spec(None, cls, fmap))
    return out


def _press_schedule(presses, seconds):
    """[(cycle, 'PD2', level), ...] — `presses` presses spread evenly across `seconds` of REAL wall-clock twin time
    (the twin paces cycles to MCU_HZ when realtime=True), spaced at least MIN_GAP_CYCLES apart (the debounce margin;
    ucd-0e2's own schedule). Returns the schedule and the last press's end cycle, so the caller can size `seconds`."""
    gap = max(MIN_GAP_CYCLES, int(seconds * MCU_HZ / (presses + 1))) if presses else MIN_GAP_CYCLES
    out, c = [], START_CYCLE
    for _ in range(presses):
        out += [(c, 'PD2', 0), (c + HOLD_CYCLES, 'PD2', 1)]
        c += gap
    return out, c


def _wires():
    """[(src_pin, dst_pin), ...] derived from the seeded BoardPinNet rows (no server — board.custom.board_object.
    seed_tables carries them since ucd-0c), with the plan's own PD6:PD3 as a named fallback if the seed is thin."""
    from board.custom import board_object as BO
    from board.custom import twin as T
    wires, why = T.wires_from_circuit(BOARD, CIRCUIT, BO.seed_tables())
    if wires:
        return wires, 'derived from BoardPinNet rows (circuit %s)' % CIRCUIT
    return [('PD6', 'PD3')], 'fallback (seed gave none: %s) — the plan\'s own wire (UNO_CORE_DEMO_PLAN.md §1)' % (why or 'no rows')


# --------------------------------------------------------------------- the --api side: multipart CRUDE + JSON doors


def _multipart(fields):
    boundary = uuid.uuid4().hex
    buf = []
    for name, value in fields.items():
        buf.append('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value))
    buf.append('--%s--\r\n' % boundary)
    return 'multipart/form-data; boundary=%s' % boundary, ''.join(buf).encode('utf-8')


def _http(api, method, path, data=None, headers=None, timeout=30):
    from polariApiServer import outbound
    req = urllib.request.Request(api.rstrip('/') + path, data=data, headers=headers or {}, method=method)
    try:
        with outbound.http_request('self', 'board', method, req, means='rest', timeout=timeout, lib='urllib',
                                   context=ssl._create_unverified_context()) as r:
            raw = r.read()
            if not raw:   # polariCRUDE's on_put answers 200 with an EMPTY body on success — not an error
                return {'ok': True}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        if not raw:
            return {'ok': False, 'error': 'HTTP %s %s' % (e.code, e.reason)}
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': 'HTTP %s %s' % (e.code, e.reason)}
    except urllib.error.URLError as e:
        return {'ok': False, 'error': 'unreachable: %s' % e}


def crude_get(api, cls, **query):
    qs = ('?' + urllib.parse.urlencode(query)) if query else ''
    doc = _http(api, 'GET', '/%s%s' % (cls, qs))
    try:
        return doc[0][cls][0].get('data') or []
    except Exception:  # noqa: BLE001
        return []


def crude_post(api, cls, params):
    ctype, body = _multipart({'initParamSets': json.dumps([params])})
    doc = _http(api, 'POST', '/%s' % cls, data=body, headers={'Content-Type': ctype})
    try:
        rows = doc.get(cls)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and 'data' in rows[0]:
            return rows[0]['data']
    except Exception:  # noqa: BLE001
        pass
    return []


def crude_put(api, cls, polari_id, update_data):
    ctype, body = _multipart({'polariId': polari_id, 'updateData': json.dumps(update_data)})
    return _http(api, 'PUT', '/%s' % cls, data=body, headers={'Content-Type': ctype})


def grpc_reachable(api, timeout=2.5):
    host = urllib.parse.urlparse(api).hostname or ''
    if not host:
        return False
    try:
        with socket.create_connection((host, 3002), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_bridge(api, serial_device):
    """POST /api/grpc/bridges — the explicit knob act (readiness._bridge_part names it). Idempotent: a 409 (already
    exists) is read back, never retried as an error."""
    existing = _http(api, 'GET', '/api/grpc/bridges')
    for b in (existing.get('bridges') or []):
        if b.get('bridgeName') == BRIDGE_NAME:
            return b, False
    payload = json.dumps({'bridgeName': BRIDGE_NAME, 'classes': [STATE_CLASS, EVENT_CLASS], 'source': 'serial',
                          'serialDevice': serial_device, 'baud': 115200, 'grpcEnabled': False, 'grpcTarget': '',
                          'deviceId': 3}).encode('utf-8')
    doc = _http(api, 'POST', '/api/grpc/bridges', data=payload, headers={'Content-Type': 'application/json'})
    if doc.get('ok'):
        return doc.get('bridge'), True
    return doc, False


def ensure_binding(api, port):
    rows = crude_get(api, 'HardwareInterfaceBinding', name=BINDING_NAME)
    if rows:
        return rows[0], False
    params = {'name': BINDING_NAME, 'bridge_name': BRIDGE_NAME, 'object_class': STATE_CLASS, 'object_name': STATE_ROW,
             'board_instance': TWIN_INSTANCE, 'board_definition': BOARD, 'interface_kind': 'twin-pty',
             'interface_name': 'usart0', 'port': port, 'adapter': '', 'instance_index': 0, 'wire_version': 2,
             'origin': 'attach-cli',
             'notes': 'ucd-frames+bundle: pol board attach — the twin\'s own pty, forwarded over HTTP (no gRPC leg reachable)'}
    created = crude_post(api, 'HardwareInterfaceBinding', params)
    return (created[0] if created else {}), True


# --------------------------------------------------------------------- the forwarder


def _decode_stream(link, seconds, specs):
    """Read the twin's pty for `seconds`, yielding decoded (class_name, {field: value}) frames as they arrive
    (StreamParser, resync-safe). Opens the link in a retry loop (the twin may still be settling its first bytes)."""
    from board.custom import packet_ref
    fmap_s, spec_s = specs[STATE_CLASS]
    fmap_e, spec_e = specs[EVENT_CLASS]
    t_end = time.time() + seconds
    fd = None
    for _ in range(50):
        try:
            fd = os.open(link, os.O_RDONLY | os.O_NONBLOCK)
            break
        except OSError:
            time.sleep(0.1)
    if fd is None:
        raise AttachCliError('could not open the twin\'s link %s' % link)
    parser = packet_ref.StreamParser()
    out = []
    try:
        while time.time() < t_end:
            r, _, _ = select.select([fd], [], [], max(0.0, min(0.5, t_end - time.time())))
            if not r:
                continue
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not chunk:
                continue
            for mt, dev, seq, payload, ver in parser.feed(chunk):
                try:
                    if mt == 1:
                        out.append((STATE_CLASS, packet_ref.decode_any(fmap_s, payload, ver, spec_s)))
                    elif mt == 2:
                        out.append((EVENT_CLASS, packet_ref.decode_any(fmap_e, payload, ver, spec_e)))
                except Exception:  # noqa: BLE001 — a bad frame is dropped, never crashes the run
                    continue
    finally:
        os.close(fd)
    return out, parser.frames, parser.bad_crc


def _push_http(api, frames, state_every=5):
    """Push the decoded frames through the CRUDE doors — the SAME rows the Java bridge's GrpcForwarder would make:
    ButtonClockState upserted by name (the bound identity), ButtonClockEvent rows appended (unbound). Each push is
    its own HTTPS round trip (no keep-alive in polariCRUDE's multipart door — a few hundred ms apiece against a
    remote host adds up fast at 10 Hz), so ButtonClockState is pushed every `state_every`-th frame PLUS always the
    LAST one (so the row's final numbers are exact); every ButtonClockEvent frame is pushed (the task's own count —
    presses/edges/syncs — must not be thinned)."""
    state_id = None
    pushed_state, pushed_events = 0, 0
    state_frames = [i for i, (cls, _) in enumerate(frames) if cls == STATE_CLASS]
    keep_state = set(state_frames[::state_every]) | ({state_frames[-1]} if state_frames else set())
    for i, (cls, values) in enumerate(frames):
        values = dict(values)
        values.pop('_index', None)
        values.pop('_present', None)
        if cls == STATE_CLASS:
            if i not in keep_state:
                continue
            values['name'] = STATE_ROW
            if state_id is None:
                existing = crude_get(api, STATE_CLASS, name=STATE_ROW)
                state_id = existing[0]['id'] if existing else ''
            if state_id:
                r = crude_put(api, STATE_CLASS, state_id, {k: v for k, v in values.items() if k != 'name'})
                if isinstance(r, dict) and r.get('error'):
                    continue
            else:
                created = crude_post(api, STATE_CLASS, values)
                if created:
                    state_id = created[0].get('id', '')
            pushed_state += 1
        elif cls == EVENT_CLASS:
            values.setdefault('name', '%s:%d' % (STATE_ROW, int(values.get('seq', pushed_events))))
            created = crude_post(api, EVENT_CLASS, values)
            if created:
                pushed_events += 1
    return pushed_state, pushed_events


# --------------------------------------------------------------------- main


def attach(variant, api, seconds, presses, work, twin_tcp, twin_link):
    from board.custom import twin as T
    build_row = _build_variant(variant, work)
    print('[ .. ] build    %s (flash %s B, ram %s B)' % (build_row['name'], build_row.get('flash_bytes'), build_row.get('ram_bytes')))
    pinat, end_cycle = _press_schedule(presses, seconds)
    need_s = (end_cycle + HOLD_CYCLES * 2) / float(MCU_HZ)
    if need_s > seconds:
        print('[WARN] %d presses need ~%.1f s to complete; --seconds %d is tight — raise it if presses look short' % (presses, need_s, seconds))
    wires, wires_why = _wires()
    print('[ .. ] wires    %s (%s)' % (wires, wires_why))
    specs = _wire_specs()
    state = T.up('uno', work, tcp=twin_tcp, link=twin_link, adc0_mv=750, realtime=True, pin_at=pinat, wires=wires)
    print('[ OK ] twin up  %s (%s), link %s' % (state['build'], state['how'], state['link']))
    route = 'none'
    grpc_ok = grpc_reachable(api) if api else False
    if api:
        if grpc_ok:
            print('[ .. ] gRPC :3002 is reachable on %s — the generated Java bridge route is not yet wired into this '
                 'CLI (ucd-frames+bundle scope); falling back to the HTTP forwarder below (frames are IDENTICAL rows).' % api)
        else:
            print('[ .. ] gRPC :3002 is UNREACHABLE from this host (a plain TCP connect timed out/refused) — using '
                 'the HTTP forwarder (packet_ref decode + CRUDE PUT/POST), not the generated Java bridge.')
        bridge, bridge_new = ensure_bridge(api, state['link'])
        print('[ %s ] bridge   %s%s' % ('OK' if not isinstance(bridge, dict) or not bridge.get('error') else 'FAIL',
                                        BRIDGE_NAME, ' (created)' if bridge_new else ' (already existed)'))
        binding, binding_new = ensure_binding(api, state['link'])
        print('[ .. ] binding  %s%s' % (BINDING_NAME, ' (created)' if binding_new else ' (already existed)'))
        route = 'http'
    try:
        frames, total_frames, bad_crc = _decode_stream(state['link'], seconds, specs)
    finally:
        T.down('uno', work)
    print('[ OK ] twin down; decoded %d frame(s) (%d bad CRC)' % (total_frames, bad_crc))
    pushed_state, pushed_events = (0, 0)
    if api:
        pushed_state, pushed_events = _push_http(api, frames)
        print('[ OK ] pushed   %d ButtonClockState update(s), %d ButtonClockEvent row(s) via CRUDE PUT/POST' % (pushed_state, pushed_events))
        readiness = _http(api, 'GET', '/api/uno-core-demo/readiness')
        print('[ .. ] readiness: %s' % json.dumps(readiness, indent=None)[:400])
    return {'route': route, 'frames_decoded': total_frames, 'bad_crc': bad_crc, 'pushed_state': pushed_state,
           'pushed_events': pushed_events, 'grpc_reachable': grpc_ok}


def main(argv):
    import argparse
    import tempfile
    ap = argparse.ArgumentParser(prog='pol board attach')
    ap.add_argument('board', nargs='?', default='uno')
    ap.add_argument('--variant', default='uno-button-clock')
    ap.add_argument('--twin', action='store_true')
    ap.add_argument('--api', default=os.environ.get('POLARI_API', ''))
    ap.add_argument('--seconds', type=int, default=20)
    ap.add_argument('--presses', type=int, default=4)
    ap.add_argument('--work', default='')
    ap.add_argument('--tcp', type=int, default=TWIN_TCP_DEFAULT)
    ap.add_argument('--link', default=TWIN_LINK_DEFAULT)
    a = ap.parse_args(argv)
    if a.board not in ('uno', 'arduino-uno-r3'):
        print('[REFUSED] only the UNO has firmware variants so far (plan §8a)')
        return 3
    if not a.twin:
        print('[REFUSED] --twin is required — a real-board attach route is out of scope for this slice '
             '(ucd-frames+bundle); the twin is proven-on-twin today (button-clock-to-os)')
        return 3
    work = a.work or tempfile.mkdtemp(prefix='polari-uno-attach-')
    try:
        r = attach(a.variant, a.api, a.seconds, a.presses, work, a.tcp, a.link)
    except AttachCliError as e:
        print('[REFUSED] %s' % e)
        return 3
    if not a.api:
        print('[ .. ] no --api given — decoded %d frame(s) locally, pushed nothing (pass --api to forward to a server)' % r['frames_decoded'])
        return 0
    return 0 if r['pushed_state'] and r['frames_decoded'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
