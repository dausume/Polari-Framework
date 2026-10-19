"""
@module board.custom.twin_sessions_cli

sim-1: `pol board twin session ...` - a thin client of the twin-session doors (/api/board/twins), so it works from any machine that can reach the backend
(the test node, a laptop); the backend holds the rows and the one control connection per session.

  pol board twin session start <config> [--ttl S] [--owner O] [--watch PD6,PB5] [--free] [--api URL]   start one (the control token is shown ONCE)
  pol board twin session list [--api URL]
  pol board twin session show <name> [--api URL]
  pol board twin session stop <name> [--api URL]
  pol board twin session inject <name> set PD2 0|1 | adc 0 750 | reset | watch PD6,PB5 | run true|false | status [--api URL]
  pol board twin session events <name> [--seconds S] [--limit N] [--replay N] [--api URL]    the pin edges as they happen, one line each

Add --json for the raw answer. Exit 0 ok, 1 refused (the words are printed), 2 bad usage.
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request


def _call(api, method, path, body=None, timeout=120):
    req = urllib.request.Request(api.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'} if body is not None else {}, method=method)
    from polariApiServer import outbound
    try:
        with outbound.http_request('self', 'board', method, req, means='rest', timeout=timeout, lib='urllib', context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': 'HTTP %s' % e.code}
    except (urllib.error.URLError, OSError) as e:
        return {'ok': False, 'error': 'cannot reach %s: %s' % (api, e)}


def line(s):
    return ('%-22s %-9s %-24s %-8s %s  :%s/:%s  %6.0fs left  %s' % (s['name'], s['state'], s['participant'], s['config'], s['firmware']['sha256'][:12],
                                                                   s['tcp_port'], s['ctl_port'], s['remaining_s'], s['host']))


def render_start(d):
    f = d['firmware']
    return '\n'.join([
        'started %s as %s on %s' % (d['name'], d['participant'], d['host']),
        '  firmware   %s (built by the shipped gen + build pipeline), %d bytes, sha256 %s - LOCKED while the session runs' % (d['config'], f['bytes'], f['sha256']),
        '  serial     tcp %s:%s (the USART0 report)    control  %s:%s (JSON lines)' % (d['host'], d['tcp_port'], d['host'], d['ctl_port']),
        '  token      %s    (shown once: a bridge needs it; the server re-derives it, no row stores it)' % d['token'],
        '  ends       in %.0f s unless stopped (pol board twin session stop %s)' % (d['remaining_s'], d['name'])])


def _inject_body(words):
    if not words:
        raise ValueError('inject needs set|adc|reset|watch|run|status')
    verb, rest = words[0], words[1:]
    if verb == 'set' and len(rest) == 2 and rest[1] in ('0', '1'):
        return {'set': rest[0], 'level': int(rest[1])}
    if verb == 'adc' and len(rest) == 2 and all(r.isdigit() for r in rest):
        return {'adc': int(rest[0]), 'mv': int(rest[1])}
    if verb == 'reset' and not rest:
        return {'reset': 1}
    if verb == 'watch' and len(rest) == 1:
        return {'watch': [p for p in rest[0].split(',') if p]}
    if verb == 'run' and len(rest) == 1 and rest[0] in ('true', 'false', '1', '0'):
        return {'run': rest[0] in ('true', '1')}
    if verb == 'status' and not rest:
        return {'status': 1}
    raise ValueError('usage: inject <name> set PD2 0|1 | adc 0 750 | reset | watch PD6,PB5 | run true|false | status')


def _events(api, name, seconds, limit, replay, as_json):
    q = '&'.join('%s=%s' % (k, v) for k, v in (('seconds', seconds), ('limit', limit), ('replay', replay)) if v)
    req = urllib.request.Request('%s/api/board/twins/%s/events%s' % (api.rstrip('/'), name, '?' + q if q else ''), headers={'Accept': 'text/event-stream'})
    from polariApiServer import outbound
    try:
        with outbound.http_request('self', 'board', 'GET', req, means='rest', timeout=(seconds or 3600) + 30, lib='urllib', context=ssl._create_unverified_context()) as r:
            for raw in r:
                text = raw.decode('utf-8', 'replace').strip()
                if not text.startswith('data:'):
                    continue
                ev = json.loads(text[5:])
                if as_json:
                    print(json.dumps(ev), flush=True)
                elif ev.get('t') == 'pin':
                    print('cycle %-12s %s -> %d' % (ev['cycle'], ev['pin'], ev['level']), flush=True)
                else:
                    print('%s %s' % (ev.get('t'), {k: v for k, v in ev.items() if k not in ('t', 'seq')} or ''), flush=True)
        return 0
    except urllib.error.HTTPError as e:
        try:
            print('[REFUSED] %s' % json.load(e).get('error'))
        except Exception:  # noqa: BLE001
            print('[REFUSED] HTTP %s' % e.code)
        return 1
    except (urllib.error.URLError, OSError) as e:
        print('[REFUSED] cannot reach %s: %s' % (api, e))
        return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pol board twin session', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('start', 'list', 'show', 'stop', 'inject', 'events'))
    ap.add_argument('rest', nargs='*')
    ap.add_argument('--api', default=os.environ.get('POLARI_API', ''))
    ap.add_argument('--ttl', type=int, default=0)
    ap.add_argument('--owner', default=os.environ.get('USER', ''))
    ap.add_argument('--watch', default='')
    ap.add_argument('--free', action='store_true')
    ap.add_argument('--seconds', type=float, default=0)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--replay', type=int, default=0)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if not a.api:
        print('[REFUSED] twin sessions run through the server - pass --api URL (or set POLARI_API)')
        return 1
    v, r = a.verb, a.rest
    if v != 'list' and not r:
        print('usage: pol board twin session %s <%s>' % (v, 'config' if v == 'start' else 'name'))
        return 2
    if v == 'events':
        return _events(a.api, r[0], a.seconds, a.limit, a.replay, a.json)
    if v == 'start':
        body = {'config': r[0], 'owner': a.owner, 'free': a.free}
        if a.ttl:
            body['ttl_s'] = a.ttl
        if a.watch:
            body['watch'] = [p for p in a.watch.split(',') if p]
        d = _call(a.api, 'POST', '/api/board/twins', body, timeout=600)
    elif v == 'list':
        d = _call(a.api, 'GET', '/api/board/twins')
    elif v == 'show':
        d = _call(a.api, 'GET', '/api/board/twins/%s' % r[0])
    elif v == 'stop':
        d = _call(a.api, 'DELETE', '/api/board/twins/%s' % r[0])
    else:
        try:
            d = _call(a.api, 'POST', '/api/board/twins/%s/inject' % r[0], _inject_body(r[1:]))
        except ValueError as e:
            print(e)
            return 2
    if a.json:
        print(json.dumps(d, indent=2))
    elif not d.get('ok'):
        print('[REFUSED] %s' % (d.get('error') or (d.get('reply') or {}).get('why') or d))
        return 1
    elif v == 'start':
        print(render_start(d))
    elif v == 'list':
        print('\n'.join([line(s) for s in d['rows']] or ['no twin sessions']))
    elif v in ('show', 'stop'):
        print(line(d))
        st = d.get('status') or {}
        if st:
            print('  status: cycle %s, sim %s ms, adc_mv %s, pb5 %s, serial bytes out %s, paused %s' % (st.get('cycle'), st.get('sim_ms'), st.get('adc_mv'), st.get('pb5'),
                                                                                                   st.get('uart_tx_bytes'), st.get('paused')))
        if d.get('end_reason'):
            print('  ended: %s' % d['end_reason'])
    else:
        print('sent %s -> %s' % (json.dumps(d['sent']), json.dumps(d['reply'])))
    return 0 if d.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
