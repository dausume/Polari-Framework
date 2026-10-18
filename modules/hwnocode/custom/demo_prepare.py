"""
@module hwnocode.custom.demo_prepare

`pol hwnocode demo-prepare [--api URL] [--dry-run] [--json]` — bring a live Polari to the point where the UNO light demo's readiness has no
MISSING part, through the server's own knob doors (idempotent; every step says whether it acted or found it already done):

  1. the light's Hardware Bridge row (`uno-light`, from grpcbridge.mapping_basis.SEED_LIGHT_BRIDGE)   POST /api/grpc/bridges
  2. the LightState schema stabilized (the v1 wire contract is pinned already)                     POST /api/schema/stability/LightState
  3. the LightState gRPC exposure enabled                                                           POST /api/grpc/exposures/LightState
  4. the bridge generated (the manifest stamped from the current contract)                         POST /api/grpc/bridges/uno-light {generate}
  then GET /api/uno-core-demo/readiness. The bridge's own status stays `never-run` until a real board runs through it (the bench).

Why a verb: these were done by hand on pol-core 2026-10-18 (the readiness row said "missing") — his rule: every by-hand remedy becomes a pol verb
with a dry run.
"""
import json
import ssl
import sys
import urllib.error
import urllib.request

from grpcbridge.mapping_basis import SEED_LIGHT_BRIDGE

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE   # the home stack's nip.io certs are self-signed (dev posture)


def _call(api, method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api.rstrip('/') + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'{}')
        except Exception:
            return e.code, {'error': str(e)}


def _bridge_body():
    b = SEED_LIGHT_BRIDGE
    return {'bridgeName': b['bridge_name'], 'classes': json.loads(b['exposed_classes_json']), 'source': b['source'], 'serialDevice': b['serial_device'],
            'baud': b['baud'], 'simRateHz': b['sim_rate_hz'], 'grpcEnabled': b['grpc_enabled'], 'grpcTarget': b['grpc_target'], 'deviceId': b['device_id']}


def prepare(api, dry_run=False):
    name = SEED_LIGHT_BRIDGE['bridge_name']
    cls = json.loads(SEED_LIGHT_BRIDGE['exposed_classes_json'])[0]
    steps = []

    def step(what, done, acted, detail=''):
        steps.append({'step': what, 'state': 'done' if done else ('would act' if dry_run else 'FAILED'), 'acted': acted, 'detail': detail})

    st, b = _call(api, 'GET', '/api/grpc/bridges/%s' % name)
    if st == 200:
        step('bridge %s exists' % name, True, False)
    elif dry_run:
        step('create bridge %s' % name, False, False, 'POST /api/grpc/bridges')
    else:
        st, r = _call(api, 'POST', '/api/grpc/bridges', _bridge_body())
        step('create bridge %s' % name, st in (200, 201) and r.get('ok'), True, r.get('error', ''))
    st, s = _call(api, 'GET', '/api/schema/stability/%s' % cls)
    stable = st == 200 and str(s.get('status', '')).startswith('stabil')
    if stable:
        step('%s schema stabilized' % cls, True, False)
    elif dry_run:
        step('stabilize %s schema' % cls, False, False, 'POST {"action": "stabilize"}')
    else:
        st, r = _call(api, 'POST', '/api/schema/stability/%s' % cls, {'action': 'stabilize'})
        step('stabilize %s schema' % cls, st == 200 and r.get('ok'), True, r.get('error', ''))
    st, e = _call(api, 'GET', '/api/grpc/exposures/%s' % cls)
    enabled = st == 200 and bool(e.get('enabled'))
    if enabled:
        step('%s gRPC exposure enabled' % cls, True, False)
    elif dry_run:
        step('enable %s gRPC exposure' % cls, False, False, 'POST {"action": "enable"}')
    else:
        st, r = _call(api, 'POST', '/api/grpc/exposures/%s' % cls, {'action': 'enable'})
        step('enable %s gRPC exposure' % cls, st == 200 and r.get('ok'), True, r.get('error', ''))
    if dry_run:
        step('generate bridge %s' % name, False, False, 'POST {"action": "generate"}')
    else:
        st, r = _call(api, 'POST', '/api/grpc/bridges/%s' % name, {'action': 'generate'})
        step('generate bridge %s' % name, st == 200 and r.get('ok'), True, ('%s files' % r.get('files')) if r.get('ok') else r.get('error', ''))
    st, rd = _call(api, 'GET', '/api/uno-core-demo/readiness')
    rows = [{'part': x.get('part'), 'status': x.get('status')} for x in (rd.get('rows') or [])] if st == 200 else []
    ok = all(s['state'] == 'done' for s in steps) if not dry_run else True
    return {'ok': ok, 'api': api, 'dry_run': dry_run, 'steps': steps, 'readiness': rows,
            'note': 'the bridge stays never-run until a real board runs through it (the bench); everything else should read ok / proven-on-twin'}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    api = None
    if '--api' in argv:
        api = argv[argv.index('--api') + 1]
    if not api:
        print('usage: python3 -m hwnocode.custom.demo_prepare --api https://api.<host> [--dry-run] [--json]')
        return 2
    r = prepare(api, dry_run='--dry-run' in argv)
    if '--json' in argv:
        print(json.dumps(r, indent=1))
    else:
        print('UNO light demo - prepare %s%s' % (api, ' (dry run)' if r['dry_run'] else ''))
        for s in r['steps']:
            print('  %-10s %s%s' % (s['state'], s['step'], (' - ' + s['detail']) if s['detail'] else ''))
        print('  readiness: ' + ', '.join('%s %s' % (x['part'], x['status']) for x in r['readiness']))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
