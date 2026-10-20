"""board_bench_selftest - lay-2 + sim-3 (PROTOTYPING_VIEWS_PLAN section 3, HARDWARE_BENCH_CONVERGENCE_PLAN section 3): the layout SCENE, the two configured PAGES and the sim bench's backend.

Checks (offline; the browser half is the Karma specs of hardware-layout-view):
  - the scene the layout door sends: boards (UNO header connectors + the breadboard geometry), the interaction of the pushbutton DERIVED from its KitPart (press D2 -> PD2, pressed level 0
    because its other side is GND), the LED's output pin through the series resistor (D6 -> PD6, not the sense stand-in D3), `watch` = every output pin; a synthetic design gives the
    potentiometer, TMP36 (500 mV + 10 mV/degC), tilt toggle and piezo their overlays, and a part with no interaction kind gets none;
  - the table doors the layout page reads (steps by query, verdict rows, models, boards rows) and that every column of every table exists on the rows its door serves;
  - /display/layout and /display/sim-bench: tabbed, only configured tables + the ONE renderer, plain-words descriptions, the demo page's LightState table is EMBEDDED from the one
    factory (the demo page itself is unchanged), scope wiring (session, rev), every row action's door exists;
  - BenchInteraction: an inject with a part records who/what/when/the twin cycle (adc has none: -1, said), set-up commands (watch, status) are not recorded, the session's rows come back in
    order, "record as evidence" writes a ScenarioRun of kind attested whose outcome is undetermined (never a proof), an empty session is refused, the doors answer.

    PYTHONPATH=.:modules python3 -m board.board_bench_selftest
"""
import contextlib
import hashlib
import json
import os
import sys
import tempfile
import types

HEX = b':020000040000FA\n:00000001FF\n'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def _items(rows):
    return [i for r in rows for i in r['items']]


def _page_items(page):
    d = json.loads(page['definition'])
    return d, {t['key']: _items(t['rows']) for t in d['tabs']}


def run():
    scene_checks()
    page_checks()
    backend_checks()
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return 0 if ok == total else 1


# ------------------------------------------------------------------------------------------------------------------------------ the scene
def _synthetic():
    """A design with a pot on A0, a TMP36 on A1, a tilt switch on D4 to GND, a piezo on D9 and a plain capacitor: one of each overlay."""
    def comp(ref, kind, key, iface, terms):
        return {'ref': ref, 'kind': kind, 'kit_key': key, 'kit_part': {'interface_kind': iface}, 'terminals': [{'id': '%s.%s' % (ref, n), 'name': n, 'net': net} for n, net in terms]}
    comps = [comp('RV1', 'pot', 'potentiometer', 'analog-in', [('a', '+5V'), ('wiper', 'N_POT'), ('b', 'GND')]),
             comp('U1', 'tmp36', 'tmp36', 'analog-in', [('vs', '+5V'), ('out', 'N_T'), ('gnd', 'GND')]),
             comp('S2', 'switch', 'tilt-sensor', 'digital-in', [('1', 'N_TILT'), ('2', 'GND')]),
             comp('BZ1', 'piezo', 'piezo', 'digital-out', [('1', 'N_BZ'), ('2', 'GND')]),
             comp('C1', 'capacitor', 'capacitor', '', [('1', 'N_BZ'), ('2', 'GND')])]
    nets = {'+5V': ['RV1.a', 'U1.vs', 'hdr:+5V'], 'GND': ['RV1.b', 'U1.gnd', 'S2.2', 'BZ1.2', 'C1.2', 'hdr:GND'], 'N_POT': ['RV1.wiper', 'hdr:A0'], 'N_T': ['U1.out', 'hdr:A1'],
            'N_TILT': ['S2.1', 'hdr:D4'], 'N_BZ': ['BZ1.1', 'C1.1', 'hdr:D9']}
    return {'components': comps, 'nets': nets, 'assignment': {}}


