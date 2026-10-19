"""
@module grpcbridge.custom.hosted_bridges

sim-2 (HARDWARE_BENCH_CONVERGENCE_PLAN.md section 3): HOSTED BRIDGES as HostedBridge rows over the bridge-engines worker's /bridges door.

    start(manager, session, bridge_name='uno-light', grpc_target='', api_host='', ttl_s=None, owner='', log_only=False) -> view
                    take the TwinSession (its host + USART tcp port), generate the bridge's project (the generate door's own code: live rows, else for
                    uno-light the code-owned rows the demo bundle uses), POST it to the worker (grpcbridge.custom.bridge_engines.resolve), write the row.
                    The bridge's gRPC target = THIS backend's gRPC bridge port on the host the request came from (the demo bundle's derivation,
                    hwnocode.custom.export_demo.grpc_target) unless `grpc_target` is given; `log_only` = no gRPC, the bridge only logs the frames it decodes.
    listing(manager) / one(manager, name)    refresh each live row from the worker first (an ended session ends its bridge)
    stop(manager, name) / logs(manager, name, tail, which)

Every refusal is a HostedRefused carrying plain words and an HTTP status the door passes on.
"""
import re
import secrets
import time

from grpcbridge.custom import bridge_engines as be, hosted_worker as W
from grpcbridge.custom import java_bridge as jb

CLASS = 'HostedBridge'
DEFAULT_BRIDGE = 'uno-light'
TTL_MAX = 14400
_FALLBACK = {}   # rows when there is no manager (the CLI's offline path, selftests)


class HostedRefused(RuntimeError):
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
    raise HostedRefused('no hosted bridge %r (GET /api/grpc/hosted-bridges lists them)' % name, 404)


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass


def _new_row(manager, **kw):
    from grpcbridge.hosted_basis import HostedBridge
    row = HostedBridge(manager=manager, **kw)
    if getattr(manager, 'objectTables', None) is None:
        _FALLBACK[kw['name']] = row
    return row


def view(row):
    now = time.time()
    return {'name': row.name, 'session': row.session, 'bridge_name': row.bridge_name, 'state': row.state, 'worker': row.worker_url,
            'worker_bridge': row.worker_bridge, 'twin': '%s:%s' % (row.twin_host, row.twin_port), 'grpc_target': row.grpc_target, 'grpc': bool(row.grpc_target),
            'build_fp': row.build_fp, 'jar_sha256': row.jar_sha256, 'owner': row.owner, 'started_at': row.started_at, 'expires_at': row.expires_at,
            'ttl_s': row.ttl_s, 'remaining_s': max(0.0, round(row.expires_at - now, 1)) if row.state in ('building', 'running') else 0,
            'ended_at': row.ended_at, 'end_reason': row.end_reason,
            'doors': {'logs': '/api/grpc/hosted-bridges/%s/logs' % row.name}}


# ------------------------------------------------------------------ the project
def grpc_target(api_host=''):
    """<host>:3002 from the address this server was reached at (the demo bundle's derivation)."""
    try:
        from hwnocode.custom.export_demo import grpc_target as derive
        return derive(api_host)
    except Exception:  # noqa: BLE001 - hwnocode not shipped here: the same rule, inline
        h = re.sub(r'^[a-z]+://', '', (api_host or '').strip()).split('/')[0]
        h = h.split(']')[0] + ']' if h.startswith('[') else h.split(':')[0]
        return '%s:3002' % (h or 'localhost')


def project(manager, bridge_name):
    """-> (files {path: text}, source). The generate door's code; for the light bridge a server without the rows falls back to the code-owned ones
    (the same project the demo bundle ships)."""
    bridge = jb.get_bridge(manager, bridge_name) if manager is not None else None
    live = None
    if bridge is not None:
        live = jb.generate_project(manager, bridge)
        if live.get('ok'):
            return live['files'], 'rows'
    if bridge_name == DEFAULT_BRIDGE:
        try:
            from hwnocode.custom import offline_project as OP
            rep = OP.light_project()
            if rep.get('ok'):
                return rep['files'], 'code-owned rows (this server has no ready %s rows%s)' % (bridge_name, ': ' + live['error'] if live else '')
        except ImportError:
            pass
    if live is not None:
        raise HostedRefused('the bridge %r cannot be generated: %s' % (bridge_name, live.get('error')), 422)
    raise HostedRefused('no bridge %r on this server (GET /api/grpc/bridges lists them)' % bridge_name, 404)


