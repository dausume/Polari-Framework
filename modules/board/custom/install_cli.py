"""
@module board.custom.install_cli

CLI parity with the installer page (brd-fi): the same doors, the same rows, the same refusals.

  pol board install uno [--variant V] [--twin] [--dry-run | --yes] [--api URL]
        plan + run + attach in one: picks (or builds) the variant's newest compatible build, prints the plan's argv
        VERBATIM (the DRY-RUN — the default), and only with --yes runs it, attaches the bridge and prints the first
        frames. Target: the UNO detected on the server's host, or --twin (the simavr twin). Exit 3 = refused
        (stale-header / unknown-class firmware, no board, the wrong host); exit 1 = the install itself failed.
  pol board variants [--api URL]      the variants (offline: the seeded four) — what each tests, what to watch
  pol board result [RECORD] [--api URL]   an install's result (default: the newest record)

The server must run on the host holding the port (the installer refuses otherwise, naming the host).
"""
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

REFUSED = 3


def _call(api, method, path, body=None, timeout=900):
    req = urllib.request.Request(api.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'} if body is not None else {}, method=method)
    from polariApiServer import outbound
    try:
        with outbound.http_request('self', 'board', method, req, means='rest', timeout=timeout, lib='urllib',
                                   context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': 'HTTP %s' % e.code}


def _refused(d):
    print('[REFUSED] %s' % d.get('error', d))
    return REFUSED if d.get('exit') == REFUSED else 1


def variants(api=''):
    if api:
        rows = _call(api, 'GET', '/api/board/variants').get('variants', [])
    else:
        from board.custom.variants import SEED_FIRMWARE_VARIANTS as rows
    for v in rows:
        print('%-16s %-8s %-16s %s' % (v['name'], v['app'], ','.join(json.loads(v['classes_json'])), v['title']))
        print('%16s watch: %s' % ('', v['what_to_watch']))
    return 0


def _print_result(r):
    print('       verdict  %s — %s' % (r.get('verdict'), r.get('verify')))
    print('       bridge   %s' % (r.get('bridge_state') or '-'))
    for f in r.get('frames') or []:
        print('       frame    seq=%s %s %s' % (f['seq'], f['class'], ', '.join('%s=%s' % kv for kv in f['values'].items())))
    if r.get('frames_total'):
        print('       rate     %s frames/s (%d frames so far)' % (r.get('frames_per_s'), r.get('frames_total')))
    if r.get('row'):
        print('       row      %s %s: %s' % (r['row_class'], r['row_name'], ', '.join('%s=%s' % (k, r['row'][k]) for k in sorted(r['row']) if k not in ('id', 'name'))))


def result(api, record=''):
    if not record:
        doc = _call(api, 'GET', '/api/board/installer')
        if not doc.get('records'):
            print('no installs yet')
            return 1
        record = doc['records'][0]['name']
    r = _call(api, 'GET', '/api/board/installer/result/%s' % record)
    if not r.get('ok'):
        return _refused(r)
    print('[ OK ] %s  (%s, %s)' % (r['record'], r.get('variant'), r.get('target_kind')))
    _print_result(r)
    return 0


def install(api, variant='uno-sim-rig', twin=False, yes=False, wait_s=180):
    doc = _call(api, 'GET', '/api/board/installer')
    if not doc.get('ok'):
        return _refused(doc)
    if twin:
        target = 'twin:arduino-uno-r3'
    elif doc.get('boards'):
        target = doc['boards'][0]['name']
    else:
        print('[REFUSED] no UNO is detected on %s (%s) — plug it in, or add --twin to install into the simavr twin' % (doc['host'], doc.get('scan_note')))
        return REFUSED
    fit = [b for b in doc['builds'] if b.get('variant') == variant and b.get('installable')]
    if fit:
        build = fit[0]['name']
        print('[ .. ] build    %s (existing; flash %s / %s B, compat %s)' % (build, fit[0]['flash_bytes'], fit[0]['flash_max'], fit[0]['compat']))
    else:
        b = _call(api, 'POST', '/api/board/installer/build', {'variant': variant})
        if not b.get('ok'):
            return _refused(b)
        if b.get('state') != 'built':
            print('[FAIL] build %s: %s' % (b.get('build'), b.get('notes')))
            return 1
        build = b['build']
        print('[ .. ] build    %s (new; flash %s B, RAM %s B)' % (build, b.get('flash_bytes'), b.get('ram_bytes')))
    p = _call(api, 'POST', '/api/board/installer/plan', {'instance': target, 'build': build})
    if not p.get('ok'):
        return _refused(p)
    print('[DRY-RUN] %s' % p['argv_text'])
    if p.get('wrapper_text'):
        print('          runs as: %s' % p['wrapper_text'])
    print('          engine %s (%s)   compat %s   target %s on %s' % (p['engine'], p['engine_how'], p['compat'], p['target_kind'], p['host']))
    print('          will stamp: %s' % p['will_stamp'])
    if not yes:
        print('          nothing was run — add --yes to install (plan %s)' % p['plan'])
        return 0
    r = _call(api, 'POST', '/api/board/installer/run', {'plan': p['plan'], 'confirm': True})
    if not r.get('ok'):
        return _refused(r)
    print('[%s] %s  %s — %s (%.1f s)' % (' OK ' if r['verdict'] == 'installed' else 'FAIL', r['name'], r['verdict'], r['verify'], r.get('elapsed_s') or 0))
    if r['verdict'] != 'installed':
        return 1
    a = _call(api, 'POST', '/api/board/installer/attach', {'record': r['name']})
    if not a.get('ok'):
        print('[REFUSED] attach: %s' % a.get('error'))
        return REFUSED
    for w in a.get('warnings') or []:
        print('[WARN] %s' % w)
    t0, res = time.time(), {}
    while time.time() - t0 < wait_s:
        res = _call(api, 'GET', '/api/board/installer/result/%s' % r['name'])
        st = res.get('bridge_state') or ''
        if st.startswith('refused') or (st == 'attached' and res.get('frames_total', 0) >= 3):
            break
        time.sleep(1.0)
    time.sleep(1.2)
    res = _call(api, 'GET', '/api/board/installer/result/%s' % r['name'])
    _print_result(res)
    return 0 if (res.get('bridge_state') == 'attached' and res.get('frames_total')) else 1


def main(argv):
    import argparse
    import os
    ap = argparse.ArgumentParser(prog='pol board')
    ap.add_argument('verb', choices=('install', 'variants', 'result'))
    ap.add_argument('rest', nargs='*')
    ap.add_argument('--variant', default='uno-sim-rig')
    ap.add_argument('--twin', action='store_true')
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--api', default=os.environ.get('POLARI_API', ''))
    a = ap.parse_args(argv)
    if a.verb == 'variants':
        return variants(a.api)
    if not a.api:
        print('[REFUSED] the installer runs through the server on the host holding the port — pass --api (or set POLARI_API)')
        return REFUSED
    if a.verb == 'result':
        return result(a.api, a.rest[0] if a.rest else '')
    if a.rest and a.rest[0] not in ('uno', 'arduino-uno-r3'):
        print('[REFUSED] only the UNO has firmware variants so far (plan §8a)')
        return REFUSED
    return install(a.api, a.variant, a.twin, a.yes and not a.dry_run)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
