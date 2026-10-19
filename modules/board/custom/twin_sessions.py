"""
@module board.custom.twin_sessions

sim-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §8): twin SESSIONS as TwinSession rows over the engines worker's /sessions door.

    start(manager, config, ttl_s=1800, owner='', watch=None) -> view + {'token': ...}   build the config's firmware (the shipped gen + build pipeline: the
                                  same .hex `pol board build` writes), POST it to the worker (board_engines.resolve_sessions), connect the ONE backend control
                                  connection, write the row. The hex sha256 on the row is the LOCKED firmware.
    listing(manager) / one(manager, name)    refresh each running row from the worker first (an ended or reaped session is marked, never left "running")
    stop(manager, name)                      DELETE on the worker, close the connection, mark the row ended
    inject(manager, name, body)              {"set":"PD2","level":0} | {"adc":0,"mv":750} | {"reset":1} | {"watch":[..]} | {"run":false} | {"status":1}
    events(manager, name, replay=0)          a Subscription on the session's control stream (see twin_ctl_hub)
    participants(manager)                    the running sessions as Hardware System participants (`twin:<board>#<n>`)

Every refusal is a SessionRefused carrying plain words and an HTTP status the door passes on.
"""
import json
import secrets
import shutil
import tempfile
import time
from urllib.parse import urlparse

from board.custom import board_engines as be, twin_session_worker as W, twin_token
from board.custom.twin_ctl_hub import Hub, HubRefused

DEFAULT_TTL_S = 1800
DEFAULT_WATCH = ['PB5', 'PD2', 'PD3', 'PD4', 'PD5', 'PD6', 'PD7']
BOARD = 'arduino-uno-r3'
MCU = 'atmega328p'
CLASS = 'TwinSession'
HUBS = {}   # row name -> Hub (this backend process's one control connection per session)
_FALLBACK = {}   # rows when there is no manager (the CLI's offline path, selftests)


class SessionRefused(RuntimeError):
    def __init__(self, why, status=409):
        super().__init__(why)
        self.status = status


# ------------------------------------------------------------------ rows
def _table(manager):
    tabs = getattr(manager, 'objectTables', None)
    return tabs.setdefault(CLASS, {}) if tabs is not None else _FALLBACK


def _rows(manager):
    return [r for r in _table(manager).values() if getattr(r, 'name', '')]


def _find(manager, name):
    for r in _rows(manager):
        if r.name == name:
            return r
    raise SessionRefused('no twin session %r (GET /api/board/twins lists them)' % name, 404)


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass


def _new_row(manager, **kw):
    from board.objects.board.TwinSession import TwinSession
    row = TwinSession(manager=manager, **kw)
    if getattr(manager, 'objectTables', None) is None:
        _FALLBACK[kw['name']] = row
    return row


def view(row):
    """The row as the doors show it - no token anywhere."""
    now = time.time()
    last = json.loads(row.last_status_json or '{}')
    return {'name': row.name, 'config': row.config, 'board': row.board, 'participant': row.participant, 'instance_index': row.instance_index, 'state': row.state,
            'firmware': {'sha256': row.hex_sha256, 'bytes': row.hex_bytes, 'locked': bool(row.firmware_locked), 'config': row.config},
            'worker': row.worker_url, 'worker_session': row.worker_session, 'host': row.host, 'tcp_port': row.tcp_port, 'ctl_port': row.ctl_port,
            'owner': row.owner, 'started_at': row.started_at, 'expires_at': row.expires_at, 'ttl_s': row.ttl_s,
            'remaining_s': 0 if row.state != 'running' else max(0.0, round(row.expires_at - now, 1)),
            'ended_at': row.ended_at, 'end_reason': row.end_reason, 'watch': json.loads(row.watch_json or '[]'), 'status': last,
            'doors': {'inject': '/api/board/twins/%s/inject' % row.name, 'events': '/api/board/twins/%s/events' % row.name}}


