"""pcb_esd_cdm_selftest - esd-6 / esd-7 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): a bidirectional TVS and a varistor modelled from their datasheet
numbers on ngspice's own elements (no vendor model file), and the charged-device model as the Industry Council's series LCR loop.
Reference (custom/reference/kicad10_esd_cdm.json): libngspice runs of OUR decks (KiCad 10.0.6 on econ-core, 2026-10-31) - m0 / m1 each model at its
cited points; m2 / m3 the CDM loop into a short (small / large JS-002 module, 500 V); the UNO R3's DIGITAL_L:7 pin alone: fa HBM 2 kV + SMBJ5.0CA, fb HBM
2 kV + S05K11, fc CDM small 500 V bare, fd CDM small 500 V + SMBJ5.0A. The recorded runner replays exactly the deck it is given and refuses any other.
The pin's absolute maximum is the ATmega328P's cited VCC + 0.5 V = 5.5 V at VCC 5 V (board.custom.electrical_atmega328p).
Run by pcb_selftest.main().
"""
import contextlib
import json
import os
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'custom', 'reference', 'kicad10_esd_cdm.json')
UNO_PIN = 'datasheet:arduino-uno-r3:foothold:DIGITAL_L:7'


def _runs():
    return json.load(open(REF))['runs']


def _recorded():
    by_deck = {r['deck']: r for r in _runs().values()}

    def run(deck, files=None):
        r = by_deck.get(deck)
        if r is None:
            return {'ok': False, 'refused': 'no recorded run for this deck (the recorded runner only replays decks run on econ-core)'}
        return {'ok': True, 'plot': r['plot'], 'vectors': r['vectors'], 'library': 'recorded: libngspice, KiCad 10.0.6, econ-core'}
    return run


def _fresh():
    from pcb import pcb_esd_protection_selftest as P
    return P._fresh()


def _pin():
    from board.custom import esd_areas as EA
    _fresh()
    EA.flag(None, 'datasheet', 'arduino-uno-r3', {'scope': 'foothold', 'target': 'DIGITAL_L:7', 'abs_max_v': 5.5})


def _shape(run):
    import numpy as np
    t, i = np.array(run['vectors']['time']['real']), np.abs(np.array(run['vectors']['vesdmeas#branch']['real']))
    j = int(i.argmax())
    ip = float(i[j])
    rise = float(t[np.argmax(i >= 0.9 * ip)] - t[np.argmax(i >= 0.1 * ip)])
    fwhm = float(t[j + np.argmax(i[j:] < 0.5 * ip)] - t[np.argmax(i >= 0.5 * ip)])
    return ip, rise, fwhm


def run_bidirectional_and_varistor(check):
    from board.custom import protection_models as PM
    from board.custom import protection_parts as PP
    _fresh()
    runs = _runs()
    ca, mov, cg = PP.part('smbj5.0ca'), PP.part('s05k11'), PP.part('cg0603mlc-05e')
    _, alpha, vv = PM.varistor_law(mov)[:3]
    m0, m1 = runs['m0'], runs['m1']
    landed = []
    for deck_run, row in ((m0, ca), (m1, mov)):
        if deck_run['deck'] != PM.check_deck(row):
            landed.append(('deck changed', row['name']))
            continue
        for k, (i, v) in enumerate(PM.check_points(row), 1):
            landed.append((row['name'], i, v, deck_run['vectors']['esd_p%d' % k]['real'][0]))
    worst = max((abs(x[3] - x[2]) for x in landed if len(x) == 4), default=9.9)
    check('ESD-6 A BIDIRECTIONAL TVS FROM ITS NUMBERS (Bourns SMBJ REV. 09/20, the SMBJ5.0CA column): two equal diodes cathode to cathode, RS 6.834 mOhm '
          'and BV 6.285 V each, derived so the PAIR lands on V_BR max 7.00 V at 10 mA and V_C 12.0 V at 326.5 A; the forward N = 1 is a labelled '
          'assumption (no forward pair for a bidirectional part) - and econ-core\'s ngspice puts it on all four points (both polarities) within 1 mV',
          ca['modelled'] == 'yes' and 'RS=0.00683381' in ca['model'] and 'BV=6.28519' in ca['model'] and 'LABELLED' in ca['model_why']
          and len([x for x in landed if x[0] == 'smbj5.0ca']) == 4 and worst < 1e-3, landed)
    check('ESD-6 A VARISTOR FROM ITS NUMBERS (TDK SIOV StandarD series, March 2018, S05K11): the varistor law through V_V max 19.8 V (18 V +10 %) at '
          '1 mA and v_c,max 36 V at i_c 1 A - alpha 11.55 - with its 1750 pF; ngspice (sgn(V) pwr(abs(V), alpha): KiCad 10 has no pwrs) lands on both '
          'points, both polarities, within 1 mV; the snapback polymer is still refused (its 30 V clamp comes without its current)',
          mov['modelled'] == 'yes' and abs(alpha - 11.555) < 1e-3 and vv == 19.8 and 'sgn(v(esd_p1))' in '\n'.join(PM.elements(mov, 1, 'x')[0])
          and 'Cprot1 esd_p1 0 1750p' in PM.elements(mov, 1, 'x')[0] and len([x for x in landed if x[0] == 's05k11']) == 4
          and 'peak pulse 100 A' in mov['ratings'] and cg['modelled'] == 'no' and 'without the current' in cg['model_why'], (mov['model'], landed))


