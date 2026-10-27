"""board_bench_setup_selftest - bench-0 (MISSION_GENERIC_PLAN.md section 13.1): the Bench, its two selection lists, the testing words (HARDWARE ONLY
said loudly), the add / remove doors, the breadboard models' derived geometry and the page.

    PYTHONPATH=.:modules python3 -m board.board_bench_setup_selftest
"""
import json


def run_bench_setup(check):
    from board.custom import bench as B
    from board.custom import bench_seed as S
    from board.custom import chip_ladder as CL
    B._MEM.clear()
    # ---- the models
    ms = {m['name']: m for m in S.SEED_BREADBOARD_MODELS}
    check('bench-0 MODELS: five breadboard models; half-400 and full-830 and mini-170 have DERIVED geometry from pv_shapes; the kit\'s is UNVERIFIED with no dimensions; the BUD carries its CITED 47.0 x 36.1 mm outline (170 tie points) but is not drawable yet (generated width is 1.26 mm off the stated one)',
          len(ms) == 5 and all(ms[k]['geometry_known'] and ms[k]['width_mm'] > 0 and 'derived' in ms[k]['basis'] for k in ('half-400', 'full-830', 'mini-170'))
          and not ms['starter-kit-breadboard']['geometry_known'] and ms['starter-kit-breadboard']['width_mm'] == -1.0
          and ms['bud-bb-32650-w']['tie_points'] == 170 and ms['bud-bb-32650-w']['kind'] == 'mini' and not ms['bud-bb-32650-w']['geometry_known']
          and (ms['bud-bb-32650-w']['width_mm'], ms['bud-bb-32650-w']['height_mm']) == (47.0, 36.1) and 'cited' in ms['bud-bb-32650-w']['basis'],
          {k: (m['geometry_known'], round(m['width_mm'], 1)) for k, m in ms.items()})
    from board.custom import pv_shapes as PV
    g0, g1 = PV.breadboard_geometry(17, 0), PV.breadboard_geometry(30, 25)
    P = 2.54
    check('bench-0 RAILS: a rail-less geometry (17 rows, rail_holes 0) has NO rail band - no rail_y entries and its height is exactly the tie-point block (11 pitches between a and j + two margins = 14 pitches); a half board with rails still has all four bands and its 20.4-pitch height',
          g0['rail_y'] == {} and abs(g0['h'] - 14 * P) < 1e-9 and abs(g0['h'] - (g0['col_y']['j'] - g0['col_y']['a'] + 2 * PV.BB_PAD * P)) < 1e-9
          and set(g1['rail_y']) == {'top+', 'top-', 'bottom-', 'bottom+'} and abs(g1['h'] - 20.4 * P) < 1e-9 and PV.hole_xy(g0, 'rail:top:+:1') is None, (g0['h'], g1['h']))
    check('bench-0 MODELS: the full board is wider than the half, the half than the mini (the geometry follows the row counts)',
          ms['full-830']['width_mm'] > ms['half-400']['width_mm'] > ms['mini-170']['width_mm'], (ms['full-830']['width_mm'], ms['half-400']['width_mm'], ms['mini-170']['width_mm']))
    # ---- the testing words (shared with the ladder)
    lb = B.ladder_boards(None)
    check('bench-0 TESTING: every ladder board has a testing group and a word; the UNO is "simulated: pins real"; the Arduino Zero and the Feather are "HARDWARE ONLY"; the C3 says STUB',
          all(r['testing_group'] in ('simulated', 'simulated-stub', 'hardware-only', 'planned') and r['testing'] for r in lb.values())
          and lb['arduino-uno-r3']['testing_group'] == 'simulated' and lb['arduino-uno-r3']['testing'].startswith('simulated: pins real')
          and lb['arduino-zero']['testing'].startswith('HARDWARE ONLY') and lb['adafruit-feather-m0-express']['testing'].startswith('HARDWARE ONLY')
          and 'STUB' in lb['esp32-c3-devkitm-1']['testing'], {k: v['testing'][:40] for k, v in lb.items() if k in ('arduino-uno-r3', 'arduino-zero', 'esp32-c3-devkitm-1')})
    check('bench-0 TESTING: the word names the software and how it simulates, and who drives the inputs (never blank)',
          all(r['software'] and r['how'] and r['inputs_driven_by'] for r in lb.values()), [k for k, r in lb.items() if not (r['software'] and r['how'] and r['inputs_driven_by'])])
    # ---- the seeded bench
    st, body = B.get_door(None, {}, 'benches')
    hb = next(r for r in body['rows'] if r['name'] == S.HOME_BENCH)
    check('bench-0 HOME: the seeded home bench holds the four boards he showed and three breadboards (2 BUD + the kit\'s); three of the four boards are HARDWARE ONLY or STUB and are NAMED',
          st == 200 and hb['boards'] == 4 and hb['breadboards'] == 3 and hb['simulated_real_pins'] == 1 and hb['hardware_only'] == 2 and hb['simulated_stub_pins'] == 1
          and 'Zero #1' in hb['hardware_only_boards'] and 'Feather M0 #1' in hb['hardware_only_boards'], hb)
    st, body = B.get_door(None, {}, 'boards', S.HOME_BENCH)
    check('bench-0 BOARDS: the bench\'s board rows carry label, testing, software, how, inputs_driven_by, section (RISC-V | convenience)',
          st == 200 and len(body['rows']) == 4 and all(k in body['rows'][0] for k in ('label', 'testing', 'software', 'how', 'inputs_driven_by', 'section'))
          and {r['section'] for r in body['rows']} == {'convenience'}, body['rows'][0] if body.get('rows') else body)
    st, body = B.get_door(None, {}, 'breadboards', S.HOME_BENCH)
    check('bench-0 BREADBOARDS: the BUD rows say UNVERIFIED geometry in capitals (cannot be drawn yet) and count 2',
          st == 200 and any(r['model'] == 'bud-bb-32650-w' and r['count'] == 2 and r['geometry'].startswith('UNVERIFIED') for r in body['rows']), body['rows'])
    # ---- the selection lists
    st, body = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-boards')
    rows = body['rows']
    check('bench-0 OPTIONS boards: every ladder board once, RISC-V first then convenience, simulatable before HARDWARE ONLY within a section; on_bench counts the home bench; can_add on every row',
          st == 200 and len(rows) == len(lb) and rows[0]['section'] == 'RISC-V' and rows[-1]['section'] == 'convenience'
          and next(r for r in rows if r['board'] == 'arduino-uno-r3')['on_bench'] == 1 and all(r['can_add'] for r in rows), [(r['section'], r['testing_group']) for r in rows][:6])
    st, body = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-breadboards')
    check('bench-0 OPTIONS breadboards: the five models, on_bench 2 for the BUD, geometry word on each',
          st == 200 and len(body['rows']) == 5 and next(r for r in body['rows'] if r['name'] == 'bud-bb-32650-w')['on_bench'] == 2 and all(r['geometry'] for r in body['rows']), body['rows'][0])
    # ---- add / remove
    st, body = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'rpi-pico2'})
    check('bench-0 ADD board: adding a Pico 2 answers 201 with its testing word (HARDWARE ONLY, no emulator) and the bench now lists five boards',
          st == 201 and body['testing'].startswith('HARDWARE ONLY') and len(body['rows']) == 5 and body['rows'][-1]['label'].endswith('#1'), body.get('testing'))
    st2, body2 = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'arduino-uno-r3'})
    check('bench-0 ADD board: a second UNO gets label "... #2"', st2 == 201 and body2['rows'][-1]['label'].endswith('#2'), body2['rows'][-1]['label'])
    st3, body3 = B.post_door(None, S.HOME_BENCH, 'boards', {'board': 'not-a-board'})
    check('bench-0 ADD board: an unknown board is 404 and names the known ones', st3 == 404 and 'known' in body3 and 'arduino-uno-r3' in body3['known'], body3.get('error'))
    st4, body4 = B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400', 'count': 2})
    st5, body5 = B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400'})
    check('bench-0 ADD breadboard: two half boards then one more make count 3 on one row; count 0 is 400; an unknown model 404',
          st4 == 201 and st5 == 201 and next(r for r in body5['rows'] if r['model'] == 'half-400')['count'] == 3
          and B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'half-400', 'count': 0})[0] == 400
          and B.post_door(None, S.HOME_BENCH, 'breadboards', {'model': 'nope'})[0] == 404, body5['rows'])
    st6, body6 = B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'board', 'key': body2['rows'][-1]['label']})
    st7, body7 = B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'breadboard', 'key': 'half-400'})
    check('bench-0 REMOVE: removing the second UNO by label leaves five boards; removing one half board leaves count 2; an unknown key is 404; a bad kind 400',
          st6 == 200 and len(body6['rows']) == 5 and st7 == 200 and next(r for r in body7['rows'] if r['model'] == 'half-400')['count'] == 2
          and B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'board', 'key': 'ghost'})[0] == 404
          and B.post_door(None, S.HOME_BENCH, 'remove', {'kind': 'thing', 'key': 'x'})[0] == 400, (len(body6['rows']), body7['rows']))
    check('bench-0 DOORS: an unknown bench is 404 on boards, breadboards, add and remove',
          B.get_door(None, {}, 'boards', 'nowhere')[0] == 404 and B.post_door(None, 'nowhere', 'boards', {'board': 'arduino-uno-r3'})[0] == 404
          and B.post_door(None, 'nowhere', 'remove', {'kind': 'board', 'key': 'x'})[0] == 404, '')
    check('bench-0 PRIVACY: no e-mail, street or invoice number in the seeds', not any(s in json.dumps(S.SEED_BENCHES + S.SEED_BREADBOARD_MODELS) for s in ('@', 'Arrowhead', 'Fairfax', '3689309', '134236176')), '')
    # ---- the ladder's own split
    st, body = CL.door(None, {'section': 'convenience'}, 'chips')
    groups = {r['name']: r['testing_group'] for r in body['rows']}
    check('chp-1 SPLIT: every ladder row carries testing_group + testing + software + how + inputs_driven_by; the SAMD21 row is hardware-only and its word starts HARDWARE ONLY',
          all(k in body['rows'][0] for k in ('testing_group', 'testing', 'software', 'how', 'inputs_driven_by')) and groups['samd21g18a'] == 'hardware-only'
          and next(r for r in body['rows'] if r['name'] == 'samd21g18a')['testing'].startswith('HARDWARE ONLY'), groups)
    st, body = CL.door(None, {}, 'emulators')
    check('chp-1 EMULATORS: every emulator row says its method and what drives the inputs; the "none" row lists the HARDWARE ONLY chips',
          all(r['method'] and r['inputs_driven_by'] for r in body['rows']) and 'samd21g18a' in next(r for r in body['rows'] if r['kind'] == 'none')['chips_covered'], body['rows'][-1])
    # ---- the pages
    from board.bench_page import BENCH_PAGES as P
    from board.chip_ladder_page import CHIP_LADDER_PAGES as CP
    d = json.loads(P[0]['definition'])
    check('bench-0 PAGE: /display/bench has the benches table above four tabs - On the bench, Add a board, Add a breadboard, Budget (ipb-2) - with Add to bench and Remove row actions',
          P[0]['pageRoute'] == 'bench' and [t['key'] for t in d['tabs']] == ['bench', 'add-board', 'add-breadboard', 'budget']
          and all('"label": "Add to bench"' in json.dumps(d['tabs'][i]) for i in (1, 2)) and '"label": "Remove"' in json.dumps(d['tabs'][0]), [t['key'] for t in d['tabs']])
    cd = json.loads(CP[0]['definition'])
    check('chp-1 PAGE: each ladder section has the three testing tables - simulated with real pins, pins stub, HARDWARE ONLY - and the Emulators tab has the hardware-only table',
          all(w in json.dumps(cd['tabs'][i]) for i in (0, 1) for w in ('testing_group', 'hardware-only', 'simulated-stub'))
          and 'HARDWARE ONLY' in json.dumps(cd['tabs'][2]), '')

