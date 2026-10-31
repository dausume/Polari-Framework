"""pcb_esd_selftest - esd-0 / esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; the user's words 2026-10-31: "flag different pieces as ESD protection areas, which
we need to establish simulations for testing where we emulate ESD events and check that the drive conditions handle it smoothly and do not break the
circuits"). Areas flagged on a definition, the standard discharge networks, an event injected into a PCB's own deck with its no-event baseline, the
break and recovery checks, the doors and the page.
Reference (custom/reference/kicad10_esd_rectifier.json): libngspice runs of OUR ESD decks (KiCad 10.0.6 on econ-core, 2026-10-31) - the rectifier hit
with HBM 2 kV at 2.5 ms into /rect_out and into Net-(D1-A), each with its baseline. The recorded runner hands back the run recorded for exactly the
deck it is given and refuses any other. The absolute maximum used below is a SYNTHETIC test value (no real part's rating). Run by pcb_selftest.main().
"""
import contextlib
import json
import os
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'custom', 'reference', 'kicad10_esd_rectifier.json')
SIM = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'simulation')
OUT, ANODE = 'layers:rectifier:net:/rect_out', 'layers:rectifier:net:Net-(D1-A)'


def _fresh():
    from board.custom import esd_areas as EA
    from pcb.custom import spice_runs as SR
    EA._MEM[EA.CLS].clear()
    for t in SR._MEM.values():
        t.clear()
    return EA


def _rows(b='rectifier'):
    from pcb.custom import kicad_read as K
    return K.read_project(K.read_dir(os.path.join(SIM, b)), b)


def _recorded():
    by_deck = {r['deck']: r for r in json.load(open(REF))['runs'].values()}

    def run(deck, files=None):
        r = by_deck.get(deck)
        if r is None:
            return {'ok': False, 'refused': 'no recorded run for this deck (the recorded runner only replays decks run on econ-core)'}
        return {'ok': True, 'plot': r['plot'], 'vectors': r['vectors'], 'library': 'recorded: libngspice, KiCad 10.0.6, econ-core'}
    return run


