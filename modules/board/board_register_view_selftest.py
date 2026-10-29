"""board_register_view_selftest — rm-3 (REGISTER_MAPPING_PLAN.md §5): the Registers view's doors over the chain - both chips answer (the C3 with every branch
at count 0, said "not ingested yet"); a branch lists its registers with title / address / roles / field count; a register's fields spell out their access
word from the RegisterAccessKind row (MCUSR's w0c flags: "write zero to clear", on_read / on_write); the firmware's settings for a register (uno-light's
DDRD init: DDD2 / DDD3 inputs, DDD6 the LED output, each with its task); the atoms that touch it (hal_usart_init -> UCSR0B); a field's pin and its
lifecycle stages (DDRD.DDD0 -> D0, owned by the boot firmware in BOOTLOADER); the doors' 404 / 422 / empty answers; the manifest.

    PYTHONPATH=.:modules python3 -m board.board_register_view_selftest      # from polari-framework/
"""
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def model():
    from board.custom import register_view as RV
    s = {r['soc']: r for r in RV.socs()}
    c3 = RV.categories('esp32c3')
    check('BOTH CHIPS ANSWER: the 328P has 96 registers / 148 fields, the C3 (rm-2b) its drawing set of 91 registers / 761 fields; the C3 register categories carry '
          'counts (pins, matrix, UART, timer, clock, reset, interrupt vectors) and a category none of its registers lands in stays future scope',
          (s['atmega328p']['registers'], s['atmega328p']['fields']) == (96, 148) and (s['esp32c3']['registers'], s['esp32c3']['fields']) == (91, 761)
          and {r['path'] for r in c3 if r['count']} >= {'mcu-pin/interrupt', 'soc-interconnect/matrix', 'mcu-peripheral/uart', 'mcu-peripheral/timer', 'mcu-system/clock'}
          and all(r['state'] == 'future scope' for r in c3 if not r['count']), s)
    t = {r['path']: r for r in RV.categories('atmega328p')}
    uart = {r['register']: r for r in RV.registers('atmega328p', 'mcu-peripheral/uart')}
    check('REGISTER CATEGORY -> REGISTERS: mcu-peripheral/uart holds the USART0 registers; UCSR0A = "USART Control and Status Register 0 A" at 0xc0 (mem), read status + control, '
          '8 fields, cited §20.11.2', t['mcu-peripheral/uart']['count'] == 7 and uart['UCSR0A']['title'] == 'USART Control and Status Register 0 A'
          and uart['UCSR0A']['address'] == '0xc0 (mem)' and uart['UCSR0A']['read_roles'] == 'status, control' and uart['UCSR0A']['fields'] == 8
          and '§20.11.2' in uart['UCSR0A']['cite'], uart.get('UCSR0A'))
    f = {r['field']: r for r in RV.detail('atmega328p', 'MCUSR')}
    check('FIELDS SPELL OUT THEIR ACCESS: MCUSR.PORF is w0c = "write zero to clear" with what a read and a write do (from the RegisterAccessKind row); fields run '
          'from the highest bit down', f['PORF']['access_means'] == 'write zero to clear' and 'CLEARS' in f['PORF']['on_write'] and f['PORF']['on_read']
          and [r['field'] for r in RV.detail('atmega328p', 'MCUSR')] == ['WDRF', 'BORF', 'EXTRF', 'PORF'], f.get('PORF'))
    st = {r['field']: r for r in RV.detail('atmega328p', 'DDRD', 'settings')}
    check('SETTINGS: uno-light\'s DDRD init - DDD2 (button) and DDD3 (sense) inputs, DDD6 the LED output, each with the task that owns it and the field\'s meaning',
          set(st) == {'DDD2', 'DDD3', 'DDD6'} and st['DDD6']['value'] == '1' and st['DDD6']['task'] == 'led_init' and st['DDD2']['task'] == 'button_init'
          and 'output' in st['DDD6']['meaning'], sorted(st))
    at = RV.detail('atmega328p', 'UCSR0B', 'atoms')
    check('ATOMS: the C atom that touches UCSR0B is hal.hal_usart_init (the cmod parse)', [a['atom'] for a in at] == ['uno:hal.hal_usart_init'], at)
    p = {r['stage']: r for r in RV.field_pins('atmega328p', 'DDRD.DDD0')}
    check('FIELD -> PIN -> STAGES: DDRD.DDD0 drives PD0 = UNO D0; its BOOTLOADER stage is owned by the boot firmware (Optiboot), ACTIVE by the bridge; a field that '
          'drives no pin (MCUSR.PORF) has no rows; an unknown register / field is None',
          p['BOOTLOADER']['owner'] == 'boot-firmware' and p['ACTIVE']['owner'] == 'bridge' and p['RESET']['board_pin'] == 'D0'
          and RV.field_pins('atmega328p', 'MCUSR.PORF') == [] and RV.detail('atmega328p', 'NOPE') is None and RV.field_pins('atmega328p', 'NOPE.X') is None,
          {k: v['owner'] for k, v in p.items()})