def run_wb0(check):
    """wb-0: rail power fields, footprints + radios on the ladder, breadboard_fit, the facet knobs, the create and attempt doors."""
    from board.custom import bench as B
    from board.custom import bench_seed as S
    from board.custom.bench_fit import breadboard_fit as F
    B._MEM.clear()
    ms = {m['name']: m for m in S.SEED_BREADBOARD_MODELS}
    check('wb-0 POWER: every model carries rail_voltage_max_v / rail_current_max_a (-1 = not determined, never a typical number) and a power_basis; none is cited so all are -1',
          all(m['rail_voltage_max_v'] == -1 and m['rail_current_max_a'] == -1 and m['power_basis'] for m in ms.values())
          and 'unverified' in ms['half-400']['power_basis'] and 'no power rails' in ms['mini-170']['power_basis'], {k: m['power_basis'][:40] for k, m in ms.items()})
    st, body = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-breadboards')
    bud = next(r for r in body['rows'] if r['name'] == 'bud-bb-32650-w')
    check('wb-0 OPTIONS breadboards: rail_power is a plain string ("unverified" here) and fit_json has one verdict per board on the bench (UNO beside)',
          st == 200 and isinstance(bud['rail_power'], str) and bud['rail_power'] == 'unverified' and set(bud['fit_json']) == {'arduino-uno-r3', 'arduino-zero', 'adafruit-feather-m0-express', 'elecrow-esp32-eval'}
          and bud['fit_json']['arduino-uno-r3']['verdict'] == 'beside' and bud['fit_json']['adafruit-feather-m0-express']['verdict'] == 'unverified', bud['fit_json'])
    st, none_bench = B.get_door(None, {'bench': 'no-such'}, 'options-breadboards')
    check('wb-0 OPTIONS breadboards: a bench with no boards gives empty fit_json', all(r['fit_json'] == {} for r in none_bench['rows']), '')
    # ---- fit cases
    half, mini = {'rows': 30}, {'rows': 17, 'rail_holes': 0}
    fp7 = {'rows': 2, 'row_spacing_pitches': 7, 'pins_per_row': 16, 'straddles': True}
    uno = B.ladder_boards(None)['arduino-uno-r3']['footprint_json']
    r = [F(uno, half), F(fp7, half), F(dict(fp7, pins_per_row=20), mini), F(dict(fp7, row_spacing_pitches=13), half), F(dict(fp7, row_spacing_pitches=-1), half), F(fp7, {'rows': -1}), F(dict(fp7, row_spacing_pitches=11), half)]
    check('wb-0 FIT: UNO beside; S=7 16 pins on 30 rows straddles with 3 free holes; 20 pins per row on a 17-row mini too-long (16 pins would fit 17 rows by the rule pins <= rows); S=13 too-wide; -1 unverified; S=11 straddles with 1 free',
          [x['verdict'] for x in r] == ['beside', 'straddles', 'too-long', 'too-wide', 'unverified', 'unverified', 'straddles'] and r[1]['free_holes_per_side'] == 3 and r[6]['free_holes_per_side'] == 1, r)
    # ---- facts on the ladder
    lb = B.ladder_boards(None)
    check('wb-0 LADDER facts: every board has footprint_json {rows, row_spacing_pitches, pins_per_row, pitch_in, straddles, basis} and radios_json with a basis; UNO/Zero shield headers straddles False; the Elecrow is wifi + ble with unverified module and IDs; no FCC id invented',
          all(set(b['footprint_json']) >= {'rows', 'row_spacing_pitches', 'pins_per_row', 'pitch_in', 'straddles', 'basis'} and b['radios_json'] and all(x['basis'] for x in b['radios_json']) for b in lb.values())
          and lb['arduino-uno-r3']['footprint_json']['straddles'] is False and lb['arduino-zero']['footprint_json']['straddles'] is False
          and {x['kind'] for x in lb['elecrow-esp32-eval']['radios_json']} == {'wifi', 'ble'} and all(x['module'] == 'unverified' and x['precertified']['fcc_id'] == 'unverified' for x in lb['elecrow-esp32-eval']['radios_json'])
          and all(x['precertified']['fcc_id'] in ('', 'unverified') for b in lb.values() for x in b['radios_json']), '')
    # ---- the boards door + facets
    def opts(**kw):
        return B.get_door(None, dict({'bench': S.HOME_BENCH}, **kw), 'options-boards')
    st, body = opts()
    rows = {r['board']: r for r in body['rows']}
    u = rows['arduino-uno-r3']
    check('wb-0 OPTIONS boards: rows carry arch, riscv, radios (plain string), radios_json, levels (string naming its basis), levels_json, footprint_json',
          st == 200 and u['arch'] == 'AVR' and u['riscv'] is False and rows['esp32-c3-devkitm-1']['riscv'] is True and u['radios'] == 'no radio'
          and rows['elecrow-esp32-eval']['radios'] == 'Wi-Fi + BLE (module unverified, uncertified/unverified)' and 'bare-c yes' in u['levels'] and 'zephyr no' in u['levels'] and 'freertos no' in u['levels'] and 'RuntimeProfile' in u['levels'] and 'freertos unverified' in rows['arduino-mega-2560']['levels']
          and 'basis:' in u['levels'] and isinstance(u['levels_json'], dict) and u['footprint_json'], (u['radios'], u['levels'], rows['elecrow-esp32-eval']['radios']))
    ra, rn = opts(arch='riscv')[1]['rows'], opts(arch='not-riscv')[1]['rows']
    rf = opts(arch='AVR')[1]['rows']
    check('wb-0 FACET arch: riscv and not-riscv partition the list; a family name filters', ra and rn and len(ra) + len(rn) == len(rows) and all(r['riscv'] for r in ra) and not any(r['riscv'] for r in rn) and {r['arch'] for r in rf} == {'AVR'}, (len(ra), len(rn)))
    rw, rno = opts(radio='wifi')[1]['rows'], opts(radio='none')[1]['rows']
    check('wb-0 FACET radio: wifi lists the ESP boards, none lists the UNO and not the Elecrow', 'elecrow-esp32-eval' in {r['board'] for r in rw} and 'arduino-uno-r3' in {r['board'] for r in rno} and 'elecrow-esp32-eval' not in {r['board'] for r in rno}, '')
    rl = opts(level='zephyr')[1]['rows']
    check('wb-0 FACET level: zephyr (status yes only) excludes the UNO and keeps a SAMD21 board', rl and all(r['levels_json']['zephyr']['status'] == 'yes' for r in rl) and 'arduino-uno-r3' not in {r['board'] for r in rl} and 'arduino-zero' in {r['board'] for r in rl}, [r['board'] for r in rl])
    bad = [opts(arch='z80'), opts(radio='x'), opts(level='ubuntu')]
    check('wb-0 FACET knobs: unknown values are 400 with the allowed list', all(st == 400 and b['allowed'] for st, b in bad), bad)
    # ---- create door
    st, b1 = B.post_door(None, '', 'create', {'name': 'wb-test', 'title': 'WB test', 'notes': 'n'})
    st2, b2 = B.post_door(None, '', 'create', {'name': 'wb-test'})
    st3, _ = B.post_door(None, '', 'create', {'title': 'x'})
    check('wb-0 CREATE: 201 makes an empty bench, a duplicate is 409, no name 400', st == 201 and any(r['name'] == 'wb-test' and r['boards'] == 0 for r in b1['rows']) and st2 == 409 and st3 == 400, (st, st2, st3))
    # ---- attempt door
    st, miss = B.post_door(None, S.HOME_BENCH, 'attempt', {'mission': 'nope'})
    check('wb-0 ATTEMPT: a missing mission is 404 with the mission names', st == 404 and 'uno-light-mission' in miss['known'], miss.get('error'))
    st, empty = B.post_door(None, 'wb-test', 'attempt', {'mission': 'uno-light-mission'})
    check('wb-0 ATTEMPT: an empty bench answers verdict none', st == 200 and empty['verdict'] == 'none' and empty['candidates'] == [], empty)
    st, att = B.post_door(None, S.HOME_BENCH, 'attempt', {'mission': 'uno-light-mission'})
    check('wb-0 ATTEMPT: the home bench (UNO modelled; Zero, Feather, Elecrow named as not modelled) MEETS the light mission via gpio-poll sensing; candidates listed, run fingerprint present',
          st == 200 and att['verdict'] == 'meets' and att['boards_used'] == ['arduino-uno-r3'] and set(att['not_modelled']) == {'arduino-zero', 'adafruit-feather-m0-express', 'elecrow-esp32-eval'}
          and att['candidates'] and 'sense-led-line:gpio-poll' in att['candidates'][0]['routes_text'] and att['gap'] == [] and att['pruned'] and att['run']['result_sha256'], {k: att[k] for k in ('verdict', 'boards_used', 'not_modelled')})