def run_esd_areas(check):
    from pcb.custom.esd_events import MODELS
    EA = _fresh()
    st, body = EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out'})
    a = body['rows'][0]
    bad = [EA.flag(None, 'layers', 'rectifier', {'scope': 'room', 'target': 'x'}), EA.flag(None, 'layers', 'rectifier', {'target': ''}),
           EA.flag(None, 'layers', 'rectifier', {'target': 'x', 'model': 'lightning'}), EA.flag(None, 'layers', 'rectifier', {'target': 'x', 'level_v': 99999}),
           EA.flag(None, 'nowhere', 'rectifier', {'target': 'x'})]
    check('ESD-0 THE NETWORKS ARE THE STANDARDS\': HBM (JS-001) 100 pF / 1.5 kOhm, IEC 61000-4-2 contact 150 pF / 330 Ohm at 2 / 4 / 6 / 8 kV - the IEC entry '
          'says the plain network misses the standard\'s sub-nanosecond first peak; A FLAGGED AREA (the rectifier\'s /rect_out net) gets the D-esd-2 '
          'criterion (5 % / 50 mV / 10 us), HBM at 2 kV, no absolute maximum (said: undetermined); bad scope, empty target, unknown model, an absurd level '
          'and an unknown definition kind are refused in words',
          (MODELS['hbm']['c_f'], MODELS['hbm']['r_ohm'], MODELS['iec-contact']['c_f'], MODELS['iec-contact']['r_ohm']) == (100e-12, 1500.0, 150e-12, 330.0)
          and MODELS['iec-contact']['levels'] == [2000.0, 4000.0, 6000.0, 8000.0] and 'first current peak' in MODELS['iec-contact']['caveat']
          and st == 201 and a['name'] == OUT and (a['level_v'], a['abs_max_v'], a['recover_pct'], a['recover_mv'], a['recover_us']) == (2000.0, -1.0, 5.0, 50.0, 10.0)
          and 'undetermined' in a['criterion'] and [b[0] for b in bad] == [400] * 5, (a, [b[1]['error'] for b in bad]))
    t1 = EA.toggle(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out'})
    t2 = EA.toggle(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out'})
    q = [EA.set_quantity(None, OUT, 'abs_max_v', 2.0)[0], EA.set_quantity(None, OUT, 'recover_us', -3)[0], EA.set_quantity(None, OUT, 'colour', 1)[0]]
    rows = {r['quantity']: r for r in EA.quantities(None, OUT)}
    check('ESD-0 CLICK-TOGGLE: the page\'s button unflags a flagged piece and flags it again; the area\'s numbers are edited one at a time (a negative '
          'recovery time and an unknown quantity refused); only abs_max_v takes a minus (-1 = not given)',
          t1[1].get('removed') == OUT and t2[0] == 201 and q == [200, 400, 400] and rows['abs_max_v']['value'] == 2.0 and rows['abs_max_v']['signed']
          and not rows['level_v']['signed'], (t1, t2, q))
    _fresh()


def run_esd_events(check):
    from pcb.custom import esd_events as E
    from pcb.custom import spice_runs as SR
    EA = _fresh()
    rows, run = _rows(), _recorded()
    EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out'})
    EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': 'Net-(D1-A)'})
    res = E.run_event(None, 'rectifier', OUT, runner=run, rows=rows)
    s = res['summary']
    by = {r['node']: r for r in res['rows']}
    kept = {r['name']: r for r in SR.runs(None, 'rectifier')}
    check('ESD-1 AN EVENT ON THE CIRCUIT (recorded: HBM 2 kV into the rectifier\'s /rect_out at 2.5 ms = a quarter of its .tran): both runs kept - the '
          'event and its baseline (the same deck, the network charged to 0 V); the measured discharge peaks at level / R (1.333 A, within 0.5 %); the '
          '100 nF on /rect_out swallows the charge - the node rises about 2 V, not kilovolts - but is still about 0.47 V high at the end of the run '
          '(R2 100k drains it over ~10 ms), so the verdict is "does not recover in time"; with no absolute maximum the break check says undetermined',
          res['ok'] and res['run'] in kept and res['baseline'] in kept and kept[res['run']]['event'].startswith('ESD hbm 2000 V into /rect_out')
          and kept[res['baseline']]['event'].startswith('no-event baseline') and abs(s['t_event_s'] - 2.5e-3) < 1e-12
          and abs(s['peak_current_a'] / s['expected_current_a'] - 1) < 0.005 and abs(s['energy_j'] - 2e-4) < 1e-12
          and by['/rect_out']['protected'] and 1.5 < by['/rect_out']['rise_v'] < 3.0 and by['/rect_out']['recovered_after_s'] == -1.0
          and 0.4 < by['/rect_out']['final_offset_v'] < 0.55 and s['verdict'].startswith('does not recover') and by['/rect_out']['breaks'].startswith('undetermined')
          and by['/signal_in']['breaks'] == '(not protected)', (s, by.get('/rect_out')))
    EA.set_quantity(None, OUT, 'abs_max_v', 2.0)
    s2, rows2, _ = E.results(None, res['run'])
    check('ESD-1 "DO NOT BREAK": give the protected net an absolute maximum (synthetic 2 V) and the same kept run now BREAKS - the peak above it, named',
          s2['verdict'] == 'BREAKS' and next(r for r in rows2 if r['node'] == '/rect_out')['breaks'].startswith('BREAKS'), s2['verdict'])
    an = E.run_event(None, 'rectifier', ANODE, runner=run, rows=rows)
    a_by = {r['node']: r for r in an['rows']}
    EA.set_quantity(None, ANODE, 'recover_us', 10000.0)
    s3, rows3, _ = E.results(None, an['run'])
    a3 = next(r for r in rows3 if r['node'] == 'net-_d1-a_')
    check('ESD-1 "HANDLE IT SMOOTHLY" (into the diode\'s anode, Net-(D1-A)): the diode carries the charge into C1, so the anode peaks at a few volts '
          '(3.43 V recorded); it comes back within the criterion only after milliseconds - fails 10 us, and with the criterion widened to 10 ms the same '
          'kept run "survives, recovers in time"',
          an['ok'] and 3.0 < a_by['net-_d1-a_']['peak_v'] < 4.0 and a_by['net-_d1-a_']['recovered'].startswith('NO - back after')
          and 1e-3 < a3['recovered_after_s'] < 10e-3 and a3['recovered'] == 'yes' and s3['verdict'].startswith('survives'), (a_by.get('net-_d1-a_'), s3['verdict']))
    pts, why = E.chart(None, res['run'])
    near = [p for p in pts if abs(p['x'] - 2.5e-3) <= 50e-6 and p['series'] == '/rect_out with the event']
    check('ESD-1 THE CHART: each protected net with the event and without it; every solver point within 50 us of the event is kept (a stride alone '
          'would step over the spike)',
          not why and {p['series'] for p in pts} == {'/rect_out with the event', '/rect_out without it'} and len(near) > 20, (why, len(near)))
    EA.flag(None, 'datasheet', 'arduino-uno-r3', {'scope': 'foothold', 'target': 'POWER:5'})
    EA.flag(None, 'layers', 'rectifier', {'scope': 'part', 'target': 'D1'})
    EA.flag(None, 'layers', 'sallen_key', {'scope': 'net', 'target': '/lowpass'})
    refusals = [E.run_event(None, 'rectifier', 'datasheet:arduino-uno-r3:foothold:POWER:5', runner=run, rows=rows),
                E.run_event(None, 'rectifier', 'nope', runner=run, rows=rows),
                E.run_event(None, 'rectifier', 'layers:rectifier:part:D1', runner=run, rows=rows),
                E.run_event(None, 'sallen_key', 'layers:sallen_key:net:/lowpass', runner=run, rows=_rows('sallen_key'))]
    check('ESD-1 REFUSED IN WORDS: an area on a dev board (an event runs on a PCB\'s circuit: 409), an unknown area (404), a part-scope area with no '
          'inject_net (which pin\'s net? 422, naming the choices), and a circuit with no transient analysis (the Sallen-Key filter runs .ac: 422)',
          [r['status'] for r in refusals] == [409, 404, 422, 422] and 'Net-(D1-A)' in refusals[2]['error'] and 'no .tran' in refusals[3]['error'],
          [r.get('error') for r in refusals])
    _fresh()


def run_esd_doors(check):
    import falcon
    import falcon.testing as ft
    from board.esd_areas_api import EsdAreasAPI
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES, SEED_BOARD_DETAILS_GRAPHS
    from board.board_esd_page import ESD_GRAPH
    from pcb.pcb_esd_api import PcbEsdAPI
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        EsdAreasAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
        PcbEsdAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    models = cl.simulate_get('/api/pcb/esd-models')
    tog = cl.simulate_post('/api/board/esd-areas/layers/demo/toggle', json={'scope': 'net', 'target': '/OUT'})
    listed = cl.simulate_get('/api/board/esd-areas/layers/demo')
    qty = cl.simulate_put('/api/board/esd-areas/quantity', json={'area': 'layers:demo:net:/OUT', 'quantity': 'abs_max_v', 'value': 6})
    unknown = cl.simulate_post('/api/pcb/demo/esd-run', json={'area': 'layers:demo:net:/NOPE'})
    noschem = cl.simulate_post('/api/pcb/demo/esd-run', json={'area': 'layers:demo:net:/OUT'})
    bad_level = cl.simulate_post('/api/pcb/demo/esd-run', json={'area': 'layers:demo:net:/OUT', 'level_v': 'loud'})
    nores = cl.simulate_get('/api/pcb/runs/nope/esd-results')
    gone = cl.simulate_post('/api/board/esd-areas/unflag', json={'name': 'layers:demo:net:/OUT'})
    check('ESD THE DOORS: the networks (HBM, IEC contact, and since esd-4 IEC\'s own current equation); flag by the toggle (201) and list it (an area name carrying a slash rides in the body); edit its absolute maximum; '
          'run refuses an unknown area (404), a board with no schematic (404) and a level that is not a number (400); results of an unknown run 404; unflag',
          models.status_code == 200 and len(models.json['rows']) == 3 and tog.status_code == 201 and listed.json['rows'][0]['target'] == '/OUT'
          and qty.status_code == 200 and unknown.status_code == 404 and noschem.status_code == 404 and 'no ingested schematic' in noschem.json['error']
          and bad_level.status_code == 400 and nores.status_code == 404 and gone.json.get('removed') == 'layers:demo:net:/OUT',
          (tog.json, unknown.json, noschem.json))
    cands = BD.part('geometry', 'breadboard-half', 'esd-candidates', None)[0]
    dev_runs = BD.part('datasheet', 'arduino-uno-r3', 'esd-runs', None)
    page = BOARD_DETAILS_PAGES[0]['definition']
    check('ESD THE PAGE: an ESD tab - the pieces to flag (a breadboard\'s footholds; a PCB\'s nets) with a Flag / unflag button, the areas with Run event '
          '(it then selects the new run), the area\'s numbers edited in place, the networks, the runs, the verdict, each node, and the chart (named graph '
          'pcb-esd-event); a dev board carries areas too (its events run on a foothold\'s pin since esd-5; none run yet here)',
          len(cands) == 400 and cands[0]['scope'] == 'foothold' and not cands[0]['flagged'] and dev_runs == ([], '')
          and '"esd"' in page and 'esd-areas/{definition_kind}/{board}/toggle' in page and '"then_scope": {"key": "esdrun", "from": "run"}' in page
          and ESD_GRAPH in {g['name'] for g in SEED_BOARD_DETAILS_GRAPHS}, (len(cands), dev_runs))
    _fresh()
