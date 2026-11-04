"""cmod_measure_selftest - msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md): REAL READINGS AGAINST THE SIMULATION AT A NODE, manual entry first. The UNO
light's led-on node (a reached run whose electrical collateral names the circuit state led-on) gives its measurement points from the ngspice .op of that
state - the LED net, the R1/LED junction, the button net, the LED current, the 5 V rail under the node's load; a built unit takes typed readings, kept as
typed, judged on read against the prediction and a cited accuracy (a FIXTURE meter here - no real instrument is seeded until its datasheet is read,
D-msv-2): in-band, unexplained, unjudged, over-range, stale; refusals; the doors; the manifest and the page.

Needs ngspice (the cst slice's engine) - the first check says so when it is missing.

    PYTHONPATH=.:modules python3 -m cmod.cmod_measure_selftest      # from polari-framework/
"""
import json
import os
import sys
import types

passed = total = 0
BS = 'uno-light-on-desk'
NODE = BS + ':light-on'
HEX = 'a' * 64


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seed(m, outcome='reached', state='led-on'):
    from cmod.custom import config_rows as R
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=18.0, ambient_max_c=30.0)
    R.upsert(m, 'BenchSolution', BS, bench='home-bench', firmware_solution='uno-light', conditions='room')
    R.upsert(m, 'StructNode', NODE, bench_solution=BS, title='light on')
    R.upsert(m, 'StructNodeRun', NODE + '#run1', node=NODE, outcome=outcome, hex_sha256=HEX)
    R.upsert(m, 'StructNodeRunEdge', NODE + '#run1:e1', run=NODE + '#run1', order=1,
             collaterals='pin-level PD6: high ; electrical circuit: ok - circuit uno-button-clock in state %s (the LED lit); no finding' % state)
    # a FIXTURE meter: invented numbers that only exercise the arithmetic - never a real instrument's (D-msv-2: the user's own are read first)
    R.upsert(m, 'InstrumentAccuracy', 'fixture-dmm-acc-vdc-6', instrument='fixture-dmm', function='V dc', range_max=6.0, pct_reading=0.5, counts=2,
             resolution=0.001, cite='FIXTURE (selftest only)')
    R.upsert(m, 'InstrumentAccuracy', 'fixture-dmm-acc-idc-0.2', instrument='fixture-dmm', function='I dc', range_max=0.2, pct_reading=1.0, counts=3,
             resolution=1e-4, cite='FIXTURE (selftest only)')
    R.upsert(m, 'InstrumentAccuracy', 'fixture-dmm-acc-idc-0.02', instrument='fixture-dmm', function='I dc', range_max=0.02, pct_reading=-1.0, counts=0,
             resolution=1e-5, cite='FIXTURE (selftest only): an unread line')


