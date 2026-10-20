"""
@module grpcbridge.custom.hosted_cli

sim-2: `pol grpc hosted ...` - a thin client of the hosted-bridge doors (/api/grpc/hosted-bridges), so it works from any machine that can reach the backend.

  pol grpc hosted start <session> [--bridge uno-light] [--ttl S] [--owner O] [--grpc-target HOST:PORT | --log-only] [--wait S] [--api URL]
                                   run the generated bridge beside a twin session (a TwinSession name, `pol board twin session list`); its gRPC target is the
                                   gRPC bridge port (3002) of the host --api points at unless --grpc-target says otherwise; waits for state running
  pol grpc hosted list [--api URL]
  pol grpc hosted show <id> [--api URL]
  pol grpc hosted stop <id> [--api URL]
  pol grpc hosted logs <id> [--tail N] [--build] [--api URL]
  pol grpc hosted engines [--api URL]      where hosted bridges would run (BRIDGE_ENGINES_URL -> topology provider grpcbridge.engines -> refusal)

Add --json for the raw answer. Exit 0 ok, 1 refused (the words are printed), 2 bad usage.
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request


def _call(api, method, path, body=None, timeout=120):
    req = urllib.request.Request(api.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'} if body is not None else {}, method=method)
    from polariApiServer import outbound
    try:
        with outbound.http_request('self', 'grpcbridge', method, req, means='rest', timeout=timeout, lib='urllib', context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': 'HTTP %s' % e.code}
    except (urllib.error.URLError, OSError) as e:
        return {'ok': False, 'error': 'cannot reach %s: %s' % (api, e)}


def line(b):
    return '%-22s %-9s session %-20s twin %-22s %s  %6.0fs left  %s' % (b['name'], b['state'], b['session'], b['twin'], 'grpc ' + b['grpc_target'] if b['grpc']
                                                                           else 'log-only', b['remaining_s'], b['jar_sha256'][:12])


def render_start(d):
    out = ['hosted bridge %s (%s) beside %s: %s' % (d['name'], d['bridge_name'], d['session'], d['state']),
           '  reads      the session\'s serial port %s    pushes to  %s' % (d['twin'], d['grpc_target'] or '(nothing: log-only)'),
           '  worker     %s    project %s' % (d['worker'], d.get('project_source', '')),
           '  jar        %s    build %s' % (d['jar_sha256'][:12] or '(not yet)', json.dumps(d.get('build') or {})),
           '  ends       in %.0f s unless stopped (pol grpc hosted stop %s)' % (d['remaining_s'], d['name'])]
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pol grpc hosted', add_help=True)
    ap.add_argument('verb', choices=['start', 'list', 'show', 'stop', 'logs', 'engines'])
    ap.add_argument('target', nargs='?', default='')
    ap.add_argument('--api', required=True)
    ap.add_argument('--bridge', default='uno-light')
    ap.add_argument('--ttl', type=int, default=0)
    ap.add_argument('--owner', default='')
    ap.add_argument('--grpc-target', default='')
    ap.add_argument('--log-only', action='store_true')
    ap.add_argument('--wait', type=float, default=300.0)
    ap.add_argument('--tail', type=int, default=100)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--json', action='store_true')
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    base = '/api/grpc/hosted-bridges'

    def show(d, text):
        print(json.dumps(d, indent=1) if a.json else text)
        return 0 if d.get('ok') else 1

    def refused(d):
        print(json.dumps(d) if a.json else 'refused: %s' % d.get('error'))
        return 1

    if a.verb in ('show', 'stop', 'logs') and not a.target:
        print('usage: pol grpc hosted %s <id>' % a.verb, file=sys.stderr)
        return 2
    if a.verb == 'start':
        if not a.target:
            print('usage: pol grpc hosted start <session>', file=sys.stderr)
            return 2
        body = {'session': a.target, 'bridge_name': a.bridge, 'owner': a.owner, 'log_only': a.log_only}
        if a.ttl:
            body['ttl_s'] = a.ttl
        if a.grpc_target:
            body['grpc_target'] = a.grpc_target
        elif not a.log_only:   # the host the person reached the server at (the demo bundle's derivation), sent explicitly: a proxy may hide it from the door
            from grpcbridge.custom.hosted_bridges import grpc_target
            body['grpc_target'] = grpc_target(a.api)
        d = _call(a.api, 'POST', base, body, timeout=180)
        if not d.get('ok'):
            return refused(d)
        deadline = time.time() + a.wait
        while d.get('state') == 'building' and time.time() < deadline:
            time.sleep(1.5)
            d = dict(_call(a.api, 'GET', '%s/%s' % (base, d['name'])), project_source=d.get('project_source'), build=d.get('build'))
            if not d.get('ok'):
                return refused(d)
        if d['state'] == 'failed':
            print(json.dumps(d) if a.json else 'FAILED: %s  (pol grpc hosted logs %s --build)' % (d['end_reason'], d['name']))
            return 1
        return show(d, render_start(d))
    if a.verb == 'list':
        d = _call(a.api, 'GET', base)
        return show(d, '\n'.join(line(b) for b in d.get('rows', [])) or 'no hosted bridges') if d.get('ok') else refused(d)
    if a.verb == 'show':
        d = _call(a.api, 'GET', '%s/%s' % (base, a.target))
        if not d.get('ok'):
            return refused(d)
        return show(d, line(d) + ('\n' + '\n'.join('  | ' + ln for ln in d.get('output_tail') or []) if d.get('output_tail') else ''))
    if a.verb == 'stop':
        d = _call(a.api, 'DELETE', '%s/%s' % (base, a.target))
        return show(d, 'stopped %s' % a.target) if d.get('ok') else refused(d)
    if a.verb == 'logs':
        d = _call(a.api, 'GET', '%s/%s/logs?tail=%d%s' % (base, a.target, a.tail, '&which=build' if a.build else ''))
        return show(d, '\n'.join(d.get('lines', []))) if d.get('ok') else refused(d)
    d = _call(a.api, 'GET', '/api/grpc/hosted-engines')
    return show(d, 'knob %s=%s\nprovider %s\nimage %s\nresolved: %s %s (%s)' % (d['knob'], d['knob_value'] or '(unset)', d['provider_module'], d['image'],
                                                                            d['resolved']['how'], d['resolved']['where'], d['resolved']['why'])) if d.get('ok') else refused(d)


if __name__ == '__main__':
    sys.exit(main())