# ------------------------------------------------------------------ the firmware
def build_hex(config):
    """-> (hex bytes, sha256, why-not). The shipped pipeline (gen + build through the engines ladder), exactly what light_twin / `pol firmware prove` build."""
    import hashlib
    from board.custom import gen, build as B
    work = tempfile.mkdtemp(prefix='twin-session-')
    try:
        try:
            gen.gen('uno', None, work, variant=config)
        except gen.GenRefused as e:
            raise SessionRefused('config %r: %s' % (config, e), 400)
        row = B.build('uno', work)
        if row.get('state') != 'built':
            raise SessionRefused('config %r did not build: %s' % (config, row.get('notes') or row.get('state')), 422)
        data = open(row['hex_path'], 'rb').read()
        return data, hashlib.sha256(data).hexdigest()
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ the worker
def _worker():
    where = be.resolve_sessions()
    if where['how'] != be.REMOTE:
        raise SessionRefused(where['why'], 503)
    return where['where']


def _next_index(manager, board):
    used = {r.instance_index for r in _rows(manager) if r.state == 'running' and r.board == board}
    n = 0
    while n in used:
        n += 1
    return n


def _end(manager, row, why, hub_close=True):
    if row.state != 'ended':
        row.state, row.ended_at, row.end_reason = 'ended', time.time(), why
        _save(manager, row)
    hub = HUBS.pop(row.name, None)
    if hub is not None and hub_close:
        hub.close(why)


def start(manager, config, ttl_s=DEFAULT_TTL_S, owner='', watch=None, free=False, hex_bytes=None):
    worker = _worker()
    if hex_bytes is None:
        hex_bytes, sha = build_hex(config)
    else:
        import hashlib
        sha = hashlib.sha256(hex_bytes).hexdigest()
    name = '%s-%s' % (config, secrets.token_hex(3))
    token = twin_token.derive(name)
    try:
        w = W.start(worker, hex_bytes, BOARD, MCU, ttl_s, token, owner=owner, free=free)
    except W.WorkerRefused as e:
        raise SessionRefused(str(e), 503 if e.status in (0, 503) else (e.status or 502))
    host = urlparse(worker).hostname or ''
    idx = _next_index(manager, BOARD)
    watch = list(watch or DEFAULT_WATCH)
    row = _new_row(manager, name=name, config=config, board=BOARD, participant='twin:%s#%d' % (BOARD, idx), instance_index=idx, state='running', hex_sha256=sha,
                   hex_bytes=len(hex_bytes), firmware_locked=True, worker_url=worker, worker_session=w['id'], host=host, tcp_port=w['ports']['tcp'],
                   ctl_port=w['ports']['ctl'], owner=owner, started_at=w['started'], expires_at=w['expires'], ttl_s=int(ttl_s), watch_json=json.dumps(watch),
                   last_status_json=json.dumps(w.get('status') or {}))
    try:
        HUBS[name] = Hub(host, row.ctl_port, token).connect(watch=watch)
    except HubRefused as e:
        try:
            W.stop(worker, w['id'])
        finally:
            _end(manager, row, 'the control connection could not be made: %s' % e)
        raise SessionRefused('the session started on the worker but its control port could not be reached from here (%s); it was stopped. Is the port range '
                             '9832-9863 published and open between this device and the worker?' % e, 502)
    _save(manager, row)
    return dict(view(row), token=token, token_note='shown once: a bridge or the CLI needs it to attach; it is derived on this server, never stored in the row')


def _refresh(manager, row):
    if row.state != 'running':
        return
    try:
        w = W.get(row.worker_url, row.worker_session)
    except W.WorkerRefused as e:
        if e.status == 404:
            _end(manager, row, 'the worker no longer has this session (it was reaped at its TTL or the worker restarted)')
        return   # unreachable: leave it running, the next look asks again
    if w.get('status'):
        row.last_status_json = json.dumps(w['status'])
    if w.get('state') == 'ended':
        _end(manager, row, w.get('end_reason') or 'ended on the worker')
    elif time.time() >= row.expires_at + 5:
        _end(manager, row, 'TTL reached (%ds)' % row.ttl_s)