# ------------------------------------------------------------------ the worker
def _worker():
    where = be.resolve()
    if where['how'] != be.REMOTE:
        raise HostedRefused(where['why'], 424)   # 424, not 503: the proxy masks 503 as "Backend unavailable"
    return where['where']


def _end(manager, row, why):
    if row.state in ('building', 'running'):
        row.state, row.ended_at, row.end_reason = 'ended', time.time(), why
        _save(manager, row)


def _apply(manager, row, w):
    """Fold the worker's view of the bridge into the row."""
    st = w.get('state')
    if w.get('jar_sha256'):
        row.jar_sha256 = w['jar_sha256']
    if st == 'failed':
        row.state, row.ended_at, row.end_reason = 'failed', time.time(), w.get('end_reason') or 'the bridge did not build'
    elif st == 'ended':
        _end(manager, row, w.get('end_reason') or 'ended on the worker')
    elif st in ('building', 'running') and row.state in ('building', 'running'):
        row.state = st
    _save(manager, row)


def start(manager, session, bridge_name=DEFAULT_BRIDGE, grpc_target_='', api_host='', ttl_s=None, owner='', log_only=False):
    from board.custom import twin_sessions as TS
    try:
        sess = TS.one(manager, session)
    except TS.SessionRefused as e:
        raise HostedRefused(str(e), e.status)
    if sess['state'] != 'running':
        raise HostedRefused('session %s has ended (%s) - start a new one' % (session, sess['end_reason']), 409)
    files, source = project(manager, bridge_name)
    worker = _worker()
    target = '' if log_only else (grpc_target_ or grpc_target(api_host))
    ttl = int(ttl_s or min(max(sess['remaining_s'], 10), TTL_MAX))
    try:
        w = W.start(worker, {'session_id': sess['name'], 'twin_host': sess['host'], 'twin_port': sess['tcp_port'], 'bridge_name': bridge_name, 'files': files,
                             'grpc_target': target, 'ttl_s': ttl, 'owner': owner})
    except W.WorkerRefused as e:
        raise HostedRefused(str(e), 424 if e.status in (0, 503) else (e.status or 502))
    name = '%s-%s' % (bridge_name, secrets.token_hex(3))
    row = _new_row(manager, name=name, session=sess['name'], bridge_name=bridge_name, state='building', worker_url=worker, worker_bridge=w['id'],
                   twin_host=sess['host'], twin_port=int(sess['tcp_port']), grpc_target=target, build_fp=w.get('build_fp', ''), owner=owner,
                   started_at=w['started'], expires_at=w['expires'], ttl_s=ttl)
    _apply(manager, row, w)
    return dict(view(row), project_source=source, build=w.get('build'))


def _refresh(manager, row):
    if row.state not in ('building', 'running'):
        return
    try:
        w = W.get(row.worker_url, row.worker_bridge)
    except W.WorkerRefused as e:
        if e.status == 404:
            _end(manager, row, 'the worker no longer has this bridge (reaped at its TTL, or the worker restarted)')
        return   # unreachable: leave it, the next look asks again
    _apply(manager, row, w)
    if row.state in ('building', 'running'):
        try:
            if TS_state(manager, row.session) != 'running':
                stop(manager, row.name, 'its session %s ended' % row.session)
        except HostedRefused:
            pass


def TS_state(manager, session):
    from board.custom import twin_sessions as TS
    try:
        return TS.one(manager, session)['state']
    except TS.SessionRefused:
        return 'ended'


def listing(manager):
    for r in _rows(manager):
        _refresh(manager, r)
    return [view(r) for r in sorted(_rows(manager), key=lambda r: r.started_at)]


def one(manager, name):
    row = _find(manager, name)
    _refresh(manager, row)
    out = view(row)
    if row.state in ('building', 'running'):
        try:
            w = W.get(row.worker_url, row.worker_bridge)
            out['output_tail'], out['rss_kb'], out['cpu_s'] = w.get('output_tail'), w.get('rss_kb'), w.get('cpu_s')
        except W.WorkerRefused:
            pass
    return out


def stop(manager, name, why=''):
    row = _find(manager, name)
    if row.state in ('building', 'running'):
        try:
            W.stop(row.worker_url, row.worker_bridge)
        except W.WorkerRefused as e:
            if e.status != 404:
                raise HostedRefused(str(e), 424)
        _end(manager, row, why or 'stopped by %s' % (row.owner or 'a person'))
    return view(row)


def logs(manager, name, tail=100, which='run'):
    row = _find(manager, name)
    try:
        return W.logs(row.worker_url, row.worker_bridge, tail, which)
    except W.WorkerRefused as e:
        raise HostedRefused(str(e), 404 if e.status == 404 else 424)