def pin_first():
    from board.custom import register_view as RV
    u = RV.pin_uses('atmega328p', 'D2')
    kinds = {r['kind'] for r in u}
    fields = {r['name']: r for r in u if r['kind'] == 'register field'}
    sets = {r['name']: r for r in u if r['kind'] == 'firmware setting'}
    certain = [r['name'] for r in u if r['kind'] == 'C atom' and r['status'] == 'certain']
    check('THE OTHER WAY IN - pin D2: its register fields WITH their register categories (EICRA.ISC0 / EIMSK.INT0 / EIFR.INTF0 through INT0, a function PD2 offers; '
          'DDRD.DDD2 / PORTD.PORTD2 / PIND.PIND2 / PCMSK2.PCINT18 naming the pin), uno-light\'s init settings of them (falling edge, pull-up, owned by button_init), the '
          'led_toggle assertion, the BUTTON_PIN HAL variable and the C atoms', kinds == {'register field', 'firmware setting', 'Catom assertion', 'HAL variable', 'C atom'}
          and fields['EICRA.ISC0']['category'] == 'mcu-pin/interrupt' and 'through INT0' in fields['EICRA.ISC0']['how'] and fields['DDRD.DDD2']['how'] == 'names the pin'
          and 'falling edge' in sets['EICRA.ISC0']['detail'] and 'button_init' in sets['EICRA.ISC0']['used_by']
          and any(r['kind'] == 'Catom assertion' and r['name'] == 'apps/light.led_toggle' for r in u)
          and any(r['kind'] == 'HAL variable' and r['name'] == 'BUTTON_PIN' for r in u), sorted(kinds))
    d6 = [r for r in RV.pin_uses('atmega328p', 'PD6') if r['kind'] == 'C atom']
    sure6 = {r['name']: r for r in d6 if r['status'] == 'certain'}
    check('CERTAIN vs REGISTER ONLY: a C atom USES the pin only on evidence - its POLARI_NODE uses() annotation declares the HAL value at the pin (D2: hal_button_init, '
          'hal_presses; D6: hal_led, apps/light.led_follow_state) or an assertion names it; an atom that only shares PORTD (hal_led for D2) is "register only", said',
          {'uno:hal.hal_button_init', 'uno:hal.hal_presses'} <= set(certain) and {'uno:hal.hal_led', 'uno:apps/light.led_follow_state'} <= set(sure6)
          and 'uses(LED_PIN)' in sure6['uno:hal.hal_led']['how']
          and next(r for r in u if r['name'] == 'uno:hal.hal_led')['status'] == 'register only', (certain, sorted(sure6)))
    d0 = RV.pin_uses('atmega328p', 'D0')
    check('D0 reaches USART0: UCSR0B.RXEN0 names it (the one USART field that configures the pin; the status / interrupt fields are one click away in UCSR0A/B), the '
          'USART_RX_vect and apply_command assertions, UART0_RX_PIN; '
          'pins() lists every 328P pin with its board name and functions; an unknown pin is None',
          any(r['name'] == 'UCSR0B.RXEN0' and r['how'] == 'names the pin' and r['category'] == 'mcu-peripheral/uart' for r in d0)
          and {r['name'] for r in d0 if r['kind'] == 'Catom assertion'} == {'hal.USART_RX_vect', 'apps/light.apply_command'}
          and any(r['kind'] == 'HAL variable' and r['name'] == 'UART0_RX_PIN' for r in d0)
          and {p['soc_pin']: p['board_pin'] for p in RV.pins('atmega328p')}['PD2'] == 'D2' and RV.pin_uses('atmega328p', 'D99') is None)