def listing(manager):
    for r in _rows(manager):
        _refresh(manager, r)
    rows = sorted(_rows(manager), key=lambda r: r.started_at)
    return [view(r) for r in rows]


def one(manager, name):
    row = _find(manager, name)
    _refresh(manager, row)
    return view(row)


def stop(manager, name):
    row = _find(manager, name)
    if row.state == 'running':
        try:
            W.stop(row.worker_url, row.worker_session)
        except W.WorkerRefused as e:
            if e.status != 404:
                raise SessionRefused(str(e), 503)
        _end(manager, row, 'stopped by %s' % (row.owner or 'a person'))
    return view(row)


# ------------------------------------------------------------------ the control channel
def _hub(manager, row):
    if row.state != 'running':
        raise SessionRefused('session %s has ended (%s)' % (row.name, row.end_reason), 409)
    hub = HUBS.get(row.name)
    if hub is None or hub.dead:   # a backend restart (or a dropped connection): derive the token again and reconnect
        try:
            HUBS[row.name] = hub = Hub(row.host, row.ctl_port, twin_token.derive(row.name)).connect(watch=json.loads(row.watch_json or '[]'))
        except HubRefused as e:
            raise SessionRefused('cannot reach the twin control port: %s' % e, 502)
    return hub


def _command(body):
    if not isinstance(body, dict) or not body:
        raise SessionRefused('inject takes {"set":"PD2","level":0|1}, {"adc":0,"mv":750}, {"reset":1}, {"watch":["PD6"]}, {"run":true|false} or {"status":1}', 400)
    if 'set' in body:
        if body.get('level') not in (0, 1, True, False):
            raise SessionRefused('"set" needs "level": 0 or 1', 400)
        return {'set': str(body['set']), 'level': int(body['level'])}
    if 'adc' in body:
        try:
            return {'adc': int(body['adc']), 'mv': int(body['mv'])}
        except (KeyError, TypeError, ValueError):
            raise SessionRefused('"adc" needs the channel and "mv" as whole numbers, like {"adc":0,"mv":750}', 400)
    if body.get('reset'):
        return {'reset': 1}
    if 'watch' in body:
        if not isinstance(body['watch'], list):
            raise SessionRefused('"watch" takes a list of pins', 400)
        return {'watch': [str(p) for p in body['watch']]}
    if 'run' in body:
        return {'run': bool(body['run'])}
    if body.get('status'):
        return {'status': 1}
    raise SessionRefused('nothing to do in %s (use set, adc, reset, watch, run or status)' % json.dumps(body), 400)


def inject(manager, name, body):
    row = _find(manager, name)
    cmd = _command(body)
    reply = _hub(manager, row).request(cmd)
    if 'watch' in cmd and reply.get('t') == 'ack':
        row.watch_json = json.dumps(cmd['watch'])
        _save(manager, row)
    if reply.get('t') == 'status':
        row.last_status_json = json.dumps(reply)
    return {'ok': reply.get('t') != 'refused', 'sent': cmd, 'reply': reply, 'session': name}


def events(manager, name, replay=0):
    row = _find(manager, name)
    return _hub(manager, row).subscribe(replay=replay)


# ------------------------------------------------------------------ the Hardware System
def participants(manager):
    """Running sessions as participants, in the shape HardwareSystem.participants_json uses ({role, kind, ref, variant})."""
    return [{'role': 'twin session %s' % r.participant, 'kind': 'hardware', 'ref': 'TwinSession:%s' % r.name, 'variant': r.participant}
            for r in sorted(_rows(manager), key=lambda r: (r.board, r.instance_index)) if r.state == 'running']
