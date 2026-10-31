"""pcb_spice_temperature_selftest - tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md; the user's words 2026-10-31: "Build it starting with whole
temperagure, since a background temperature being the basis is the norm anyways, then part level, and so on"). A PCB's circuit at a temperature: the deck
(the board's .temp, a part's own temp=, R / C / L coefficients), what responds, the inputs a person gives, a sweep and its comparison, the ratings, each
part at its own temperature from the board over time, the doors and the page.
References (custom/reference/kicad10_sim_<b>_temps.json): libngspice runs of OUR decks (KiCad 10.0.6 on econ-core, 2026-10-31) - the rectifier with the
board at -40 / 25 / 85 / 125 C and with D1 alone at 100 C on a 25 C board; the Sallen-Key filter at -40 / 25 / 85 C. The recorded runner below hands
back the run recorded for exactly the deck it is given (it refuses any other deck), so the sweep plumbing runs here on a host without libngspice.
Rated ranges and coefficients used below are SYNTHETIC test values (no real part's datasheet is named or implied). Run by pcb_selftest.main().
"""
import contextlib
import json
import os
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'simulation')
REF = os.path.join(HERE, 'custom', 'reference')
DEMOS = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2')


def _project(b):
    from pcb.custom import kicad_read as K
    return K.read_project(K.read_dir(os.path.join(DEMOS, 'ecc83') if b == 'ecc83' else os.path.join(SIM, b)), b)


def _recorded(board):
    ref = json.load(open(os.path.join(REF, 'kicad10_sim_%s_temps.json' % board)))['runs']
    by_deck = {r['deck']: r for r in ref.values()}

    def run(deck, files=None):
        r = by_deck.get(deck)
        if r is None:
            return {'ok': False, 'refused': 'no recorded run for this deck (the recorded runner only replays decks run on econ-core)'}
        return {'ok': True, 'plot': r['plot'], 'vectors': r['vectors'], 'library': 'recorded: libngspice, KiCad 10.0.6, econ-core'}
    return run, ref


def _fresh():
    from pcb.custom import spice_runs as SR
    from pcb.custom import temperature_inputs as TI
    from pcb.custom import thermal_inputs as THI
    for mem in (SR._MEM, TI._MEM, THI._MEM):
        for t in mem.values():
            t.clear()


