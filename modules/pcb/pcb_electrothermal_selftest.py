"""pcb_electrothermal_selftest - tmp-3 / tmp-4 / tmp-5 (AI-Notes/plans/TEMPERATURE_PLAN.md; the user's words 2026-10-31: "Build it starting with whole
temperagure ... then part level, and so on"). The circuit heating itself (the Foster -> Cauer ladder, the ladder solved with the board, each part's
power from the run, the settle-or-run-away loop), timing at a temperature (a clock's bound, a UART link, logic delays) and cited datasheet curves
for parts no SPICE model carries.
References (custom/reference/kicad10_electrothermal.json): libngspice runs (KiCad 10.0.6 on econ-core, 2026-11-01) of every deck the loop wrote -
the kicad-demos rectifier with D1's CITED Rth j-a (Vishay 1N4148), two SYNTHETIC transistor stages (ngspice's default NPN, a synthetic 200 K/W), the
Cauer ladder of a synthetic Foster network run as an RC circuit, and the rectifier with C1 at an X7R's low corner. The recorded runner hands back
the run recorded for exactly the deck it is given and refuses any other, so the loop replays here on a host without libngspice.
Run by pcb_selftest.main().
"""
import contextlib
import json
import os
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'custom', 'reference', 'kicad10_electrothermal.json')
SIM = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'simulation')


def _recorded():
    ref = json.load(open(REF))['runs']
    by_deck = {r['deck']: r for r in ref.values()}

    def run(deck, files=None):
        r = by_deck.get(deck)
        if r is None:
            return {'ok': False, 'refused': 'no recorded run for this deck (the recorded runner only replays decks run on econ-core)'}
        return {'ok': r['ok'], 'plot': r['plot'], 'vectors': r['vectors'], 'errors': r['errors'], 'library': 'recorded: libngspice, KiCad 10.0.6, econ-core'}
    return run, by_deck


def _fresh():
    from pcb.custom import spice_runs as SR
    from pcb.custom import temperature_inputs as TI
    from pcb.custom import thermal_inputs as THI
    from pcb.custom import temperature_curves as TC
    from pcb.custom import electrothermal as ET
    for mem in (SR._MEM, TI._MEM, THI._MEM, TC._MEM):
        for t in mem.values():
            t.clear()
    ET._LAST.clear()


def _rect():
    from pcb.custom import kicad_read as K
    return K.read_project(K.read_dir(os.path.join(SIM, 'rectifier')), 'rectifier')


def _cited_1n4148():
    from pcb.custom import thermal_inputs as THI
    from pcb.custom.electrothermal_fixtures import VISHAY_1N4148
    THI._save(None, 'PartThermalModel', '1N4148', dict(VISHAY_1N4148, board='', part_key='1N4148', origin='cited'))


def run_cauer(check):
    import numpy as np
    from materialsScience.engines.thermal_cauer import foster_to_cauer, cauer_zth
    from materialsScience.engines.thermal_rc import zth
    from pcb.custom.electrothermal_fixtures import cauer_deck, CAUER_CHECK, CAUER_TIMES
    nets = ([[2.0, 0.01]], CAUER_CHECK, [[0.05, 1e-6], [0.4, 1e-3], [1.0, 0.1], [2.5, 10.0], [6.0, 300.0]])
    worst, sums = 0.0, []
    for st in nets:
        lad, _ = foster_to_cauer(st)
        worst = max([worst] + [abs(cauer_zth(lad, t) / zth(st, t) - 1) for t in (1e-7, 1e-5, 1e-3, 0.1, 1, 10, 1e3, 1e5)])
        sums.append(abs(sum(r for r, _ in lad) - sum(r for r, _ in st)))
    one, _ = foster_to_cauer([[2.0, 0.01]])
    bad = [foster_to_cauer(x)[1] for x in ([[1.0, 0.1], [2.0, 0.1]], [[0.0, 1.0]])]
    check('TMP-3 FOSTER -> CAUER, exact: the continued-fraction expansion in rational arithmetic gives a ladder whose step response (an independent '
          'eigen-solution) is the datasheet\'s Zth(t) to 1e-12 for 1, 3 and 5 stages from 1e-7 s to 1e5 s, with the same steady Rth; one stage is R = R, '
          'C = tau / R; two stages sharing a tau, or none with R > 0, are refused in words',
          worst < 1e-12 and max(sums) < 1e-12 and abs(one[0][0] - 2.0) < 1e-15 and abs(one[0][1] - 0.005) < 1e-15 and 'share one tau' in bad[0]
          and 'no stage' in bad[1], (worst, sums, one, bad))
    run, by_deck = _recorded()
    r = by_deck.get(cauer_deck(foster_to_cauer(CAUER_CHECK)[0]))
    t, v = r['vectors']['time']['real'], r['vectors']['n1']['real']
    err = [abs(float(np.interp(x, t, v)) / zth(CAUER_CHECK, x) - 1) for x in CAUER_TIMES if x >= 1e-3]
    check('TMP-3 THE LADDER IN NGSPICE (recorded on econ-core): the Cauer ladder as an RC circuit (K/W = ohm, J/K = F), a 1 A step into its first node '
          '- the node voltage is the Foster Zth(t) within 1e-4 from 1 ms to 10 s (an established solver, not our eigen-solution)',
          r is not None and max(err) < 1e-4, err)


