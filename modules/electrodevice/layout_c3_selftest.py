"""
Selftest — c3g-5 (AI-Notes/plans/C3_SESSION_PLAN.md section 6): the layout engine answers for the ESP32-C3 config as well as the UNO, from ONE per-board table
(electrodevice.custom.layout_boards). Offline, no manager (the seeds): the C3 layout passes the netlist gate on the half breadboard with the dev kit's headers, its scene carries the
twin facts (clock in ns, release 'z', no ADC), the steps name the C3 dev kit and never the UNO, the UNO's answer keeps its shape, and the refusals are in words.

Run with the layout self-test (it calls run_checks), or alone from polari-framework/:
    PYTHONPATH=.:modules python3 -B -m electrodevice.layout_c3_selftest
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def _check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + str(extra)[:300]) if (extra and not cond) else ""}')


class _Req:
    def __init__(self, params=None):
        self.params = params or {}
        self.bounded_stream = types.SimpleNamespace(read=lambda: b'{}')

    def get_param(self, k):
        return self.params.get(k)


def _refused(fn):
    from electrodevice.custom.layout_words import LayoutRefused
    try:
        fn()
    except LayoutRefused as e:
        return str(e)
    return ''


def run_checks(check=_check, seeded_manager=None):
    from electrodevice.custom import layout_boards as LB
    from electrodevice.custom import layout_core as C
    print('c3g-5: the layout of the ESP32-C3 config')
    r = C.layout_place('esp32c3-light', 'bench-half-1', header_board='bench-c3-1')
    nets = r['nets']
    check('layout_place(esp32c3-light) is ok on bench-half-1 with header board bench-c3-1, and the netlist gate says equal', r['ok'] and r['verdict']['ok'] and r['verdict']['equal'], r['verdict']['words'])
    check('nets: LED_CONTROL carries hdr:GPIO0 and hdr:GPIO1, BUTTON_INPUT carries hdr:GPIO3, GND carries hdr:GND', {'hdr:GPIO0', 'hdr:GPIO1'} <= set(nets['LED_CONTROL'])
          and 'hdr:GPIO3' in nets['BUTTON_INPUT'] and 'hdr:GND' in nets['GND'], nets)
    check('no drift between the circuit rows and the config; the circuit is c3-light', not any('lists BoardPin' in n for n in r['notes']) and r['circuit'] == 'c3-light', r['notes'])
    notes = r['notes']
    check('the two C3 notes are present: no board on the bench (the reference board cited), and the LED current at 3.3 V = about 5.9 mA with the forward voltage said to be assumed',
          len(notes) == 2 and 'No ESP32-C3 board is on the bench' in notes[0] and 'ESP32-C3-DevKitM-1' in notes[0] and 'about 5.9 mA' in notes[1] and 'assumed' in notes[1] and 'not cited' in notes[1], notes)
    sc = r['scene']
    check('scene: clock is ns at 1 GHz, adc_max_mv 0, board_definition esp32-c3', sc['clock'] == {'unit': 'ns', 'hz': 1000000000} and sc['adc_max_mv'] == 0 and sc['board_definition'] == 'esp32-c3', sc)
    it = next((p['interaction'] for p in sc['parts'].values() if p.get('interaction')), {})
    check("the pushbutton's interaction is a press on GPIO3 (twin_pin GPIO3), pressed_level 0, released_level 'z'",
          (it.get('control'), it.get('pin'), it.get('twin_pin'), it.get('pressed_level'), it.get('released_level')) == ('press', 'GPIO3', 'GPIO3', 0, 'z'), it)
    led = next((p['output'] for p in sc['parts'].values() if p.get('output')), {})
    check("the LED's output twin_pin is GPIO0, and watch == ['GPIO0']", led.get('twin_pin') == 'GPIO0' and sc['watch'] == ['GPIO0'], (led, sc['watch']))
    hdr = sc['boards'][0]
    j1 = next((c for c in hdr['connectors'] if c['name'] == 'J1'), {})
    check('the header board has connectors J1 and J3 with 15 labels each; GPIO0 is among J1\'s labels and IO0 sits at the same index of its silk',
          [c['name'] for c in hdr['connectors']] == ['J1', 'J3'] and all(len(c['labels']) == 15 and len(c['silk']) == 15 for c in hdr['connectors']) and 'GPIO0' in j1.get('labels', [])
          and j1['silk'][j1['labels'].index('GPIO0')] == 'IO0', hdr['connectors'])
    text = ' '.join(s['text'] for s in r['_steps'])
    check('the steps name "the ESP32-C3 dev kit" and a pin as "J1 header, pin 9 (printed IO0)", and never say UNO', 'the ESP32-C3 dev kit' in text and 'J1 header, pin 9 (printed IO0)' in text and 'UNO' not in text, text[:200])
    check('the C3 answer is deterministic (same sha twice)', C.layout_place('esp32c3-light', 'bench-half-1', header_board='bench-c3-1')['sha'] == r['sha'])
    check('with no header board named, a C3 config draws from its own bench-c3-1', C.layout_place('esp32c3-light')['header_board'] == 'bench-c3-1')

    print('c3g-5: the UNO keeps its shape')
    u = C.layout_place('uno-light')
    usc = u['scene']
    uit = next((p['interaction'] for p in usc['parts'].values() if p.get('interaction')), {})
    check('uno-light: clock is cycle at 16 MHz, adc_max_mv 5000, released_level 1, header connectors still five, no board notes, header board bench-uno-1',
          usc['clock'] == {'unit': 'cycle', 'hz': 16000000} and usc['adc_max_mv'] == 5000 and uit.get('released_level') == 1 and len(usc['boards'][0]['connectors']) == 5 and not u['notes']
          and u['header_board'] == 'bench-uno-1' and usc['board_definition'] == 'arduino-uno-r3', (usc['clock'], uit, u['notes']))
    check('uno-light: same sha and steps_sha twice; the steps still say "the UNO" and a pin as "DIGITAL_L header, pin 7"', C.layout_place('uno-light')['sha'] == u['sha'] and C.layout_place('uno-light')['steps_sha'] == u['steps_sha']
          and 'the UNO' in u['_steps'][0]['text'] and any('DIGITAL_L header, pin 7)' in s['text'] for s in u['_steps']))
    check('the UNO row of the table: pins D<n>, supply +5V; the +5V rail wire keeps its name stem', LB.of('arduino-uno-r3')['pin'] == 'D%d' and LB.of('arduino-uno-r3')['supply'] == '+5V')

    print('c3g-5: refusals in words')
    why = _refused(lambda: C.layout_place('uno-light', header_board='bench-c3-1'))
    check('the UNO config with the C3 header board is refused naming both boards', 'arduino-uno-r3' in why and 'esp32-c3' in why, why)
    why2 = _refused(lambda: C.layout_place('esp32c3-light', header_board='bench-uno-1'))
    check('the C3 config with the UNO header board is refused naming both boards', 'arduino-uno-r3' in why2 and 'esp32-c3' in why2, why2)
    from cmod.custom import fsc_link
    real = fsc_link.configs
    fsc_link.configs = lambda m=None: dict(real(m), madeup=dict(real(m)['esp32c3-light'], board_definition='nope-board'))
    try:
        why3 = _refused(lambda: C.layout_place('madeup'))
    finally:
        fsc_link.configs = real
    check('an unknown board_definition on a made-up config row is refused naming the boards known', 'nope-board' in why3 and 'arduino-uno-r3' in why3 and 'esp32-c3' in why3, why3)

    print('c3g-5: the door and the board table')
    from electrodevice.layout_api import LayoutAPI
    api = LayoutAPI(polServer=None, manager=seeded_manager() if seeded_manager else None)
    resp = types.SimpleNamespace(media=None, status='200 OK')
    api.on_get_layout(_Req(), resp, 'esp32c3-light')
    m = resp.media or {}
    check('door GET /api/layout/esp32c3-light: ok, gate ok, header board bench-c3-1, scene clock ns, no private keys', m.get('ok') and m['verdict']['ok'] and m['header_board'] == 'bench-c3-1'
          and m['scene']['clock']['unit'] == 'ns' and not any(k.startswith('_') for k in m), m)
    check('the connector table and power labels: the C3 power labels are GND 3V3 5V RST; its twin_pin/adc_channel answer GPIO3 / None; the UNO answers D6 -> PD6, A0 -> 0',
          LB.power_labels('esp32-c3') == frozenset({'GND', '3V3', '5V', 'RST'}) and LB.twin_pin('esp32-c3', 'GPIO3') == 'GPIO3' and LB.twin_pin('esp32-c3', 'GND') == '' and LB.adc_channel('esp32-c3', 'GPIO1') is None
          and LB.twin_pin('arduino-uno-r3', 'D6') == 'PD6' and LB.adc_channel('arduino-uno-r3', 'A0') == 0)
    from electrodevice.custom import board_family as BF
    check('header_label keeps a tie that is one of the board\'s pins (3V3 on the C3) and aliases otherwise (5V -> +5V on the UNO)', BF.header_label('3V3', BF.devboard_pins('esp32-c3')) == '3V3'
          and BF.header_label('5V', BF.devboard_pins('arduino-uno-r3')) == '+5V' and '+5V' in BF.devboard_pins('arduino-uno-r3') and '+5V' not in BF.devboard_pins('esp32-c3'))
    return _results


def main():
    run_checks()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