def run_deck(check):
    from pcb.custom import kicad_spice as P
    rect, sk = _project('rectifier'), _project('sallen_key')
    plain = P.build_deck(rect)
    hot = P.build_deck(rect, temp_c=85, part_temps={'D1': 125, 'V1': 50, 'R9': 3}, coefficients={'R2': (1e-4, 0.0, 'test')})
    lines = hot['deck'].splitlines()
    t = hot['temperature']
    check('TMP-1 THE BOARD\'S TEMPERATURE is one .temp line after the includes (every model\'s own temperature terms act); without one the deck is '
          'unchanged (ngspice runs at its default 27 C); a .temp / .options temp= the schematic carries would be left out (the board\'s wins)',
          lines[2] == '.temp 85' and '.temp' not in plain['deck'] and t['temp_c'] == 85.0 and plain['temperature']['temp_c'] is None
          and all(P.TEMP_DIRECTIVE.match(x) for x in ('.temp 50', '.TEMP 0', '.options reltol=1e-4 temp=60'))
          and not P.TEMP_DIRECTIVE.match('.tran 1u 10m') and not P.TEMP_DIRECTIVE.match('.options tempfile=x'), lines[:4])
    el = {e['ref']: e['value'] for e in hot['elements'].values()}
    check('TMP-2 A PART\'S OWN TEMPERATURE is an instance temp= where ngspice takes one (D1 1N4148 temp=125); a source takes none (V1: said) and a ref '
          'not in the deck is said; an R / C / L coefficient is written as tc1= tc2= (R2)',
          el['D1'] == '1N4148 temp=125' and t['part_temps'] == {'D1': 125.0} and 'V element' in t['refused']['V1'] and 'not in the deck' in t['refused']['R9']
          and el['R2'] == '100k tc1=0.0001 tc2=0.0' and t['coefficients']['R2'][2] == 'test', (el, t))
    x = P.build_deck(sk, part_temps={'U1': 60, 'R1': 40})
    bsim = '.model nb NMOS (LEVEL=14 VERSION=4.8)\n.model n1 NMOS (LEVEL=1 VTO=1)\n.model vd VDMOS (VTO=1)\n.model n49 nmos\n+ level=49'
    check('TMP-2 WHERE NGSPICE REFUSES, NOTHING IS WRITTEN (probed on econ-core\'s libngspice 2026-10-31): a subcircuit (temp= on an X line crashes the '
          'library) and a BSIM MOSFET (level 14 / 49: the line does not parse) stay at the board\'s temperature, in words; levels 1-3 / 6 and VDMOS take '
          'it; a MOSFET whose model card cannot be found is refused (its level is unknown); a continued (+) model line is read',
          'U1' in x['temperature']['refused'] and 'crashes' in x['temperature']['refused']['U1'] and 'temp=' not in x['elements']['XU1']['value']
          and x['temperature']['part_temps'] == {'R1': 40.0} and P.instance_temp_refusal('M', bsim, 'nb').startswith('MOSFET model nb is level 14')
          and P.instance_temp_refusal('M', bsim, 'n49').startswith('MOSFET model n49 is level 49') and P.instance_temp_refusal('M', bsim, 'n1') == ''
          and P.instance_temp_refusal('M', bsim, 'vd') == '' and 'not found' in P.instance_temp_refusal('M', bsim, 'nope'), x['temperature'])
    run, ref = _recorded('rectifier')
    check('THE RECORDED RUNS ARE OF THESE DECKS: every reference run\'s deck text equals the deck built here for its temperature (so the recorded '
          'results belong to exactly what the code writes)',
          all(ref[k]['deck'] == P.build_deck(rect, temp_c=float(k))['deck'] for k in ('-40', '25', '85', '125'))
          and ref['parts']['deck'] == P.build_deck(rect, temp_c=25, part_temps={'D1': 100})['deck'], sorted(ref))