def run_coupled(check):
    from materialsScience.engines.fem_plate_transient import solve_plate_transient_2d as S
    from materialsScience.engines.thermal_cauer import foster_to_cauer
    from materialsScience.engines.thermal_rc import junction_trajectory, rth
    st = [[2.0, 0.01], [8.0, 1.0], [15.0, 20.0]]
    lad, _ = foster_to_cauer(st)
    src = [{'name': 'U1', 'power_w': 0.5, 'x0': 0.02, 'y0': 0.02, 'x1': 0.03, 'y1': 0.03}]
    args = (0.05, 0.05, 0.81 * 1.5e-3, 1850 * 760 * 1.5e-3, 10.0, 3000.0)
    a = S(*args, sources=src, refine=4)
    b = S(*args, sources=src, refine=4, ladders={'U1': lad})
    sa, sb = a['sources'][0], b['sources'][0]
    f = [x + z for x, z in zip(sa['meanRise'], junction_trajectory(st, a['times'], a['powers']['U1']))]
    k = next(i for i, x in enumerate(a['times']) if x > 10)
    bad = S(*args, sources=src, refine=4, ladders={'U1': [[1.0, 0.0]]})
    check('TMP-3 THE LADDER SOLVED WITH THE BOARD (a synthetic 3-stage part, 0.5 W on a 50 mm plate): one linear system, energy balances to 1e-12 '
          '(the ladder\'s stored heat counted); at the end both forms give the same junction (1e-4: board + P x Rth); early on the plate under the part '
          'is COOLER with the ladder - it gets the heat only as fast as the part lets it out (Foster puts all 0.5 W into the board at once) - and the '
          'heat into the plate climbs to the full 0.5 W; a ladder stage with no capacity is refused',
          b['ok'] and b['balanceError'] < 1e-12 and b['ladderDofs'] == 3 and abs(sb['junctionRise'][-1] / f[-1] - 1) < 1e-4
          and abs(f[-1] - sa['meanRise'][-1] - 0.5 * rth(st)) < 1e-9 and sb['meanRise'][k] < 0.5 * sa['meanRise'][k]
          and abs(sb['heatToPlate'][-1] - 0.5) < 1e-3 and not bad['ok'] and 'C > 0' in bad['error'],
          (b.get('balanceError'), sb['junctionRise'][-1], f[-1], sb['meanRise'][k], sa['meanRise'][k], sb['heatToPlate'][-1]))


