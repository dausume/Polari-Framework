"""pcb_esd_protection_selftest - esd-3 / esd-4 / esd-5 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): protection parts modelled from their datasheet numbers,
IEC 61000-4-2's own discharge current equation, and an event on a foothold of a board with no simulated circuit (the pin alone).
Reference (custom/reference/kicad10_esd_protection.json): libngspice runs of OUR decks (KiCad 10.0.6 on econ-core, 2026-10-31) - e0/e1 the rectifier,
HBM 2 kV into /rect_out with the SMBJ5.0A there; e2/e3 the rectifier, the IEC equation at 4 kV; e4/e5 the UNO R3's DIGITAL_L:7 pin alone, HBM 2 kV;
e6/e7 the same pin with the SMBJ5.0A. The recorded runner replays exactly the deck it is given and refuses any other.
The pin's absolute maximum is the ATmega328P's cited VCC + 0.5 V = 5.5 V at VCC 5 V (board.custom.electrical_atmega328p, V_PIN abs-max).
Run by pcb_selftest.main().
"""
import contextlib
import json
import math
import os
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'custom', 'reference', 'kicad10_esd_protection.json')
UNO_PIN = 'datasheet:arduino-uno-r3:foothold:DIGITAL_L:7'


def _recorded():
    by_deck = {r['deck']: r for r in json.load(open(REF))['runs'].values()}

    def run(deck, files=None):
        r = by_deck.get(deck)
        if r is None:
            return {'ok': False, 'refused': 'no recorded run for this deck (the recorded runner only replays decks run on econ-core)'}
        return {'ok': True, 'plot': r['plot'], 'vectors': r['vectors'], 'library': 'recorded: libngspice, KiCad 10.0.6, econ-core'}
    return run


def _fresh():
    from board.custom import protection_parts as PP
    from pcb import pcb_esd_selftest as T
    PP._MEM[PP.CLS].clear()
    return T._fresh()


def run_protection_parts(check):
    import re
    from board.custom import protection_parts as PP
    _fresh()
    smbj, cg = PP.part('smbj5.0a'), PP.part('cg0603mlc-05e')
    p = dict(re.findall(r'(\w+)=([\d.e+-]+)', smbj['model']))
    rs, n, bv, ibv = float(p['RS']), float(p['N']), float(p['BV']), float(p['IBV'])
    v_clamp = bv + PP.VT_TNOM * math.log(326.5 / ibv) + 326.5 * rs
    v_fwd = n * PP.VT_TNOM * math.log(50.0 / PP.IS_A) + 50.0 * rs
    check('ESD-3 A TVS FROM ITS DATASHEET (Bourns SMBJ REV. 09/20, row SMBJ5.0A): BV = V_BR max 7.00 V at I_T 10 mA; RS and N derived so the model '
          'lands exactly on the 8/20 us clamping pair (12.0 V at 326.5 A) and the forward pair (3.5 V at 50 A) - both recomputed here within 1 mV; '
          'no capacitance modelled (only a graph) and said',
          smbj['modelled'] == 'yes' and bv == 7.0 and ibv == 0.01 and abs(v_clamp - 12.0) < 1e-3 and abs(v_fwd - 3.5) < 1e-3
          and 'only as a graph' in smbj['notes'] and 'no capacitance given' in smbj['model_why'], (smbj['model'], v_clamp, v_fwd))
    bad = [PP.define(None, {'name': 'smbj5.0a', 'kind': 'tvs-uni'}), PP.define(None, {'name': 'x', 'kind': 'zener'}),
           PP.define(None, {'name': 'x', 'kind': 'tvs-uni', 'v_c_v': -5})]
    st, mine = PP.define(None, {'name': 'my-tvs', 'kind': 'tvs-uni', 'v_br_max': 6.0, 'i_t_ma': 1.0, 'v_c_v': 9.0, 'i_pp_a': 20.0, 'v_f_v': 1.2,
                                'i_f_a': 1.0})
    half = PP.define(None, {'name': 'half-tvs', 'kind': 'tvs-uni', 'v_br_max': 6.0})[1]
    check('ESD-3 REFUSED IN WORDS, NOT GUESSED: the UNO\'s CG0603MLC-05E is a snapback polymer (300 V trigger, 30 V clamp by TLP) - catalogued, not '
          'modelled; a bidirectional TVS and a varistor are refused the same way; a person\'s own TVS is modelled from its numbers (origin custom), one '
          'missing numbers says which; a cited name, an unknown kind and a negative rating are refused',
          cg['modelled'] == 'no' and 'snapback' in cg['model_why'] and PP.spice_model({'kind': 'tvs-bi'})[3] and PP.spice_model({'kind': 'varistor'})[3]
          and st == 201 and mine['modelled'] and mine['origin'] == 'custom' and not half['modelled'] and 'i_pp_a' in half['model_why']
          and [b[0] for b in bad] == [409, 400, 400], (cg['model_why'], half, [b[1] for b in bad]))
    _fresh()