def scene_checks():
    print('-- the scene')
    from electrodevice.custom import layout_core as C
    from electrodevice.custom import layout_scene as S
    r = C.public(C.layout_place('uno-light', None, None))
    sc = r['scene']
    b = {x['name']: x for x in sc['boards']}
    check('lay-2: the layout door carries `scene`: the UNO (header connectors from board_uno) first, then the breadboard (30 rows, 5 holes a side, 25 rail holes, 2.54 mm)',
          [x['role'] for x in sc['boards']] == ['header', 'bench'] and [c['name'] for c in b['bench-uno-1']['connectors']] == ['POWER', 'ANALOG', 'DIGITAL_L', 'DIGITAL_H', 'ICSP']
          and (b['bench-half-1']['rows'], b['bench-half-1']['holes_per_side'], b['bench-half-1']['rail_holes'], b['bench-half-1']['pitch_mm']) == (30, 5, 25, 2.54))
    sw = sc['parts']['SW1']['interaction']
    check('sim-3: the pushbutton\'s overlay is DERIVED from its KitPart (digital-in): press, D2 -> PD2, pressed level 0 because its other side is joined to GND',
          sw and sw['control'] == 'press' and sw['pin'] == 'D2' and sw['twin_pin'] == 'PD2' and sw['pressed_level'] == 0, sw)
    led = sc['parts']['LED1']['output']
    check('sim-3: the LED\'s output pin is found THROUGH its series resistor and is the config\'s own led pin (D6 -> PD6), not the stand-in sense jumper\'s D3', led and led['kind'] == 'led' and led['twin_pin'] == 'PD6', led)
    check('sim-3: the resistor has no interaction and no output (it draws as a plain sprite); `watch` lists every output pin', sc['parts']['R1']['interaction'] is None and sc['parts']['R1']['output'] is None and sc['watch'] == ['PD6'])
    d = _synthetic()
    comps = d['components']
    ix = {c['ref']: S._interaction(d, comps, c) for c in comps}
    out = {c['ref']: S._output(d, comps, c) for c in comps}
    check('sim-3: the potentiometer is a slider on A0 (ADC channel 0): 0 % = 0 mV, 100 % = 5000 mV', ix['RV1']['control'] == 'slider' and ix['RV1']['adc'] == 0 and ix['RV1']['twin_pin'] == 'PC0'
          and ix['RV1']['offset_mv'] + 100 * ix['RV1']['per_unit_mv'] == 5000 and ix['RV1']['offset_mv'] == 0)
    t = ix['U1']
    check('sim-3: the TMP36 is a temperature slider on A1: mv = 500 + 10 x degC (0 degC -> 500 mV, 25 degC -> 750 mV, 125 degC -> 1750 mV), cited to the Analog Devices datasheet',
          t['control'] == 'slider' and t['adc'] == 1 and t['unit'] == '°C' and [t['offset_mv'] + t['per_unit_mv'] * x for x in (0, 25, 125)] == [500, 750, 1750] and 'Analog Devices' in t['basis'])
    check('sim-3: the tilt sensor is a toggle on D4 (pressed level 0: its other side is GND)', ix['S2']['control'] == 'toggle' and ix['S2']['twin_pin'] == 'PD4' and ix['S2']['pressed_level'] == 0)
    check('sim-3: the piezo shows a tone on D9 (PB1); a part with no interaction kind (the capacitor) has no overlay and no output', out['BZ1']['kind'] == 'tone' and out['BZ1']['twin_pin'] == 'PB1'
          and ix['C1'] is None and out['C1'] is None)
    check('sim-3: the twin\'s accepted ADC range is the 5 V rail (a slider can never ask for more)', S.ADC_MAX_MV == 5000 and S.INTERACTIONS[('analog-in', 'tmp36')]['max'] * 10 + 500 <= 5000)

    print('-- the table doors')
    import falcon
    import falcon.testing as ft
    from electrodevice.layout_api import LayoutAPI
    app = falcon.App()
    srv = types.SimpleNamespace(falconServer=app)
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        LayoutAPI(polServer=srv, manager=None)
    cl = ft.TestClient(app)
    steps = cl.simulate_get('/api/layout/steps?config=uno-light').json
    check('lay-2: GET /api/layout/steps?config= serves the steps as `rows` (step, kind, title, text) - 11 for uno-light; the by-path door still answers', steps['ok'] and len(steps['rows']) == 11
          and set(steps['rows'][0]) == {'step', 'kind', 'title', 'text'} and cl.simulate_get('/api/layout/uno-light/steps').json['sha'] == steps['sha'])
    ver = cl.simulate_get('/api/layout/verdict?config=uno-light').json
    check('lay-2: GET /api/layout/verdict?config= serves the verdict as rows: the whole gate first (ok), one row per design net (equal), one per electrical rule',
          ver['ok'] and ver['rows'][0]['status'] == 'ok' and sum(1 for x in ver['rows'] if x['check'].startswith('Net ')) == 4 and sum(1 for x in ver['rows'] if x['check'].startswith('Rule ')) == 2
          and all(set(x) == {'check', 'subject', 'status', 'words'} for x in ver['rows']), ver['rows'][:2])
    check('lay-2: a missing config is refused in words (400), an unknown one in words (not a 200)', cl.simulate_get('/api/layout/steps').status_code == 400 and cl.simulate_get('/api/layout/verdict?config=nope').status_code != 200)
    models = cl.simulate_get('/api/layout/models').json
    boards = cl.simulate_get('/api/layout/boards').json
    check('lay-2: /api/layout/models and /api/layout/boards serve `rows` for the Board models / Boards tables (5 models; the boards on the bench)', models['count'] == 5 and boards['rows'] == boards['boards'] and len(boards['rows']) >= 3)
    wc = cl.simulate_get('/api/layout/wire-colors').json
    DOORS['/api/layout/steps?'] = steps['rows']
    DOORS['/api/layout/verdict?'] = ver['rows']
    DOORS['/api/layout/models'] = models['rows']
    DOORS['/api/layout/boards'] = boards['rows']
    DOORS['/api/layout/wire-colors?'] = wc['rows']