def doors():
    from board.register_view_api import RegisterViewAPI
    api = RegisterViewAPI(polServer=None, manager=None)

    def call(method, *args, params=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        getattr(api, method)(types.SimpleNamespace(get_param=lambda k: (params or {}).get(k)), resp, *args)
        return resp
    socs, tree, regs = call('on_get_socs'), call('on_get_categories', 'esp32c3'), call('on_get_registers', 'atmega328p', params={'category': 'mcu-system/reset'})
    f, bad_view, ghost = call('on_get_register', 'atmega328p', 'UCSR0A'), call('on_get_register', 'atmega328p', 'UCSR0A', params={'view': 'x'}), \
        call('on_get_register', 'atmega328p', 'NOPE')
    pins, nopin, bad_soc = call('on_get_field_pins', 'atmega328p', 'DDRD.DDD6'), call('on_get_field_pins', 'atmega328p', 'MCUSR.PORF'), call('on_get_categories', 'z80')
    uses, hal, ghost_pin = call('on_get_pin_uses', 'atmega328p', 'D2'), call('on_get_pin_uses', 'atmega328p', 'D2', params={'kind': 'HAL variable'}), \
        call('on_get_pin_uses', 'atmega328p', 'D99')
    check('PIN DOORS: .../pins/D2/uses = flat rows of every kind (soc_pin PD2); ?kind=HAL variable narrows to BUTTON_PIN; an unknown pin 404',
          uses.media['soc_pin'] == 'PD2' and uses.media['count'] > 10 and all(not isinstance(v, (dict, list)) for r in uses.media['rows'] for v in r.values())
          and [r['name'] for r in hal.media['rows']] == ['BUTTON_PIN'] and ghost_pin.status.startswith('404'), (uses.media.get('count'), ghost_pin.status))
    check('DOORS: /api/board/socs lists both chips; .../esp32c3/register-categories answers; .../registers?category=mcu-system/reset = MCUSR + WDTCSR; .../registers/UCSR0A = '
          '8 flat field rows; unknown view 422, unknown register 404; .../fields/DDRD.DDD6/pins = 4 stages, MCUSR.PORF = no rows with a note; unknown soc 422',
          socs.media['count'] == 2 and tree.media['count'] > 0 and [r['register'] for r in regs.media['rows']] == ['MCUSR', 'WDTCSR']
          and f.media['count'] == 8 and all(not isinstance(v, (dict, list)) for r in f.media['rows'] for v in r.values())
          and bad_view.status.startswith('422') and ghost.status.startswith('404') and pins.media['count'] == 4 and nopin.media['count'] == 0
          and 'note' in nopin.media and bad_soc.status.startswith('422'), (regs.media.get('rows') and [r['register'] for r in regs.media['rows']], bad_soc.status))
    from moduleService.manifests import conform
    r = conform('board')
    check('MANIFEST: pol modules conform board is clean with the register view files listed', r['ok'], r.get('findings'))


def main():
    model()
    pin_first()
    doors()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
