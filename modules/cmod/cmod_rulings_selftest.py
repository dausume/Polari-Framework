"""cmod_rulings_selftest - msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md sections 2 and 4): A PERSON RULES ON WHAT THE SIMULATION DOES NOT
EXPLAIN, AND THE FAULT RANKING SUGGESTS WHY. The UNO light's led-on node (the msv-0 fixture: a FIXTURE meter, never a real instrument's numbers):

- the faults injected into the cst deck read as physics says (an open D6 joint: no LED current, D6's net pulled to the meter's few mV; a reversed LED:
  the junction at 5 V; R1 at 2.2k: about a tenth of the current)
- the ranking over ALL of a unit's readings: one LED-current reading of 0 ties every fault that stops the current, and names the point that tells them
  apart; adding that point's reading puts the open LED joint first, alone (the plan's check)
- rulings: accepted-variance only on an unexplained reading, scoped to the unit by default, covering a later reading near it on that unit, not another
  unit (unless design scope), and never across a rebuild; lot needs the unit's lot; a mistake needs a cause and stays OPEN until a later reading of
  the point counts - the rework in between does not close it; a measurement error is measured again; a stale reading is refused
- the queue, the doors, the page tab, the manifest

    PYTHONPATH=.:modules python3 -m cmod.cmod_rulings_selftest      # from polari-framework/
"""
import json
import types

from cmod.cmod_measure_selftest import BS, HEX, NODE, _manager, _seed

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _refused(fn, status=None, has=''):
    from cmod.custom.config_rows import ConfigRefused
    try:
        fn()
    except ConfigRefused as e:
        return (status is None or e.status == status) and has in e.why
    return False


