"""cmod_bench_views_selftest — hsp-3b + the bridge half of hsp-3c (HARDWARE_SYSTEM_PINS_PLAN.md §7 "The two bench views"): struct INSTANCES derived from the
bench's bridges x HardwareInterfaceBindings (no new stored row); a field's signal paths drawn from the Catom assertions (the button route, the UI route in
through the bridge, the read route out to the LED pin, a gap); the bridge's mode picks its hops (serial = the cable path; simulated = the twin -> the
board-engines worker on the isle) and the mode door toggles it; uno_core_demo reads where its bridge is from PolariBridgeInstance in both modes; the
/display/bench-views page (Structs / Bridges / HAL tabs over configured tables, every door it names registered); the doors; the manifests.

    PYTHONPATH=.:modules python3 -m cmod.cmod_bench_views_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0
BENCH, INST = 'home-bench', 'uno-1-bridge/LightState_t[0]'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def structs():
    from cmod.custom import bench_structs as BS
    ii = BS.instances(BENCH)
    check('INSTANCES: home-bench has ONE struct instance - LightState_t[0] on uno-1-bridge, becoming LightState \'uno-light\' through the HardwareInterfaceBinding '
          'uno-light/LightState/0; 7 fields, 6 asserted, the pins its assertions name', [i['name'] for i in ii] == [INST] and ii[0]['object'] == 'uno-light'
          and ii[0]['binding'] == 'uno-light/LightState/0' and (ii[0]['fields'], ii[0]['asserted_fields']) == (7, 6) and ii[0]['pins'] == 'PD0,PD1,PD2,PD6'
          and ii[0]['state'] == 'bound', ii)
    two = BS.instances(BENCH, binding_rows=[{'name': 'uno-light/LightState/%d' % k, 'bridge_name': 'uno-light', 'object_class': 'LightState',
                                             'object_name': 'light-%d' % k, 'instance_index': k} for k in (0, 1)])
    none = BS.instances(BENCH, binding_rows=[])
    check('INSTANCES, NOT TYPES: two bindings of one struct = two rows (light[0], light[1], each its own object); no binding = one row said unbound',
          [i['name'] for i in two] == ['uno-1-bridge/LightState_t[0]', 'uno-1-bridge/LightState_t[1]'] and two[1]['object'] == 'light-1'
          and none[0]['state'] == 'unbound' and 'no HardwareInterfaceBinding' in none[0]['why'], [i['name'] for i in two])
    f = {r['field']: r for r in BS.fields(BENCH, INST)}
    check('FIELDS: led_on is changed by led_toggle + apply_command and read by led_follow_state (PD0, PD2, PD6), unverified; name is a GAP; every field names its '
          'Polari attribute', f['led_on']['changed_by'] == 'apps/light.led_toggle, apps/light.apply_command' and f['led_on']['read_by'] == 'apps/light.led_follow_state'
          and f['led_on']['pins'] == 'PD0,PD2,PD6' and f['led_on']['verdict'] == 'unverified' and f['name']['verdict'] == 'gap'
          and all(r['attribute'] == 'LightState.' + k for k, r in f.items()), {k: r['verdict'] for k, r in f.items()})
    p = BS.path(BENCH, INST, 'led_on')
    route = lambda n: [(s['kind'], s['what'].split(' ')[0]) for s in p if s['route'] == n]   # noqa: E731
    check('PATH, the button route: PD2 (falling edge) -> led_toggle -> led_on -> telemetry_send (verified) -> uno-1-bridge -> LightState.led_on',
          route(1) == [('pin', 'PD2'), ('catom', 'apps/light.led_toggle'), ('field', 'LightState_t[0].led_on'), ('catom', 'apps/light.telemetry_send'),
                       ('bridge', 'uno-1-bridge'), ('object', 'LightState')] and p[3]['status'] == 'verified', route(1))
    check('PATH, the UI route comes IN through the bridge: LightState -> uno-1-bridge -> PD0 -> USART_RX_vect (isr) -> apply_command -> led_on -> ... out again',
          route(2)[:6] == [('object', 'LightState'), ('bridge', 'uno-1-bridge'), ('pin', 'PD0'), ('catom', 'hal.USART_RX_vect'), ('catom', 'apps/light.apply_command'),
                           ('field', 'LightState_t[0].led_on')] and route(2)[-1] == ('object', 'LightState'), route(2))
    check('PATH, the read route goes OUT to the light: led_on -> led_follow_state -> PD6; a field nothing asserts (name) = one gap row; an unknown instance = None',
          route(3) == [('field', 'LightState_t[0].led_on'), ('catom', 'apps/light.led_follow_state'), ('pin', 'PD6')]
          and [s['kind'] for s in BS.path(BENCH, INST, 'name')] == ['gap'] and BS.path(BENCH, 'nope', 'led_on') is None, route(3))


def bridges():
    from grpcbridge.custom import bridge_paths as BP
    b = dict(BP.SEED_POLARI_BRIDGES[0])
    serial = BP.bridge_hops(b)
    sim = BP.bridge_hops(dict(b, mode='simulated'))
    check('HOPS BY MODE: serial = the cable path (chip-pins -> converter -> connector -> host-port -> userspace); simulated = chip-pins -> twin -> the board-engines '
          'worker at https://board-engines.isle, the twin\'s pins at -1 (no electrical level)', [h['kind'] for h in serial] == list(BP.HOP_KINDS)
          and [h['kind'] for h in sim] == list(BP.TWIN_HOP_KINDS) and 'https://board-engines.isle' in sim[-1]['what'] and sim[0]['signal_level'] == '-1'
          and serial[0]['signal_level'] != '-1', ([h['kind'] for h in sim], sim[0]['signal_level']))
    from grpcbridge.bridges_api import BenchBridgesAPI
    row = types.SimpleNamespace(**b)
    api = BenchBridgesAPI(polServer=None, manager=None)
    api.manager = types.SimpleNamespace(objectTables={'PolariBridgeInstance': {row.name: row}}, db=None)

    def call(method, params=None, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(get_param=lambda k: (params or {}).get(k), bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, BENCH)
        return resp
    t1 = call('on_post_mode', body={'bridge': b['name']})
    h1 = call('on_get', {'view': 'hops', 'bridge': b['name']})
    t2 = call('on_post_mode', body={'bridge': b['name']})
    bad = call('on_post_mode', body={'bridge': b['name'], 'mode': 'teleport'})
    ghost = call('on_post_mode', body={'bridge': 'nope'})
    empty = call('on_get', {'view': 'hops', 'bridge': ''})
    check('MODE DOOR: POST .../home-bench/mode {bridge} toggles serial -> simulated (the hops follow: the twin worker) -> serial (click toggle); an unknown mode 422; '
          'an unknown bridge 404; ?view=hops&bridge= with nothing picked = no rows, said',
          (t1.media['was'], t1.media['mode']) == ('serial', 'simulated') and h1.media['rows'][-1]['kind'] == 'userspace' and 'board-engines' in h1.media['rows'][-1]['what']
          and t2.media['mode'] == 'serial' and row.mode == 'serial' and bad.status.startswith('422') and ghost.status.startswith('404')
          and empty.media['count'] == 0 and 'pick a bridge' in empty.media['note'], (t1.media.get('mode'), t2.media.get('mode'), bad.status))
    from uno_core_demo.custom import readiness as R
    ser = R.bridge_location('uno-light')
    sim_mgr = types.SimpleNamespace(objectTables={'PolariBridgeInstance': {'b': types.SimpleNamespace(**dict(b, mode='simulated'))}, 'BridgePath': {}})
    simw = R.bridge_location('uno-light', sim_mgr)
    part = next(r for r in R.readiness()['rows'] if r['part'] == 'bridge') if isinstance(R.readiness(), dict) else next(r for r in R.readiness() if r['part'] == 'bridge')
    check('uno_core_demo READS ITS BRIDGE FROM PolariBridgeInstance: serial = bound at https://api.polari-pol.isle over the USB-B cable path; simulated = the twin -> '
          'https://board-engines.isle; the bridge part\'s reason carries it; a bridge no instance carries is said', 'mode serial, bound' in ser and 'USB-B' in ser
          and 'https://api.polari-pol.isle' in ser and 'mode simulated' in simw and 'https://board-engines.isle' in simw and 'where: uno-1-bridge' in part['why']
          and 'no PolariBridgeInstance carries' in R.bridge_location('nope'), (ser[:160], simw[:160]))


def doors():
    from cmod.cmod_bench_structs_api import BenchStructsAPI
    api = BenchStructsAPI(polServer=None, manager=None)

    def get(params):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get(types.SimpleNamespace(get_param=lambda k: params.get(k)), resp, BENCH)
        return resp
    i, f, p = get({}), get({'view': 'fields', 'instance': INST}), get({'view': 'path', 'instance': INST, 'field': 'led_on'})
    none, bad, ghost, crossing = get({'view': 'path', 'instance': INST, 'field': ''}), get({'view': 'x'}), get({'view': 'fields', 'instance': 'nope'}), \
        get({'view': 'instances', 'bridge': 'uno-1-bridge'})
    check('DOOR: GET /api/cmod/bench-structs/home-bench = the instances (each with tab=structs for the Bridges view\'s jump); ?view=fields / ?view=path rows are flat; '
          'a path with no field picked = no rows, said; unknown view 422; unknown instance 404; ?bridge= narrows to the structs crossing it',
          i.media['count'] == 1 and i.media['rows'][0]['tab'] == 'structs' and f.media['count'] == 7 and p.media['count'] >= 15
          and all(not isinstance(v, (dict, list)) for r in f.media['rows'] + p.media['rows'] for v in r.values()) and none.media['count'] == 0 and 'note' in none.media
          and bad.status.startswith('422') and ghost.status.startswith('404') and crossing.media['count'] == 1, (i.media.get('count'), p.media.get('count'), bad.status))


def page():
    from cmod.bench_views_page import BENCH_VIEWS_PAGES
    from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS
    pg = BENCH_VIEWS_PAGES[0]
    d = json.loads(pg['definition'])
    tabs = {t['key']: t for t in d['tabs']}
    items = [it for t in d['tabs'] for r in t['rows'] for it in r['items']] + [it for r in d['rows'] for it in r['items']]
    blob = json.dumps(d)
    check('PAGE /display/bench-views: the bench picker above four tabs (structs, bridges, hal, registers), linkable by ?bench=&instance=&bridge=&variant=&soc=&pin=; '
          'registered in cmod\'s pages',
          list(tabs) == ['structs', 'bridges', 'hal', 'registers'] and d['scope_from_query'] == ['bench', 'instance', 'bridge', 'variant', 'soc', 'pin']
          and pg in SEED_CMOD_PAGE_DISPLAYS
          and pg['pageRoute'] == 'bench-views', list(tabs))
    check('PAGE wiring: the clicks chain bench -> instance -> field (Structs), bench -> bridge (Bridges, with "Switch mode" and the jump into Structs), bench -> variant '
          '-> variable -> "Use this pin" (HAL, THE slot write); every table has a description', all(k in blob for k in ('selectScope": "instance', 'selectScope": "field',
                                                                                                                 'selectScope": "bridge', 'selectScope": "variant',
                                                                                                                 'selectScope": "variable', 'rowLinkTabField": "tab',
                                                                                                                 'Switch mode', 'Use this pin', '/set',
                                                                                                                 'selectScope": "category', 'selectScope": "register',
                                                                                                                 'selectScope": "pin', '/register-categories', '/uses'))
          and all(it.get('description') for it in items), [it.get('id') for it in items if not it.get('description')])


def registers_tab():
    """rm-4: every door the Registers tab names answers on the board doors (the {scope:..} placeholders filled the way a click fills them)."""
    from board.register_view_api import RegisterViewAPI
    from cmod.bench_views_page import BENCH_VIEWS_PAGES
    d = json.loads(BENCH_VIEWS_PAGES[0]['definition'])
    tab = next(t for t in d['tabs'] if t['key'] == 'registers')
    paths = [it['componentProps']['inputs'].get('dataPath') for r in tab['rows'] for it in r['items'] if it['componentProps']['inputs'].get('dataPath')]
    scope = {'soc': 'atmega328p', 'category': 'mcu-pin/interrupt', 'register': 'EICRA', 'field': 'atmega328p:DDRD.DDD2', 'pin': 'PD2', 'rev': '0'}
    api = RegisterViewAPI(polServer=None, manager=None)
    import re
    from urllib.parse import parse_qsl
    routes = [('/api/board/socs', 'on_get_socs', ()), (r'/api/board/socs/([^/]+)/register-categories', 'on_get_categories', 1),
              (r'/api/board/socs/([^/]+)/registers/([^/?]+)', 'on_get_register', 2), (r'/api/board/socs/([^/]+)/registers', 'on_get_registers', 1),
              (r'/api/board/socs/([^/]+)/fields/([^/]+)/pins', 'on_get_field_pins', 2), (r'/api/board/socs/([^/]+)/pins/([^/]+)/uses', 'on_get_pin_uses', 2),
              (r'/api/board/socs/([^/]+)/pins', 'on_get_pins', 1)]
    got = {}
    for raw in paths:
        url = re.sub(r'\{scope:([a-z]+)\}', lambda m: scope[m.group(1)], raw)
        path, _, q = url.partition('?')
        params = dict(parse_qsl(q))
        for pat, meth, _n in routes:
            m = re.fullmatch(pat, path)
            if m:
                resp = types.SimpleNamespace(status='200 OK', media=None)
                getattr(api, meth)(types.SimpleNamespace(get_param=lambda k, p=params: p.get(k)), resp, *m.groups())
                got[path] = (resp.status, (resp.media or {}).get('count'))
                break
        else:
            got[path] = ('no route', None)
    check('rm-4 REGISTERS TAB: every door it names answers on a click\'s values (EICRA in mcu-pin/interrupt, DDRD.DDD2, pin PD2) - 200 with rows, no unrouted path; the '
          'access words are their own table (RegisterAccessKind)', all(st == '200 OK' and (n or 0) > 0 for st, n in got.values()) and len(got) == 7 and len(paths) == 9
          and any(it['componentProps']['inputs'].get('className') == 'RegisterAccessKind' for r in tab['rows'] for it in r['items']), got)


def registered():
    from moduleService.manifests import conform
    for mod in ('cmod', 'grpcbridge', 'uno_core_demo'):
        r = conform(mod)
        check('MANIFEST: pol modules conform %s is clean' % mod, r['ok'], r.get('findings'))


def main():
    structs()
    bridges()
    doors()
    page()
    registers_tab()
    registered()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