def run_iec_waveform(check):
    from pcb import pcb_esd_selftest as T
    from pcb.custom import esd_events as E
    ip, tr, i30, i60 = E.iec_check(4000.0)
    check('ESD-4 IEC 61000-4-2\'S OWN EQUATION (2008, §6.2, under Figure 2) reproduces its Table 3 at 4 kV: first peak 15 A +-15 % (14.9), rise 0.8 ns '
          '+-25 % (0.81), 8 A +-30 % at 30 ns (8.0), 4 A +-30 % at 60 ns (4.0); it scales linearly with the level (8 kV = twice 4 kV)',
          abs(ip - 15) < 0.15 * 15 and abs(tr - 0.8e-9) < 0.25 * 0.8e-9 and abs(i30 - 8) < 0.3 * 8 and abs(i60 - 4) < 0.3 * 4
          and abs(E.iec_current(2e-9, 8000.0) - 2 * E.iec_current(2e-9, 4000.0)) < 1e-12, (ip, tr, i30, i60))
    EA = _fresh()
    rows, run = T._rows(), _recorded()
    EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out', 'protection_parts': ''})
    res = E.run_event(None, 'rectifier', T.OUT, model='iec-contact-waveform', level_v=4000.0, runner=run, rows=rows)
    s = res['summary']
    out = next(r for r in res['rows'] if r['node'] == '/rect_out')
    check('ESD-4 THE EQUATION IN THE SOLVER (recorded: 4 kV into the rectifier\'s /rect_out): sampled as an ngspice PWL source (every sample a '
          'breakpoint), the measured first peak is Table 3\'s 15 A within 1 % - the sub-nanosecond peak is resolved, not stepped over; the 100 nF takes '
          'its ~0.58 uC and rises ~5.8 V; the caveat (a forced current overstates a high-impedance net) rides in the summary',
          res['ok'] and abs(s['peak_current_a'] / s['expected_current_a'] - 1) < 0.01 and s['expected_current_a'] == 15.0
          and 5.3 < out['rise_v'] < 6.3 and 'high-impedance' in s['basis'], (s, out['rise_v']))
    _fresh()


def run_protected_events(check):
    from board.custom import esd_areas as EA
    from board.custom import esd_footholds as EF
    from pcb import pcb_esd_selftest as T
    from pcb.custom import esd_events as E
    _fresh()
    rows, run = T._rows(), _recorded()
    EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out', 'protection_parts': 'smbj5.0a'})
    res = E.run_event(None, 'rectifier', T.OUT, runner=run, rows=rows)
    prot = E.protection_results(None, res['run'])[0]
    check('ESD-3 A TVS ON A PCB NET (recorded: HBM 2 kV into the rectifier\'s /rect_out with the SMBJ5.0A placed from it to ground, both runs): the '
          '100 nF already holds the net near 2.8 V, below the TVS\'s 7 V breakdown, so the TVS carries next to nothing (picoamps) and is far from its '
          'I_PP - the protection was not what saved this net, and the rows say so',
          res['ok'] and len(prot) == 1 and prot[0]['part'] == 'smbj5.0a' and prot[0]['peak_current_a'] < 1e-6 and prot[0]['breaks'].startswith('no')
          and 'smbj5.0a' in res['summary']['protection_parts'], prot)
    EA.flag(None, 'datasheet', 'arduino-uno-r3', {'scope': 'foothold', 'target': 'DIGITAL_L:7', 'abs_max_v': 5.5,
                                                  'document': 'ATmega328P absolute maximum, VCC + 0.5 V at VCC 5 V (board.custom.electrical_atmega328p)'})
    bare = EF.run_pin_event(None, 'datasheet', 'arduino-uno-r3', UNO_PIN, runner=run)
    EA.toggle_protection(None, UNO_PIN, 'smbj5.0a')
    tvs = EF.run_pin_event(None, 'datasheet', 'arduino-uno-r3', UNO_PIN, runner=run)
    b, t = bare['rows'][0], tvs['rows'][0]
    tp = E.protection_results(None, tvs['run'])[0][0]
    check('ESD-5 A DEV BOARD PIN WITH NO CIRCUIT (recorded: the UNO\'s DIGITAL_L:7, the pin alone - 10 pF held at its 5 V logic level - HBM 2 kV): bare, '
          'the 100 pF shares its charge with the pin\'s 10 pF and the pin goes to ~1.8 kV (2000 x 100 / 110) - BREAKS; with the SMBJ5.0A it peaks at '
          '~7.15 V, the TVS carrying the HBM current (~1.3-1.5 A, under 1 % of its I_PP) - and STILL BREAKS against the ATmega328P\'s 5.5 V: a 5 V TVS '
          'clamps above a 5 V chip\'s absolute maximum, which the check says plainly',
          bare['ok'] and tvs['ok'] and b['node'] == 'pin' and 1750 < b['peak_v'] < 1850 and bare['summary']['verdict'] == 'BREAKS'
          and 7.0 < t['peak_v'] < 7.3 and t['breaks'].startswith('BREAKS') and 1.2 < tp['peak_current_a'] < 1.6 and abs(tp['source_peak_a'] - 1.33) < 0.02
          and tp['breaks'].startswith('no') and 'the pin alone' in tvs['summary']['basis'], (b['peak_v'], t['peak_v'], tp))
    keyed = {r['name'] for r in __import__('pcb.custom.spice_runs', fromlist=['runs']).runs(None, EF.board_key('datasheet', 'arduino-uno-r3'))}
    refused = [EF.run_any(None, 'nope', runner=run)]
    EA.flag(None, 'datasheet', 'arduino-uno-r3', {'scope': 'net', 'target': '+5V'})
    refused.append(EF.run_pin_event(None, 'datasheet', 'arduino-uno-r3', 'datasheet:arduino-uno-r3:net:+5V', runner=run))
    EA.flag(None, 'datasheet', 'arduino-uno-r3', {'scope': 'foothold', 'target': 'NOPE:1'})
    refused.append(EF.run_pin_event(None, 'datasheet', 'arduino-uno-r3', 'datasheet:arduino-uno-r3:foothold:NOPE:1', runner=run))
    bad_part = EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out', 'protection_parts': 'unobtainium'})
    EA.flag(None, 'layers', 'rectifier', {'scope': 'net', 'target': '/rect_out', 'protection_parts': 'cg0603mlc-05e'})
    polymer = E.run_event(None, 'rectifier', T.OUT, runner=run, rows=rows)
    check('ESD-5 KEPT AND REFUSED: a dev board\'s runs are kept under "datasheet:arduino-uno-r3" (the event and its baseline); refused in words - an '
          'unknown area through the shared door (404), a net area on a board with no circuit (one foothold '
          'only, 422), an unknown foothold (404), an unknown protection part (400), a part that cannot be modelled (the polymer, 422)',
          len(keyed) == 4 and [r['status'] for r in refused] == [404, 422, 404] and bad_part[0] == 400 and polymer['status'] == 422
          and 'snapback' in polymer['error'], ([r.get('error') for r in refused], polymer.get('error')))
    _fresh()