def run_cdm_loop(check):
    from pcb.custom import esd_cdm as C
    from pcb.custom import esd_events as E
    runs = _runs()
    rows = {r['module']: r for r in C.cdm_check()}
    s, g = rows['small'], rows['large']
    check('ESD-7 THE CDM LOOP FROM PUBLIC NUMBERS (Industry Council White Paper 2 rev. 3.0): C = the JS-002 module (6.8 / 55 pF, Table C-II), R = 25 Ohm '
          'spark + 1 Ohm detector (Annex D, Figure D2), L = 15.88 nH solved so Eq. 9 gives Table C-III\'s 7.2 A on the small module at 500 V; the large '
          'module is then a CHECK - 12.8 A against 12.1 A +-15 %, inside; the loop\'s shape is slower than JS-002\'s (rise 278 / 596 ps, FWHM 0.70 / '
          '2.1 ns) - reported as NOT met, not hidden',
          abs(C.L_LOOP - 15.876e-9) < 0.01e-9 and C.R_LOOP == 26.0 and s['peak_ok'] and g['peak_ok'] and abs(g['peak_a'] - 12.816) < 0.01
          and not s['rise_ok'] and not s['fwhm_ok'] and not g['fwhm_ok'] and g['role'] == 'a check' and set(E.MODELS) >= {'cdm-small', 'cdm-large'}
          and E.MODELS['cdm-small']['levels'] == [125.0, 250.0, 500.0, 750.0, 1000.0], rows)
    shapes = {k: _shape(runs[k]) for k in ('m2', 'm3')}
    same = all(runs[k]['deck'] == E.short_deck(m, 500.0) for k, m in (('m2', 'cdm-small'), ('m3', 'cdm-large')))
    check('ESD-7 NGSPICE AGREES WITH THE LOOP\'S OWN SOLUTION: the deck\'s network (switch, 26 Ohm, 15.9 nH) into a short on econ-core\'s libngspice - '
          'peak 7.199 / 12.81 A, rise and FWHM within 1 % of the closed form',
          same and abs(shapes['m2'][0] - s['peak_a']) / s['peak_a'] < 1e-3 and abs(shapes['m3'][0] - g['peak_a']) / g['peak_a'] < 1e-3
          and all(abs(shapes[k][1] - r['rise_s']) / r['rise_s'] < 0.01 and abs(shapes[k][2] - r['fwhm_s']) / r['fwhm_s'] < 0.01
                  for k, r in (('m2', s), ('m3', g))), (shapes, same))


