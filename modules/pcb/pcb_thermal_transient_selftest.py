"""pcb_thermal_transient_selftest - bob-3g (BENCH_BOARDS_PLAN bob-3; the user's words 2026-10-31: "some components are black boxes and we need the capability to
run simulations based on their data sheets specified thermal behavior over time"). The transient plate FEM (materialsScience.engines.fem_plate_transient)
and the datasheet Foster network (materialsScience.engines.thermal_rc) checked against the answers they must reproduce exactly, then the inputs a person
gives (PartPowerInput / PartThermalModel, in memory), the board over time on a real board's rows (kicad-demos 9.0.2 ecc83), the doors and the page.
The Foster numbers below are SYNTHETIC test values (no real part is named or implied). Run by pcb_selftest.main().
"""
import contextlib
import json
import math
import os
import types

from pcb.pcb_thermal_spread_selftest import DEMOS

#: synthetic two-stage network for the checks - not any real part's datasheet
STAGES = [[20.0, 2.0], [40.0, 30.0]]


def run_transient_engine(check):
    from materialsScience.engines.fem_plate_transient import solve_plate_transient_2d as T
    from materialsScience.engines.fem_plate_thermal import solve_plate_conduction_2d as S
    W, H, K, C, h = 0.05, 0.04, 0.81 * 1.6e-3, 1850 * 760 * 1.6e-3, 10.0
    o = T(W, H, K, C, h, 600, sources=[{'name': 'all', 'power_w': 0.5, 'x0': 0, 'y0': 0, 'x1': W, 'y1': H}])
    q, th = 0.5 / (W * H), 0.0
    for a, b in zip(o['times'], o['times'][1:]):
        th = (C / (b - a) * th + q) / (C / (b - a) + 2 * h)   # backward Euler on the lumped plate, step for step
    exact = q / (2 * h) * (1 - math.exp(-600 * 2 * h / C))
    fem = o['sources'][0]['meanRise'][-1]
    check('TRANSIENT PLATE = BACKWARD EULER EXACTLY: heat put in everywhere leaves no gradient, so the FEM must equal the lumped recurrence '
          '(C/dt + 2h) T_n = C/dt T_n-1 + q step for step (1e-9), and the continuous answer q/2h (1 - e^(-2ht/C)) within 1% (first order in dt)',
          abs(fem - th) < 1e-9 * th and abs(fem / exact - 1) < 0.01, (fem, th, exact))
    src = {'name': 'R', 'power_w': 0.3, 'x0': 0.02, 'y0': 0.018, 'x1': 0.024, 'y1': 0.022}
    late, st = T(W, H, K, C, h, 20000, sources=[src]), S(W, H, K, h, sources=[src])
    check('TRANSIENT PLATE settles onto the STEADY solve (a source left on for 180 plate time constants: same peak to 1e-6) and conserves energy '
          '(in = stored + lost through the faces, to 1e-9)', abs(late['maxRise'][-1] / st['maxRise'] - 1) < 1e-6 and late['balanceError'] < 1e-9
          and abs(late['steadyMaxRise'] - st['maxRise']) < 1e-9 * st['maxRise'], (late['maxRise'][-1], st['maxRise'], late['balanceError']))
    p = T(W, H, K, C, h, 300, sources=[dict(src, on_s=10, period_s=40)])
    check('TRANSIENT PLATE, duty cycle: on 10 s every 40 s for 300 s puts in exactly 0.3 W x 10 s x 8 pulses = 24 J, every switch is a step boundary, '
          'the step lengths repeat (few factorisations) and energy still balances', abs(p['inputJ'] - 24.0) < 1e-9 and p['balanceError'] < 1e-9
          and p['factorisations'] < 20 and all(any(abs(t - s) < 1e-9 for t in p['times']) for s in (10, 40, 50, 290)), (p['inputJ'], p['factorisations']))
    check('TRANSIENT PLATE REFUSES in words: no heat capacity, no run length, a period with no on time',
          'heat capacity' in T(W, H, K, 0, h, 10)['error'] and 't_end' in T(W, H, K, C, h, 0)['error']
          and 'on time' in T(W, H, K, C, h, 10, sources=[dict(src, period_s=5)])['error'])


