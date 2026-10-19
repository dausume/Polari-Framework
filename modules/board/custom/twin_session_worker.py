"""
@module board.custom.twin_session_worker

sim-1: the HTTP client of the engines worker's /sessions door (prf-board-engines/board_sessions.py, sim-0). Every call goes through the outbound seam
(system kind `engine`, name `board`, means `session`) so the traffic map and the policies see it. A worker's refusal comes back as WorkerRefused carrying
the worker's own words.
"""
import base64
import json
import ssl
import urllib.error
import urllib.request


class WorkerRefused(RuntimeError):
    def __init__(self, why, status=0):
        super().__init__(why)
        self.status = status


def _call(method, url, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'} if data else {})
    from polariApiServer import outbound
    try:
        with outbound.http_request('engine', 'board', method, req, means='session', timeout=timeout, lib='urllib', context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            why = json.load(e).get('error') or str(e)
        except Exception:  # noqa: BLE001
            why = str(e)
        raise WorkerRefused('the worker at %s refused (%s): %s' % (url.rsplit('/sessions', 1)[0], e.code, why), e.code)
    except (urllib.error.URLError, OSError) as e:
        raise WorkerRefused('the worker at %s is unreachable: %s' % (url.rsplit('/sessions', 1)[0], e))


def start(worker, hex_bytes, board, mcu, ttl_s, token, owner='', free=False):
    body = {'hex_b64': base64.b64encode(hex_bytes).decode(), 'board': board, 'mcu': mcu, 'ttl_s': int(ttl_s), 'token': token, 'owner': owner, 'free': bool(free)}
    return _call('POST', '%s/sessions' % worker, body, timeout=30)


def get(worker, sid):
    return _call('GET', '%s/sessions/%s' % (worker, sid))


def listing(worker):
    return _call('GET', '%s/sessions' % worker)


def stop(worker, sid):
    return _call('DELETE', '%s/sessions/%s' % (worker, sid))
