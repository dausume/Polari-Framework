"""
@module cmod.custom.capability_cli

`pol capability prove <name> [--twin|--hardware] [--api URL]` (hw priorities P1): runs the capability's acceptance
Scenario (firmwarefaults.custom.acceptance.run) HERE (the engines resolve through the board seam on this device,
same as `pol faults run`) and reports the outcome. --hardware is wired to the EXISTING stopgap flash/detect path
(cmod.custom.firmware.run(mode='hardware') -> board.custom.installer.detected) — with no board plugged in it REFUSES
with the readiness reason; this CLI does not try to make it pass (AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §3 P2:
the UNO is not attached yet).

proof-push rule: a proof counts only when its run row exists on the server the pages read. With --api (or
POLARI_API set) the finished run is also POSTed to `POST /api/capabilities/<name>/runs` on that server, which stores
it and re-derives the capability's status — the local JSON under ~/.cache/polari-faults/runs/ stays the on-host
record either way.

    python3 -m cmod.custom.capability_cli prove <name> [--twin|--hardware] [--api URL]
    python3 -m cmod.custom.capability_cli list
"""
import argparse
import json
import os
import ssl
import sys


def _http(method, url, body=None):
    from polariApiServer import outbound
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with outbound.http_request('self', 'cmod', method, req, means='rest', timeout=900, lib='urllib',
                                   context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001 — an HTTP error body is still JSON when the server refused
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': str(e)}


def cmd_prove(a):
    from cmod.custom import capabilities as CAP
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom.sink import LocalSink
    cap = CAP.find(a.name)
    if cap is None:
        print('[REFUSED] no Purpose %r (pol capability list)' % a.name)
        return 3
    ok, why = CAP.validate(cap)
    if not ok:
        print('[REFUSED] %s' % why)
        return 3
    mode = 'hardware' if a.hardware else 'digital-twin'
    sink = LocalSink()
    out = ACC.run(cap['acceptance_scenario'], mode=mode, sink=sink)
    tag = {'passed': '[PASS]', 'failed': '[FAIL]', 'inapplicable': '[N/A ]', 'undetermined': '[ ?? ]'}.get(out['outcome'], '[    ]')
    print('%s %s on %s (scenario %s) — %s' % (tag, a.name, mode, out['scenario'], out['verdict_words']))
    print('       record    %s' % sink.flush(out['name']))
    api = getattr(a, 'api', '') or ''
    if api:
        d = _http('POST', '%s/api/capabilities/%s/runs' % (api.rstrip('/'), a.name),
                  {k: v for k, v in out.items() if k != 'result'})
        if d.get('ok'):
            print('       pushed    %s/api/capabilities/%s — status now %s (%s)' % (api.rstrip('/'), a.name, d.get('status'), d.get('status_why')))
        else:
            print('       NOT pushed to %s: %s' % (api, d.get('error', d)))
    return 0 if out['outcome'] == 'passed' else (3 if out['outcome'] == 'inapplicable' else 1)


def cmd_list(a):
    from cmod.custom import capabilities as CAP
    for cap in CAP.SEED_CAPABILITIES:
        ok, why = CAP.validate(cap)
        status, proof, swhy = CAP.derive_status(cap)
        print('  %-20s %-20s %s' % (cap['name'], status, cap['goal']))
        print('       validator  %s' % ('ok' if ok else why))
        print('       proof      %s (%s)' % (proof or '-', swhy))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='pol capability')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prove')
    p.add_argument('name')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--twin', action='store_true')
    g.add_argument('--hardware', action='store_true')
    p.add_argument('--api', default=os.environ.get('POLARI_API', ''))
    sub.add_parser('list')
    a = ap.parse_args(argv)
    return {'prove': cmd_prove, 'list': cmd_list}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
