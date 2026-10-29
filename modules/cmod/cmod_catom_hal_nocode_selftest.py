"""cmod_catom_hal_nocode_selftest — hsp-3c, the HAL half (HARDWARE_SYSTEM_PINS_PLAN.md §7 "From no-code"): a slot choice is THE write - checked against the
proposed set and the variant's own rules, written to the FirmwareVariant knob (one place, never a copy), read back by the variable, rendered by `pol board gen`
(board_config.h + the build's repro block) and refused by gen when the HAL refuses; lifecycle conditions judged in the board's context (D13 is a warning, a
refusal only with a programmer on the ICSP header); the `hal` drawing (one card per variable, options = pins that will be kept, worked-out fields refused);
the doors; the seed rows; the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_catom_hal_nocode_selftest      # from polari-framework/
"""
import json
import os
import sys
import tempfile
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _fresh_rows():
    from cmod.custom import catom_variables as CV
    from board.custom import variants as V
    from board.custom import variants_c3 as V3
    cv = [types.SimpleNamespace(**dict(r)) for r in CV.SEED_VARIABLES]
    fv = [types.SimpleNamespace(**dict(V.find('uno-light'))), types.SimpleNamespace(**dict(V3.find('esp32c3-light')))]
    return cv, fv


def write_path():
    from cmod.custom import catom_variables as CV
    p = CV.propose('uno-light', {'LED_PIN': 'D7'})
    check('WRITE: LED_PIN = D7 passes the HAL check (a WARNING since hsp-3d\'s electrical rule: nothing is wired to D7) and the variant\'s rules; the write is the '
          'FirmwareVariant knob led_pin = 7 (the one place the build reads)',
          p['ok'] and p['results'][0]['verdict'] == 'warning' and p['writes'] == [{'target': 'FirmwareVariant', 'name': 'uno-light', 'knob': 'led_pin', 'value': 7,
                                                                                      'variable': 'LED_PIN'}] and p['variant_rule'].startswith('ok'), p)
    p = CV.propose('uno-light', {'LED_PIN': 'D2'})
    check('THE HAL CATCHES WHAT THE VARIANT MISSES: LED_PIN = D2 - the variant\'s rules accept led_pin 2, the HAL refuses it (BUTTON_PIN holds PD2: one pin, one role)',
          not p['ok'] and p['variant_rule'].startswith('ok') and 'BUTTON_PIN already claims PD2' in p['results'][0]['refusals'][0] and not p['writes'], p['results'])
    p = CV.propose('esp32c3-light', {'LED_PIN': 'GPIO9'})
    check('THE VARIANT CATCHES WHAT THE HAL ONLY WARNS: C3 LED_PIN = GPIO9 is a strapping WARNING to the HAL, REFUSED by the light variant (LIGHT_FORBIDDEN) - both must pass',
          not p['ok'] and p['results'][0]['verdict'] == 'warning' and 'led_pin 9 is strapping' in p['variant_rule'] and not p['writes'], (p['results'], p['variant_rule']))
    p = CV.propose('uno-light', {'LED_PIN': 'D3', 'SENSE_PIN': 'D6'})
    check('A SWAP IN ONE WRITE: LED D6 <-> SENSE D3 together is checked against the PROPOSED set (one at a time it would collide)',
          p['ok'] and len(p['writes']) == 2 and not CV.propose('uno-light', {'LED_PIN': 'D3'})['ok'], p['results'])
    p = CV.propose('uno-light', {'LED_PIN': '6', 'F_CPU': '8000000'})
    check('UNCHANGED is skipped and said ("6" = D6 already); a variable with no knob (F_CPU) is written to its own bench value; an unknown variable is refused by name',
          [r['verdict'] for r in p['results']] == ['unchanged', 'accepted'] and p['writes'][0]['target'] == 'CatomVariable' and p['writes'][0]['field'] == 'bench_value'
          and 'no catom variable NOPE' in CV.propose('uno-light', {'NOPE': 1}).get('error', ''), p)
    cv, fv = _fresh_rows()
    touched, written, missing = CV.apply_writes(CV.propose('uno-light', {'LED_PIN': 'D7', 'F_CPU': '8000000'}, cv, fv)['writes'], cv, fv)
    vs = {v['variable']: v for v in CV.variables('uno-light', cv, fv)}
    _t, _w, miss = CV.apply_writes(CV.propose('uno-light', {'LED_PIN': 'D8'})['writes'], cv, [])
    check('APPLIED + READ BACK: the knob row now holds led_pin 7 and the variable READS it (D7, bench scope, basis = the FirmwareVariant knob) - no second copy; F_CPU bench '
          '8000000; a row that is not stored is reported, never invented',
          json.loads(fv[0].knobs_json)['led_pin'] == 7 and len(touched) == 2 and (vs['LED_PIN']['value'], vs['LED_PIN']['scope']) == ('D7', 'bench')
          and 'FirmwareVariant uno-light knobs led_pin 7' in vs['LED_PIN']['bench_basis'] and vs['F_CPU']['value'] == '8000000'
          and written == ['FirmwareVariant uno-light knob led_pin = 7', 'CatomVariable uno-light:F_CPU bench_value = 8000000'] and 'no stored row' in miss[0], (written, miss))
    return cv, fv


