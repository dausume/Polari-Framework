"""
@module cmod.custom.fsc_cli

fsc-2: `pol firmware scores | profile | score-values` (polari-cli/scripts/firmware.sh dispatches here). Local by default (the pure path: seeds + committed files, no server: finished
needs ScenarioRuns, so with no server every built solution is shown as `plan` and says why); with `--api URL` (or $POLARI_API) it asks that server's doors instead and so reads the live
profiles, ScenarioRuns and rows. Both paths go through the SAME doors (cmod.custom.fsc_doors) - nothing is computed twice.

    python3 -m cmod.custom.fsc_cli scores [--profile P[,Q]] [--mission M] [--scope both|finished|plan] [--board B] [--normalization competitive|sol-0-compatible] [--top] [--limit N] [--json] [--api URL]
    python3 -m cmod.custom.fsc_cli profile show [<name>] [--json] [--api URL]
    python3 -m cmod.custom.fsc_cli profile create <name> [--copy-of P] [--weight term=w ...] [--purpose-weight purpose:term=w ...] [--hardware B] [--api URL]
    python3 -m cmod.custom.fsc_cli profile weight <name> term=w [...] [--purpose-weight purpose:term=w ...] [--api URL]
    python3 -m cmod.custom.fsc_cli score-values refresh [--mission M] [--limit N] [--api URL]
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _local(method, path, params=None, body=None):
    import falcon
    from falcon import testing
    from types import SimpleNamespace
    from cmod.cmod_fsc_api import FscAPI
    app = falcon.App()
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):     # the tree base class prints a notice when it is built with no manager; the pure path has none
        FscAPI(polServer=SimpleNamespace(falconServer=app, manager=None, idList=[]), manager=None)
    c = testing.TestClient(app)
    r = c.simulate_request(method=method, path=path, params=params or {}, body=json.dumps(body) if body is not None else None)
    return r.status_code, r.json


def _remote(api, method, path, params=None, body=None):
    from urllib.parse import urlencode
    url = api.rstrip('/') + path + (('?' + urlencode(params)) if params else '')
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {'ok': False, 'error': str(e)}


def call(a, method, path, params=None, body=None):
    api = (getattr(a, 'api', '') or '').rstrip('/')
    return _remote(api, method, path, params, body) if api else _local(method, path, params, body)


def _need_server(a, what, equivalent):
    if getattr(a, 'api', ''):
        return True
    print('[REFUSED] %s needs a live server (the person\'s own profile is a row there). Pass --api URL (or set POLARI_API). The equivalent door call:\n  %s' % (what, equivalent))
    return False


def _refused(code, d):
    print('[REFUSED] %s (HTTP %s)' % (d.get('error', d), code))
    return 3


def cmd_scores(a):
    path = '/api/firmware-scores/top' if a.top else '/api/firmware-scores'
    params = {k: v for k, v in (('mission', a.mission), ('profile', a.profile), ('scope', a.scope), ('board', a.board), ('normalization', a.normalization)) if v}
    if a.top:
        params.pop('profile', None)
    code, d = call(a, 'GET', path, params)
    if code != 200:
        return _refused(code, d)
    if a.json:
        print(json.dumps(d, indent=1, default=str))
        return 0
    if a.top:
        print('Top scorer of each profile - %s' % d['mission'])
        for r in d['rows']:
            print('  %-34s %-9s %-60s runner-up: %s (%s)' % (r['profile_title'], r['top_state'], r['top_routes'][:60], r['runner_up_routes'][:40], r['runner_up_score']))
        return 0
    print('Firmware scores - %s - %s' % (d['mission'], d['set']))
    for p in d['profiles']:
        print('  profile %s (%s)%s' % (p['name'], p['mode'], ''.join('\n    note: ' + n for n in p['notes'])))
    shown = 0
    for r in d['rows']:
        if r['state'] == 'failed':
            continue
        if a.limit and shown >= a.limit:
            break
        shown += 1
        print('  #%-3s %-8s %7s  %s%s' % (r['rank'], r['state'], r['score'], r['long_label'][:78], ('\n         ' + r['deciding_terms']) if r.get('deciding_terms') else ''))
    fails = [r for r in d['rows'] if r['state'] == 'failed']
    for r in fails[:10]:
        print('  FAILED  %s - %s' % (r['long_label'][:70], r['reason'][:160]))
    for s in d['suggestions']:
        print('  suggestion: ' + s['message'])
    for u in d['unmatched_configs'][:10]:
        print('  not a full realisation: %s - %s' % (u['config'], u['why'][:150]))
    return 0


def _weights(items):
    out = {}
    for it in items or []:
        t, _, w = it.partition('=')
        out[t] = float(w)
    return out


def _pweights(items):
    out = {}
    for it in items or []:
        p, _, rest = it.partition(':')
        t, _, w = rest.partition('=')
        out.setdefault(p, {})[t] = float(w)
    return out


def cmd_profile(a):
    if a.verb == 'show':
        code, d = call(a, 'GET', '/api/firmware-score-profiles')
        if code != 200:
            return _refused(code, d)
        rows = [r for r in d['rows'] if not a.name or r['name'] == a.name]
        if a.name and not rows:
            print('[REFUSED] no profile %r (known: %s)' % (a.name, ', '.join(r['name'] for r in d['rows'])))
            return 3
        if a.json:
            print(json.dumps(rows, indent=1))
            return 0
        for r in rows:
            print('%s - %s%s [%s, %s]' % (r['name'], r['display_name'], ' (seeded: copy before editing)' if r['seeded'] else '', r['normalization'], r['hardware'] or 'any hardware'))
            print('   ' + r['description'])
            for t in r['terms']:
                print('   %-24s %-6s %s%s' % (t['term'], t['weight'], ('Purpose ' + t['purpose']) if t.get('purpose') else 'whole solution', ' (falls back to %s)' % ' + '.join(x['term'] for x in t['fallback']) if t.get('fallback') else ''))
        return 0
    body = {'name': a.name}
    if a.verb == 'create' and a.copy_of:
        body['copy_of'] = a.copy_of
    if a.verb == 'create' and a.hardware:
        body['hardware'] = a.hardware
    w = _weights(getattr(a, 'weight', None) or getattr(a, 'terms', None))
    if w:
        body['weights'] = w
    pw = _pweights(a.purpose_weight)
    if pw:
        body['purpose_weights'] = pw
    if not _need_server(a, 'pol firmware profile %s' % a.verb, 'POST /api/firmware-score-profiles ' + json.dumps(body)):
        return 3
    code, d = call(a, 'POST', '/api/firmware-score-profiles', body=body)
    if code not in (200, 201):
        return _refused(code, d)
    print('%s profile %s: %s' % ('created' if d.get('created') else 'updated', d['name'], ', '.join('%s %s' % (t['term'], t['weight']) for t in d['terms'])))
    return 0


def cmd_values(a):
    body = {k: v for k, v in (('mission', a.mission), ('limit', a.limit)) if v}
    if not _need_server(a, 'pol firmware score-values refresh', 'POST /api/firmware-scores/values ' + json.dumps(body)):
        return 3
    code, d = call(a, 'POST', '/api/firmware-scores/values', body=body)
    if code not in (200, 201):
        return _refused(code, d)
    print('wrote %s for %s (%d finished, %d plans)' % (', '.join('%d %s' % (v, k) for k, v in d['written'].items()), d['mission'], d['finished'], d['plans']))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pol firmware')
    sub = ap.add_subparsers(dest='cmd', required=True)
    api_default = os.environ.get('POLARI_API', '')
    s = sub.add_parser('scores')
    s.add_argument('--profile', default='')
    s.add_argument('--mission', default='')
    s.add_argument('--scope', default='')
    s.add_argument('--board', default='')
    s.add_argument('--normalization', default='')
    s.add_argument('--top', action='store_true')
    s.add_argument('--limit', type=int, default=0)
    s.add_argument('--json', action='store_true')
    s.add_argument('--api', default=api_default)
    p = sub.add_parser('profile')
    p.add_argument('verb', choices=['show', 'create', 'weight'])
    p.add_argument('name', nargs='?', default='')
    p.add_argument('terms', nargs='*', default=[])
    p.add_argument('--copy-of', default='')
    p.add_argument('--weight', action='append', default=[])
    p.add_argument('--purpose-weight', action='append', default=[])
    p.add_argument('--hardware', default='')
    p.add_argument('--json', action='store_true')
    p.add_argument('--api', default=api_default)
    v = sub.add_parser('score-values')
    v.add_argument('verb', choices=['refresh'])
    v.add_argument('--mission', default='')
    v.add_argument('--limit', type=int, default=0)
    v.add_argument('--api', default=api_default)
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.cmd == 'profile' and a.verb != 'show' and not a.name:
        print('[REFUSED] pol firmware profile %s needs a profile name' % a.verb)
        return 3
    return {'scores': cmd_scores, 'profile': cmd_profile, 'score-values': cmd_values}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