def run_new_protected_pins(check):
    from board.custom import esd_areas as EA
    from board.custom import esd_footholds as EF
    from pcb.custom import esd_events as E
    run = _recorded()
    _pin()
    out = {}
    for label, part, model, level in (('fa', 'smbj5.0ca', None, None), ('fb', 's05k11', None, None), ('fc', '', 'cdm-small', 500.0),
                                      ('fd', 'smbj5.0a', 'cdm-small', 500.0)):
        if part:
            EA.toggle_protection(None, UNO_PIN, part)
        res = EF.run_pin_event(None, 'datasheet', 'arduino-uno-r3', UNO_PIN, model=model, level_v=level, runner=run)
        out[label] = (res, E.protection_results(None, res['run'])[0] if res.get('run') else [])
        if part:
            EA.toggle_protection(None, UNO_PIN, part)
    pin = {k: (r['rows'][0] if r.get('rows') else {}) for k, (r, _) in out.items()}
    prot = {k: (p[0] if p else {}) for k, (_, p) in out.items()}
    check('ESD-6 ON THE UNO\'S PIN, HBM 2 kV: the bidirectional SMBJ5.0CA holds it at 7.28 V (its forward diode adds to the one-way part\'s 7.15 V) - '
          'still above the ATmega328P\'s 5.5 V; the S05K11 varistor lets 35.6 V through at 1.32 A, and the row says 1.32 A is past its cited 1 A, '
          'where the law understates the voltage',
          all(out[k][0]['ok'] for k in ('fa', 'fb')) and abs(pin['fa'].get('peak_v', 0) - 7.2804) < 0.01 and pin['fa']['breaks'].startswith('BREAKS')
          and abs(pin['fb'].get('peak_v', 0) - 35.608) < 0.05 and prot['fa'].get('in_model', '').startswith('yes')
          and prot['fb'].get('in_model', '').startswith('NO') and 'understates' in prot['fb']['in_model'] and prot['fb']['breaks'].startswith('no'),
          (pin, prot))
    check('ESD-7 ON THE UNO\'S PIN, CDM 500 V (small module): bare, the pin rises to 312 V (BREAKS; 5.96 A into its 10 pF, against 7.2 A into a short); '
          'with the SMBJ5.0A it is held at 7.27 V - still above 5.5 V - the TVS carrying 7.19 A (2.2 % of its I_PP) and back in time',
          all(out[k][0]['ok'] for k in ('fc', 'fd')) and abs(pin['fc'].get('peak_v', 0) - 311.81) < 0.5 and pin['fc']['breaks'].startswith('BREAKS')
          and abs(out['fc'][0]['summary']['expected_current_a'] - 7.2) < 1e-6 and abs(out['fc'][0]['summary']['peak_current_a'] - 5.963) < 0.01
          and abs(pin['fd'].get('peak_v', 0) - 7.2744) < 0.01 and pin['fd']['recovered'] == 'yes' and abs(prot['fd'].get('peak_current_a', 0) - 7.188) < 0.01
          and 'Eq. 9' in out['fd'][0]['summary']['basis'], (pin, prot, out['fc'][0].get('summary')))
    _fresh()


def run_cdm_doors(check):
    import falcon
    import falcon.testing as ft
    from board.custom import board_details as BD
    from board.esd_areas_api import EsdAreasAPI
    from pcb.pcb_esd_api import PcbEsdAPI
    _fresh()
    app = falcon.App()
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        EsdAreasAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
        PcbEsdAPI(polServer=types.SimpleNamespace(falconServer=app), manager=None)
    cl = ft.TestClient(app)
    models = {r['name']: r for r in cl.simulate_get('/api/pcb/esd-models').json['rows']}
    cat = {r['name']: r for r in cl.simulate_get('/api/board/protection-parts').json['rows']}
    page_models = {r['model']: r for r in BD.part('datasheet', 'arduino-uno-r3', 'esd-models', None, {})[0]}
    check('ESD-6/7 THE DOORS: the models door lists the two CDM modules with their inductance; the Board Details models table shows it '
          '(series LCR loop, 15.9 nH); the protection catalogue offers the SMBJ5.0CA and the S05K11 as modelled',
          abs(models['cdm-small']['l_h'] - 15.876e-9) < 1e-11 and models['hbm']['l_h'] == 0.0 and page_models['cdm-large']['source'] == 'series LCR loop'
          and abs(page_models['cdm-small']['inductance_nh'] - 15.876) < 0.01 and cat['smbj5.0ca']['modelled'] == 'yes' and cat['s05k11']['modelled'] == 'yes',
          (models.get('cdm-small'), page_models.get('cdm-small')))
    _fresh()