DOORS = {}


# ------------------------------------------------------------------------------------------------------------------------------ the pages
def _door_rows(path):
    for k, rows in DOORS.items():
        if path.startswith(k):
            return rows
    return None


def page_checks():
    print('-- the pages')
    from board.layout_page import LAYOUT_PAGES
    from hwnocode.sim_bench_page import SIM_BENCH_PAGES
    from hwnocode.light_page import LIGHT_PAGES, light_state_table
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS
    for label, page, tabs, nrender in (('/display/layout', LAYOUT_PAGES[0], ['layout', 'boards'], 1), ('/display/sim-bench', SIM_BENCH_PAGES[0], ['bench', 'evidence'], 1)):
        d, byt = _page_items(page)
        items = [i for v in byt.values() for i in v]
        names = {i['componentProps']['componentName'] for i in items}
        check('%s is a registered page with tabs %s (a scope change is applied IN PLACE only on a tabbed page, so the renderer keeps its zoom and its live stream)' % (label, tabs),
              page['isPage'] is True and [t['key'] for t in d['tabs']] == tabs and page['pageRoute'] == label[9:] and
              (page in SEED_BOARD_PAGE_DISPLAYS or page in SEED_HWNOCODE_PAGE_DISPLAYS))
        check('%s: only configured tables + the ONE sanctioned renderer (no api-json-panel, no other custom component), exactly %d renderer' % (label, nrender),
              names == {'class-rows-table', 'hardware-layout-view'} and sum(1 for i in items if i['componentProps']['componentName'] == 'hardware-layout-view') == nrender, names)
        tables = [i for i in items if i['componentProps']['componentName'] == 'class-rows-table']
        check('%s: every table says in plain words what it is for and what one row is' % label, all('What this is for' in i['description'] and 'One row' in i['description'] for i in tables if i['id'] != 'light-state' and i['id'] != 'sim-light-state'),
              [i['id'] for i in tables if 'One row' not in i['description']])
    d, lay = _page_items(LAYOUT_PAGES[0])
    view = next(i for i in lay['layout'] if i['componentProps']['componentName'] == 'hardware-layout-view')['componentProps']['inputs']
    check('lay-2: the renderer is configured by inputs: dataPath (the layout door, {config} filled from ?config=), stepsPath, mode build, board/scheme from the page scope',
          view['dataPath'] == '/api/layout/{config}' and view['stepsPath'] == '/api/layout/steps' and view['mode'] == 'build' and view['board'] == '{scope:board}' and view['scheme'] == '{scope:scheme}')
    t = {i['id']: i['componentProps']['inputs'] for i in lay['layout'] + lay['boards'] if i['componentProps']['componentName'] == 'class-rows-table'}
    check('lay-2: the steps and the gate verdict follow the picture\'s announced config/board/scheme (page scope); the schemes table selects scope `scheme` and has the copy-before-edit row action (seeded rows only) of the scores page',
          '{scope:config}' in t['lay-steps']['dataPath'] and '{scope:config}' in t['lay-verdict']['dataPath'] and t['lay-colours']['selectScope'] == 'scheme' and t['lay-colours']['rowAction']['path'] == '/api/layout/wire-colors'
          and t['lay-colours']['rowAction']['body_template'] == {'name': 'my-{name}', 'copy_of': '{name}'} and t['lay-colours']['rowAction']['show_when_field'] == 'seeded' and t['lay-boards']['selectScope'] == 'board')
    for tid, inp in t.items():
        rows = _door_rows(inp['dataPath'])
        cols = [c for c in inp['columns'].split(',') if c]
        check('lay-2: table %s reads %s and each of its columns (%s) is a field of the rows that door serves' % (tid, inp['dataPath'].split('?')[0], inp['columns']),
              rows and all(c in rows[0] for c in cols), [c for c in cols if rows and c not in rows[0]])
    # the sim bench
    d, sim = _page_items(SIM_BENCH_PAGES[0])
    sv = next(i for i in sim['bench'] if i['componentProps']['componentName'] == 'hardware-layout-view')['componentProps']['inputs']
    check('sim-3: the renderer is in BENCH mode bound to the page scope `session`', sv['mode'] == 'bench' and sv['session'] == '{scope:session}')
    st = {i['id']: i['componentProps']['inputs'] for i in sim['bench'] + sim['evidence'] if i['componentProps']['componentName'] == 'class-rows-table'}
    check('sim-3: the sessions table is a configured table on /api/board/twins with select_scope session; "Start a session" posts the config to /api/board/twins and picks the new session',
          st['sim-sessions']['dataPath'].startswith('/api/board/twins') and st['sim-sessions']['selectScope'] == 'session' and st['sim-firmwares']['rowAction']['path'] == '/api/board/twins'
          and st['sim-firmwares']['rowAction']['body_template'] == {'config': '{name}'} and st['sim-firmwares']['rowAction']['then_scope'] == {'key': 'session', 'from': 'name'})
    check('sim-3: the firmware panel shows config, the LOCKED hex sha256, board, ports, time left, and has a Stop session row action; the bridge table has "Attach a bridge" posting to /api/grpc/hosted-bridges',
          all(c in st['sim-firmware-panel']['columns'] for c in ('config', 'hex_sha256', 'locked_text', 'board', 'ports', 'remaining_s')) and st['sim-firmware-panel']['rowAction']['label'] == 'Stop session'
          and st['sim-firmware-panel']['rowAction']['path'] == '/api/board/twins/{name}/stop' and st['sim-bridge-attach']['rowAction']['path'] == '/api/grpc/hosted-bridges'
          and st['sim-bridge-attach']['rowAction']['body_template'] == {'session': '{name}'})
    check('sim-3: "Record this session as evidence" posts to /api/board/twins/{name}/record', st['sim-record']['rowAction']['label'] == 'Record this session as evidence' and st['sim-record']['rowAction']['path'] == '/api/board/twins/{name}/record')
    demo = next(i for p in LIGHT_PAGES if p['pageRoute'] == 'uno-core-demo' for r in json.loads(p['definition'])['rows'] for i in r['items'] if i['id'] == 'light-state')
    emb = next(i for i in sim['bench'] if i['id'] == 'sim-light-state')
    same = lambda a, b: {k: v for k, v in a.items() if k not in ('id', 'componentProps')} == {k: v for k, v in b.items() if k not in ('id', 'componentProps')}   # noqa: E731
    di, ei = demo['componentProps']['inputs'], emb['componentProps']['inputs']
    check('sim-3 (D-hbc-5): the App UI beside the bench is the demo page\'s OWN LightState table from the one factory (same title, description, columns, "Turn the light on / off" action); only its data door differs',
          same(demo, emb) and {k: v for k, v in di.items() if k != 'dataPath'} == {k: v for k, v in ei.items() if k != 'dataPath'} and di['dataPath'] == '' and ei['dataPath'].startswith('/api/board/twins/light-state') and demo['componentProps'] == light_state_table()['componentProps'])
    check('the demo page /display/uno-core-demo still has its LightState table as a CLASS table (no data path), unchanged', di['className'] == 'LightState' and di['dataPath'] == '' and di['rowAction']['body_template']['solutionName'] == 'light-toggle')
    import polariapps.apps_seed  # noqa: F401  (imports clean with the two new nav entries)
    blob = json.dumps([p['definition'] for p in LAYOUT_PAGES + SIM_BENCH_PAGES])
    check('both pages: scope `rev` refreshes the tables the renderer and the row actions touch (rev=r{scope:rev} in the data paths) and no page carries a raw JSON panel', 'rev=r{scope:rev}' in blob and 'api-json-panel' not in blob)