def conditions():
    from cmod.custom import catom_variables as CV
    r = CV.propose('uno-light', {'LED_PIN': 'D13'})['results'][0]
    led = {'variable': 'LED_PIN', 'role': 'gpio.out', 'soc': 'atmega328p', 'board': 'arduino-uno-r3'}
    ic = CV.check(led, 'D13', (), {'icsp': 'connected'})
    check('CONDITIONS in the board\'s context (pin_stages.DEFAULT_CONTEXT): D13 is a WARNING (the L LED buffer) with the ICSP reservation listed as not applied; with '
          'icsp=connected it is REFUSED (a programmer drives SCK)',
          r['verdict'] == 'warning' and any('not applied (condition icsp=connected' in w for w in r['why']) and ic['verdict'] == 'refused' and 'ICSP SCK' in ic['refusals'][0],
          (r['verdict'], ic['verdict']))


def electrical():
    from cmod.custom import catom_variables as CV
    from cmod.custom import hal_electrical as HE
    vs = {v['variable']: v for v in CV.variables('uno-light')}
    moved = CV.propose('uno-light', {'LED_PIN': 'D7'})['results'][0]
    fight = HE.role_check({'variable': 'PWM_PIN', 'role': 'pwm.out', 'board': 'arduino-uno-r3'}, 'D3', 'D3')
    c3 = CV.variables('esp32c3-light')[2]
    check('ELECTRICAL (hsp-3d\'s owed rule) against the bench wiring: LED_PIN at D6 is LED_CONTROL\'s output (quoting electrical_check\'s findings); LED_PIN -> D7 is '
          'a WARNING (the wire would not move); a second output on LED_CONTROL (anything driving D3 while D6 does) is REFUSED (two outputs fight); the C3 is judged '
          'against its light DESIGN (c3-light: GPIO0 the LED net\'s output, at its own cited 3.3 V) and says the rows are a design, not a measured bench', 'D6 is on LED_CONTROL as its output' in vs['LED_PIN']['status_why'] and 'single_output ok' in vs['LED_PIN']['status_why']
          and moved['verdict'] == 'warning' and any('the wire would not' in w for w in moved['why'])
          and fight['effect'] == 'refused' and 'two outputs fight' in fight['lines'][0] and 'D6' in fight['lines'][0]
          and 'GPIO0 is on LED_CONTROL as its output' in c3['status_why'] and '3.3 V' in c3['status_why'] and 'a DESIGN' in c3['status_why'] and c3['status'] == 'accepted',
          (moved['verdict'], fight['effect']))


