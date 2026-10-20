"""grpcbridge.custom.hosted_proof - the BOTH-DIRECTIONS proof of sim-2 against a Polari server (the test node), run from any machine that reaches the engines workers
and the server:

    HOSTED_PROOF_API=https://api.prf.<test node>   BOARD_ENGINES_URL=http://<engines host>:9830   BRIDGE_ENGINES_URL=http://<engines host>:9870 \
        PYTHONPATH=.:modules python3 -m grpcbridge.grpcbridge_hosted_selftest

  1. a REAL uno-light twin session (this process holds the control connection) and a REAL hosted bridge beside it whose gRPC target is the SERVER's :3002;
  2. UP: PD2 0 then 1 (the button) -> within 2 s the server's LightState row `uno-light` reads led_on=True toggles=1 source=button (GET /LightState);
  3. DOWN: POST /executeSolutionStepped {light-toggle} on the server -> the twin's watched PD6 FALLS on the events stream, and the next report (the row) says source=command.
Everything it starts is stopped in a finally block. The server needs LightState exposed over gRPC with the pinned contract (the uno-light demo's own setup)."""
import json
import re
import ssl
import tempfile
import time
import types
import urllib.request


def _http(method, url, body=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={'Content-Type': 'application/json'} if body is not None else {})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl._create_unverified_context()) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw.strip().startswith((b'{', b'[')) else raw.decode('utf-8', 'replace'))


def row(api, name='uno-light'):
    """The LightState row `name` as the server serves it, or None."""
    _, d = _http('GET', api + '/LightState')
    for grp in d:
        for blk in grp.get('LightState', []):
            for r in blk.get('data', []):
                if r.get('name') == name:
                    return r
    return None


def _wait_row(api, test, secs):
    t0 = time.time()
    last = None
    while time.time() - t0 < secs:
        last = row(api)
        if last and test(last):
            return last, round((time.time() - t0) * 1000)
        time.sleep(0.1)
    return last, None


def run(check, api):
    import os
    from board.custom import twin_sessions as TS
    from grpcbridge.custom import bridge_engines as be, hosted_bridges as HB
    from board.custom import board_engines as bce
    bce._CAP_CACHE.clear()
    be.forget()
    api = api.rstrip('/')
    mgr = types.SimpleNamespace(objectTables={}, db=None, idList=[])
    os.environ.setdefault('POLARI_TWIN_TOKEN_FILE', os.path.join(tempfile.gettempdir(), 'hosted-proof-token-%d' % os.getpid()))
    s = h = sub = None
    try:
        try:
            code, tw = _http('GET', api + '/api/board/twins')
            before = row(api)
        except Exception as e:  # noqa: BLE001
            return check('sim-2 proof: the server answers (GET /api/board/twins, GET /LightState)', False, '%s: %s' % (api, e))
        check('sim-2 proof: the server answers GET /api/board/twins (200, sim-1 doors) and serves the LightState row uno-light', code == 200 and isinstance(tw, dict) and before is not None,
              'twins=%s row=%s' % (str(tw)[:80], before))
        s = TS.start(mgr, 'uno-light', ttl_s=600, owner='hosted-proof', watch=['PD6', 'PB5'])
        h = HB.start(mgr, s['name'], api_host=api, ttl_s=540, owner='hosted-proof')
        t0 = time.time()
        while h['state'] == 'building' and time.time() - t0 < 300:
            time.sleep(1)
            h = dict(h, **{k: v for k, v in HB.one(mgr, h['name']).items() if k in ('state', 'jar_sha256', 'end_reason')})
        check('sim-2 proof: the hosted bridge is running (gRPC target %s)' % h['grpc_target'], h['state'] == 'running', str(h)[:300])
        end = time.time() + 20
        while time.time() < end and 'grpc=' not in ' '.join(HB.logs(mgr, h['name'], tail=50)['lines']):
            time.sleep(0.3)
        time.sleep(2.0)   # the gRPC channel + the Commands stream come up
        sub = TS.events(mgr, s['name'])
        base_toggles = (row(api) or {}).get('toggles')
        TS.inject(mgr, s['name'], {'set': 'PD2', 'level': 0})
        time.sleep(0.07)
        t_press = time.time()
        TS.inject(mgr, s['name'], {'set': 'PD2', 'level': 1})
        up, ms = _wait_row(api, lambda r: r.get('toggles') == 1 and r.get('source') == 'button' and r.get('led_on') is True, 2.0)
        check('sim-2 proof UP: press on the twin (PD2 0 then 1) -> the SERVER\'s LightState row uno-light reads led_on=True toggles=1 source=button within 2 s (took %s ms; was toggles=%s)'
              % (ms, base_toggles), ms is not None and ms <= 2000, str(up))
        events = []
        while True:
            ev = sub.get(timeout=0.2)
            if ev is None:
                break
            events.append(ev)
        check('sim-2 proof UP: the twin\'s watched PD6 rose on the events stream (the firmware lit the LED)', any(e.get('pin') == 'PD6' and e.get('level') == 1 for e in events), str(events[-5:]))
        seq_before = (up or {}).get('seq')
        code, out = _http('POST', api + '/executeSolutionStepped', {'solutionName': 'light-toggle', 'inputParams': {'object': 'uno-light', 'led_on': True}}, timeout=60)
        down_events, t_cmd = [], time.time()
        while time.time() - t_cmd < 3.0 and not any(e.get('pin') == 'PD6' and e.get('level') == 0 for e in down_events):
            ev = sub.get(timeout=0.2)
            if ev is not None:
                down_events.append(ev)
        fell = [e for e in down_events if e.get('pin') == 'PD6' and e.get('level') == 0]
        check('sim-2 proof DOWN: POST /executeSolutionStepped light-toggle on the server -> the twin\'s watched PD6 FALLS on the events stream (HTTP %s, %.0f ms after the post)'
              % (code, (time.time() - t_cmd) * 1000), code == 200 and bool(fell), 'post=%s events=%s' % (str(out)[:200], down_events[-5:]))
        down, ms2 = _wait_row(api, lambda r: r.get('source') == 'command' and r.get('led_on') is False and r.get('seq') != seq_before, 3.0)
        check('sim-2 proof DOWN: the next report says source=command (the server\'s row reads led_on=False toggles=%s source=command)' % (down or {}).get('toggles'), ms2 is not None, str(down))
        logs = re.sub(r'\s+', ' ', ' '.join(HB.logs(mgr, h['name'], tail=40)['lines']))
        check('sim-2 proof: the bridge\'s own log shows both reports (button, then command)', 'source=button' in logs and 'source=command' in logs, logs[-400:])
    finally:
        if sub is not None:
            sub.close()
        for fn, r in ((HB.stop, h), (TS.stop, s)):
            if r:
                try:
                    fn(mgr, r['name'])
                except Exception as e:  # noqa: BLE001
                    print('cleanup:', e)