def run_foster(check):
    from materialsScience.engines.thermal_rc import junction_trajectory, zth, rth, check_stages
    times = [0.0] + [0.01 * 1.5 ** k for k in range(40)]
    on = junction_trajectory(STAGES, times, [0.0] + [0.5] * 40)
    check('FOSTER NETWORK = THE DATASHEET CURVE EXACTLY: a constant power P gives P x Zth(t), Zth = sum R_i (1 - e^(-t/tau_i)), at every time (1e-12) '
          'however uneven the steps - each stage is solved in closed form, so short time constants cost nothing',
          max(abs(z - 0.5 * zth(STAGES, t)) for z, t in zip(on, times)) < 1e-12 and abs(rth(STAGES) - 60.0) < 1e-12)
    grid = [0.1 * k for k in range(1001)]
    pulse = junction_trajectory(STAGES, grid, [0.0] + [0.5 if t <= 10 + 1e-9 else 0.0 for t in grid[1:]])
    sup = [0.5 * (zth(STAGES, t) - zth(STAGES, t - 10)) for t in grid if t > 10.05]
    check('FOSTER NETWORK, a 10 s pulse: after it ends the rise is P (Zth(t) - Zth(t - 10 s)) - superposition, the way a datasheet\'s single-pulse '
          'curve is read', max(abs(a - b) for a, b in zip([z for z, t in zip(pulse, grid) if t > 10.05], sup)) < 1e-12)
    check('FOSTER NETWORK REFUSES in words: a negative R, a zero tau, not a pair',
          'R >= 0' in check_stages([[-1, 1]]) and 'tau > 0' in check_stages([[1, 0]]) and 'not a pair' in check_stages([[1]]) and check_stages(STAGES) == '')


def _fresh():
    from pcb.custom import thermal_inputs as TI
    for t in TI._MEM.values():
        t.clear()
    return TI


def run_inputs(check):
    from pcb.custom import kicad_read as K
    TI = _fresh()
    rows = K.read_project(K.read_dir(os.path.join(DEMOS, 'ecc83')), 'ecc83')
    before = {r['ref']: r for r in TI.parts(None, 'ecc83', rows)}
    for q, v in (('power_w', 0.5), ('r1_k_w', 20), ('tau1_s', 2), ('r2_k_w', 40), ('tau2_s', 30), ('tj_max_c', 155), ('rth_ja_k_w', 200)):
        TI.set_quantity(None, 'ecc83', 'R4', q, v)
    after = {r['ref']: r for r in TI.parts(None, 'ecc83', rows)}
    qs = {r['quantity']: r for r in TI.quantities(None, 'ecc83', 'R4')}
    check('GIVEN POWER + DATASHEET MODEL per placed part (PartPowerInput / PartThermalModel): ecc83 has no run, so nothing is heated until a person '
          'gives R4 0.5 W - then R4 is used at 0.5 W "given"; its Foster stages are kept in order ([[20, 2], [40, 30]]), Rth j-board = 60 K/W, Tj max 155',
          before['R4']['used_w'] == 0.0 and 'not heated' in before['R4']['used_from'] and after['R4']['used_w'] == 0.5
          and after['R4']['used_from'].startswith('given') and json.loads(TI._MEM['PartThermalModel']['ecc83:R4']['foster_json']) == STAGES
          and after['R4']['rth_j_board_k_w'] == 60.0 and after['R4']['tj_max_c'] == 155.0 and len(qs) == 5 + 2 * TI.STAGES and qs['r3_k_w']['given'] is False,
          after.get('R4'))
    bad = [TI.set_quantity(None, 'ecc83', 'R4', 'power_w', -1)[0], TI.set_quantity(None, 'ecc83', 'R4', 'volts', 1)[0], TI.set_quantity(None, 'ecc83', 'R4', 'on_s', 'x')[0]]
    TI.clear_quantity(None, 'ecc83', 'R4', 'r2_k_w')
    TI.clear_quantity(None, 'ecc83', 'R4', 'power_w')
    cleared = {r['ref']: r for r in TI.parts(None, 'ecc83', rows)}['R4']
    check('INPUTS REFUSE in words (a negative number, an unknown quantity, text: 400) and CLEAR back to not given (power -1: the part is not heated '
          'again; a stage\'s R 0: that stage adds nothing - Rth j-board falls to 20 K/W)',
          bad == [400, 400, 400] and cleared['given_w'] == -1.0 and cleared['used_w'] == 0.0 and cleared['rth_j_board_k_w'] == 20.0, (bad, cleared))
    TI.set_quantity(None, 'ecc83', 'R4', 'r2_k_w', 40)
    TI._save(None, 'PartThermalModel', 'ECC83', {'board': '', 'ref': '', 'part_key': 'ECC83', 'foster_json': '[[5, 1]]'})
    TI._save(None, 'PartThermalModel', '47K', {'board': '', 'ref': '', 'part_key': '47K', 'foster_json': '[[7, 1]]'})
    shared = TI.models(None, 'ecc83', rows)
    check('A DATASHEET MODEL SHARED BY PART: a board-free row keyed by the symbol value (ECC83, the tube - a black box) applies to every placed part '
          'with that value (U1); the part\'s own row wins where it has one (R4 keeps its 60 K/W over a 47K row)',
          shared['U1']['name'] == 'ECC83' and shared['U1']['rth'] == 5.0 and shared['R4']['rth'] == 60.0 and set(shared) == {'R4', 'U1'}, sorted(shared))


