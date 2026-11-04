"""cmod_procedure_selftest - msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b): THE GENERATED STEP-BY-STEP TEST AND THE GUIDED SHEET.

The UNO light's topology is applied from its shipped spec (bss-8). Its "on by the button" node has a reached run whose electrical collateral names
the state led-on, and so it has measurement points (msv-0). The procedure is generated from those, never typed. The test checks:
- the order: power off, the continuity checks, power on, flash, boot, every node
- the words
- a node continuing from the one before vs RESET first
- what is owed
- frozen once per build
- a session on a built unit: answered, judged, resumed (the presses asked again), done
- the left pane's picture, the print view, the doors, the manifest and the page.

Needs ngspice (the cst slice's engine) - the first check says so when it is missing.

    PYTHONPATH=.:modules python3 -m cmod.cmod_procedure_selftest      # from polari-framework/
"""
import json
import os
import sys
import types

passed = total = 0
BS = 'uno-light-on-desk'
NODE = BS + ':on-by-button'
HEX = 'c' * 64


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _refused(fn):
    from cmod.custom.config_rows import ConfigRefused
    try:
        fn()
    except ConfigRefused as e:
        return e.status
    return None


def main():
    from cmod.cmod_light_topology_selftest import _manager, _seed
    from cmod.custom import bench_topology_spec as SP
    from cmod.custom import config_rows as R
    from cmod.custom import measure_points as MP
    from cmod.custom import measure_readings as MR
    from cmod.custom import procedure_svg as SVG
    from cmod.custom import test_procedures as TP
    from cmod.custom import test_sessions as TS
    from electrodevice.custom.spice_run import capability
    from instruments.instruments_seed import SEED_ACCURACY
    if not capability()['available']:
        check('ngspice is available (the cst slice engine)', False, 'ngspice missing: run in the backend image')
        return
    m = _manager()
    _seed(m)
    SP.apply(m, BS)
    R.upsert(m, 'StructNodeRun', NODE + '#run1', node=NODE, outcome='reached', hex_sha256=HEX)
    R.upsert(m, 'StructNodeRunEdge', NODE + '#run1:e1', run=NODE + '#run1', order=1,
             collaterals='pin-level PD6: high ; electrical circuit: ok - circuit uno-button-clock in state led-on (the LED lit); no finding')
    MP.derive(m, NODE)
    for a in SEED_ACCURACY:
        R.upsert(m, 'InstrumentAccuracy', a['name'], **{k: v for k, v in a.items() if k != 'name'})

    g = TP.generate(m, BS)
    st = g['steps']
    kinds = [s['kind'] for s in st]
    on = next(i for i, s in enumerate(st) if s['words'].startswith('plug the USB'))
    check('ORDER: power OFF first, every continuity check before power ON, then flash + boot; the build is the one its runs used',
          st[0]['words'].startswith('power OFF') and set(kinds[1:on]) == {'continuity'} and 'continuity' not in kinds[on:]
          and st[on + 1]['words'].startswith('flash build %s..' % HEX[:12]) and st[on + 2]['words'].startswith('wait for the reset') and g['hex_sha256'] == HEX,
          [(s['kind'], s['words'][:40]) for s in st[:on + 3]])
    cont = {(s['plus_at'], s['minus_at'], s.get('part', '')): s['expect'] for s in st if s['kind'] == 'continuity'}
    check('CONTINUITY from the circuit rows: 5V-GND no steady beep; D6-D3 BEEP (both on LED_CONTROL); each used pin against its header neighbours NO beep '
          '(D6-D5, D6-D7, D3-D2, D3-D4, D2-D1); the switch D2-GND no beep released, BEEP held',
          cont[('5V', 'GND', '')].startswith('NO steady beep') and cont[('D6', 'D3', '')].startswith('BEEP')
          and all(cont[(a, b, '')].startswith('NO beep') for a, b in (('D6', 'D5'), ('D6', 'D7'), ('D3', 'D2'), ('D3', 'D4'), ('D2', 'D1')))
          and cont[('D2', 'GND', 'ubc-sw1')].startswith('BEEP while held') and kinds.count('continuity') == 9
          and sum(1 for s in st if s['kind'] == 'continuity' and s['part'] == 'ubc-sw1' and s['expect'].startswith('NO beep')) == 1, cont)
    i = next(k for k, s in enumerate(st) if s['kind'] == 'stimulus' and s['node'] == NODE and s['words'].startswith('press and release the button'))
    mine = st[i:i + 7]
    check('ON BY THE BUTTON: after RESET, "press and release the button on D2 (ubc-sw1)"; then its 5 measurements (the msv-0 points, their probe words '
          'and predictions) and one look: the LED ubc-led1 LIT (circuit state led-on)',
          st[i - 1]['words'].startswith('press and release the RESET') and st[i]['words'] == 'press and release the button on D2 (ubc-sw1)'
          and [s['kind'] for s in mine] == ['stimulus'] + ['measure'] * 5 + ['observe'] and mine[-1]['expect'] == 'it is LIT'
          and any(s['mode'] == 'I dc' and s['expect'].startswith('14.72 mA') for s in mine), [(s['kind'], s['words'][:50], s['expect'][:30]) for s in mine])
    after = st[i + 7]
    check('A NODE THAT CONTINUES the one just tested needs no RESET (idle: "wait - nothing to touch" right after); one that does not, starts with RESET',
          after['words'].startswith('wait') and after['node'].endswith(':idle') and st[i + 8]['words'].startswith('press and release the RESET'), (after, st[i + 8]))
    check('OWED: the 10 nodes with no reached run are named (their stimuli listed, their checks owed); the run one is not',
          len(g['owed']) == 10 and not any(o.startswith(NODE + ':') for o in g['owed']), g['owed'])
    check('the held press says keep holding; the long press its 0.5 s knob; a command says what is sent; the bounce a jabbing tap',
          any('keep holding' in s['words'] for s in st) and any('hold it for 0.5 s' in s['words'] for s in st)
          and any(s['words'].startswith("send the command 'led_on'") for s in st) and any('jabbing' in s['words'] for s in st))

    p = TP.freeze(m, BS)
    p2 = TP.freeze(m, BS)
    p3 = TP.freeze(m, BS, {'hex_sha256': 'd' * 64})
    check('FROZEN per build: rows <proc>-s<n>; an unchanged regeneration returns the same procedure; another build gets a new one',
          p['name'] == BS + '-proc-1' and len(p['rows']) == len(st) and p['rows'][0]['name'] == BS + '-proc-1-s1' and p2['unchanged'] and p2['name'] == p['name']
          and p3['name'] == BS + '-proc-2' and p['owed'].count('no reached run') == 10, (p['name'], p2.get('unchanged'), p3['name']))

    unit = MR.add_unit(m, BS, {'hex_sha256': HEX})['name']
    R.upsert(m, 'BenchSolution', 'other-bench-solution', bench='home-bench', firmware_solution='uno-light', conditions='room')
    other = MR.add_unit(m, 'other-bench-solution', {})['name']
    check('session refusals: an unknown procedure 404, a unit of another Bench Solution 409, an unknown mode 422',
          _refused(lambda: TS.start(m, unit, {'procedure': 'nope'})) == 404 and _refused(lambda: TS.start(m, other, {'procedure': p['name']})) == 409
          and _refused(lambda: TS.start(m, unit, {'procedure': p['name'], 'mode': 'telepathy'})) == 422)
    s = TS.start(m, unit, {'procedure': p['name'], 'who': 'a tester'})
    check('a session <unit>-<proc>-t1, open, guided', s['name'] == '%s-%s-t1' % (unit, p['name']) and s['state'] == 'open' and s['mode'] == 'guided', s)
    rows = p['rows']
    by = {(r['plus_at'], r['minus_at'], r['part']): r['name'] for r in rows if r['kind'] == 'continuity'}
    a1 = TS.answer(m, s['name'], by[('D6', 'D3', '')], {'outcome': 'beep'})
    a2 = TS.answer(m, s['name'], by[('D2', 'D1', '')], {'outcome': 'beep', 'note': 'a solder bridge?'})
    check('CONTINUITY judged: D6-D3 beep = pass; D2-D1 beep = FAIL (it should not)', a1['verdict'] == 'pass' and a2['verdict'] == 'fail', (a1, a2))
    check('a wrong answer for the step kind is refused (422)', _refused(lambda: TS.answer(m, s['name'], by[('D6', 'D3', '')], {'outcome': 'yes'})) == 422)
    meas = {r['mode'] + ':' + r['point'].split('-mp-')[-1]: r['name'] for r in rows if r['kind'] == 'measure'}
    led = meas['I dc:i-ubc-led1']
    rail = meas['V dc:v-5v-rail']
    obs = next(r['name'] for r in rows if r['kind'] == 'observe')
    for r in rows:   # everything up to and including the button press, done
        if r['order'] <= st[i]['order'] and r['kind'] in ('setup', 'stimulus'):
            TS.answer(m, s['name'], r['name'], {'outcome': 'done'})
    a3 = TS.answer(m, s['name'], led, {'value': '14.6 mA', 'instrument': 'tekpower-tp4000zc'})
    a4 = TS.answer(m, s['name'], rail, {'value': '4.6 V', 'instrument': 'tekpower-tp4000zc'})
    check('MEASURE steps are ordinary readings (naming the session and the step), judged: the LED 14.6 mA on the TP4000ZC = pass; the rail 4.6 V = unexplained',
          a3['verdict'] == 'pass' and a3['session'] == s['name'] and a3['step'] == led and a4['verdict'] == 'unexplained', (a3.get('words'), a4.get('words')))
    a5 = TS.answer(m, s['name'], obs, {'outcome': 'no'})
    check('a LOOK answered no = fail', a5['verdict'] == 'fail')
    v = TS.sheet(m, s['name'])
    check('THE SHEET: one row per step in order with the answer and verdict; the summary counts; next = the first pending step',
          len(v['rows']) == len(rows) and v['summary'].get('pass') == 2 and v['summary'].get('fail') == 2 and v['summary'].get('unexplained') == 1
          and v['next'] is not None and v['next']['verdict'] == 'pending', v['summary'])
    # resume before the node's remaining measurements: the RESET and the press are asked again
    rest = [r for r in rows if r['node'] == NODE and r['kind'] == 'measure' and r['name'] not in (led, rail)]
    for r in rows:   # the continuity checks still pending: answered, so the next pending is the node's measurement
        if r['kind'] == 'continuity' and r['name'] not in (by[('D6', 'D3', '')], by[('D2', 'D1', '')]):
            TS.answer(m, s['name'], r['name'], {'outcome': 'beep' if r['expect'].startswith('BEEP') else 'no-beep'})
    v0 = TS.sheet(m, s['name'])
    r = TS.resume(m, s['name'])
    again = [x for x in r['rows'] if x['ask_again']]
    check('RESUME: the next step was a measurement of on-by-button, so the RESET before it and the press are ASKED AGAIN (next = the RESET)',
          v0['next']['step'] == rest[0]['name'] and [x['words'][:30] for x in again] == ['press and release the RESET bu', 'press and release the button o']
          and r['next']['step'] == again[0]['step'], ([x['words'] for x in again], r['next']))
    for x in again:
        TS.answer(m, s['name'], x['step'], {'outcome': 'done'})
    check('...answered again, the next is the measurement once more', TS.sheet(m, s['name'])['next']['step'] == rest[0]['name'])
    for x in TS.sheet(m, s['name'])['rows']:
        if x['verdict'] == 'pending':
            TS.answer(m, s['name'], x['step'], {'outcome': 'skipped'} if x['kind'] != 'continuity' else {'outcome': 'no-beep'})
    end = TS.sheet(m, s['name'])
    check('every step answered: the session is DONE, nothing pending; a skipped measurement is skipped', R.get(m, 'TestSession', s['name'])['state'] == 'done'
          and end['next'] is None and 'pending' not in end['summary'] and end['summary'].get('skipped', 0) >= 1, end['summary'])

    svg = SVG.draw(m, by[('D6', 'D3', '')])
    anode = next(x['name'] for x in rows if x['kind'] == 'measure' and x['plus_at'] == 'LED_ANODE')
    svg2 = SVG.draw(m, anode)
    check('THE LEFT PANE: an SVG of the UNO headers + the circuit parts; D6-D3 rings the red and black probes on the two pins; the R1/LED junction (no board pin) '
          'lights its net red among the parts', svg.startswith('<svg') and svg.count('stroke="%s" stroke-width="4"' % SVG.RED) == 1
          and svg.count('stroke="%s" stroke-width="4"' % SVG.BLACK) == 1 and 'stroke="%s" stroke-width="4"' % SVG.RED not in svg2
          and ('fill="%s">LED_ANODE' % SVG.RED) in svg2, svg2[:200])
    html = SVG.print_view(m, s['name'])
    check('THE PRINT VIEW: every step as a block with a box to write in, the pictures inline', html.startswith('<!doctype html>') and html.count('<section>') == len(rows)
          and html.count('<svg') >= 9)

    # the doors
    import falcon
    import falcon.testing
    from cmod.cmod_measure_api import MeasureAPI
    app = falcon.App()
    MeasureAPI(polServer=types.SimpleNamespace(falconServer=app), manager=m)
    c = falcon.testing.TestClient(app)
    base = '/api/cmod/bench-topology/%s' % BS
    pv = c.simulate_get(base + '/procedures/preview')
    pp = c.simulate_post(base + '/procedures', body='{}')
    ls = c.simulate_get(base + '/procedures')
    sp = c.simulate_get(base + '/procedures/%s/steps' % p['name'])
    pic = c.simulate_get(base + '/procedures/%s/steps/%s/picture' % (p['name'], rows[2]['name']))
    ns = c.simulate_post(base + '/units/%s/sessions' % unit, body=json.dumps({'procedure': p['name']}))
    sh = c.simulate_get(base + '/sessions/%s' % ns.json['name'])
    an = c.simulate_post(base + '/sessions/%s/steps/%s' % (ns.json['name'], rows[0]['name']), body=json.dumps({'outcome': 'done'}))
    rs = c.simulate_post(base + '/sessions/%s/resume' % ns.json['name'], body='{}')
    pr = c.simulate_get(base + '/sessions/%s/print' % ns.json['name'])
    sm = c.simulate_get(base + '/sessions/%s/summary' % ns.json['name'])
    check('doors: preview (nothing stored), POST procedures (unchanged), list, steps, the picture as image/svg+xml, start a session, the sheet, answer, resume, '
          'print as text/html, the summary rows', pv.status_code == 200 and len(pv.json['rows']) == len(st) and pp.json.get('unchanged') and len(ls.json['rows']) == 2
          and len(sp.json['rows']) == len(rows) and pic.headers['content-type'].startswith('image/svg+xml') and pic.text.startswith('<svg')
          and ns.status_code == 200 and len(sh.json['rows']) == len(rows) and an.json['verdict'] == 'done' and rs.status_code == 200
          and pr.headers['content-type'].startswith('text/html') and any(x['verdict'] == 'done' for x in sm.json['rows']),
          (pv.status_code, pp.json.get('unchanged'), pic.headers.get('content-type'), ns.status_code, an.json))
    bad = c.simulate_get('/api/cmod/bench-topology/other-bench-solution/procedures/%s/steps' % p['name'])
    bad2 = c.simulate_get('/api/cmod/bench-topology/other-bench-solution/sessions/%s' % ns.json['name'])
    bad3 = c.simulate_post(base + '/sessions/%s/steps/%s' % (ns.json['name'], rows[0]['name']), body=json.dumps({'outcome': 'beep'}))
    check('door refusals: a procedure / session of another Bench Solution 404, a wrong answer 422',
          bad.status_code == 404 and bad2.status_code == 404 and bad3.status_code == 422, (bad.status_code, bad2.status_code, bad3.status_code))

    here = os.path.dirname(os.path.abspath(__file__))
    man = json.load(open(os.path.join(here, 'polari-app.json')))
    flat = json.dumps(man)
    check('the manifest lists the four rows, the three custom modules and this selftest',
          all(x in flat for x in ('objects/cmod/TestProcedure"', 'objects/cmod/TestProcedureStep"', 'objects/cmod/TestSession"', 'objects/cmod/TestStepMark"',
                                  'custom/test_procedures', 'custom/test_sessions', 'custom/procedure_svg', 'cmod_procedure_selftest')))
    from cmod.cmod_basis import CMOD_CLASSES
    check('the classes are registered', {'TestProcedure', 'TestProcedureStep', 'TestSession', 'TestStepMark'} <= {k.__name__ for k in CMOD_CLASSES})
    from cmod.hardware_events_page import HARDWARE_EVENTS_PAGES
    pdef = json.loads(HARDWARE_EVENTS_PAGES[0]['definition'])
    tab = next(t for t in pdef['tabs'] if t['key'] == 'sheet')
    ids = [it['id'] for row in tab['rows'] for it in row['items']]
    ok = ids == ['he-proc-form', 'he-procs', 'he-session-form', 'he-sessions', 'he-step-picture', 'he-sheet', 'he-answer-form', 'he-take-form', 'he-resume-form', 'he-summary'] \
        and tab['rows'][2]['cssClass'] == 'side-by-side' and tab['rows'][2]['items'][0]['componentProps']['componentName'] == 'api-svg-panel' \
        and [t['key'] for t in pdef['tabs']][-1] == 'sheet'
    check('the Hardware Events page has the Test sheet tab: generate, sessions, LEFT the picture (api-svg-panel) beside the sheet, answer, resume, summary', ok)


if __name__ == '__main__':
    sys.path[:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]
    main()
    print('\n%d/%d passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