def main():
    from cmod.custom import config_rows as R
    from cmod.custom import fault_signatures as FS
    from cmod.custom import measure_points as MP
    from cmod.custom import measure_readings as MR
    from cmod.custom import variance_rulings as VR
    from electrodevice.custom.spice_run import capability
    if not capability()['available']:
        check('ngspice is available (the cst slice engine)', False, 'ngspice missing: run in the backend image')
        return
    from cmod.custom import node_electrical as NE
    c = NE.circuit('uno-light')
    cat, state = c['cat'], next(s for s in c['states'] if s['name'] == 'led-on')

    # --- the faults in the deck
    fl = {f['id']: f for f in FS.faults(cat)}
    check('THE FAULTS come from the circuit rows: every part\'s legs open, each pin\'s joint open, every net pair bridged, R1 at its E12 neighbours and a '
          'decade either side, the LED reversed, D2\'s / D3\'s wire on each other (a used neighbour); none typed per bench',
          {'open:ubc-led1:LED_ANODE', 'open-pin:D6', 'bridge:GND|LED_ANODE', 'value:ubc-r1=180', 'value:ubc-r1=270', 'value:ubc-r1=2.2k', 'value:ubc-r1=22',
           'reversed:ubc-led1', 'wrong-pin:D2>D3', 'wrong-pin:D3>D2', 'none'} <= set(fl), sorted(fl))
    check('a wire on an UNUSED neighbour reads as the open joint, so it is named in that fault\'s words, not ranked twice',
          'D5 / D7' in fl['open-pin:D6']['words'] and not any(k.startswith('wrong-pin:D6') for k in fl))
    pt = {'quantity': 'V dc', 'plus_at': 'LED_CONTROL', 'si_unit': 'V'}
    pi = {'quantity': 'I dc', 'plus_at': 'ubc-led1', 'si_unit': 'A'}
    pa = {'quantity': 'V dc', 'plus_at': 'LED_ANODE', 'si_unit': 'V'}
    v_open = FS.predict(cat, state, fl['open-pin:D6'], pt)
    check('an open D6 joint: no LED current (nanoamps through the 1 Gohm); D6\'s net reads what the 10 Mohm meter pulls it to (about 50 mV), not the bare deck\'s floating 1 V',
          abs(FS.predict(cat, state, fl['open-pin:D6'], pi)) < 1e-7 and 0.01 < v_open < 0.1, v_open)
    check('a reversed LED: the junction at 5 V, no current; R1 at 2.2k: about a tenth of the 14.7 mA',
          abs(FS.predict(cat, state, fl['reversed:ubc-led1'], pa) - 5.0) < 1e-3 and 0.001 < FS.predict(cat, state, fl['value:ubc-r1=2.2k'], pi) < 0.002)
    check('no fault = the nominal (14.715 mA)', abs(FS.predict(cat, state, fl['none'], pi) - 0.0147152) < 2e-6)

    # --- the ranking
    m = _manager()
    _seed(m)
    pts = {p['name'].split('-mp-')[-1]: p['name'] for p in MP.derive(m, NODE)}
    MR.add_unit(m, BS, {'name': 'u1', 'hex_sha256': HEX})
    r0 = MR.add_reading(m, 'u1', {'point': pts['i-ubc-led1'], 'value': '0.00 mA', 'instrument': 'fixture-dmm'})
    g = FS.rank(m, 'u1')
    tied = [x['fault'] for x in g['ranked'] if x['rank'] == 1]
    check('ONE READING (0 mA through the LED): every fault that stops the current ties first - the ranking says so instead of picking one',
          {'open-pin:D6', 'open:ubc-led1:LED_ANODE', 'reversed:ubc-led1'} <= set(tied) and 'tie' in g['words'], (tied, g['words']))
    check('... and names the point that tells them apart: the R1/LED junction (5 V for an open LED leg, ~50 mV for an open D6)',
          g['next'] and g['next']['point'] == pts['v-led-anode'] and 'measure' in g['words'], g['next'])
    MR.add_reading(m, 'u1', {'point': pts['v-led-anode'], 'value': '4.99 V', 'instrument': 'fixture-dmm'})
    MR.add_reading(m, 'u1', {'point': pts['v-led-control'], 'value': '5.00 V', 'instrument': 'fixture-dmm'})
    g = FS.rank(m, 'u1')
    top = [x for x in g['ranked'] if x['rank'] == 1]
    check('THE PLAN\'S CHECK: with the junction at 5 V and D6 at 5 V, the open LED joint ranks first (tied only with the LED\'s other open leg and the '
          'reversed LED, which read the same at every point), explaining all three readings; the open D6 joint is ranked below it',
          top and top[0]['cause'] in ('open', 'reversed-polarity') and any(x['fault'].startswith('open:ubc-led1') for x in top) and top[0]['explains'] == 3
          and all(x['fault'] != 'open-pin:D6' for x in top), [(x['rank'], x['fault'], x['explains']) for x in g['ranked']])
    check('the rail point is left out of the ranking, said (no circuit fault moves the supply\'s figure here)',
          all('rail' not in x['point'] for f in g['ranked'] for x in f['predictions']))
    check('the ranking carries its basis (the knobs said) and every prediction in words', 'KNOB' in g['basis'] and 'predicts' in top[0]['words'])

    # --- rulings
    rid = r0['name']
    check('a ruling needs who and why', _refused(lambda: VR.rule(m, 'u1', {'reading': rid, 'ruling': 'mistake', 'cause': 'open'}), has='who'))
    check('a mistake needs a cause from the list', _refused(lambda: VR.rule(m, 'u1', {'reading': rid, 'ruling': 'mistake', 'who': 'a tester', 'words': 'x'}),
                                                            has='cause'))
    check('an unknown ruling is refused by name', _refused(lambda: VR.rule(m, 'u1', {'reading': rid, 'ruling': 'fine', 'who': 'a', 'words': 'b'}), has='accepted-variance'))
    ok = MR.add_reading(m, 'u1', {'point': pts['v-led-control'], 'value': '5.00 V', 'instrument': 'fixture-dmm'})
    check('accepted variance only on an UNEXPLAINED reading (an in-band one needs nothing): 409',
          _refused(lambda: VR.rule(m, 'u1', {'reading': ok['name'], 'ruling': 'accepted-variance', 'who': 'a', 'words': 'b'}), status=409, has='in-band'))
    v = VR.rule(m, 'u1', {'reading': rid, 'ruling': 'mistake', 'cause': 'cold-joint', 'who': 'a tester', 'words': 'the LED anode lead was not in its row'})
    check('A MISTAKE ruled: open, the reading does not count, the fault ranking\'s first suggestion kept beside it as evidence',
          v['standing'] == 'mistake-open' and not v['counts'] and 'explains' in v['suggested'], v)
    q = VR.queue(m, 'u1')
    check('the queue lists the open mistake and the other unexplained readings, with the ranking',
          [x['ruling'] for x in q['open_mistakes']] == [v['name']] and q['ranking'] and {x['point'] for x in q['waiting']} >= {pts['v-led-anode']}, q['words'])
    w = VR.rework(m, 'u1', {'ruling': v['name'], 'words': 'pushed the LED anode lead into its row', 'who': 'a tester'})
    check('rework is kept on the mistake - and does NOT close it', w['ruling'] == v['name'] and VR.rulings(m, 'u1')[0]['state'] == 'open')
    check('rework only on a mistake, and says what and who', _refused(lambda: VR.rework(m, 'u1', {'ruling': v['name'], 'words': ''}), has='who'))
    MR.add_reading(m, 'u1', {'point': pts['i-ubc-led1'], 'value': '9.0 mA', 'instrument': 'fixture-dmm'})
    check('a re-read that still does not count leaves it open', VR.rulings(m, 'u1')[0]['state'] == 'open')
    fix = MR.add_reading(m, 'u1', {'point': pts['i-ubc-led1'], 'value': '14.7 mA', 'instrument': 'fixture-dmm', 'range_max': '200 mA'})
    rr = [x for x in VR.rulings(m, 'u1') if x['name'] == v['name']][0]
    check('AN IN-BAND RE-READ CLOSES THE MISTAKE (closed_by names it; the rework is on the ruling)',
          rr['state'] == 'closed' and rr['closed_by'] == fix['name'] and 'pushed' in rr['rework'], rr)
    cur = {x['point']: x for x in MR.readings(m, 'u1') if x['current']}
    check('the readings carry their standing: the re-read counts; the old one is mistake-closed',
          cur[pts['i-ubc-led1']]['standing'] == 'counts' and cur[pts['i-ubc-led1']]['counts']
          and [x for x in MR.readings(m, 'u1') if x['name'] == rid][0]['standing'] == 'mistake-closed')

    # accepted variance: unit scope by default; covers a later reading near it on this unit only
    odd = MR.add_reading(m, 'u1', {'point': pts['v-led-anode'], 'value': '2.60 V', 'instrument': 'fixture-dmm'})
    check('2.60 V at the junction is unexplained (outside the corners)', odd['verdict'] == 'unexplained', odd['verdict'])
    a = VR.rule(m, 'u1', {'reading': odd['name'], 'ruling': 'accepted-variance', 'who': 'a tester', 'words': 'this kit\'s LED reads high (a blue-ish die)'})
    check('ACCEPTED VARIANCE: unit scope by default, the reading counts', a['scope'] == 'unit' and a['standing'] == 'accepted' and a['counts'], a)
    def _read(unit, value):
        n = MR.add_reading(m, unit, {'point': pts['v-led-anode'], 'value': value, 'instrument': 'fixture-dmm'})['name']
        return [x for x in MR.readings(m, unit) if x['name'] == n][0]
    again = _read('u1', '2.605 V')
    check('it covers a later reading NEAR it on the same unit (covered_by)', again['standing'] == 'accepted' and again['covered_by'] == a['name'], again)
    far = _read('u1', '2.90 V')
    check('... but not one that has moved further: a new question', far['standing'] == 'needs-ruling', far)
    MR.add_unit(m, BS, {'name': 'u2', 'hex_sha256': HEX})
    o2 = MR.add_reading(m, 'u2', {'point': pts['v-led-anode'], 'value': '2.60 V', 'instrument': 'fixture-dmm'})
    s2 = [x for x in MR.readings(m, 'u2') if x['name'] == o2['name']][0]
    check('unit scope does not reach another unit', s2['standing'] == 'needs-ruling', s2)
    d = VR.rule(m, 'u2', {'reading': o2['name'], 'ruling': 'accepted-variance', 'scope': 'design', 'who': 'a tester', 'words': 'every kit LED reads so'})
    MR.add_unit(m, BS, {'name': 'u3', 'hex_sha256': HEX})
    o3 = MR.add_reading(m, 'u3', {'point': pts['v-led-anode'], 'value': '2.60 V', 'instrument': 'fixture-dmm'})
    check('DESIGN scope reaches every unit of the Bench Solution on the same build',
          [x for x in MR.readings(m, 'u3') if x['name'] == o3['name']][0]['covered_by'] == d['name'])
    MR.add_unit(m, BS, {'name': 'u4', 'hex_sha256': 'b' * 64})
    o4 = MR.add_reading(m, 'u4', {'point': pts['v-led-anode'], 'value': '2.60 V', 'instrument': 'fixture-dmm'})
    check('... never across a rebuild (another hex): the reading is a new question',
          [x for x in MR.readings(m, 'u4') if x['name'] == o4['name']][0]['standing'] == 'needs-ruling')
    check('LOT scope needs the unit\'s part_lot: 409',
          _refused(lambda: VR.rule(m, 'u3', {'reading': o3['name'], 'ruling': 'accepted-variance', 'scope': 'lot', 'who': 'a', 'words': 'b'}), status=409, has='part_lot'))
    me = VR.rule(m, 'u1', {'reading': far['name'], 'ruling': 'measurement-error', 'who': 'a tester', 'words': 'the black probe slipped off GND'})
    check('A MEASUREMENT ERROR: the reading does not count; measure again', me['standing'] == 're-measure' and not me['counts'])
    check('ruling again supersedes: the newest of a reading is in force',
          VR.rule(m, 'u1', {'reading': far['name'], 'ruling': 'mistake', 'cause': 'other', 'who': 'a', 'words': 'b'})['standing'] == 'mistake-open'
          and [x for x in VR.rulings(m, 'u1') if x['name'] == me['name']][0]['state'] == 'superseded')
    R.upsert(m, 'MeasurementReading', o4['name'], hex_sha256='c' * 64)
    check('no ruling on a STALE reading (another build than the prediction): 409',
          _refused(lambda: VR.rule(m, 'u4', {'reading': o4['name'], 'ruling': 'mistake', 'cause': 'open', 'who': 'a', 'words': 'b'}), status=409, has='stale'))
    check('a reading of another unit is not found here: 404',
          _refused(lambda: VR.rule(m, 'u2', {'reading': rid, 'ruling': 'mistake', 'cause': 'open', 'who': 'a', 'words': 'b'}), status=404))

    # --- the doors, the page, the manifest
    from cmod import cmod_measure_api as API
    routes = []
    srv = types.SimpleNamespace(falconServer=types.SimpleNamespace(add_route=lambda path, res, suffix=None: routes.append((path, suffix))))
    api = API.MeasureAPI(polServer=srv, manager=m)
    want = {'rulings', 'rework', 'queue', 'ranking', 'ranking_summary'}
    check('the doors: rulings (GET/POST), rework, ruling-queue, fault-ranking and its summary', want <= {s for _p, s in routes}, routes)
    resp = types.SimpleNamespace(media=None, status=None)
    api.on_get_ranking(None, resp, BS, 'u1')
    check('GET fault-ranking gives rows (a table reads rows)', resp.media['ok'] and resp.media['rows'] and 'rank' in resp.media['rows'][0], resp.media)
    resp = types.SimpleNamespace(media=None, status=None)
    api.on_get_ranking_summary(None, resp, BS, 'u1')
    check('the summary door gives the ranking in words, its basis last', resp.media['ok'] and resp.media['rows'][-1]['words'].startswith('basis:'))
    resp = types.SimpleNamespace(media=None, status=None)
    api.on_get_queue(None, resp, BS, 'nope')
    check('an unknown unit: 404 in words', resp.media['ok'] is False and 'nope' in resp.media['error'])
    from cmod.hardware_events_page import HARDWARE_EVENTS_PAGES
    tabs = json.loads(HARDWARE_EVENTS_PAGES[0]['definition'])['tabs']
    ids = json.dumps([t for t in tabs if t.get('key') == 'rulings' or t.get('id') == 'rulings'])
    check('the page has the Rulings tab: the queue, the ranking and its words, the ruling and rework forms, the rulings table',
          all(k in ids for k in ('he-queue', 'he-ranking', 'he-ranking-words', 'he-rule-form', 'he-rework-form', 'he-rulings')), [t.get('key') or t.get('id') for t in tabs])
    man = json.load(open(__import__('os').path.join(__import__('os').path.dirname(__file__), 'polari-app.json')))
    flat = json.dumps(man)
    check('the manifest lists the objects, the modules and this selftest',
          all(k in flat for k in ('objects/cmod/VarianceRuling', 'objects/cmod/VarianceRulingRework', 'custom/fault_signatures', 'custom/variance_rulings',
                                  'cmod_rulings_selftest')))


if __name__ == '__main__':
    main()
    print('\n  cmod_rulings_selftest: %d/%d passed' % (passed, total))
    raise SystemExit(0 if passed == total else 1)