def run_device_power(check):
    from pcb.custom import kicad_spice as P
    from pcb.custom import spice_runs as SR
    from pcb.custom import thermal as TH
    from pcb.custom.electrothermal_fixtures import bjt_rows
    _fresh()
    rows = bjt_rows(0)
    d = P.build_deck(rows, save_power=True)
    plain = P.build_deck(rows)
    run, _ = _recorded()
    d25 = P.build_deck(rows, temp_c=25.0, save_power=True)
    SR.store(None, 'bjt-fixed', d25['deck'], run(d25['deck']), 'recorded', 'econ-core')
    parts, why = TH.dissipation(None, 'bjt-fixed', rows=rows)
    q = next(p for p in parts if p['ref'] == 'Q1')
    vs = {v['vector']: json.loads(v['values_json']) for v in SR._table(None, 'SpiceVector')}
    vi = -vs['v1#branch'][-1] * 10.0 + -vs['v2#branch'][-1] * vs['base'][-1]
    check('TMP-3 EACH PART\'S OWN POWER FROM THE RUN: with save_power the deck keeps the device vectors (".save all @q1[p]"; without it the deck is '
          'unchanged); the transistor\'s ngspice power equals V_CE x I_C + V_BE x I_B from the run\'s own source currents (1e-9), and the unit is W',
          '.save all @q1[p]' in d['deck'] and '.save' not in plain['deck'] and not why and abs(q['avg_w'] - vi) < 1e-9 * vi
          and 'own device power' in q['basis'] and SR.unit_of('@q1[p]') == 'W' and SR.unit_of('@d1[id]') == 'A', (q, vi))
    _fresh()
    rect = _rect()
    dr = P.build_deck(rect, temp_c=25.0, save_power=True)
    SR.store(None, 'rectifier', dr['deck'], run(dr['deck']), 'recorded', 'econ-core')
    parts, why = TH.dissipation(None, 'rectifier', rows=rect)
    d1 = next(p for p in parts if p['ref'] == 'D1')
    proj, _ = SR.projection(None, 'rectifier')
    check('TMP-3 A DIODE\'S POWER = (Va - Vk) x its own current @d1[id] - its @d1[p] reads inf in KiCad 10\'s libngspice (probed), said; the device '
          'vectors are not nets (the projection leaves them out)',
          '.save all @d1[id]' in dr['deck'] and d1['avg_w'] > 0 and 'reads inf' in d1['basis'] and not any(p['net'].startswith('@') for p in proj), d1)
    _fresh()


def run_self_heating(check):
    from pcb.custom import electrothermal as ET
    from pcb.custom import thermal_inputs as THI
    from pcb.custom.electrothermal_fixtures import bjt_rows, RTH_SYNTHETIC
    _fresh()
    run, _ = _recorded()
    _cited_1n4148()
    rect = ET.settle(None, 'rectifier', 25.0, runner=run, rows=_rect())
    THI.set_quantity(None, 'bjt-fixed', 'Q1', 'rth_ja_k_w', RTH_SYNTHETIC)
    THI.set_quantity(None, 'bjt-re', 'Q1', 'rth_ja_k_w', RTH_SYNTHETIC)
    fixed = ET.settle(None, 'bjt-fixed', 25.0, runner=run, rows=bjt_rows(0))
    re = ET.settle(None, 'bjt-re', 25.0, runner=run, rows=bjt_rows(100))
    d1 = rect['rows'][0]
    check('TMP-3 THE RECTIFIER SETTLES at once: D1 takes microwatts, x the CITED 350 K/W (Vishay 1N4148, Doc 81857 Rev. 1.6: on the datasheet\'s own '
          'test board - the demo has no layout, said) = a few mK; the first pass already moves less than the 0.05 K tolerance',
          rect['verdict'] == 'settled' and rect['passes'] == 1 and 0 < d1['temp_c'] - 25 < 0.05 and abs(d1['temp_c'] - 25 - 350 * d1['power_w']) < 1e-9
          and 'datasheet Rth j-a 350' in d1['basis'] and 'no layout' in rect['basis'], (rect['verdict'], d1))
    last = [r for r in re['rows'] if r['pass'] == re['passes']][0]
    check('TMP-3 THE TEXTBOOK PAIR (ngspice\'s default NPN, synthetic 200 K/W, ~10 mA at 25 C either way): held at a fixed V_BE it RUNS AWAY - every '
          'pass hotter by more than the last, the loop gain above 1; with a 100 ohm emitter resistor it SETTLES (gain ~0.02) at the temperature its own '
          'power gives: T = 25 + 200 K/W x P(T) within the tolerance',
          fixed['verdict'] == 'runaway' and fixed['loop_gain'] > 1 and fixed['changes_c'][-1] > fixed['changes_c'][-2] > fixed['changes_c'][-3]
          and re['verdict'] == 'settled' and 0 < re['loop_gain'] < 0.1 and abs(last['temp_c'] - 25 - RTH_SYNTHETIC * last['power_w']) < 1e-9
          and abs(last['temp_c'] - last['ran_at_c']) < ET.TOL_C and 40 < last['temp_c'] < 46 and ET.last('bjt-re') is re,
          (fixed['verdict'], fixed['changes_c'], re['verdict'], re['loop_gain'], last))
    nothing = ET.settle(None, 'bjt-re', 25.0, runner=lambda deck, files=None: {'ok': False, 'refused': 'no solver'}, rows=bjt_rows(100))
    bad = ET.settle(None, 'bjt-re', 25.0, runner=run, rows=bjt_rows(100), relax=0)
    none = ET.settle(None, 'nowhere', 25.0, rows={'SchematicSymbol': []})
    THI._MEM['PartThermalModel'].clear()
    cold = ET.settle(None, 'bjt-re', 25.0, runner=run, rows=bjt_rows(100))
    check('TMP-3 THE LOOP SAYS WHY IT STOPPED: no solver -> stopped (in words); relax 0 -> 400; no schematic -> 404; no layout and no datasheet Rth '
          '-> nothing heats (give one)',
          nothing['verdict'] == 'stopped' and 'no solver' in nothing['why'] and bad['status'] == 400 and none['status'] == 404
          and cold['verdict'] == 'nothing heats' and 'Rth j-a' in cold['why'], (nothing.get('why'), bad, none, cold.get('why')))
    _fresh()