def run_reach_and_inputs(check):
    from pcb.custom import spice_temperature as ST
    from pcb.custom import temperature_inputs as TI
    _fresh()
    rect, sk = _project('rectifier'), _project('sallen_key')
    r = {x['ref']: x for x in ST.reach(None, 'rectifier', rows=rect)}
    s = {x['ref']: x for x in ST.reach(None, 'sallen_key', rows=sk)}
    check('WHAT RESPONDS (rectifier): the diode through its model - diode.mod names no temperature terms, so ngspice\'s defaults act (EG 1.11 eV, XTI 3); '
          'R1, R2, C1 are ideal with no coefficient: unchanged by temperature (said, with where to give one); the source is ideal; the diode can have its '
          'own temperature, the source cannot. (Sallen-Key) the op-amp subcircuit responds inside its model and cannot have its own temperature',
          r['D1']['acts'] == 'yes' and 'EG 1.11' in r['D1']['through'] and r['R1']['acts'] == 'no' and 'ideal resistor' in r['R1']['through']
          and r['C1']['acts'] == 'no' and r['V1']['acts'] == 'no' and r['D1']['own_temperature'] == 'yes' and r['V1']['own_temperature'].startswith('no')
          and s['U1']['acts'] == 'inside its model' and s['U1']['own_temperature'].startswith('no'), {k: (v['acts'], v['through'][:50]) for k, v in r.items()})
    st = [TI.set_quantity(None, 'rectifier', 'R2', 'tc1_ppm_k', 100)[0], TI.set_quantity(None, 'rectifier', 'D1', 't_min_c', -65)[0],
          TI.set_quantity(None, 'rectifier', 'D1', 't_max_c', 100)[0]]
    bad = [TI.set_quantity(None, 'rectifier', 'D1', 't_max_c', -70), TI.set_quantity(None, 'rectifier', 'D1', 't_min_c', -300),
           TI.set_quantity(None, 'rectifier', 'D1', 'colour', 1), TI.set_quantity(None, 'rectifier', 'D1', 't_min_c', 'cold')]
    q = {x['quantity']: x for x in TI.quantities(None, 'rectifier', 'D1')}
    r2 = {x['ref']: x for x in ST.reach(None, 'rectifier', rows=rect)}['R2']
    parts = {x['ref']: x for x in TI.parts(None, 'rectifier', rect)}
    check('WHAT A PERSON GIVES (synthetic values): a rated range (negative allowed: -65 C) and a resistor\'s TCR in ppm/K; a range that inverts, a '
          'temperature below absolute zero, an unknown quantity and text are refused in words (400); every row is signed (the page\'s box takes a minus); '
          'R2 then responds through tc1 1e-4 /K; the parts list shows the range and what the coefficient does',
          st == [200, 200, 200] and [b[0] for b in bad] == [400] * 4 and 't_min_c < t_max_c' in bad[0][1]['error'] and 'absolute zero' in bad[1][1]['error']
          and q['t_min_c']['value'] == -65.0 and q['t_min_c']['given'] and q['tc1_ppm_k']['value'] == '' and all(x['signed'] for x in q.values())
          and r2['acts'] == 'yes' and 'tc1 0.0001' in r2['through'] and parts['D1']['rated_range'] == '-65 .. 100 C'
          and parts['R2']['coefficient_use'].startswith('written into the deck') and 'SPICE model' in parts['D1']['coefficient_use'], (st, [b[1] for b in bad]))
    cl = TI.clear_quantity(None, 'rectifier', 'R2', 'tc1_ppm_k')
    shared = TI.put_behaviour(None, '', '', '100k', {'tc1_ppm_k': 200, 'document': 'a test document', 'page_table': 'Table 2'})
    co = TI.coefficients(None, 'rectifier', rect)
    refused = TI.put_behaviour(None, 'rectifier', 'D1', '', {'t_min_c': 10, 't_max_c': 5})
    check('CLEAR puts a number back to not given; a behaviour WITH ITS CITATION can be shared by part (every symbol valued 100k: R2 gets tc1 200 ppm/K, '
          'cited) and a bad one is refused (400)',
          cl[1]['cleared'] and shared[0] == 201 and set(co) == {'R2'} and abs(co['R2'][0] - 200e-6) < 1e-15
          and co['R2'][1:] == (0.0, 'a test document, Table 2') and refused[0] == 400, (cl[1], co, refused))
    _fresh()