def run_protection_doors(check):
    import falcon
    import falcon.testing as ft
    from board.esd_areas_api import EsdAreasAPI
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        EsdAreasAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    cat = cl.simulate_get('/api/board/protection-parts')
    made = cl.simulate_post('/api/board/protection-parts', json={'name': 'door-tvs', 'kind': 'varistor'})
    cl.simulate_post('/api/board/esd-areas/datasheet/arduino-uno-r3', json={'scope': 'foothold', 'target': 'DIGITAL_L:7'})
    on = cl.simulate_post('/api/board/esd-areas/protection', json={'area': UNO_PIN, 'part': 'smbj5.0a'})
    listed = BD.part('datasheet', 'arduino-uno-r3', 'esd-protection', None, {'area': UNO_PIN})[0]
    off = cl.simulate_post('/api/board/esd-areas/protection', json={'area': UNO_PIN, 'part': 'smbj5.0a'})
    knob = cl.simulate_put('/api/board/esd-areas/quantity', json={'area': UNO_PIN, 'quantity': 'pin_cap_pf', 'value': 4.5})
    nolevel = cl.simulate_post('/api/board/esd-areas/run', json={'area': UNO_PIN, 'level_v': 'loud'})
    nothing = cl.simulate_post('/api/board/esd-areas/run', json={'area': 'nope'})
    page = BOARD_DETAILS_PAGES[0]['definition']
    check('ESD-3/5 THE DOORS AND THE PAGE: the protection catalogue (each with modelled yes / no and why); a person\'s own part (201, a varistor - '
          'catalogued, not modelled); a part toggled onto an area and off again (click-toggle), the page listing it as on the area; the pin knob '
          'edited; the shared run door refuses a level that is not a number (400) and an unknown area (404); the ESD tab runs every area through '
          '/api/board/esd-areas/run and has the protection tables',
          cat.status_code == 200 and {r['name'] for r in cat.json['rows']} >= {'smbj5.0a', 'cg0603mlc-05e'} and made.status_code == 201
          and not made.json['modelled'] and on.json.get('added') == 'smbj5.0a' and off.json.get('removed') == 'smbj5.0a'
          and next(r for r in listed if r['name'] == 'smbj5.0a')['on_area'] == 'yes' and knob.status_code == 200 and nolevel.status_code == 400
          and nothing.status_code == 404 and '/api/board/esd-areas/run' in page and 'esd-protection?area=' in page and 'esd-protection-results' in page,
          (made.json, on.json, off.json, nothing.json))
    _fresh()