def run_curves(check):
    from pcb.custom import kicad_spice as P
    from pcb.custom import temperature_curves as TC
    _fresh()
    cat = {c['name']: c for c in TC.catalogue(None)}
    sq, tl, x7r, c0g = cat['sq2310es-rds-on'], cat['tlcy5200-vf'], cat['x7r'], cat['c0g']
    v = {t: TC.value_at(sq, t) for t in (25, 75, 125, 175, 200, 0)}
    check('TMP-5 A TABLE\'S ROWS, NOTHING PAST THEM (Vishay SQ2310ES R_DS(on) max, S21-1074 Rev. C): 0.030 / 0.045 / 0.054 ohm at 25 / 125 / 175 C '
          'exactly, a straight line between (75 C: 0.0375), and 200 C or 0 C refused - not extrapolated',
          v[25]['value'] == 0.030 and v[125]['value'] == 0.045 and v[175]['value'] == 0.054 and abs(v[75]['value'] - 0.0375) < 1e-12
          and not v[200]['inside'] and not v[0]['inside'] and 'not extrapolated' in v[200]['words'] and 'table\'s own row' in v[125]['words'], v)
    l100, lout = TC.value_at(tl, 100), TC.value_at(tl, 101)
    b = TC.value_at(x7r, 85)
    c = TC.value_at(c0g, 125)
    check('TMP-5 ONE STATED COEFFICIENT, A BOUND: the TLCY5200\'s V_F 2.1 V - 3.5 mV/K (Doc 81354 Rev. 1.6) is 1.8375 V at 100 C and refused past its '
          '-40 .. 100 C range; X7R is a +-15 % bound (0.85 / 1.15 corners) and C0G +-30 ppm/K x 100 K = +-0.3 % at 125 C',
          abs(l100['value'] - 1.8375) < 1e-12 and not lout['inside'] and abs(b['low'] - 0.85) < 1e-12 and abs(b['high'] - 1.15) < 1e-12
          and abs(c['low'] - 0.997) < 1e-12 and abs(c['high'] - 1.003) < 1e-12 and 'straight line' in l100['words'], (l100, b, c))
    rect = _rect()
    st, body = TC.bind(None, 'rectifier', 'C1', 'x7r')
    miss = TC.bind(None, 'rectifier', 'C1', 'unobtainium')
    vals, notes = TC.deck_values(None, 'rectifier', 85.0, 'low', rows=rect)
    deck = P.build_deck(rect, temp_c=85.0, values=vals)
    rows = TC.at_temperatures(None, 'rectifier', [-40.0, 85.0, 150.0], rows=rect)
    check('TMP-5 GIVEN TO A PART AND PUT IN THE CIRCUIT: C1 (100n) takes the X7R curve (POST; an unknown curve 404); at 85 C its low corner writes '
          'C1 = 85n into the deck; at 150 C the class says nothing (outside -55 .. 125 C: inside no) and the deck leaves C1 alone',
          st == 200 and miss[0] == 404 and vals['C1'][0] == '8.5e-08' and 'C1 /rect_out GND 8.5e-08' in deck['deck']
          and deck['temperature']['curves']['C1'].startswith('low corner') and [r['inside'] for r in rows] == ['yes', 'yes', 'no']
          and rows[0]['in_deck'].startswith('nominal x the corner') and TC.deck_values(None, 'rectifier', 150.0, 'low', rows=rect)[0] == {},
          (body, vals, rows[:1]))
    run, _ = _recorded()
    res = TC.run_at(None, 'rectifier', 85.0, 'low', runner=run, rows=rect)
    corner = TC.run_at(None, 'rectifier', 85.0, 'sideways', rows=rect)
    gone = TC.unbind(None, 'rectifier', 'C1', 'capacitance')
    check('TMP-5 THE RUN WITH THE CURVE (recorded on econ-core): the rectifier at 85 C with C1 at its X7R low corner runs and is kept, saying the value '
          'it used; an unknown corner is refused (400); DELETE takes the curve away again',
          res['ok'] and res['corner'] == 'low' and 'x 0.85' in res['curve_values']['C1'] and corner['status'] == 400 and gone[0] == 200
          and TC.bound(None, 'rectifier', rect) == {}, (res.get('curve_values'), corner, gone))
    _fresh()