def run_sweep(check):
    from pcb.custom import spice_runs as SR
    from pcb.custom import spice_temperature as ST
    from pcb.custom import temperature_inputs as TI
    _fresh()
    rect = _project('rectifier')
    run, ref = _recorded('rectifier')
    name, results = ST.sweep(None, 'rectifier', [-40.0, 25.0, 85.0, 125.0], runner=run, rows=rect)
    rows, why = ST.compare(None, 'rectifier')
    out = {r['temp_c']: r for r in rows if r['net'] == '/rect_out'}
    peaks = [out[t]['max'] for t in (-40.0, 25.0, 85.0, 125.0)]
    kept = sorted((r for r in SR.runs(None, 'rectifier')), key=lambda r: r['temp_c'])
    check('TMP-1 A SWEEP (the rectifier at -40 / 25 / 85 / 125 C, recorded on econ-core): four runs kept under one sweep name, each with its temperature '
          '(mode board); /rect_out\'s peak RISES with temperature - the diode drops less when hot (its saturation current grows) - by about +2 mV/K, '
          'each change measured from the 25 C run; GND stays 0 V by definition',
          not why and all(r['ok'] for r in results) and len({r['sweep'] for r in kept}) == 1 and [r['temp_c'] for r in kept] == [-40.0, 25.0, 85.0, 125.0]
          and all(r['temp_mode'] == 'board' for r in kept) and kept[0]['temperature'] == '-40 C board' and peaks == sorted(peaks)
          and out[25.0]['peak_change'] == 0.0 and all(1.5e-3 < out[t]['peak_change_per_k'] < 2.5e-3 for t in (-40.0, 85.0, 125.0))
          and all(r['max'] == 0.0 for r in rows if r['net'] == 'GND'), ([round(p, 4) for p in peaks], {t: out[t]['peak_change_per_k'] for t in out}))
    trend, _ = ST.trend(None, 'rectifier')
    over, _ = ST.overlay(None, 'rectifier', max_rows=50)
    check('THE CHARTS: the trend has one line per net, x = the temperature (4 points each); the overlay draws every node vector at every temperature '
          '(no branch currents), labelled with its temperature',
          {p['x'] for p in trend if p['series'].startswith('/rect_out')} == {-40.0, 25.0, 85.0, 125.0}
          and {p['series'] for p in over if p['series'].startswith('/rect_out')} == {'/rect_out (V) at %g C' % t for t in (-40, 25, 85, 125)}
          and not any('#branch' in p['series'] for p in over), sorted({p['series'] for p in over})[:6])
    TI.set_quantity(None, 'rectifier', 'D1', 't_min_c', -65)
    TI.set_quantity(None, 'rectifier', 'D1', 't_max_c', 100)
    rt = ST.ratings(None, 'rectifier', [-40.0, 25.0, 85.0, 125.0], rows=rect)
    ok = ST.ratings(None, 'rectifier', [-40.0, 25.0, 85.0], rows=rect)
    check('RATINGS (synthetic range -65 .. 100 C on D1): swept to 125 C it is ABOVE its rated maximum by 25 C (margin -25), swept to 85 C it is inside; '
          'a part with no range is not listed',
          len(rt) == 1 and rt[0]['verdict'] == 'ABOVE its rated maximum' and rt[0]['high_margin_c'] == -25.0 and rt[0]['low_margin_c'] == 25.0
          and ok[0]['verdict'] == 'inside its rated range', rt)
    sk_run, sk_ref = _recorded('sallen_key')
    ST.sweep(None, 'sallen_key', [-40.0, 25.0, 85.0], runner=sk_run, rows=_project('sallen_key'))
    lp = {r['temp_c']: r for r in ST.compare(None, 'sallen_key')[0] if r['net'] == '/lowpass'}
    stop = {k: sk_ref[k]['vectors']['/lowpass']['mag'][50] for k in ('-40', '25', '85')}
    check('AN AC SWEEP (Sallen-Key, recorded): the passband barely moves - peak |V| changes by under 1e-6 from -40 to 85 C (the resistors and capacitors '
          'are ideal; only the op-amp model responds) - while deep in the stop band (100 kHz) the op-amp model\'s cold response differs by over 10x',
          len(lp) == 3 and all(abs(r['peak_change']) < 1e-6 for r in lp.values()) and lp[25.0]['unit'] == '|V|'
          and stop['-40'] > 10 * stop['25'], ({t: r['max'] for t, r in lp.items()}, stop))
    refused, _ = ST.sweep(None, 'rectifier', [60.0], runner=run, rows=rect)
    newest, _ = ST.compare(None, 'rectifier')
    check('A TEMPERATURE THAT DID NOT RUN IS KEPT AND SAID: a sweep whose only temperature has no recorded run is kept as a refused run, and its '
          'comparison says no temperature ran (and why)', ST.compare(None, 'rectifier')[1].startswith('sweep %s: no temperature ran' % refused), newest)
    _fresh()


