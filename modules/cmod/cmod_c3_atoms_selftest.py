"""cmod_c3_atoms_selftest — the ESP32-C3 firmware as atoms (cmod.custom.c3_atoms): the committed manifest is what a fresh parse gives (regenerating unchanged sources
gives the same atoms); the chip HAL's atoms reach the registers through the ESP-IDF drivers, every link cited to the IDF source; each call is judged on ITS OWN
arguments (the LED config's output setup lands on GPIO0 only, the button's interrupt on GPIO3 only; the trace UART is UART1 - not ingested, said; uart_up's two
callers resolved separately, the guarded uart_set_pin adds nothing for UART0); the pins an atom's body names are its declared HAL values; RV32 widths; cost not
measured, said; the rows reach the seed as project c3 and the Registers view's pins show the code that uses them, the UNO's atoms never on a C3 pin.

    PYTHONPATH=.:modules python3 -m cmod.cmod_c3_atoms_selftest      # from polari-framework/
"""
import json
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from cmod.custom import c3_atoms as C
    committed = json.load(open(C.MANIFEST))
    fresh = C.generate()
    check('C3 ATOMS: the committed polari-firmware.json is what a fresh parse of the sources gives (41 atoms, no parse problem)',
          fresh == committed and len(committed['atoms']) == 41 and not committed['problems'], (len(fresh['atoms']), fresh == committed))
    A = {a['name']: a for a in committed['atoms']}

    def regs(n):
        return [r['name'] for r in A[n]['resources'] if r['kind'] == 'register']

    def declared(n):
        return [r['name'] for r in A[n]['resources'] if r['kind'] == 'declared']
    check('CHIP HAL: hal_led_write -> GPIO_OUT_W1TS / W1TC (gpio_set_level), declares LED_PIN; hal_sense_read -> GPIO_IN, SENSE_PIN; hal_button_arm -> the GPIO '
          'interrupt map + GPIO_PIN3 (gpio_isr_handler_add on BUTTON_GPIO), BUTTON_PIN',
          regs('apps/light_hal.hal_led_write') == ['GPIO_OUT_W1TS_REG', 'GPIO_OUT_W1TC_REG'] and declared('apps/light_hal.hal_led_write') == ['LED_PIN']
          and regs('apps/light_hal.hal_sense_read') == ['GPIO_IN_REG'] and declared('apps/light_hal.hal_sense_read') == ['SENSE_PIN']
          and regs('apps/light_hal.hal_button_arm') == ['INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG', 'GPIO_PIN3_REG'], regs('apps/light_hal.hal_button_arm'))
    init = set(regs('apps/light_hal.hal_pins_init'))
    check('PER CALL, NOT PER BODY: hal_pins_init\'s three gpio_config calls are judged on their own initializers - output enable + matrix select only for the LED (GPIO0), '
          'the interrupt type only for the button (GPIO3), the IO MUX pad of all three; never an output register for an input pin',
          {'IO_MUX_GPIO0_REG', 'IO_MUX_GPIO1_REG', 'IO_MUX_GPIO3_REG', 'GPIO_ENABLE_W1TS_REG', 'GPIO_FUNC0_OUT_SEL_CFG_REG', 'GPIO_PIN3_REG'} <= init
          and not {'GPIO_FUNC1_OUT_SEL_CFG_REG', 'GPIO_FUNC3_OUT_SEL_CFG_REG', 'GPIO_PIN0_REG', 'GPIO_PIN1_REG'} & init, sorted(init))
    up = [(r['kind'], r['name']) for r in A['main/polari_c3.uart_up']['resources'] if r['kind'] in ('register', 'note')]
    check('PORTS FROM THE CALLERS: uart_up(port, ...) configures UART0 (clock, reset, baud, frame, its interrupt) through its FRAME_UART caller; its TRACE_UART caller is '
          'UART1 - "not ingested", said; the guarded uart_set_pin adds no UART0 pin routing (the FRAME caller passes -1); polari_line writes the trace UART1, not UART0\'s FIFO',
          {'UART0_CLKDIV_REG', 'UART0_CONF0_REG', 'SYSTEM_PERIP_CLK_EN0_REG', 'SYSTEM_PERIP_RST_EN0_REG', 'INTERRUPT_CORE0_UART_INTR_MAP_REG'} <= {n for k, n in up if k == 'register'}
          and ('note', '(UART1 - its registers are not ingested)') in up and not any('OUT_SEL' in n or 'IN_SEL' in n for _k, n in up)
          and 'UART0_FIFO_REG' not in regs('main/polari_c3.polari_line'), up)
    cited = [r['detail'] for a in committed['atoms'] for r in a['resources'] if r['kind'] == 'register']
    check('CITED: every register link names the ESP-IDF file:line chain it was read from (components/...:NNN) and the IDF version', cited
          and all('components/' in d and 'ESP-IDF v5.5.5' in d and any(ch.isdigit() for ch in d.split('components/')[1][:60]) for d in cited), cited[:1])
    tel = A['main/polari_c3.telemetry_task']
    check('the timestamp: esp_timer_get_time reaches SYSTIMER UNIT0 (SYSTIMER_COUNTER_ESPTIMER = 0); the frames go out UART0\'s FIFO',
          {'SYSTIMER_UNIT0_OP_REG', 'SYSTIMER_UNIT0_VALUE_LO_REG', 'UART0_FIFO_REG'} <= set(regs('main/polari_c3.telemetry_task')), regs('main/polari_c3.telemetry_task'))
    check('RV32: an int is 4 bytes here (the C3\'s ilp32), struct widths are not computed (0, never a wrong sum); cost NOT measured, said on every atom; isr_safe '
          'undetermined (the AVR rules do not analyse FreeRTOS), said', committed['parser']['abi'] == 'riscv32 ilp32'
          and all(a['cost']['why'].startswith('not measured') and a['isr_safe'] == 'undetermined' for a in committed['atoms'])
          and any(p['ctype'] == 'int' and p['width_bytes'] == 4 for a in committed['atoms'] for p in a['ports']), tel['ports'])
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    seeded = {n: rs for n, _c, rs in CMOD_SEED_PAIRS}
    c3 = [a for a in seeded['CFunctionAtom'] if a['name'].startswith('c3:')]
    check('SEEDED: the C3 atoms are CFunctionAtom rows of project c3 (41), beside the UNO\'s; CProject c3 with its modules', len(c3) == 41
          and any(p['name'] == 'c3' for p in seeded['CProject']) and any(m['project'] == 'c3' for m in seeded['CModule']), len(c3))
    from board.custom import register_view as RV
    u0 = RV.pin_uses('esp32c3', 'GPIO0')
    certain = [r['name'] for r in u0 if r['kind'] == 'C atom' and r['status'] == 'certain']
    check('THE PINS SHOW THEIR CODE: C3 GPIO0 -> hal_led_write and hal_pins_init are CERTAIN ("its body names LED_GPIO (the HAL value LED_PIN)"), no UNO atom on a C3 pin, '
          'and the C3 register GPIO_OUT_W1TS lists only C3 code', set(certain) == {'c3:apps/light_hal.hal_led_write', 'c3:apps/light_hal.hal_pins_init'}
          and not any(r['name'].startswith('uno:') for r in u0) and any('names LED_GPIO' in r['how'] for r in u0 if r['kind'] == 'C atom')
          and all(x['atom'].startswith('c3:') for x in RV.detail('esp32c3', 'GPIO_OUT_W1TS_REG', 'atoms')), certain)
    from moduleService.manifests import conform
    r = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with c3_atoms + c3_fake_headers + this selftest listed', r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
