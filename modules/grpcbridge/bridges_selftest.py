"""bridges_selftest — hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7): where a bridge is. The home bench's UNO bridge is bound to polari-pol at its isle URL over the
five-hop path; levels are cited or -1 (the UNO's +5V from the board's own rail, the S3's unread); a bridge without a polari_node refuses by name, a URL that is
not the node's isle name is a gap; the maps a bridge uses are cmod's definitions; the door serves the views; the manifest conforms.

    PYTHONPATH=.:modules python3 -m grpcbridge.bridges_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from grpcbridge.custom import bridge_paths as BP
    check('NODE URL: polari-pol -> https://api.polari-pol.isle (what `isle polari instance deploy --name polari-pol` registers)',
          BP.node_url('polari-pol') == 'https://api.polari-pol.isle')
    out = BP.bench_bridges('home-bench')
    uno = next(b for b in out['bridges'] if b['name'] == BP.UNO_BRIDGE)
    check('BOUND: the UNO bridge = hardware home-bench/UNO #1, Polari node polari-pol at its isle URL, serial, PD0/PD1, using the LightState map',
          uno['status'] == 'bound' and uno['polari_node_url'] == 'https://api.polari-pol.isle' and uno['hardware_id'] == 'home-bench/UNO #1'
          and uno['pins'] == 'PD0,PD1' and uno['maps'] == 'LightState_t->LightState' and 'api.polari-pol.isle' in uno['status_why'], uno)
    hops = [h for h in out['hops'] if h['path'] == BP.UNO_PATH]
    check('PATH: the UNO path is the five hops in order (chip-pins -> converter -> connector -> host-port -> userspace); the converter is the 16U2 interface row',
          [h['kind'] for h in hops] == list(BP.HOP_KINDS) and hops[1]['ref'] == 'UsbInterfaceDefinition:atmega16u2-bridge'
          and next(p for p in out['paths'] if p['name'] == BP.UNO_PATH)['hops'] == ' -> '.join(BP.HOP_KINDS), [h['kind'] for h in hops])
    check('LEVELS cited or -1: the UNO chip + 16U2 hops = 5 V from the board\'s own +5V rail (cited); connector / host port / userspace -1 saying why; '
          'every S3 hop -1 with what to read',
          hops[0]['signal_level_v'] == 5.0 and "'+5V'" in hops[0]['basis'] and hops[1]['signal_level_v'] == 5.0 and all(h['signal_level_v'] == -1 for h in hops[2:])
          and all(h['signal_level'] == '-1' and h['basis'] for h in out['hops'] if h['path'] == BP.S3_PATH)
          and 'unread' in next(h for h in out['hops'] if h['path'] == BP.S3_PATH and h['kind'] == 'converter')['basis'], [h['signal_level'] for h in out['hops']])
    names = {p['name'] for p in out['paths']}
    nonode = BP.check_bridge(dict(BP.SEED_POLARI_BRIDGES[0], polari_node='', polari_node_url=''), names)
    wrong = BP.check_bridge(dict(BP.SEED_POLARI_BRIDGES[0], polari_node_url='https://polari-pol.local'), names)
    badname = BP.check_bridge(dict(BP.SEED_POLARI_BRIDGES[0], polari_node='Polari Pol'), names)
    nopath = BP.check_bridge(dict(BP.SEED_POLARI_BRIDGES[0], path='nowhere'), names)
    check('REFUSES: a bridge without a polari_node (named), a URL that is not the node\'s isle name (the right one said), a non-isle node name, a missing path',
          nonode[0] == 'gap' and 'names no polari_node' in nonode[1] and wrong[0] == 'gap' and 'https://api.polari-pol.isle' in wrong[1]
          and badname[0] == 'gap' and 'not an isle name' in badname[1] and nopath[0] == 'gap' and 'not a BridgePath' in nopath[1], (nonode, wrong, badname, nopath))
    try:
        from cmod.custom.catom_assertions import SEED_STRUCT_OBJECT_MAPS, SEED_ASSERTIONS
        maps_ok = {m for b in BP.SEED_POLARI_BRIDGES for m in b['maps'].split(',')} <= {m['name'] for m in SEED_STRUCT_OBJECT_MAPS}
        bridged = {a['bridge'] for a in SEED_ASSERTIONS if a['bridge']} <= {b['name'] for b in BP.SEED_POLARI_BRIDGES}
    except ImportError as e:
        maps_ok = bridged = False
        print('    (cmod not importable: %s)' % e)
    check('DEFINITIONS (D-hsp-8): every map a bridge uses is a cmod StructObjectMap; every bridge a catom assertion names is a PolariBridgeInstance', maps_ok and bridged)
    check('ROWS are plain (no nested dicts / lists) for configured tables', all(not isinstance(v, (dict, list)) for k in ('bridges', 'paths', 'hops') for r in out[k] for v in r.values()))
    from grpcbridge.bridges_api import BenchBridgesAPI
    api = BenchBridgesAPI(polServer=None, manager=None)

    def get(bench, view=''):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get(types.SimpleNamespace(get_param=lambda k: view or None), resp, bench)
        return resp
    full, hv, bad = get('home-bench'), get('home-bench', 'hops'), get('home-bench', 'raw')
    check('DOOR: GET /api/grpc/bench-bridges/home-bench = bridges + paths + hops; ?view=hops = 10 rows; unknown view 422',
          full.media['ok'] and len(full.media['bridges']) == 1 and len(full.media['paths']) == 2 and hv.media['count'] == 10 and bad.status.startswith('422'))
    json.dumps(full.media)
    from moduleService.manifests import conform
    r = conform('grpcbridge')
    check('MANIFEST: pol modules conform grpcbridge is clean with the new classes + files listed', r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