def run_parts(check):
    from pcb.custom import kicad_spice as P
    from pcb.custom import spice_runs as SR
    from pcb.custom import spice_temperature as ST
    from pcb.custom import thermal_inputs as THI
    _fresh()
    rect = _project('rectifier')
    run, ref = _recorded('rectifier')
    res = ST.run_at(None, 'rectifier', 25.0, part_temps={'D1': 100.0}, runner=run, rows=rect)
    peak = {k: max(ref[k]['vectors']['/rect_out']['real']) for k in ('85', '125', 'parts')}
    check('TMP-2 ONE PART AT ITS OWN TEMPERATURE (recorded: the board at 25 C, D1 alone at 100 C): the run is kept in mode parts with D1\'s temperature; '
          'only the diode responds in this circuit, so its /rect_out peak lands between the whole board at 85 C and at 125 C, close to the straight line '
          'between them (within 1 mV)',
          res['ok'] and res['temperature']['part_temps'] == {'D1': 100.0} and SR.runs(None, 'rectifier')[0]['temperature'] == '25 C board; D1 100 C'
          and SR.runs(None, 'rectifier')[0]['temp_mode'] == 'parts'
          and peak['85'] < peak['parts'] < peak['125'] and abs(peak['parts'] - (peak['85'] + (peak['125'] - peak['85']) * 15 / 40)) < 1e-3, peak)
    rows = _project('ecc83')
    THI.set_quantity(None, 'ecc83', 'R4', 'power_w', 0.5)
    final, why = ST.part_temperatures(None, 'ecc83', 25.0, 'final', rows=rows)
    peakm, _ = ST.part_temperatures(None, 'ecc83', 25.0, 'peak', rows=rows)
    f, pk = {r['ref']: r for r in final}, {r['ref']: r for r in peakm}
    placed = {p['ref'] for p in rows['PcbPad']}
    check('TMP-2 EVERY PART\'S OWN TEMPERATURE FROM THE BOARD OVER TIME (ecc83, R4 0.5 W given): every placed part gets a row (unpowered ones probed as '
          '0 W sources), R4 is the hottest, every other part is warmer than the 25 C background but cooler than R4 (it warms from its neighbour), '
          'temp = background + rise, and each part\'s own peak is at least its end-of-run value',
          not why and set(f) == placed and final[0]['ref'] == 'R4' and all(25.0 < r['temp_c'] < f['R4']['temp_c'] for k, r in f.items() if k != 'R4')
          and all(abs(r['temp_c'] - 25.0 - r['rise_c']) < 1e-12 for r in final) and all(pk[k]['rise_c'] >= f[k]['rise_c'] - 1e-12 for k in f)
          and 'neighbours' in f['R1']['from'], [(r['ref'], round(r['temp_c'], 2)) for r in final[:5]])
    d = P.build_deck(rows, temp_c=25.0, part_temps={r['ref']: r['temp_c'] for r in final})
    t = d['temperature']
    check('TMP-2 THE PARTS\' TEMPERATURES IN THE DECK (ecc83): R1-R4, C1, C2 carry their own temp=; the connectors and the tubes (no simulation model '
          'in this demo) are said to be not in the deck',
          set(t['part_temps']) == {'R1', 'R2', 'R3', 'R4', 'C1', 'C2'} and abs(t['part_temps']['R4'] - f['R4']['temp_c']) < 1e-9
          and all('not in the deck' in w for w in t['refused'].values()) and 'temp=' in d['elements']['R4']['value'], t)
    THI._MEM['PartPowerInput'].clear()
    none, why = ST.part_temperatures(None, 'ecc83', 25.0, rows=rows)
    check('TMP-2 NOTHING POWERED -> NO RISE, SAID: with no power on the board every part stays at the background (the reason is given)',
          not none and 'stays at the background 25 C' in why, why)
    _fresh()


