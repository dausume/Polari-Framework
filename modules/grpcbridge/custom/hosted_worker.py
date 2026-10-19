"""
@module grpcbridge.custom.hosted_worker

sim-2: the HTTP client of the bridge-engines worker's /bridges door (prf-bridge-engines/bridge_hosted.py). Every call goes through the outbound seam (system
kind `engine`, name `grpcbridge`, means `bridge`). A worker's refusal comes back as WorkerRefused carrying the worker's own words.
"""
import json
import ssl
import urllib.error
import urllib.request


class WorkerRefused(RuntimeError):
    def __init__(self, why, status=0):
        super().__init__(why)
        self.status = status


def _call(method, url, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'} if data else {})
    from polariApiServer import outbound
    base = url.split('/bridges', 1)[0]
    try:
        with outbound.http_request('engine', 'grpcbridge', method, req, means='bridge', timeout=timeout, lib='urllib', context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            why = json.load(e).get('error') or str(e)
        except Exception:  # noqa: BLE001
            why = str(e)
        raise WorkerRefused('the worker at %s refused (%s): %s' % (base, e.code, why), e.code)
    except (urllib.error.URLError, OSError) as e:
        raise WorkerRefused('the worker at %s is unreachable: %s' % (base, e))


def start(worker, body):
    return _call('POST', '%s/bridges' % worker, body, timeout=60)


def get(worker, bid):
    return _call('GET', '%s/bridges/%s' % (worker, bid))


def listing(worker):
    return _call('GET', '%s/bridges' % worker)


def stop(worker, bid):
    return _call('DELETE', '%s/bridges/%s' % (worker, bid))


def logs(worker, bid, tail=100, which='run'):
    return _call('GET', '%s/bridges/%s/logs?tail=%d&which=%s' % (worker, bid, int(tail), which))