def build(cv, fv):
    from board.custom import gen
    from board.custom import gen_c3
    mgr = types.SimpleNamespace(objectTables={'CatomVariable': {r.name: r for r in cv}})
    row = gen.gen('uno', variant='uno-light', work=tempfile.mkdtemp(), variant_rows=fv, manager=mgr)
    cfg = open(os.path.join(row['project_dir'], 'board_config.h')).read()
    hal = json.loads(row['repro_json']).get('catom_hal') or {}
    check('GEN CARRIES IT: `pol board gen uno --variant uno-light` after the write renders #define LED_PIN 7 into board_config.h; the repro block records the HAL '
          'values it was judged with (LED_PIN D7, F_CPU 8000000)', '#define LED_PIN      7' in cfg and hal.get('values', {}).get('LED_PIN') == 'D7'
          and hal['values']['F_CPU'] == '8000000', hal)
    try:
        gen.gen('uno', variant='uno-light', work=tempfile.mkdtemp(), led_pin=2)
        refused = ''
    except gen.GenRefused as e:
        refused = str(e)
    plain = gen.gen('uno', variant='uno-sim-rig', work=tempfile.mkdtemp())
    c3 = json.loads(gen_c3.gen_c3(variant='esp32c3-light', work=tempfile.mkdtemp())['repro_json']).get('catom_hal') or {}
    check('GEN REFUSES what the HAL refuses: --led_pin 2 (the variant allows it) stops with the HAL\'s reason; a variant with no catom variables is untouched (no '
          'catom_hal); the C3 light build carries its HAL verdicts too', 'the HAL refuses this build' in refused and 'BUTTON_PIN already claims PD2' in refused
          and 'catom_hal' not in json.loads(plain['repro_json']) and c3.get('verdicts', {}).get('LED_PIN') == 'accepted', (refused[:200], c3.get('verdicts')))


def drawing():
    from cmod.custom import hal_nocode as HN
    d = HN.render_definition('uno-light')
    f = {s['boundObjectFieldValues']['variable']: s['boundObjectFieldValues'] for s in d['stateInstances']}
    check('DRAWING: hal-uno-light = 6 cards, every one a HalVariableState; the category validator passes it', len(d['stateInstances']) == 6
          and {s['stateClass'] for s in d['stateInstances']} == {'HalVariableState'} and HN.validate(d)[0], HN.validate(d))
    check('SLOTS ON THE CARD: LED_PIN offers D6 first - the one pin the LED is WIRED to - then D4..D13 as warnings (off the wire; D11-13 also the ICSP net / L LED), '
          'never D0-D3 (the serial line, the button, the sense pin); BUTTON_PIN offers D2 only (the variant fixes the button to INT0); F_CPU is typed in',
          f['LED_PIN']['options'] == 'D6, D4 (warning), D5 (warning), D7 (warning), D8 (warning), D9 (warning), D10 (warning), D11 (warning), D12 (warning), D13 (warning)'
          and f['BUTTON_PIN']['options'] == 'D2' and f['F_CPU']['options'] == 'a number, typed in', (f['LED_PIN']['options'], f['BUTTON_PIN']['options']))

    def edit(var, **kv):
        dd = HN.render_definition('uno-light')
        s = next(s for s in dd['stateInstances'] if s['stateName'] == 'hal-' + var)
        s['boundObjectFieldValues'].update(kv)
        return dd
    ok, why, p = HN.write_back(edit('LED_PIN', value='D7'), 'uno-light')
    bad_derived = HN.write_back(edit('LED_PIN', verdict='accepted!'), 'uno-light')
    bad_value = HN.write_back(edit('LED_PIN', value='D1'), 'uno-light')
    ghost = edit('LED_PIN')
    ghost['stateInstances'][0]['boundObjectFieldValues']['variable'] = 'GHOST_PIN'
    compute = edit('LED_PIN')
    compute['stateInstances'][0]['stateClass'] = 'VariableAssignment'
    check('WRITE BACK: a card\'s new value goes through the same write (LED_PIN D7 -> the knob); a typed-in verdict is refused naming the state; D1 is refused with the '
          'lifecycle reason (the 16U2 serial line) and the variant\'s rule; a card for a variable the variant lacks and a compute kind are refused',
          ok and p['writes'][0]['knob'] == 'led_pin' and not bad_derived[0] and "state 'hal-LED_PIN'" in bad_derived[1] and 'worked out' in bad_derived[1]
          and not bad_value[0] and '16U2' in bad_value[1] and 'variant\'s own rule' in bad_value[1] and not HN.write_back(ghost, 'uno-light')[0]
          and not HN.write_back(compute, 'uno-light')[0], (why, bad_derived[1][:120], bad_value[1][:300]))