def run_board_over_time(check):
    from pcb.custom import kicad_read as K
    from pcb.custom import thermal_spread as TS
    from pcb.custom import thermal_transient as TT
    TI = _fresh()
    rows = K.read_project(K.read_dir(os.path.join(DEMOS, 'ecc83')), 'ecc83')
    for q, v in (('power_w', 0.5), ('r1_k_w', 20), ('tau1_s', 2), ('r2_k_w', 40), ('tau2_s', 30), ('tj_max_c', 155), ('rth_ja_k_w', 200)):
        TI.set_quantity(None, 'ecc83', 'R4', q, v)
    s, j, chart, why = TT.transient(None, 'ecc83', rows=rows)
    st, hot, _, _ = TS.spread(None, 'ecc83', rows=rows, refine=10)
    r4, h4 = j[0], hot[0]
    series = {c['series'] for c in chart}
    check('THE BOARD OVER TIME (ecc83, R4 0.5 W given, always on, a synthetic 2-stage datasheet model): the run lasts 5 plate time constants and ends '
          'within 1% of the steady solve (board under R4 and the junction), energy balances (1e-9), the junction ends at the board + P x 60 K/W, Tj at '
          'a 25 C room is read against Tj max, and the chart carries the hottest point, the board under R4 and R4\'s junction',
          not why and abs(s['t_end_s'] / s['plate_time_constant_s'] - 5) < 0.5 and abs(r4['board_peak_rise_c'] / h4['mean_rise_c'] - 1) < 0.01
          and abs(r4['junction_peak_rise_c'] / h4['junction_rise_c'] - 1) < 0.01 and s['balance_error'] < 1e-9
          and abs(h4['junction_rise_c'] - h4['mean_rise_c'] - 30.0) < 1e-9 and abs(r4['tj_peak_c'] - 25 - r4['junction_peak_rise_c']) < 1e-9
          and abs(r4['margin_c'] - (155 - r4['tj_peak_c'])) < 1e-9 and r4['datasheet_ja_rise_c'] == 100.0
          and series == {'board, hottest point', 'R4: board under it', 'R4: junction'}, (s.get('t_end_s'), r4, h4))
    TI.set_quantity(None, 'ecc83', 'R4', 'on_s', 60)
    p, pj, _, _ = TT.transient(None, 'ecc83', rows=rows)
    st2, _, _, _ = TS.spread(None, 'ecc83', rows=rows, refine=10)
    check('A SINGLE 60 s PULSE: the hottest moment is the end of the pulse (peak at 60 s), the board has nearly cooled by the end of the run, the '
          'junction peaks above the board under it, and the steady view says a single pulse leaves nothing there (see Thermal over time)',
          abs(p['peak_at_s'] - 60) < 1e-9 and p['final_max_rise_c'] < 0.05 * p['peak_rise_c'] and pj[0]['junction_peak_rise_c'] > pj[0]['board_peak_rise_c']
          and 'single pulse' in st2['basis'] and st2['max_rise_c'] == -1.0, (p['peak_at_s'], p['final_max_rise_c'], st2['basis'][-160:]))
    TI.set_quantity(None, 'ecc83', 'R4', 'period_s', 240)
    st3, hot3, _, _ = TS.spread(None, 'ecc83', rows=rows, refine=10)
    check('A DUTY CYCLE in the steady view counts at its average: on 60 s every 240 s -> R4 heats the board with 0.5 x 60/240 = 0.125 W',
          abs(hot3[0]['power_w'] - 0.125) < 1e-12, hot3[0]['power_w'] if hot3 else st3)
    _fresh()


