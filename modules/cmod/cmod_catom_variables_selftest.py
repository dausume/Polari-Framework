"""cmod_catom_variables_selftest — hsp-3d (HARDWARE_SYSTEM_PINS_PLAN.md §7 "Catom VARIABLES = the generalized HAL"): the plan's proof - UART0_TX_PIN = PD2 refused
naming the pins that offer TXD; = PD1 accepted with the bootloader warning naming Optiboot; the pin view's rows show uart.tx at PD1; the generated HAL lines carry
the value - plus the scope ladder (chip -> board -> bench), one pin one role, the C3's IO MUX vs GPIO matrix and strapping warnings, number roles, the
defines-role assertions, the no-code slots, the doors, and the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_catom_variables_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from cmod.custom import catom_variables as CV
    from cmod.custom import catom_assertions as CA
    uno = CV._rows('uno-light', None)
    var = {v['variable']: v for v in uno}
    tx = var['UART0_TX_PIN']
    r = CV.check(tx, 'PD2', uno)
    check('PROOF 1: UART0_TX_PIN = PD2 is REFUSED, naming what PD2 offers and the pin that offers TXD (PD1)',
          r['verdict'] == 'refused' and 'PD2 offers INT0, PCINT18, not uart.tx' in r['why'][0] and 'offered by PD1 (TXD)' in r['why'][0], r['why'][:2])
    r = CV.check(tx, 'PD1', uno)
    check('PROOF 2: UART0_TX_PIN = PD1 is accepted WITH the bootloader warning naming Optiboot (verdict warning, nothing refused)',
          r['verdict'] == 'warning' and r['function'] == 'TXD' and any('BOOTLOADER' in w and 'Optiboot' in w for w in r['why']), r['why'][:3])
    pins = {p['variable']: p for p in CV.pin_roles('uno-light')}
    check('PROOF 3: the pin view\'s rows (the same rows the rules read) put uart.tx at PD1, gpio.out at PD6, int.ext at PD2, gpio.in at PD3',
          (pins['UART0_TX_PIN']['pin'], pins['UART0_TX_PIN']['role']) == ('PD1', 'uart.tx') and pins['LED_PIN']['pin'] == 'PD6'
          and (pins['BUTTON_PIN']['pin'], pins['BUTTON_PIN']['role']) == ('PD2', 'int.ext') and pins['SENSE_PIN']['pin'] == 'PD3', pins)
    h = CV.render_header('uno-light')
    check('PROOF 4: the generated HAL lines carry the values in the firmware\'s own spelling (UART0_TX_PIN PD1, LED_PIN 6 - an Arduino number, F_CPU 16000000UL)',
          '#define UART0_TX_PIN   PD1' in h and '#define LED_PIN        6 ' in h and '#define F_CPU          16000000UL' in h and 'WARNING' in h, h)
    vs = {v['variable']: v for v in CV.variables('uno-light')}
    check('SCOPES: the narrowest value wins - LED_PIN board D13 overridden by the bench D6 (scope bench, basis the uno-light knobs); UART0 pins from the chip default '
          '(cited Table 14-9); F_CPU from the board',
          (vs['LED_PIN']['value'], vs['LED_PIN']['scope']) == ('D6', 'bench') and 'led_pin 6' in vs['LED_PIN']['value_basis']
          and (vs['UART0_TX_PIN']['value'], vs['UART0_TX_PIN']['scope']) == ('PD1', 'chip') and 'Table 14-9' in vs['UART0_TX_PIN']['value_basis']
          and vs['F_CPU']['scope'] == 'board', {k: (v['value'], v['scope']) for k, v in vs.items()})
    check('SEEDS: every uno-light variable holds (UART pins warn for the bootloader; LED / button / sense / F_CPU accepted)',
          {k: v['status'] for k, v in vs.items()} == {'UART0_TX_PIN': 'warning', 'UART0_RX_PIN': 'warning', 'LED_PIN': 'accepted', 'BUTTON_PIN': 'accepted',
                                                      'SENSE_PIN': 'accepted', 'F_CPU': 'accepted'}, {k: v['status'] for k, v in vs.items()})
    r = CV.check(var['LED_PIN'], 'D1', uno)
    check('LIFECYCLE + ONE PIN ONE ROLE: LED_PIN = D1 refused - D1 reserved in BOOTLOADER / INIT / RUNTIME by the serial transport (a GPIO claim fights the 16U2), '
          'and UART0_TX_PIN already claims PD1',
          r['verdict'] == 'refused' and any('RUNTIME' in w and '16U2' in w for w in r['why']) and any('UART0_TX_PIN already claims PD1' in w for w in r['why']), r['why'])
    r = CV.check(var['BUTTON_PIN'], 'PD6', uno)
    check('ROLE: an external interrupt on PD6 refused, naming PD2 (INT0) and PD3 (INT1)', r['verdict'] == 'refused' and 'PD2 (INT0), PD3 (INT1)' in r['why'][0], r['why'][0])
    check('PIN NAMES: D6 / 6 / PD6 resolve to PD6, A0 to PC0; a non-pin is refused by name',
          CV.resolve_pin('atmega328p', 'D6') == CV.resolve_pin('atmega328p', '6') == CV.resolve_pin('atmega328p', 'PD6') == 'PD6'
          and CV.resolve_pin('atmega328p', 'A0') == 'PC0' and CV.check(var['LED_PIN'], 'D99', uno)['why'] == ["'D99' is not a pin of the atmega328p"])
    check('NUMBER role: F_CPU = "fast" refused; 8000000 accepted', CV.check(var['F_CPU'], 'fast', uno)['verdict'] == 'refused'
          and CV.check(var['F_CPU'], '8000000', uno)['verdict'] == 'accepted')
    c3 = CV._rows('esp32c3-light', None)
    c3v = {v['variable']: v for v in CV.variables('esp32c3-light')}
    m = CV.check(c3v['UART0_TX_PIN'], 'GPIO7', c3)
    s9 = CV.check(c3v['UART0_TX_PIN'], 'GPIO9', c3)
    check('C3: UART0 TX on GPIO21 is the IO MUX function (warning: the download-boot link); GPIO7 routes it through the GPIO matrix naming GPIO21; GPIO9 warns its '
          'strapping role; the light pins GPIO0/3/1 accepted (lifecycle_c3 gives them no row)',
          c3v['UART0_TX_PIN']['function'] == 'U0TXD' and c3v['UART0_TX_PIN']['status'] == 'warning' and m['function'] == 'matrix:U0TXD' and 'GPIO21' in m['why'][0]
          and s9['verdict'] == 'warning' and any('strapping' in w for w in s9['why'])
          and all(c3v[k]['status'] == 'accepted' for k in ('LED_PIN', 'BUTTON_PIN', 'SENSE_PIN')), (m['why'][0], {k: v['status'] for k, v in c3v.items()}))
    ra = CV.role_assertions('uno-light')
    txa = [a for a in ra if a['variable'] == 'UART0_TX_PIN']
    check('ASSERTIONS: each pin variable makes a defines-role Catom assertion by the catoms that read it (UART0_TX_PIN -> telemetry_send + hal_usart_send at PD1); '
          'defines-role is in the assertion vocabulary',
          'defines-role' in CA.KINDS and {a['atom'] for a in txa} == {'apps/light.telemetry_send', 'hal.hal_usart_send'} and all(a['pins'] == 'PD1' and a['kind'] == 'defines-role'
                                                                                                                                for a in txa), txa)
    sl = CV.slots(var['UART0_TX_PIN'], uno)
    sb = CV.slots(var['LED_PIN'], uno)
    check('SLOTS (no-code): the uart.tx slot offers only PD1 (with its warning); the gpio.out slot lists accepted pins first, leaves out D0/D1 (transport) and the '
          'pins other variables claim, and counts the refusals',
          [o['pin'] for o in sl['options']] == ['PD1'] and sl['options'][0]['verdict'] == 'warning' and 'PD1' not in [o['pin'] for o in sb['options']]
          and 'PD0' not in [o['pin'] for o in sb['options']] and 'PD2' not in [o['pin'] for o in sb['options']] and sb['refused'] > 0
          and sb['options'][0]['verdict'] == 'accepted', ([o['pin'] for o in sl['options']], [o['pin'] for o in sb['options']]))
    from cmod.cmod_catom_api import CatomVariableAPI
    api = CatomVariableAPI(polServer=None, manager=None)

    def call(method, variant, params=None, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(get_param=lambda k: (params or {}).get(k), bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, variant)
        return resp
    g, hd, sv, bad = call('on_get', 'uno-light'), call('on_get', 'uno-light', {'view': 'header'}), call('on_get', 'uno-light', {'view': 'slots', 'variable': 'BUTTON_PIN'}), \
        call('on_get', 'nope')
    p2, p1 = call('on_post_check', 'uno-light', body={'variable': 'UART0_TX_PIN', 'value': 'PD2'}), call('on_post_check', 'uno-light', body={'variable': 'UART0_TX_PIN', 'value': 'PD1'})
    check('DOORS: GET /api/cmod/catom-variables/uno-light = 6 variables; ?view=header = the HAL text; ?view=slots&variable=BUTTON_PIN = PD2; unknown variant 404; '
          'POST .../check refuses PD2 and warns PD1 with written=false',
          g.media['count'] == 6 and '#define UART0_TX_PIN' in hd.media['text'] and [o['pin'] for o in sv.media['options']] == ['PD2'] and bad.status.startswith('404')
          and p2.media['verdict'] == 'refused' and p1.media['verdict'] == 'warning' and p1.media['written'] is False, (g.media.get('count'), bad.status))
    from moduleService.manifests import conform
    r = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with CatomVariable + the new files listed', r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