def run_timing(check):
    from board.custom import timing_drift as T
    derived = {k: T.ubrr(16e6, *k) for k in T.TABLE_16MHZ}
    check('TMP-4 THE BAUD DIVISOR FROM THE CHIP\'S OWN EQUATIONS (ATmega328P Table 20-1) = its printed Table 20-7 at 16 MHz: 9600 -> UBRR 103 / 207, '
          '0.2 %; 115.2k -> UBRR 8, -3.5 % and UBRR 16, +2.1 % (to the table\'s one decimal)',
          all(derived[k][0] == n and round(derived[k][1], 1) == e for k, (n, e) in T.TABLE_16MHZ.items()), derived)
    rows = {(r['baud'], r['u2x'], r['temp_c']): r for r in T.uart_rows()}
    check('TMP-4 A UART LINK AT TEMPERATURE (the UNO\'s CSTCE16M0V53-R0: +-0.5 % initial + 0.3 % over -20 .. 80 C + 0.2 % aging, bounds): 9600 fits the '
          'recommended share anywhere in the range; 115.2k with U2X is inside the receiver\'s window (+3.12 % worst against +3.90) but beyond the '
          'recommended +-1.5 %; at 85 C or -40 C the resonator is unrated - said, not guessed',
          rows[(9600, 1, 25.0)]['verdict'] == 'fits the recommended share' and rows[(115200, 1, 25.0)]['verdict'].startswith('inside the receiver')
          and abs(rows[(115200, 1, 25.0)]['worst_high_pct'] - 3.124) < 1e-3 and rows[(115200, 1, 85.0)]['verdict'] == 'unrated'
          and rows[(9600, 0, -40.0)]['verdict'] == 'unrated' and '-4.54' in rows[(9600, 0, 25.0)]['window_pct'],
          [(k, r['verdict']) for k, r in rows.items() if k[2] == 25.0])
    rc = {r['temp_c']: r for r in T.uart_rows(temps=(25.0, 50.0), bauds=(115200,), clock='atmega328p-rc-factory')}
    lvc = {r['temp_c']: r for r in T.delay_rows('sn74lvc245a-n', (25.0, 50.0, 100.0, 130.0))}
    ahct = {r['temp_c']: r for r in T.delay_rows('sn74ahct125-n', (25.0, 100.0))}
    check('TMP-4 THE RC OSCILLATOR AS SHIPPED is rated only at 25 C (+-10 %); LOGIC IS SLOWER HOT - SN74LVC245A max t_pd 6.1 ns at 25 C, 6.3 ns in the '
          '-40 .. 85 C column, 7.3 ns in the -40 .. 125 C column, unrated at 130 C; the SN74AHCT125 has no column past 85 C',
          rc[50.0]['verdict'] == 'unrated' and rc[25.0]['verdict'].startswith('OUTSIDE') and [lvc[t]['max_ns'] for t in (25.0, 50.0, 100.0, 130.0)]
          == [6.1, 6.3, 7.3, -1.0] and ahct[100.0]['max_ns'] == -1.0 and ahct[25.0]['max_ns'] == 5.5, (rc, lvc, ahct))