def doors():
    from cmod.cmod_catom_api import CatomVariableAPI
    cv, fv = _fresh_rows()
    sol = types.SimpleNamespace(name='hal-uno-light', definition='{}')
    api = CatomVariableAPI(polServer=None, manager=None)
    api.manager = types.SimpleNamespace(objectTables={'CatomVariable': {r.name: r for r in cv}, 'FirmwareVariant': {r.name: r for r in fv},
                                                      'SolutionDefinition': {sol.name: sol}}, db=None)

    def call(method, variant, params=None, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(get_param=lambda k: (params or {}).get(k), bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, variant)
        return resp
    s1 = call('on_post_set', 'uno-light', body={'variable': 'LED_PIN', 'value': 'D7'})
    hd = call('on_get', 'uno-light', {'view': 'header'})
    s2 = call('on_post_set', 'uno-light', body={'variable': 'LED_PIN', 'value': 'D2'})
    check('DOORS: POST .../uno-light/set LED_PIN D7 writes the stored FirmwareVariant knob and refreshes the stored hal-uno-light drawing; the header view then says '
          'LED_PIN 7; LED_PIN D2 = 422 refused, nothing written', s1.status == '200 OK' and s1.media['written'] == ['FirmwareVariant uno-light knob led_pin = 7']
          and json.loads(fv[0].knobs_json)['led_pin'] == 7 and '"value": "D7"' in sol.definition and '#define LED_PIN        7' in hd.media['text']
          and s2.status.startswith('422') and s2.media['refused'] and s2.media['written'] == [], (s1.media, s2.status))
    g = call('on_get_solution', 'uno-light')
    d = g.media['definition']
    next(s for s in d['stateInstances'] if s['stateName'] == 'hal-SENSE_PIN')['boundObjectFieldValues']['value'] = 'D8'
    put = call('on_put_solution', 'uno-light', body={'definition': d})
    d2 = put.media['definition']
    next(s for s in d2['stateInstances'] if s['stateName'] == 'hal-SENSE_PIN')['boundObjectFieldValues']['role'] = 'uart.tx'
    put_bad = call('on_put_solution', 'uno-light', body=d2)
    check('DOORS: GET .../solution = the drawing; PUT with SENSE_PIN D8 writes knob sense_pin = 8 and returns the redrawn cards; PUT with a typed-in role = 422 naming the '
          'state; GET for an unknown variant 404', g.media['solution']['category'] == 'hal' and put.status == '200 OK'
          and put.media['written'] == ['FirmwareVariant uno-light knob sense_pin = 8'] and json.loads(fv[0].knobs_json)['sense_pin'] == 8
          and put_bad.status.startswith('422') and "hal-SENSE_PIN" in put_bad.media['error'] and call('on_get_solution', 'nope').status.startswith('404'),
          (put.status, put.media.get('written') or put.media.get('error'), put_bad.media.get('error', '')[:120]))


def registered():
    from hwnocode.custom.seed_rows import solution_definitions
    rows = {r['name']: r for r in solution_definitions()}
    check('SEEDS: the hal-uno-light and hal-esp32c3-light drawings are seeded as SolutionDefinition rows of category hal (rendered from the rows, never typed)',
          rows.get('hal-uno-light', {}).get('category') == 'hal' and rows.get('hal-esp32c3-light', {}).get('category') == 'hal', sorted(n for n in rows if n.startswith('hal')))
    from cmod import cmod_basis as B
    from hwnocode.custom import cross_domain as CD
    check('REGISTERED: HalVariableState is in CMOD_CLASSES + HAL_NODE_KIND_CLASSES with a palette (category HAL); the Purpose / Mission validators read the same table',
          B.HalVariableState in B.CMOD_CLASSES and B.HAL_NODE_KIND_CLASSES == [B.HalVariableState] and B.HalVariableState.statePalette['category'] == 'HAL'
          and set(CD.DECLARATIVE) == {'purpose', 'mission', 'hal'})
    from moduleService.manifests import conform
    r = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with HalVariableState + hal_nocode + this selftest listed', r['ok'], r.get('findings'))


def main():
    cv, fv = write_path()
    conditions()
    electrical()
    build(cv, fv)
    drawing()
    doors()
    registered()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