def run_temperature_doors(check):
    import falcon
    import falcon.testing as ft
    from pcb.pcb_temperature_api import PcbTemperatureAPI
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES, SEED_BOARD_DETAILS_GRAPHS
    from board.board_temperature_page import TREND_GRAPH, OVERLAY_GRAPH
    _fresh()
    app = falcon.App()
    srv = types.SimpleNamespace(falconServer=app)
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        PcbTemperatureAPI(polServer=srv, manager=None)
    cl = ft.TestClient(app)
    grades = cl.simulate_get('/api/pcb/demo/temperature-grades')
    put = cl.simulate_put('/api/pcb/demo/temperature-inputs/U1/t_min_c', json={'value': -40})
    got = {r['quantity']: r for r in cl.simulate_get('/api/pcb/demo/temperature-inputs/U1').json['rows']}
    dele = cl.simulate_delete('/api/pcb/demo/temperature-inputs/U1/t_min_c')
    cited = cl.simulate_post('/api/pcb/demo/temperature-behaviours/U1', json={'t_min_c': -40, 't_max_c': 85, 'document': 'a test document'})
    by_part = cl.simulate_post('/api/pcb/temperature-behaviours/by-part/10k', json={'tc1_ppm_k': 100})
    check('THE DOORS: the grades (five, AEC-Q100 named for the automotive ones); PUT a negative rated minimum (200) and read it back; DELETE clears it; '
          'POST a cited behaviour (201, origin cited) and one shared by part',
          grades.status_code == 200 and len(grades.json['rows']) == 5 and 'AEC-Q100' in grades.json['rows'][3]['basis'] and put.status_code == 200
          and got['t_min_c']['value'] == -40.0 and dele.json['cleared'] and cited.status_code == 201 and by_part.status_code == 201,
          (grades.status_code, put.status_code, cited.json, by_part.json))
    bad = [cl.simulate_post('/api/pcb/demo/simulate-at', json={'temp_c': 900}), cl.simulate_post('/api/pcb/demo/simulate-at', json={'temp_c': 'warm'}),
           cl.simulate_post('/api/pcb/demo/temperature-sweep', json={'temps': []}), cl.simulate_post('/api/pcb/demo/temperature-sweep/arctic'),
           cl.simulate_post('/api/pcb/demo/simulate-parts', json={'mode': 'sometimes'})]
    nothing = [cl.simulate_post('/api/pcb/demo/simulate-at', json={'temp_c': 50}), cl.simulate_post('/api/pcb/demo/temperature-sweep/industrial'),
               cl.simulate_get('/api/pcb/demo/temperature-sweep'), cl.simulate_get('/api/pcb/demo/temperature-reach')]
    check('THE DOORS REFUSE IN WORDS: a temperature out of -200 .. 400 C or not a number, an empty sweep, an unknown grade, an unknown mode (400); a board '
          'with no schematic (404) and no sweep kept (404)',
          [b.status_code for b in bad] == [400] * 5 and 'within -200 .. 400' in bad[0].json['error'] and 'no grade' in bad[3].json['error']
          and [n.status_code for n in nothing] == [404] * 4 and 'no ingested schematic' in nothing[0].json['error']
          and 'no temperature sweep' in nothing[2].json['error'], [(b.status_code, b.json.get('error')) for b in bad + nothing])
    at = BD.part('layers', 'demo', 'temperature-at', None)[0]
    pr = BD.part('layers', 'demo', 'part-run', None)[0]
    dev = BD.part('datasheet', 'uno', 'temperature-grades', None)
    page = BOARD_DETAILS_PAGES[0]['definition']
    names = {g['name'] for g in SEED_BOARD_DETAILS_GRAPHS}
    check('THE PAGE: a Temperature tab (run at one typed temperature, sweep a grade by its row button, what responds, each net across the sweep, the trend '
          'and overlay charts, each part\'s range and coefficients edited in place - signed boxes - and the ratings) and a Parts at their own temperature '
          'tab (two run rows: end of run / own peak, and each part\'s temperature); the Board Details door serves them for a PCB and refuses a dev board',
          '"temperature"' in page and '"part-temperatures"' in page and 'temperature-sweep/{grade}' in page and '"editSignedField": "signed"' in page
          and 'simulate-parts' in page and {TREND_GRAPH, OVERLAY_GRAPH} <= names and at[0]['temp_c'] == 25.0 and at[0]['signed']
          and [r['mode'] for r in pr] == ['final', 'peak'] and dev[0] == [] and 'only a PCB' in dev[1] and 'temperature,points' in page, (at, pr, dev))
    _fresh()
