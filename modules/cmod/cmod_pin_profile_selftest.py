"""cmod_pin_profile_selftest - pp-0: pin profiles per Purpose and per Mission (cmod.custom.pin_profiles / pin_profile_mission / pin_profile_doors).
Called from cmod_selftest.main as `pin_profile_parts(check)`; also runnable alone: PYTHONPATH=.:modules python3 -m cmod.cmod_pin_profile_selftest."""
import json
import re
from types import SimpleNamespace

INIT, BUTTON, OBSERVE, CONTROL = ('initialization', 'ensure-button-controls-light', 'ensure-polari-observes-hardware-state', 'ensure-polari-can-control-light')
LIGHT = [INIT, BUTTON, OBSERVE, CONTROL]
LED_ID = BUTTON + ':the-led:digital-out'


def _manager():
    from cmod.custom.selftest_purpose import _manager as m
    return m()


def _by(res, role, kind):
    return next((p for p in res['profiles'] if p['role'] == role and p['kind'] == kind), None)


def _words(obj):
    """Every key and every string value inside obj, lower-cased (the vocabulary scan)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k).lower())
            out += _words(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += _words(v)
    elif isinstance(obj, str):
        out.append(obj.lower())
    return out


def _has_word(texts, words):
    pat = re.compile(r'(?<![a-z])(%s)(?![a-z])' % '|'.join(re.escape(w) for w in words))
    return [t for t in texts if pat.search(t)]


def pin_profile_parts(check):
    from cmod.custom import pin_profiles as PP
    from cmod.custom import pin_profile_mission as PM

    def light_purposes():
        init, button, observe, control = (PP.derive_profiles(n) for n in LIGHT)
        b = _by(button, 'the button', 'interrupt-in')
        check('pp-0: the button Purpose needs interrupt-in for "the button": inputs, pull-up (a switch to ground), falling edge, debounce 30 ms from criterion debounce_ms',
              b is not None and b['signal']['direction'] == 'inputs' and b['drive']['need'] == 'pull-up' and b['drive']['load_class'] == 'a switch to ground'
              and b['timing']['edge']['value'] == 'falling' and b['timing']['debounce']['value'] == 30
              and b['timing']['debounce']['criterion'] == 'debounce_ms' and b['lifecycle_phases'] == ['init'], b and (b['drive'], b['timing']))
        led = _by(button, 'the LED', 'digital-out')
        cur = led['drive']['current'] if led else {}
        check('pp-0: the LED is digital-out: outputs, drive source-current into an LED through R1 (220 ohm), current undetermined with the assumed-Vf reason (and a Vf-free ceiling, labelled)',
              led is not None and led['signal']['direction'] == 'outputs' and led['drive']['need'] == 'source-current'
              and led['drive']['load']['series_parts'] == ['ubc-r1'] and led['drive']['load']['series_ohms'] == 220
              and cur.get('value') == 'undetermined' and 'assumed' in cur.get('reason', '') and cur.get('ceiling_ma') == 22.7 and 'not a design target' in cur.get('ceiling_basis', '')
              and led['lifecycle_phases'] == ['runtime'], led and led['drive'])
        check('pp-0: led_toggle touches D6 but its atom does not settle a kind - its pin-function pwm-out is folded into the LED digital-out, never a profile of its own (said in evidence)',
              _by(button, 'the LED', 'pwm-out') is None and 'pwm-out' in led['evidence']['kind'] and 'does not settle' in led['evidence']['kind'], led['evidence']['kind'])
        sense = _by(button, 'the sense line', 'interrupt-in')
        check('pp-0: the sense line (D3 role) is interrupt-in, inputs, origin bench, task undetermined (no task of the Purpose reads it), high-impedance, edge any',
              sense is not None and sense['origin'] == 'bench' and sense['signal']['direction'] == 'inputs' and sense['task'].startswith('undetermined')
              and sense['drive']['need'] == 'high-impedance' and sense['timing']['edge']['value'] == 'any'
              and 'not of this Purpose' in sense['evidence']['kind'], sense and sense['evidence'])
        check('pp-0: the control Purpose has the transport rx (reserved), the LED and the sense line; the observe Purpose only the transport tx (reserved)',
              {(p['role'], p['kind']) for p in control['profiles']} == {('the transport', 'uart-rx'), ('the LED', 'digital-out'), ('the sense line', 'interrupt-in')}
              and {(p['role'], p['kind']) for p in observe['profiles']} == {('the transport', 'uart-tx')}
              and all(p['reserved'] for p in observe['profiles'] if p['role'] == 'the transport'),
              [(p['role'], p['kind']) for p in control['profiles'] + observe['profiles']])
        check('pp-0: initialization has the transport rx + tx (init), the LED (init, no sense line: nothing drives the line at run time), and the button with debounce undetermined (no criterion, named)',
              {(p['role'], p['kind']) for p in init['profiles']} == {('the transport', 'uart-rx'), ('the transport', 'uart-tx'), ('the LED', 'digital-out'), ('the button', 'interrupt-in')}
              and _by(init, 'the button', 'interrupt-in')['timing']['debounce']['value'] == 'undetermined'
              and 'no debounce_ms criterion' in _by(init, 'the button', 'interrupt-in')['timing']['debounce']['reason'],
              [(p['role'], p['kind']) for p in init['profiles']])
        un = {u['task'].rpartition(':')[2]: u['why'] for u in init['unresolved']}
        check('pp-0: tasks that give no pin are listed with the reason, not invented: tick_init = whole peripheral TIMER2, boot_session_mint = memory field; usart_send D0 (uart-tx cannot sit on RXD) dropped by name',
              'TIMER2' in un.get('tick_init', '') and 'memory field' in un.get('boot_session_mint', '')
              and any(i['pin'] == 'D0' and 'TXD' in i['why'] for i in observe['ignored']), (un, observe['ignored']))
        try:
            PP.derive_profiles('no-such-purpose')
            refused = False
        except ValueError as e:
            refused = 'no Purpose named' in str(e)
        check('pp-0: an unknown Purpose is refused by name', refused)

    def vocabulary_and_evidence():
        every = [p for n in LIGHT for p in PP.derive_profiles(n)['profiles']]
        check('pp-0: signal and drive are separate keys of every profile; each carries its own fields',
              every and all('signal' in p and 'drive' in p and set(p['signal']) >= {'direction', 'family'} and set(p['drive']) >= {'need', 'load_class', 'current'} for p in every))
        bad_drive = [t for p in every for t in _has_word(_words(p['drive']), PP.SIGNAL_WORDS)]
        bad_signal = [t for p in every for t in _has_word(_words(p['signal']), PP.DRIVE_WORDS)]
        check('pp-0: no signal word (output/input/uart/interrupt/edge/rx/tx/protocol) in any drive field, no drive word (current/supply/source/sink/pull/load/ohm/resistor) in any signal field',
              not bad_drive and not bad_signal, (bad_drive[:3], bad_signal[:3]))
        sections = ('kind', 'role', 'signal', 'drive', 'timing', 'lifecycle_phases', 'lifecycle', 'count')
        missing = [(p['id'], s) for p in every for s in sections if not (p['evidence'].get(s) or '').strip()]
        check('pp-0: every field of every profile has evidence (or the evidence says undetermined and why)', not missing, missing[:4])

        def leaves(p):
            for sec in ('drive', 'timing'):
                for k, v in (p[sec].items() if sec == 'timing' else [('current', p['drive']['current'])]):
                    yield (p['id'], sec, k, v)
        unreasoned = [(i, s, k) for p in every for (i, s, k, v) in leaves(p) if v.get('value') == 'undetermined' and not v.get('reason')]
        uncited = [(i, s, k) for p in every for (i, s, k, v) in leaves(p)
                   if v.get('value') not in ('undetermined', 'not applicable') and not (v.get('criterion') or v.get('from') or v.get('reason'))]
        check('pp-0: every undetermined number says why, and every number named is from a criterion, a claim or a circuit/datasheet reason', not unreasoned and not uncited, (unreasoned[:3], uncited[:3]))

    def rollup():
        res = PM.mission_profiles('light', purposes=LIGHT)
        got = {(p['role'], p['kind']): p for p in res['profiles']}
        check('pp-0: the Mission roll-up of the light Purposes is exactly: transport uart-rx + uart-tx (reserved), the LED digital-out, the button interrupt-in, the sense line interrupt-in',
              set(got) == {('the transport', 'uart-rx'), ('the transport', 'uart-tx'), ('the LED', 'digital-out'), ('the button', 'interrupt-in'), ('the sense line', 'interrupt-in')}
              and res['pins_needed'] == 5 and got[('the transport', 'uart-rx')]['reserved'] and got[('the transport', 'uart-tx')]['reserved'], sorted(got))
        led = got[('the LED', 'digital-out')]
        check('pp-0: the LED drive three Purposes need counts ONCE, listing all three; the transport rx lists the two that use it',
              sum(1 for p in res['profiles'] if p['role'] == 'the LED') == 1 and led['purposes'] == [INIT, BUTTON, CONTROL]
              and got[('the transport', 'uart-rx')]['purposes'] == [INIT, CONTROL], (led['purposes'], got[('the transport', 'uart-rx')]['purposes']))
        check('pp-0: the reserved transport profiles carry the lifecycle rows that reserve D0/D1 (bootloader + init + runtime) and the host-participant evidence; default importance is required',
              {c['phase'] for c in got[('the transport', 'uart-rx')]['lifecycle']} >= {'bootloader', 'init', 'runtime'}
              and 'host participant' in got[('the transport', 'uart-rx')]['evidence']['reserved'] and all(p['importance'] == 'required' for p in res['profiles']))
        check('pp-0: timing of a merged profile stays per Purpose (the button: debounce 30 ms for the button Purpose, undetermined for initialization)',
              got[('the button', 'interrupt-in')]['timing_by_purpose'][BUTTON]['debounce']['value'] == 30
              and got[('the button', 'interrupt-in')]['timing_by_purpose'][INIT]['debounce']['value'] == 'undetermined')
        mgr = _manager()
        row = SimpleNamespace(name='demo-mission', purposes_json=json.dumps([{'purpose': INIT, 'importance': 'required'}, {'purpose': BUTTON, 'importance': 'safety'},
                                                                              {'purpose': CONTROL, 'importance': 'desired'}]))
        mgr.objectTables['HardwareMission'] = {'1': row}
        m2 = PM.mission_profiles('demo-mission', manager=mgr)
        gi = {(p['role'], p['kind']): p['importance'] for p in m2['profiles']}
        check('pp-0: a HardwareMission row (read from objectTables, no import) supplies the Purposes and their importance; a merged profile takes the strongest (LED: safety)',
              m2['basis'] == 'HardwareMission demo-mission' and gi[('the LED', 'digital-out')] == 'safety' and gi[('the transport', 'uart-rx')] == 'required', gi)
        try:
            PM.mission_profiles('none-here', manager=mgr)
            refused = False
        except ValueError as e:
            refused = '?purposes=a,b' in str(e)
        check('pp-0: a Mission that is not there (and no Purposes named) is refused, naming the ?purposes=a,b fallback', refused)

    def corrections():
        from cmod.custom import overrides as OV
        mgr = _manager()
        base = PP.derive_profiles(BUTTON, manager=mgr)
        derived = _by(base, 'the LED', 'digital-out')
        none, why = OV.create('PinProfile', LED_ID, 'drive_current_ma', '8', '  ', 'sub-test', mgr)
        check('pp-0: a PinProfile correction without a why is refused (never defaulted)', none is None and 'why' in why, why)
        row, why = OV.create('PinProfile', LED_ID, 'drive_current_ma', '8', 'measured on the bench with a meter', 'sub-test', mgr)
        if row is not None and row.id not in mgr.objectTables.setdefault('DerivedOverride', {}):
            mgr.objectTables['DerivedOverride'][row.id] = row
        ovr = PP.derive_profiles(BUTTON, manager=mgr)
        led = _by(ovr, 'the LED', 'digital-out')
        o = (led['overrides'] or [{}])[0]
        check('pp-0: a DerivedOverride correction is applied and shown with who / when / why and the derived value beside it',
              row is not None and led['drive']['current']['value'] == 8 and o.get('who') == 'sub-test' and o.get('when') and o.get('why') == 'measured on the bench with a meter'
              and o.get('derived') == 'undetermined' and o.get('ref', '').startswith('DerivedOverride:PinProfile:') and 'corrected by sub-test' in led['evidence']['drive'], led['overrides'])
        check('pp-0: the derivation itself is unchanged (no manager, or a manager with no override, still says undetermined)',
              derived['drive']['current']['value'] == 'undetermined' and _by(PP.derive_profiles(BUTTON), 'the LED', 'digital-out')['drive']['current']['value'] == 'undetermined')
        check('pp-0: the corrected profile shows the correction in its plain-words row (table), and the vocabulary stays separate',
              '(sub-test' in PP.summary(led)['corrections'] and not _has_word(_words(led['drive']), PP.SIGNAL_WORDS))
        bad, why = OV.create('PinProfile', LED_ID, 'v_forward', '1', 'x', 'sub-test', mgr)
        none2, why2 = OV.create('PinProfile', BUTTON + ':the-led:uart-tx', 'drive_need', 'sink-current', 'x', 'sub-test', mgr)
        check('pp-0: a field that is not overridable, and a profile that does not exist, are both refused by name', bad is None and 'overridable' in why and none2 is None and 'no PinProfile' in why2, (why, why2))
        ok, _w = OV.retire(row.name, mgr)
        check('pp-0: retiring the override restores the derived value', ok and _by(PP.derive_profiles(BUTTON, manager=mgr), 'the LED', 'digital-out')['drive']['current']['value'] == 'undetermined')

    def doors():
        import falcon
        from falcon import testing
        from cmod.cmod_pin_profile_api import PinProfileAPI
        mgr = _manager()
        mgr.objectTables['HardwareMission'] = {'1': SimpleNamespace(name='demo-mission', purposes_json=json.dumps([{'purpose': BUTTON, 'importance': 'required'}, {'purpose': CONTROL, 'importance': 'important'}]))}

        class Mis0:        # stands in for mis-0's doors: same depth, same {name} field, literal last segment
            def on_get_solution(self, req, res, name):
                res.media = {'door': 'solution', 'name': name}

            def on_get_resolution(self, req, res, name):
                res.media = {'door': 'resolution', 'name': name}

            def on_get_mission(self, req, res, name):
                res.media = {'door': 'mission', 'name': name}

        def build(mine_first):
            app = falcon.App()
            ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])

            def theirs():
                m = Mis0()
                app.add_route('/api/missions/{name}', m, suffix='mission')
                app.add_route('/api/missions/{name}/solution', m, suffix='solution')
                app.add_route('/api/missions/{name}/resolution', m, suffix='resolution')
            if mine_first:
                PinProfileAPI(polServer=ps, manager=mgr)
                theirs()
            else:
                theirs()
                PinProfileAPI(polServer=ps, manager=mgr)
            return testing.TestClient(app)
        for first in (False, True):
            c = build(first)
            r1, r2, r3 = (c.simulate_get('/api/missions/demo-mission/%s' % s) for s in ('solution', 'resolution', 'pin-profiles'))
            r0 = c.simulate_get('/api/missions/demo-mission')
            check('pp-0: /api/missions/{name}/pin-profiles beside mis-0\'s /api/missions/{name}, /solution, /resolution on one falcon.App (%s registered first): all four answer, none shadows another' % ('mine' if first else 'theirs'),
                  r1.json.get('door') == 'solution' and r2.json.get('door') == 'resolution' and r0.json.get('door') == 'mission'
                  and r3.status_code == 200 and r3.json['ok'] and r3.json['mission'] == 'demo-mission', (r0.text[:80], r1.text[:80], r2.text[:80], r3.text[:120]))
        r = c.simulate_get('/api/capabilities/%s/pin-profiles' % BUTTON)
        check('pp-0: GET /api/capabilities/{name}/pin-profiles returns the derived profiles with evidence and one plain-words row each',
              r.status_code == 200 and r.json['ok'] and len(r.json['profiles']) == len(r.json['rows']) == 3 and r.json['rows'][0]['evidence'] and r.json['unresolved'], r.text[:200])
        check('pp-0: an unknown Purpose is a 404 naming it',
              c.simulate_get('/api/capabilities/nope/pin-profiles').status_code == 404 and 'nope' in c.simulate_get('/api/capabilities/nope/pin-profiles').json['error'])
        r = c.simulate_get('/api/missions/demo-mission/pin-profiles')
        led = next((p for p in r.json['profiles'] if p['role'] == 'the LED'), {})
        check('pp-0: GET /api/missions/{name}/pin-profiles rolls the Mission\'s Purposes up (LED once, listing both; importance = strongest = required)',
              led.get('purposes') == [BUTTON, CONTROL] and led.get('importance') == 'required' and r.json['basis'] == 'HardwareMission demo-mission', r.text[:200])
        r = c.simulate_get('/api/missions/anything/pin-profiles?purposes=%s,%s' % (INIT, OBSERVE))
        check('pp-0: ?purposes=a,b names the Purposes when no Mission row exists (works before mis-0 merges); an unnamed Mission without it is a 404',
              r.status_code == 200 and r.json['basis'] == 'an explicit list of Purposes' and r.json['pins_needed'] == 4 and c.simulate_get('/api/missions/anything/pin-profiles').status_code == 404,
              (r.status_code, r.json.get('pins_needed')))
        t = c.simulate_get('/api/pin-profiles').json
        tm = c.simulate_get('/api/pin-profiles?view=mission&purposes=%s' % ','.join(LIGHT)).json
        tu = c.simulate_get('/api/pin-profiles?view=unresolved').json
        check('pp-0: the page doors answer {ok, rows} in plain words: every light Purpose, the 5-profile Mission, and the unresolved tasks',
              t['ok'] and {r_['purpose'] for r_ in t['rows']} >= set(LIGHT) and tm['count'] == 5 and tu['count'] > 0 and all({'purpose', 'task', 'why'} <= set(x) for x in tu['rows'])
              and all(not str(v).startswith(('{', '[')) for r_ in t['rows'] for v in r_.values()), (t.get('count'), tm.get('count'), tu.get('count')))

    def page():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS
        pg = next((p for p in SEED_CMOD_PAGE_DISPLAYS if p['name'] == 'pin-profiles'), None)
        d = json.loads(pg['definition']) if pg else {}
        items = [i for row in d.get('rows', []) for i in row.get('items', [])] if pg else []
        comps = {i['componentProps']['componentName'] for i in items}
        check('pp-0: /display/pin-profiles is a configured page titled "Pin profiles": class-rows-table only (no api-json-panel, no new component), every table described',
              pg is not None and pg['pageRoute'] == 'pin-profiles' and d.get('title') == 'Pin profiles' and comps == {'class-rows-table'} and len(items) == 3
              and all(i.get('description') and i['componentProps']['inputs']['dataPath'].startswith('/api/pin-profiles') for i in items), (comps, len(items)))
        import os
        src = open(os.path.join(os.path.dirname(__file__), '..', 'polariapps', 'apps_seed.py')).read()
        check('pp-0: the Hardware home links the page in its own group entry, beside the Purposes', "_tgrp('Pin profiles'" in src and "route='/display/pin-profiles'" in src)
    return (light_purposes, vocabulary_and_evidence, rollup, corrections, doors, page)


if __name__ == '__main__':
    import sys
    passed = total = 0

    def check(label, cond, extra=''):
        global passed, total
        total += 1
        passed += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))
    for part in pin_profile_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