def _walk(node, out):
    """Every dict/list node under `node`, collecting the strings under dataPath / path keys."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('dataPath', 'data_path', 'path') and isinstance(v, str) and v.startswith('/api/'):
                out.append(v)
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)


def run_wb2(check):
    """wb-2: /display/workbench, its door paths, the new plain-string columns, the attempts doors."""
    import re
    from board.custom import bench as B
    from board.custom import bench_seed as S
    from board.workbench_page import WORKBENCH_PAGES as W
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as ALL
    B._MEM.clear()
    B._LAST.clear()
    page = W[0]
    d = json.loads(page['definition'])
    keys = [t['key'] for t in d['tabs']]
    check('wb-2 PAGE: /display/workbench exists in the board seeds with 5 tabs name / breadboards / boards / instruments (osc-0) / mission',
          page['pageRoute'] == 'workbench' and page in ALL and keys == ['name', 'breadboards', 'boards', 'instruments', 'mission'], keys)
    st = d['rows'][0]['items'][0]['componentProps']
    steps = st['inputs']['steps']
    check('wb-2 STEPS: a steps strip of 5 steps whose targets are the tab keys; steps 1-4 done on bench set, step 5 on attempt set',
          st['componentName'] == 'steps' and [x['target'] for x in steps] == keys
          and [x['label'] for x in steps] == ['Name the bench', 'Breadboards', 'Dev / eval boards', 'Instruments', 'Mission']
          and all(x['done_when']['op'] == 'set' for x in steps) and steps[4]['done_when']['scope_key'] == '{scope:attempt}'
          and all(x['done_when']['scope_key'] == '{scope:bench}' for x in steps[:4]), steps)
    items = [it for t in d['tabs'] for r in t['rows'] for it in r['items']]
    kinds = [it['componentProps']['componentName'] for it in items]
    form = next((it for it in items if it['componentProps']['componentName'] == 'door-form'), None)
    fi = form['componentProps']['inputs'] if form else {}
    check('wb-3 CREATE: step 1 carries a door-form (name required; title, notes) that POSTs /api/board/benches and sets scope bench from the response field `bench` (what create_bench returns); the benches table reloads on rev',
          form is not None and [f['name'] for f in fi.get('fields', [])] == ['name', 'title', 'notes'] and fi['fields'][0].get('required') is True
          and fi['action']['path'] == '/api/board/benches' and fi['action']['then_scope'] == {'key': 'bench', 'from': 'bench'}
          and 'bench' in B.post_door(None, '', 'create', {'name': 'wb3-shape-check'})[1]
          and 'rev=r{scope:rev}' in json.dumps(d['tabs'][0]), fi)
    check('wb-2 PAGE: picker-buttons for Breadboards, Boards, Instruments, Missions; the boards popup has the three facets arch / radio / level; Add has show_when_field can_add; the attempt action sets scope attempt from verdict',
          kinds.count('picker-button') == 4
          and [f['query_param'] for f in next(i for i in items if i['id'] == 'wb-pick-boards')['componentProps']['inputs']['popup']['facets']] == ['arch', 'radio', 'level']
          and next(i for i in items if i['id'] == 'wb-pick-boards')['componentProps']['inputs']['popup']['action']['show_when_field'] == 'can_add'
          and next(i for i in items if i['id'] == 'wb-pick-missions')['componentProps']['inputs']['popup']['action']['then_scope'] == {'key': 'attempt', 'from': 'verdict'}, kinds)
    # every door path the page uses is a registered route
    paths = []
    _walk(d, paths)
    api = open(__file__.replace('board_bench_setup_selftest.py', 'bench_api.py')).read()
    mapi = open(__file__.replace('board/board_bench_setup_selftest.py', 'cmod/cmod_mission_api.py')).read()
    bapi = open(__file__.replace('board/board_bench_setup_selftest.py', 'cmod/cmod_budget_api.py')).read()   # ipb-2: the bench's Budget tab
    iapi = open(__file__.replace('board/board_bench_setup_selftest.py', 'instruments/instruments_api.py')).read()   # osc-0: the instruments tab's doors
    routes = re.findall(r"add\('([^']+)'", api) + re.findall(r"add\('([^']+)'", mapi) + re.findall(r"add\('([^']+)'", iapi) + re.findall(r"add\('([^']+)'", bapi)

    def hits(path):
        p = re.sub(r'\{scope:[^}]*\}', 'X', path.split('?')[0])
        return any(re.fullmatch(re.sub(r'\{[^}]+\}', '[^/]+', r), p) for r in routes)
    bad = [p for p in paths if not hits(p)]
    check('wb-2 PATHS: every dataPath / action path in the page (%d) matches a route in bench_api.py, cmod_mission_api.py or instruments_api.py' % len(paths), paths and not bad, bad)
    # new columns
    st, bb = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-breadboards')
    half = next(r for r in bb['rows'] if r['name'] == 'half-400')
    kit = next(r for r in bb['rows'] if r['name'] == 'starter-kit-breadboard')
    check('wb-2 COLUMNS breadboards: outline + fits are plain strings; half-400 fits says "Arduino Uno R3: beside" style per board, the kit outline is unverified; no bench -> "no boards on the bench yet"',
          isinstance(half['outline'], str) and ' x ' in half['outline'] and kit['outline'] == 'unverified' and isinstance(half['fits'], str) and ': beside' in half['fits'] and ' \u00b7 ' in half['fits']
          and all(r['fits'] == 'no boards on the bench yet' for r in B.get_door(None, {'bench': 'none-here'}, 'options-breadboards')[1]['rows']), (half['outline'], half['fits']))
    st, bo = B.get_door(None, {'bench': S.HOME_BENCH}, 'options-boards')
    fp = {r['board']: r['footprint'] for r in bo['rows']}
    check('wb-2 COLUMNS boards: footprint is a plain string; UNO says beside the breadboard; a board with no numbers says unverified; the radio knob accepts unverified',
          all(isinstance(v, str) and v for v in fp.values()) and 'beside the breadboard' in fp['arduino-uno-r3'] and fp['elecrow-esp32-eval'] == 'unverified' and fp['esp32-c3-devkitm-1'] == 'unverified'
          and B.get_door(None, {'radio': 'unverified'}, 'options-boards')[0] == 200
          and all('unverified' in r['radios'] for r in B.get_door(None, {'radio': 'unverified'}, 'options-boards')[1]['rows']), list(fp.items())[:3])
    st, bn = B.get_door(None, {}, 'benches')
    row = bn['rows'][0]
    check('wb-2 COUNTS: bench rows carry board_count and breadboard_count equal to boards / breadboards', row['board_count'] == row['boards'] and row['breadboard_count'] == row['breadboards'] and isinstance(row['board_count'], int), row)
    from cmod.custom import mission_doors as D

    class _R:
        media = None

    class _A:
        manager = None

        def _rows(self, c):
            return []
    r = _R()
    D.missions_table(_A(), None, r)
    m0 = r.media['rows'][0]
    check('wb-2 COLUMNS missions: purposes_text is a plain string naming each purpose with its importance; purposes stays the count', isinstance(m0['purposes_text'], str) and 'initialization (required)' in m0['purposes_text'] and isinstance(m0['purposes'], int), m0['purposes_text'])
    # attempts doors
    st, none_yet = B.get_door(None, {}, 'attempts', S.HOME_BENCH)
    check('wb-2 ATTEMPTS: before any attempt the three doors answer empty rows; an unknown bench is 404',
          st == 200 and none_yet['rows'] == [] and B.get_door(None, {}, 'attempts-candidates', S.HOME_BENCH)[1]['rows'] == [] and B.get_door(None, {}, 'attempts-pruned', S.HOME_BENCH)[1]['rows'] == []
          and B.get_door(None, {}, 'attempts', 'no-such')[0] == 404, none_yet)
    st, att = B.post_door(None, S.HOME_BENCH, 'attempt', {'mission': 'uno-light-mission'})
    st, summ = B.get_door(None, {}, 'attempts', S.HOME_BENCH)
    st, cand = B.get_door(None, {}, 'attempts-candidates', S.HOME_BENCH)
    st, prun = B.get_door(None, {}, 'attempts-pruned', S.HOME_BENCH)
    s0 = summ['rows'][0]
    scalar = all(isinstance(v, (str, int, float)) for rows in (summ['rows'], cand['rows'], prun['rows']) for r in rows for v in r.values())
    check('wb-2 ATTEMPTS: after an attempt on home-bench the summary row has verdict meets / mission / boards_used / not_modelled / the run sha; candidates and pruned rows are listed; every cell is a scalar (no raw JSON)',
          len(summ['rows']) == 1 and s0['verdict'] == 'meets' and s0['mission'] == 'uno-light-mission' and s0['boards_used'] == 'arduino-uno-r3' and 'elecrow-esp32-eval' in s0['not_modelled']
          and s0['run_sha'] == att['run']['result_sha256'] and cand['rows'] and cand['rows'][0]['board'] == 'arduino-uno-r3' and cand['rows'][0]['meets_criteria'] == 'yes'
          and prun['rows'] and all(r['reason'] for r in prun['rows']) and scalar, s0)
    B.post_door(None, 'wb-test', 'create', {'name': 'wb-test'})
    B.post_door(None, 'wb-test', 'attempt', {'mission': 'uno-light-mission'})
    check('wb-2 ATTEMPTS: an empty bench stores verdict none (its own row, home-bench untouched)',
          B.get_door(None, {}, 'attempts', 'wb-test')[1]['rows'][0]['verdict'] == 'none' and B.get_door(None, {}, 'attempts', S.HOME_BENCH)[1]['rows'][0]['verdict'] == 'meets', '')


def main():
    fails = []

    def check(label, cond, extra=''):
        print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, '' if cond else '  <- %r' % (extra,)))
        if not cond:
            fails.append(label)
    run_bench_setup(check)
    run_wb0(check)
    run_wb2(check)
    print('bench setup selftest: %d failure(s)' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