def run_doors_and_page(check):
    import falcon
    import falcon.testing as ft
    from pcb.pcb_temperature_api import PcbTemperatureAPI
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        PcbTemperatureAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    none = cl.simulate_get('/api/pcb/demo/self-heating')
    nos = cl.simulate_post('/api/pcb/demo/self-heating', json={'ambient_c': 25})
    badh = cl.simulate_post('/api/pcb/demo/self-heating', json={'ambient_c': 25, 'max_passes': 'many'})
    cat = cl.simulate_get('/api/pcb/temperature-curves')
    bind = cl.simulate_post('/api/pcb/demo/temperature-curves/C1', json={'from': 'x7r'})
    nob = cl.simulate_post('/api/pcb/demo/temperature-curves/C1', json={})
    unb = cl.simulate_delete('/api/pcb/demo/temperature-curves/C1/capacitance')
    badc = cl.simulate_post('/api/pcb/demo/simulate-curves', json={'temp_c': 'hot'})
    check('TMP-3/5 THE DOORS: GET self-heating before a loop 404s in words, POST on a board with no schematic 404s, a non-number 400s; the curve catalogue '
          'lists the five cited curves; POST gives a part a curve (a missing "from" 400s), DELETE takes it away; simulate-curves refuses a non-number',
          none.status_code == 404 and nos.status_code == 404 and badh.status_code == 400 and cat.status_code == 200 and len(cat.json['rows']) == 5
          and bind.status_code == 200 and nob.status_code == 400 and unb.status_code == 200 and badc.status_code == 400,
          [x.status_code for x in (none, nos, badh, cat, bind, nob, unb, badc)])
    page = BOARD_DETAILS_PAGES[0]['definition']
    uno = BD.part('datasheet', 'arduino-uno-r3', 'timing-uart', None, {})
    other = BD.part('datasheet', 'esp32-c3', 'timing-clocks', None, {})
    lvc = BD.part('datasheet', 'sn74lvc245a-n', 'logic-delays', None, {'temps': '25,100'})
    sh = BD.part('layers', 'demo', 'self-heat-run', None)[0]
    check('TMP-3/4/5 THE PAGE: Self-heating (run the loop at a typed background; each pass), Temperature curves (the cited catalogue, give one to a part, '
          'each curve at the simulated temperatures, run with them) and Timing at temperature (the clock, a UART link, logic delays) tabs; the Board '
          'Details door gives the UNO its UART rows, the C3 a reason (no cited clock yet), the LVC245A its delays at the asked temperatures',
          all(x in page for x in ('"self-heating"', '"temperature-curves"', '"timing"', '/api/pcb/{board}/self-heating', '/api/pcb/{board}/simulate-curves',
                                  '{scope:tcurve}')) and uno[0] and uno[0][0]['clock'] == 'cstce16m0v53-r0' and other[0] == []
          and 'no cited clock' in other[1] and [r['max_ns'] for r in lvc[0]] == [6.1, 7.3] and sh[0]['verdict'] == 'not run', (other, lvc, sh))
    _fresh()