# ------------------------------------------------------------------------------------------------------------------------------ the backend
def _mgr():
    return types.SimpleNamespace(objectTables={}, db=None, idList=[], noteTreeMutation=lambda *a, **k: None)


@contextlib.contextmanager
def _env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    os.environ.update({k: v for k, v in kv.items() if v is not None})
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def backend_checks():
    print('-- the sim bench backend (fake worker + fake twin control port)')
    with tempfile.TemporaryDirectory(prefix='bench-test-') as td, _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret')):
        _backend()


def _backend():
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    from board.custom import bench_interactions as BI, twin_sessions as TS
    from board.custom.twin_session_fakes import FakeWorker
    from board.board_basis import BenchInteraction, BOARD_CLASSES
    from board.board_seed import BOARD_SEED_PAIRS
    check('sim-3: BenchInteraction is a BOARD_CLASSES member with plain_words, observed and never seeded', BenchInteraction in BOARD_CLASSES and BenchInteraction.plain_words and [r for n, _c, r in BOARD_SEED_PAIRS if n == 'BenchInteraction'] == [[]])
    worker = FakeWorker(sessions=True)
    mgr = _mgr()
    real_build = TS.build_hex
    TS.build_hex = lambda config: (HEX, hashlib.sha256(HEX).hexdigest())
    try:
        with _env(BOARD_ENGINES_URL=worker.url):
            server = types.SimpleNamespace(falconServer=falcon.App(), manager=mgr)
            with contextlib.redirect_stdout(open(os.devnull, 'w')):
                construct_board_endpoints(server)
            cl = ft.TestClient(server.falconServer)
            name = cl.simulate_post('/api/board/twins', json={'config': 'uno-light', 'ttl_s': 120, 'owner': 'bench'}).json['name']
            sub = TS.events(mgr, name)
            # set-up commands are not interactions
            w = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'watch': ['PD6']})
            check('sim-3: a watch (set-up) is sent to the twin and is NOT recorded as an interaction', w.json['ok'] and w.json['interaction'] is None and BI.listing(mgr, name) == [])
            press = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'PD2', 'level': 0, 'part': 'SW1', 'kind': 'press'})
            rel = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'PD2', 'level': 1, 'part': 'SW1', 'kind': 'release'})
            adc = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'adc': 1, 'mv': 750, 'part': 'U1', 'what': 'temperature set to 25 °C on U1'})
            rows = cl.simulate_get('/api/board/twins/%s/interactions' % name).json['rows']
            check('sim-3: a press then a release are recorded in order with the part, the plain-words action and the TWIN\'S OWN CYCLE from the ack; meta keys never reach the twin',
                  [r['kind'] for r in rows[:2]] == ['press', 'release'] and rows[0]['part'] == 'SW1' and rows[0]['what'] == 'pressed on SW1: PD2 driven to 0' and rows[0]['twin_cycle'] > 0 and rows[1]['twin_cycle'] > rows[0]['twin_cycle']
                  and press.json['sent'] == {'set': 'PD2', 'level': 0} and rows[0]['ok'] and rows[0]['seq'] == 1 and rows[1]['seq'] == 2, rows[:2])
            check('sim-3: an analog input has no cycle in the twin\'s ack, so it records -1 and says "not reported by the twin" (never a guess); a person\'s own words for the action are kept',
                  rows[2]['kind'] == 'adc' and rows[2]['twin_cycle'] == -1 and rows[2]['twin_cycle_text'] == 'not reported by the twin' and rows[2]['what'] == 'temperature set to 25 °C on U1' and rows[2]['value'] == 750.0, rows[2])
            bad = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'PX9', 'level': 1})
            rows = cl.simulate_get('/api/board/twins/%s/interactions' % name).json['rows']
            check('sim-3: a refused action is recorded too (ok false, the twin\'s words)', bad.status_code == 409 and rows[3]['ok'] is False and 'not a pin' in rows[3]['reply'])
            evs = [sub.get(1) for _ in range(3)]
            check('sim-3: the SSE stream, subscribed BEFORE injecting, carries the output pin\'s edge (PD6 rises after the PD2 press path) - the picture lights from this', any(e and e.get('pin') == 'PD6' for e in evs), evs)
            sub.close()
            no = cl.simulate_get('/api/board/twins/interactions')
            allr = cl.simulate_get('/api/board/twins/interactions?session=all').json
            one = cl.simulate_get('/api/board/twins?name=%s' % name).json
            check('sim-3: by-query doors: interactions needs ?session= (400 in words), ?session=all lists every session\'s rows, /api/board/twins?name= keeps the one session with the firmware-panel fields',
                  no.status_code == 400 and allr['count'] == 4 and one['count'] == 1 and one['rows'][0]['hex_sha256'] == hashlib.sha256(HEX).hexdigest() and one['rows'][0]['running_now'] is True
                  and 'locked' in one['rows'][0]['locked_text'] and one['rows'][0]['ports'].startswith('serial report'))
            rec = cl.simulate_post('/api/board/twins/%s/record' % name, json={})
            run = [r for r in mgr.objectTables.get('ScenarioRun', {}).values()]
            check('sim-3 (D-hbc-4): "record as evidence" writes ONE ScenarioRun of kind attested, side bench-session, outcome undetermined (nobody judged it), with the locked firmware sha256 and every interaction in repro_json; it is not a proof',
                  rec.status_code == 200 and rec.json['kind'] == 'attested' and rec.json['interactions'] == 4 and len(run) == 1 and run[0].kind == 'attested' and run[0].outcome == 'undetermined'
                  and run[0].side == 'bench-session' and run[0].scenario == 'bench-session:uno-light' and run[0].firmware_sha256 == hashlib.sha256(HEX).hexdigest()
                  and len(json.loads(run[0].repro_json)['interactions']) == 4 and 'unauthenticated' in run[0].verdict_words, rec.json)
            ev = cl.simulate_get('/api/board/twins/evidence').json
            check('sim-3: GET /api/board/twins/evidence lists it for the Evidence tab', ev['count'] == 1 and ev['rows'][0]['kind'] == 'attested' and ev['rows'][0]['outcome'] == 'undetermined')
            judged = cl.simulate_post('/api/board/twins/%s/record' % name, json={'outcome': 'passed', 'observed': 'LED followed the button every time'})
            wrong = cl.simulate_post('/api/board/twins/%s/record' % name, json={'outcome': 'great'})
            check('sim-3: a person may judge it (passed + their own words); any other outcome is refused 400 in words', judged.status_code == 200 and judged.json['outcome'] == 'passed' and wrong.status_code == 400)
            name2 = cl.simulate_post('/api/board/twins', json={'config': 'uno-light', 'ttl_s': 60}).json['name']
            empty = cl.simulate_post('/api/board/twins/%s/record' % name2, json={})
            check('sim-3: a session with nothing done on it is refused (409) in words, no row written', empty.status_code == 409 and 'no recorded interactions' in empty.json['error'])
            ls = cl.simulate_get('/api/board/twins/light-state').json
            vr = cl.simulate_get('/api/board/variants').json
            check('sim-3: /api/board/twins/light-state serves `rows` (the App UI table\'s door), /api/board/variants now serves `rows` too (the firmware table), the older `variants` key is kept',
                  ls['ok'] and ls['rows'] == [] and vr['rows'] == vr['variants'] and any(v['name'] == 'uno-light' for v in vr['rows']))
            stop = cl.simulate_post('/api/board/twins/%s/stop' % name, json={})
            after = cl.simulate_get('/api/board/twins?name=%s' % name).json['rows'][0]
            check('sim-3: POST .../stop (the row button) ends the session; running_now turns false so the Stop button hides', stop.status_code == 200 and stop.json['state'] == 'ended' and after['running_now'] is False)
            TS.stop(mgr, name2)
    finally:
        TS.build_hex = real_build
        TS.HUBS.clear()
        worker.close()


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(run())
