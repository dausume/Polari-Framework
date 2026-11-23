"""
@module board.custom.install_cli

CLI parity with the installer page (brd-fi): the same doors, the same rows, the same refusals.

  pol board install uno|c3 --sim|--real [--variant V] [--dry-run | --yes] [--anyway REASON] [--api URL]
        ins-c3-1: the board word picks the board (uno | arduino-uno-r3 | c3 | esp32c3 | esp32-c3); --variant defaults to that board's own (uno-sim-rig | esp32c3-light).
        A C3 --sim starts a twin session on the ESP engines worker with the build's own image (no bridge is attached: press it on the Sim bench or with
        `pol board twin session inject`); a C3 --real prints esptool's exact command and the three checks (chip-HAL build, the three files are the image the twin
        ran, the Purposes ran this image) and runs only past them and the gate; with no board detected it plans against `undetected:<board>`, prints the dry run
        and its checks, and refuses (exit 3) only with --yes.
        UNO: plan + run + attach in one: picks (or builds) the variant's newest compatible build, prints the plan's argv
        VERBATIM (the DRY-RUN — the default), and only with --yes runs it, attaches the bridge and prints the first
        frames. ins-0: --sim = the twin (--twin is the old spelling), --real = the UNO detected on the server's host.
        ins-1: a --real install of a Mission config is offered only past THE CONFIRMED-SIM GATE (the four Purposes
        passed on the twin + a person's tick for this hex); otherwise the words say what is missing and offer the
        sim install (exit 3). --anyway "reason" records the reason on the plan and installs regardless. A --sim
        install with --yes also runs the four Purposes on the twin (or prints the exact command when this server
        cannot run the twin itself) and then says how to tick the confirmation. Exit 3 = refused (stale-header /
        unknown-class firmware, no board, the wrong host, the gate); exit 1 = the install itself failed.
  pol board gate <config> [--api URL]      the Real side's verdict for a config: offered | not offered + what is missing
  pol board confirm-sim <config> [--hex SHA | --build B] [--words W] [--api URL]
        the person's tick: "I checked the simulated board does what the firmware says" for the config's newest build
        (or the named hex / build) — a SimInstallConfirmation row (who = the signed-in user of the request)
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
        with outbound.http_request('self', 'board', method, req, means='rest', timeout=timeout, lib='urllib') as r:
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


def _print_gate(g, indent='          '):
    print('%sgate     %s' % (indent, g.get('words', '')))
    for p in g.get('purposes') or []:
        print('%s         %-40s %-20s %s' % (indent, p['purpose'], p['status'], p.get('run') or '-'))
    if g.get('offer'):
        print('%s         %s' % (indent, g['offer']))
    if g.get('anyway'):
        print('%s         %s (--anyway "reason")' % (indent, g['anyway']))


def gate(api, config):
    g = _call(api, 'GET', '/api/board/installer/gate?config=%s' % config)
    if not g.get('ok'):
        return _refused(g)
    print('[%s] %s' % (' OK ' if g['offered'] else 'WAIT', config))
    _print_gate(g, '       ')
    return 0 if g['offered'] else REFUSED


def confirm_sim(api, config, hex_sha='', build='', words=''):
    body = {'config': config, 'source': 'cli'}
    if hex_sha:
        body['hex_sha256'] = hex_sha
    if build:
        body['build'] = build
    if words:
        body['words'] = words
    r = _call(api, 'POST', '/api/board/installer/sim-confirmations', body)
    if not r.get('ok'):
        return _refused(r)
    c = r['confirmation']
    print('[ OK ] %s: %s ticked "%s" for %s (%s…) at %s — %d/%d Purposes passed on the twin' % (c['name'], c['who_words'], c['words'], config, c['hex_sha256'][:16],
                                                                                         c['confirmed_at'], c['purposes_passed'], c['purposes_total']))
    for v in c.get('voided') or []:
        print('       voided   %s (%s…)' % (v['name'], v['hex_sha256'][:16]))
    _print_gate(r['verdict'], '       ')
    return 0


def _sim_purposes(api, variant):
    """After a sim install: run the four Purposes on the twin through the server, or print the exact command when it cannot."""
    r = _call(api, 'POST', '/api/board/installer/sim-install', {'config': variant}, timeout=1800)
    if not r.get('ok'):
        print('[WAIT] Purposes: %s' % r.get('error'))
        if r.get('retry'):
            print('       run      %s' % r['retry'])
        return
    for p in r.get('runs') or []:
        print('[%s] %-40s %s' % ({'passed': 'PASS', 'failed': 'FAIL'}.get(p.get('outcome'), ' ?? '), p['purpose'], (p.get('words') or '')[:120]))


def _print_checks(checks, indent='          '):
    for c in checks or []:
        print('%s[%s] %-20s %s' % (indent, ' ok ' if c['ok'] else 'MISSING', c['name'], c['words']))


def kind_of(word):
    """The installer kind a board word names (uno, c3 ...), or None."""
    from board.custom import install_kinds as IK
    return IK.of_alias(word)


def install(api, variant='', twin=False, yes=False, wait_s=180, anyway='', board='uno'):
    kind = kind_of(board)
    variant = variant or kind['default_variant']
    doc = _call(api, 'GET', '/api/board/installer?board=%s' % kind['name'])
    if not doc.get('ok'):
        return _refused(doc)
    if twin:
        target = kind['twin']
    elif doc.get('boards'):
        target = doc['boards'][0]['name']
    elif not yes:
        target = 'undetected:%s' % kind['board']   # nothing is plugged in: the plan can still be READ (and is refused)
        print('[ .. ] no %s is detected on %s (%s): planning against %s to show the command and its checks' % (kind['label'], doc['host'], doc.get('scan_note'), target))
    else:
        print('[REFUSED] no %s is detected on %s (%s) — plug it in, or add --sim to install into %s' % (kind['label'], doc['host'], doc.get('scan_note'), 'the twin' if kind['steps'] else 'the simavr twin'))
        return REFUSED
    print('[MODE] %s install — %s' % ('SIM' if twin else 'REAL', next((m['words'] for m in doc.get('modes') or [] if m['name'] == ('sim' if twin else 'real')), target)))
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
    if not twin:   # ins-1: the gate, read before the plan so the words come first
        g = _call(api, 'GET', '/api/board/installer/gate?config=%s&build=%s' % (variant, build))
        if g.get('ok'):
            _print_gate(g, '       ')
    body = {'instance': target, 'build': build}
    if anyway:
        body.update(install_anyway=True, reason=anyway)
    p = _call(api, 'POST', '/api/board/installer/plan', body)
    if not p.get('ok'):
        if p.get('argv_text'):   # a refused plan still shows the command that would run, and its checks
            print('[DRY-RUN] %s' % p['argv_text'])
            _print_checks(p.get('checks'))
        return _refused(p)
    print('[DRY-RUN] %s' % p['argv_text'])
    _print_checks(p.get('checks'))
    if p.get('wrapper_text'):
        print('          runs as: %s' % p['wrapper_text'])
    print('          engine %s (%s)   compat %s   target %s on %s   mode %s   gate %s' % (p['engine'], p['engine_how'], p['compat'], p['target_kind'], p['host'],
                                                                                          p.get('install_mode'), p.get('gate')))
    if p.get('override_reason'):
        print('          INSTALL ANYWAY recorded: %s' % p['override_reason'])
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
    if twin:
        _sim_purposes(api, variant)
        print('          when you have watched it: pol board confirm-sim %s --api %s   (or tick it on the installer page / the sim bench)' % (variant, api))
    if kind['steps']:   # a C3 session has no bridge to attach and no frames to wait for: the record names the session and how to press it
        print('          %s' % r.get('notes'))
        return 0
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
    ap.add_argument('verb', choices=('install', 'variants', 'result', 'gate', 'confirm-sim'))
    ap.add_argument('rest', nargs='*')
    ap.add_argument('--variant', default='')
    ap.add_argument('--twin', action='store_true')
    ap.add_argument('--sim', action='store_true')
    ap.add_argument('--real', action='store_true')
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--anyway', default='')
    ap.add_argument('--hex', default='')
    ap.add_argument('--build', default='')
    ap.add_argument('--words', default='')
    ap.add_argument('--api', default=os.environ.get('POLARI_API', ''))
    a = ap.parse_args(argv)
    if a.verb == 'variants':
        return variants(a.api)
    if not a.api:
        print('[REFUSED] the installer runs through the server on the host holding the port — pass --api (or set POLARI_API)')
        return REFUSED
    if a.verb == 'result':
        return result(a.api, a.rest[0] if a.rest else '')
    if a.verb in ('gate', 'confirm-sim'):
        if not a.rest:
            print('[REFUSED] name the config: pol board %s <config>' % a.verb)
            return REFUSED
        return gate(a.api, a.rest[0]) if a.verb == 'gate' else confirm_sim(a.api, a.rest[0], a.hex, a.build, a.words)
    if a.rest and kind_of(a.rest[0]) is None:
        print('[REFUSED] the installer has firmware for the UNO (uno) and the ESP32-C3 (c3) so far, not %r (plan §8a)' % a.rest[0])
        return REFUSED
    if a.sim and a.real:
        print('[REFUSED] pick one mode: --sim (the twin) or --real (a detected board)')
        return REFUSED
    if not (a.sim or a.real or a.twin):
        print('[REFUSED] say which install: --sim (the twin; validate and confirm there first) or --real (a detected board)')
        return REFUSED
    return install(a.api, a.variant, a.twin or a.sim, a.yes and not a.dry_run, anyway=a.anyway, board=a.rest[0] if a.rest else 'uno')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