def main():
    from cmod.custom import config_rows as R
    from cmod.custom import measure_points as MP
    from cmod.custom import measure_readings as MR
    from electrodevice.custom.spice_run import capability
    if not capability()['available']:
        check('ngspice is available (the cst slice engine)', False, 'ngspice missing: run in the backend image')
        return
    m = _manager()
    _seed(m)
    pts = {p['name'].split('-mp-')[-1]: p for p in MP.derive(m, NODE)}
    check('POINTS DERIVED from the run\'s circuit state led-on: the three nets, the LED current, the 5 V rail - each with where the probes go',
          set(pts) == {'v-led-control', 'v-led-anode', 'v-button-input', 'i-ubc-led1', 'v-5v-rail'}, sorted(pts))
    led = pts.get('i-ubc-led1', {})
    check('the LED current predicted = the bss-12 figure (14.715 mA, the ideal-source worst-case bound - the basis says so)',
          abs(led.get('nominal', 0) - 0.0147152) < 2e-6 and 'worst-case bound' in led.get('basis', '') and 'series' in led.get('where', ''), led)
    check('the LED net is probed at D6 or D3 (the board pins on it); the R1/LED junction has no pin and says so',
          'D6' in pts['v-led-control']['where'] and 'no board pin' in pts['v-led-anode']['where'] and abs(pts['v-led-anode']['nominal'] - 1.762652) < 1e-5,
          (pts['v-led-control']['where'], pts['v-led-anode']['where']))
    rail = pts['v-5v-rail']
    check('the rail = VCC minus the ground return over R_supply (both knobs, said): 5 - 14.715 mA x 0.5 ohm', abs(rail['nominal'] - (5.0 - 0.0147152 * 0.5)) < 1e-5
          and 'R_supply' in rail['basis'], rail)
    check('the points carry the run, its build and the state', all(p['run'] == NODE + '#run1' and p['hex_sha256'] == HEX and p['state'] == 'led-on' for p in pts.values()))
    again = MP.derive(m, NODE)
    check('derive again = the same points (upserted, no duplicates)', len(again) == 5 and len(R.rows(m, 'MeasurementPoint', node=NODE)) == 5)

    m2 = _manager()
    _seed(m2, outcome='diverged')
    try:
        MP.derive(m2, NODE)
        check('a node with no reached run is refused (409)', False)
    except R.ConfigRefused as e:
        check('a node with no reached run is refused (409): run it first', e.status == 409 and 'run it first' in e.why, e.why)

    u = MR.add_unit(m, BS, {'build_method': 'breadboard', 'hex_sha256': HEX, 'built_by': 'a person'})
    check('a built unit: named <bs>-unit-1 when unnamed, its build kept', u['name'] == BS + '-unit-1' and u['hex_sha256'] == HEX, u)
    try:
        MR.add_unit(m, BS, {'build_method': 'glued'})
        check('a build method outside the list is refused', False)
    except R.ConfigRefused:
        check('a build method outside the list is refused', True)
    unit = u['name']
    r1 = MR.add_reading(m, unit, {'point': rail['name'], 'value': '4.995 V', 'instrument': 'fixture-dmm', 'who': 'a person'})
    check('IN BAND: 4.995 V on the rail vs 4.9926 V, band +/-(0.5 % + 2 counts of 1 mV) = 27 mV', r1['verdict'] == 'in-band' and abs(r1['band'] - (0.005 * 4.995 + 0.002)) < 1e-9
          and r1['entered'] == '4.995 V' and r1['via'] == 'manual', r1['words'])
    r2 = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.2', 'unit': 'mA', 'instrument': 'fixture-dmm', 'range_max': '200 mA'})
    check('UNEXPLAINED: 14.2 mA vs 14.715 mA is outside the 200 mA range\'s +/-0.442 mA (no tolerance band yet - msv-1 - so a person looks)',
          r2['verdict'] == 'unexplained' and abs(r2['value'] - 0.0142) < 1e-12 and 'msv-1' in r2['words'], r2['words'])
    r3 = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.7 mA', 'instrument': 'fixture-dmm', 'range_max': '200 mA'})
    check('IN BAND: 14.7 mA (a later reading of the same point - kept beside the first, never edited)', r3['verdict'] == 'in-band' and r3['name'].endswith('#r2'), r3['words'])
    r4 = MR.add_reading(m, unit, {'point': pts['v-led-control']['name'], 'value': '4.6 V'})
    check('UNJUDGED: no instrument said - the delta stands (-0.4 V), the band is unmeasured', r4['verdict'] == 'unjudged' and abs(r4['delta'] + 0.4) < 1e-9
          and 'unmeasured' in r4['words'], r4['words'])
    r5 = MR.add_reading(m, unit, {'point': led['name'], 'value': '250 mA', 'instrument': 'fixture-dmm', 'range_max': '200 mA'})
    check('OVER RANGE: 250 mA on the 200 mA range', r5['verdict'] == 'over-range', r5['words'])
    r6 = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.7 mA', 'instrument': 'fixture-dmm', 'range_max': '20 mA'})
    r6b = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.7 mA', 'instrument': 'fixture-dmm'})
    check('no range said = the SMALLEST range that holds the value (here the 20 mA one, whose line is unread)', 'range 0.02' in r6b['words'], r6b['words'])
    check('an UNREAD accuracy line (-1) is unjudged, said', r6['verdict'] == 'unjudged' and 'unread' in r6['words'], r6['words'])
    for bad, why in (({'point': led['name'], 'value': '5 V'}, 'a V unit on a current point'), ({'point': led['name'], 'value': 'about 14'}, 'not a number'),
                     ({'point': 'nope', 'value': '1 V'}, 'no such point'), ({'point': led['name'], 'value': '1 mA', 'via': 'telepathy'}, 'an unknown via'),
                     ({'point': led['name'], 'value': '1 mA', 'instrument': 'no-such-meter'}, 'no such instrument')):
        try:
            MR.add_reading(m, unit, bad)
            check('refused: %s' % why, False)
        except R.ConfigRefused as e:
            check('refused: %s (%s)' % (why, e.status), True)
    rows = MR.readings(m, unit)
    cur = [r for r in rows if r['point'] == led['name'] and r['current']]
    check('readings newest first, judged on read; one current per point', len(rows) == 7 and len(cur) == 1 and cur[0]['name'] == r6b['name'], [(r['name'], r['current']) for r in rows])
    MR.add_unit(m, BS, {'name': unit, 'hex_sha256': 'b' * 64})
    r7 = MR.add_reading(m, unit, {'point': rail['name'], 'value': '4.99 V', 'instrument': 'fixture-dmm'})
    check('STALE: a reading on another build than the prediction says so', r7['stale'] and 'STALE' in r7['words'], r7['words'])
    # the seeded EXAMPLE meters (D-msv-2: the user owns none yet)
    from instruments.instruments_seed import SEED_ACCURACY
    for a in SEED_ACCURACY:
        R.upsert(m, 'InstrumentAccuracy', a['name'], **{k: v for k, v in a.items() if k != 'name'})
    k = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.6 mA', 'instrument': 'tekpower-tp4000zc'})
    check('TP4000ZC example (the sigrok + cheap meter): 14.6 mA picks the 40 mA range, band 1.5 % + 5 x 10 uA = 0.269 mA, so -0.115 mA is IN BAND',
          'on the 0.04 range' in k['words'] and abs(k['band'] - (0.015 * 0.0146 + 5e-5)) < 1e-12 and k['verdict'] == 'in-band', k['words'])
    f = MR.add_reading(m, unit, {'point': led['name'], 'value': '14.2 mA', 'instrument': 'tekpower-tp4000zc'})
    check('TP4000ZC example: 14.2 mA (-0.515 mA) is outside its 0.263 mA band - unexplained', f['verdict'] == 'unexplained', f['words'])

    # the doors
    import falcon
    import falcon.testing
    from cmod.cmod_measure_api import MeasureAPI
    app = falcon.App()
    MeasureAPI(polServer=types.SimpleNamespace(falconServer=app), manager=m)
    c = falcon.testing.TestClient(app)
    base = '/api/cmod/bench-topology/%s' % BS
    g = c.simulate_get(base + '/nodes/light-on/measurement-points')
    check('door GET .../nodes/{slug}/measurement-points', g.status_code == 200 and len(g.json['rows']) == 5, g.status_code)
    p = c.simulate_post(base + '/units/%s/readings' % unit, body=json.dumps({'point': rail['name'], 'value': '4.98 V', 'instrument': 'fixture-dmm'}))
    check('door POST .../units/{unit}/readings -> the row + its judgement', p.status_code == 200 and p.json['verdict'] == 'in-band', p.json)
    p = c.simulate_post(base + '/units/%s/readings' % unit, body=json.dumps({'point': rail['name'], 'value': '4.98 A'}))
    check('door: a wrong unit = 422 in words', p.status_code == 422 and 'point measures V' in p.json['error'], p.json)
    p = c.simulate_get('/api/cmod/bench-topology/other-bench/units/%s/readings' % unit)
    check('door: a unit of another Bench Solution = 404', p.status_code == 404, p.status_code)
    p = c.simulate_post(base + '/units', body=json.dumps({'build_method': 'pcb'}))
    check('door POST .../units', p.status_code == 200 and p.json['name'] == BS + '-unit-2', p.json)
    p = c.simulate_post(base + '/nodes/no-such/measurement-points')
    check('door: deriving for no node = 404', p.status_code == 404, p.status_code)

    # the manifest and the page
    here = os.path.dirname(os.path.abspath(__file__))
    man = json.load(open(os.path.join(here, 'polari-app.json')))
    files = man['files']
    ok = all(os.path.exists(os.path.join(here, f + '.py')) for f in ['objects/cmod/BuiltUnit', 'objects/cmod/MeasurementPoint', 'objects/cmod/MeasurementReading']
             + ['custom/measure_points', 'custom/measure_readings', 'cmod_measure_api'])
    check('the manifest lists the rows, the code, the doors and this selftest', ok and 'cmod_measure_api' in files['api'] and 'custom/measure_readings' in files['custom']
          and 'cmod_measure_selftest' in files['selftests'] and {'BuiltUnit', 'MeasurementPoint', 'MeasurementReading', 'MeasureAPI'} <= set(man['classes']))
    from cmod.cmod_basis import CMOD_CLASSES
    from instruments.instruments_basis import INSTRUMENTS_CLASSES
    check('the classes are registered (cmod: the unit, point, reading; instruments: the accuracy)',
          {'BuiltUnit', 'MeasurementPoint', 'MeasurementReading'} <= {k.__name__ for k in CMOD_CLASSES} and 'InstrumentAccuracy' in {k.__name__ for k in INSTRUMENTS_CLASSES})
    from cmod.hardware_events_page import HARDWARE_EVENTS_PAGES
    text = json.dumps(HARDWARE_EVENTS_PAGES)
    check('the Hardware Events page has the Measured tab: units, the node\'s points, the manual reading form, the judged readings',
          all(k in text for k in ('he-units', 'he-points', 'he-reading-form', 'he-readings', '/units/{scope:unit}/readings', '/measurement-points')))


if __name__ == '__main__':
    main()
    print('%d/%d passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