def run_doors(check):
    import falcon
    import falcon.testing as ft
    from pcb.pcb_thermal_api import PcbThermalAPI
    from board.pin_view_api import PinViewAPI
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES, SEED_BOARD_DETAILS_GRAPHS, TRANSIENT_GRAPH
    _fresh()
    app = falcon.App()
    srv = types.SimpleNamespace(falconServer=app)
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        PcbThermalAPI(polServer=srv, manager=None)
        PinViewAPI(polServer=srv, manager=None)
    cl = ft.TestClient(app)
    put = cl.simulate_put('/api/pcb/demo/thermal-inputs/U1/power_w', json={'value': 1.5})
    neg = cl.simulate_put('/api/pcb/demo/thermal-inputs/U1/power_w', json={'value': -2})
    got = {r['quantity']: r for r in cl.simulate_get('/api/pcb/demo/thermal-inputs/U1').json['rows']}
    dele = cl.simulate_delete('/api/pcb/demo/thermal-inputs/U1/power_w')
    model = cl.simulate_post('/api/pcb/demo/thermal-models/U1', json={'foster': STAGES, 'tj_max_c': 150, 'document': 'a test document', 'page_table': 'Fig. 9'})
    refused = cl.simulate_post('/api/pcb/demo/thermal-models/U1', json={'foster': [[1, 0]]})
    via_details = BD.part('layers', 'demo', 'thermal-inputs', None, params={'ref': 'U1'})[0]
    check('THE DOORS: PUT gives a number (200) and refuses a negative one in words (400); GET lists every number for the part; DELETE clears it; POST '
          'keeps a whole datasheet model WITH its citation (201, origin cited) and refuses a stage with tau 0 (400); the Board Details door serves the '
          'same rows by ?ref=',
          put.status_code == 200 and neg.status_code == 400 and 'number >= 0' in neg.json['error'] and got['power_w']['value'] == 1.5
          and got['power_w']['given'] is True and dele.json['rows'][0]['value'] == -1.0 and model.status_code == 201
          and model.json['model']['origin'] == 'cited' and refused.status_code == 400 and 'tau > 0' in refused.json['error']
          and {r['quantity'] for r in via_details} == set(got), (put.status_code, neg.status_code, model.status_code, refused.json))
    tr = cl.simulate_get('/api/pcb/demo/thermal-transient')
    bad_h = cl.simulate_get('/api/pcb/demo/thermal-transient?h=0')
    pv = cl.simulate_get('/api/board/pcb%3Alayers%2Fdemo/pin-view')
    pv_dev = cl.simulate_get('/api/board/pcb%3Adatasheet%2Funo/pin-view')
    check('THE BOARD OVER TIME door says why in words when there is no board (404) and refuses a bad h (400); THE PIN VIEW takes the Board Details id '
          '(pcb:layers/<board> - the slash the page scope carries) and asks for the PCB itself (fixes bob-3f: the Thermal tab\'s drawing named '
          'pcb:layers/<board>, which no single path field can carry); a non-PCB definition is a 404 in words',
          tr.status_code == 404 and 'no PCB outline' in tr.json['error'] and bad_h.status_code == 400 and pv.status_code == 404
          and "'demo'" in pv.json['error'] and pv_dev.status_code == 404 and 'not a PCB' in pv_dev.json['error'], (tr.json, pv.json, pv_dev.json))
    page = json.dumps(BOARD_DETAILS_PAGES)
    graph = next(g for g in SEED_BOARD_DETAILS_GRAPHS if g['name'] == TRANSIENT_GRAPH)
    check('THE PAGE: a Thermal over time tab - the parts (click one), its numbers edited in place (PUT, Clear = DELETE), the board over time, each '
          'part over time and the chart (named graph pcb-thermal-transient, long form x / y / series); the thermal tables refresh after an edit',
          'thermal-time' in page and 'bd-thermal-inputs' in page and 'thermal-inputs/{ref}/{quantity}' in page and 'bd-junctions' in page
          and TRANSIENT_GRAPH in page and json.loads(graph['definition'])['graphConfig']['seriesDimension'] == 'series'
          and page.count('rev=r{scope:rev}') >= 9 and 'peaks read high' not in page)
    _fresh()
