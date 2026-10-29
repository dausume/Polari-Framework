"""board_registers_c3_selftest — rm-2b (REGISTER_MAPPING_PLAN.md D-rm-4, "the C3 drawing set"): the ESP32-C3 registers the drawing touches, from the TRM v1.4 (the same
file the C3 pin rows cite), with every bit position and address checked against ESP-IDF v5.5.5 at ingest (2026-10-29; the values pinned below are those it agreed on).
Every field cites its Register section + page and keeps the TRM's own access code; no two fields of a register share a bit; the per-pad facts are the pad's own (drive
table, reset state from Table 5.12-1); the access words cover every field (w1-set / w1-clear / fifo new); the rows reach the chain (Peripheral.registers_refs_json, SocPin /
PeripheralSignal references resolve, the TRM is the Datasheet); the Registers view answers for the C3 both ways in; the RESET stage reads the cited pad reset.

    PYTHONPATH=.:modules python3 -m board.board_registers_c3_selftest      # from polari-framework/
"""
import contextlib
import io
import json
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def table():
    from board.custom import registers_esp32c3 as R
    from board.custom import register_access as RA
    regs = {r['register']: r for r in R.REGISTERS}
    check('rm-2b THE DRAWING SET: 91 registers / 761 fields (pins x22 per-pad registers, the matrix, strap + reset cause, the GPIO + UART interrupt map, the system timer, '
          'clock/reset enables, UART0)', (len(R.REGISTERS), len(R.FIELDS)) == (91, 761) and {'GPIO_PIN21_REG', 'IO_MUX_GPIO0_REG', 'GPIO_FUNC6_IN_SEL_CFG_REG', 'GPIO_STRAP_REG',
                                                                                         'RTC_CNTL_RESET_STATE_REG', 'INTERRUPT_CORE0_UART_INTR_MAP_REG', 'SYSTIMER_UNIT0_VALUE_LO_REG',
                                                                                         'SYSTEM_PERIP_CLK_EN0_REG', 'UART0_CONF0_REG'} <= set(regs), (len(R.REGISTERS), len(R.FIELDS)))
    check('rm-2b CITED: every field names its TRM Register section + page and keeps the TRM\'s own access code ("TRM access R/W" ...); every register its section, page and '
          'reset', all('p.' in f['page_table'] and f['notes'].startswith('TRM access ') for f in R.FIELDS) and all('p.' in r['where'] and r['reset'] for r in R.REGISTERS))
    overlap = []
    for name in regs:
        bits = {}
        for f in [f for f in R.FIELDS if f['register'] == name]:
            for b in range(f['bit_lo'], f['bit_hi'] + 1):
                if b in bits:
                    overlap.append((name, f['field'], bits[b]))
                bits[b] = f['field']
    check('rm-2b no two fields of a register share a bit', not overlap, overlap[:3])
    addr = {n: R.address(regs[n]) for n in ('GPIO_OUT_REG', 'GPIO_PIN3_REG', 'GPIO_FUNC21_OUT_SEL_CFG_REG', 'IO_MUX_GPIO21_REG', 'UART0_CONF0_REG', 'SYSTEM_PERIP_CLK_EN0_REG',
                                            'INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG', 'RTC_CNTL_RESET_STATE_REG', 'SYSTIMER_UNIT0_VALUE_HI_REG')}
    check('rm-2b ADDRESSES = the module base (Table 3.3-3 p.98) + the printed offset - the values ESP-IDF v5.5.5 agreed on at ingest',
          addr == {'GPIO_OUT_REG': '0x60004004', 'GPIO_PIN3_REG': '0x60004080', 'GPIO_FUNC21_OUT_SEL_CFG_REG': '0x600045A8', 'IO_MUX_GPIO21_REG': '0x60009058',
                   'UART0_CONF0_REG': '0x60000020', 'SYSTEM_PERIP_CLK_EN0_REG': '0x600C0010', 'INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG': '0x600C2040',
                   'RTC_CNTL_RESET_STATE_REG': '0x60008038', 'SYSTIMER_UNIT0_VALUE_HI_REG': '0x60023040'}, addr)
    F = {(f['register'], f['field']): f for f in R.FIELDS}
    pos = {k: (F[k]['bit_hi'], F[k]['bit_lo']) for k in (('GPIO_PIN3_REG', 'INT_TYPE'), ('GPIO_PIN3_REG', 'INT_ENA'), ('IO_MUX_GPIO3_REG', 'MCU_SEL'), ('IO_MUX_GPIO3_REG', 'FUN_DRV'),
                                                        ('UART0_CONF0_REG', 'BIT_NUM'), ('UART0_STATUS_REG', 'TXFIFO_CNT'), ('SYSTEM_PERIP_CLK_EN0_REG', 'SYSTIMER_CLK_EN'),
                                                        ('RTC_CNTL_RESET_STATE_REG', 'RESET_CAUSE_PROCPU'), ('GPIO_FUNC6_IN_SEL_CFG_REG', 'SIG_IN_SEL'))}
    check('rm-2b BIT POSITIONS as ESP-IDF agreed (INT_TYPE 9:7, INT_ENA 17:13, MCU_SEL 14:12, FUN_DRV 11:10, BIT_NUM 3:2, TXFIFO_CNT 25:16, SYSTIMER_CLK_EN 29, RESET_CAUSE 5:0, '
          'SIG_IN_SEL 6)', pos == {('GPIO_PIN3_REG', 'INT_TYPE'): (9, 7), ('GPIO_PIN3_REG', 'INT_ENA'): (17, 13), ('IO_MUX_GPIO3_REG', 'MCU_SEL'): (14, 12),
                                  ('IO_MUX_GPIO3_REG', 'FUN_DRV'): (11, 10), ('UART0_CONF0_REG', 'BIT_NUM'): (3, 2), ('UART0_STATUS_REG', 'TXFIFO_CNT'): (25, 16),
                                  ('SYSTEM_PERIP_CLK_EN0_REG', 'SYSTIMER_CLK_EN'): (29, 29), ('RTC_CNTL_RESET_STATE_REG', 'RESET_CAUSE_PROCPU'): (5, 0),
                                  ('GPIO_FUNC6_IN_SEL_CFG_REG', 'SIG_IN_SEL'): (6, 6)}, pos)
    check('rm-2b PER PAD: the drive codes 1 / 2 swap on GPIO2/3/4/5/18/19 (Table 5.12-1 p.174 - the register text prints GPIO18 twice and omits GPIO4, the table is taken); '
          'reset per pad: GPIO9 input + pull-up, GPIO21 (U0TXD) output + pull-up, GPIO0 input disabled; GPIO19 notes its USB pull-up',
          F[('IO_MUX_GPIO4_REG', 'FUN_DRV')]['values']['1'] == '~20 mA' and F[('IO_MUX_GPIO8_REG', 'FUN_DRV')]['values']['1'] == '~10 mA'
          and (F[('IO_MUX_GPIO9_REG', 'FUN_IE')]['reset_value'], F[('IO_MUX_GPIO9_REG', 'FUN_WPU')]['reset_value']) == ('1', '1')
          and 'output enabled' in regs['IO_MUX_GPIO21_REG']['reset'] and F[('IO_MUX_GPIO0_REG', 'FUN_IE')]['reset_value'] == '0'
          and 'USB pull-up' in regs['IO_MUX_GPIO19_REG']['reset'] and 'omits GPIO4' in F[('IO_MUX_GPIO4_REG', 'FUN_DRV')]['notes'])
    check('rm-2b RESETS from the printed reset rows: GPIO_FUNCn_OUT_SEL 0x80 (= 128, simple GPIO output), UART0 8 data bits + 1 stop bit, both FIFO thresholds 0x60, UART0 / '
          'UART_MEM / TIMERGROUP / SYSTIMER clocks ON at reset, their resets released; the reset cause codes are Table 6.1-1\'s',
          F[('GPIO_FUNC3_OUT_SEL_CFG_REG', 'OUT_SEL')]['reset_value'] == '0x80' and (F[('UART0_CONF0_REG', 'BIT_NUM')]['reset_value'], F[('UART0_CONF0_REG', 'STOP_BIT_NUM')]['reset_value']) == ('3', '1')
          and all(F[('SYSTEM_PERIP_CLK_EN0_REG', '%s_CLK_EN' % w)]['reset_value'] == '1' for w in ('UART', 'UART_MEM', 'TIMERGROUP', 'SYSTIMER'))
          and all(F[('SYSTEM_PERIP_RST_EN0_REG', '%s_RST' % w)]['reset_value'] == '0' for w in ('UART', 'UART_MEM', 'TIMERGROUP', 'SYSTIMER'))
          and F[('RTC_CNTL_RESET_STATE_REG', 'RESET_CAUSE_PROCPU')]['values']['0x15'].startswith('USB (UART) reset'))
    kinds = {f['access'] for f in R.FIELDS}
    acc = {k['name']: k for k in RA.ACCESS_KINDS}
    check('rm-2b THE ACCESS WORDS cover every field: the TRM\'s WT set / clear registers are w1-set / w1-clear (they act on ANOTHER register), UART_FIFO is fifo (a read pops) - '
          'each a RegisterAccessKind row with its read / write effect; the TRM itself defines W0C ("Write 0 to clear", legend p.893-894) like the UNO\'s MCUSR rows',
          not RA.problems(R.FIELDS) and {'w1-set', 'w1-clear', 'fifo'} <= kinds and 'GPIO_OUT_REG' in acc['w1-set']['write_effect']
          and F[('UART0_FIFO_REG', 'RXFIFO_RD_BYTE')]['access'] == 'fifo' and 'pops' in acc['fifo']['read_effect'].lower(), sorted(kinds))
    check('rm-2b NO VALUE GUESSED: the UART frame-format codes are not in the TRM register text - the rows quote its ranges and say so', 'not the code of each value' in F[('UART0_CONF0_REG', 'BIT_NUM')]['notes'])


def chain():
    from board.custom import board_object as BO
    with contextlib.redirect_stdout(io.StringIO()):
        t = BO.seed_tables()
    regs = [r for r in t['Register'] if r['soc'] == 'esp32c3']
    flds = [f for f in t['RegisterField'] if f['soc'] == 'esp32c3']
    sig, sp = {r['name'] for r in t['PeripheralSignal']}, {r['name'] for r in t['SocPin']}
    per = {r['peripheral']: r for r in t['Peripheral'] if r['soc'] == 'esp32c3'}
    check('rm-2b IN THE CHAIN: 91 Register + 761 RegisterField rows for esp32c3; every affects_pin is a SocPin, every affects_signal a PeripheralSignal; the TRM is their Datasheet; '
          'GPIO / UART0 / SYSTIMER / SYSTEM / RTC_CNTL / INTMTX list their registers, a block with none says so', (len(regs), len(flds)) == (91, 761)
          and all(f['affects_pin'] in sp for f in flds if f['affects_pin']) and all(f['affects_signal'] in sig for f in flds if f['affects_signal'])
          and {f.get('datasheet') for f in flds} == {'espressif-esp32-c3-trm'}
          and all(json.loads(per[p]['registers_refs_json']) for p in ('GPIO', 'UART0', 'SYSTIMER', 'SYSTEM', 'RTC_CNTL', 'INTMTX'))
          and per['I2C0']['undetermined'].startswith('no register of this block'), (len(regs), len(flds)))


def views():
    from board.custom import register_view as RV
    from board.custom import pin_stages as P
    u3 = RV.pin_uses('esp32c3', 'GPIO3')
    u20 = RV.pin_uses('esp32c3', 'GPIO20')
    check('rm-2b BOTH WAYS for the C3: pin GPIO3 -> its GPIO_PIN3 / IO_MUX_GPIO3 fields with their categories + the BUTTON_PIN HAL value + the C3\'s OWN atoms (hal_button_arm '
          'certain - cmod.custom.c3_atoms), never a UNO atom; GPIO20 reaches GPIO_FUNC6_IN_SEL (U0RXD_in) as the matrix signal of its IO MUX function U0RXD',
          any(r['name'] == 'GPIO_PIN3_REG.INT_TYPE' and 'mcu-pin/interrupt' in r['category'] for r in u3) and any(r['kind'] == 'HAL variable' and r['name'] == 'BUTTON_PIN' for r in u3)
          and any(r['kind'] == 'C atom' and r['name'] == 'c3:apps/light_hal.hal_button_arm' and r['status'] == 'certain' for r in u3)
          and not any(r['name'].startswith('uno:') for r in u3)
          and any(r['name'] == 'GPIO_FUNC6_IN_SEL_CFG_REG.IN_SEL' and 'IO MUX function' in r['how'] for r in u20), [r['name'] for r in u20][:6])
    s9 = P.assess('esp32-c3', 'GPIO9')['stages'][0]
    s21 = P.assess('esp32-c3', 'GPIO21')['stages'][0]
    check('rm-2b RESET STAGE from the cited pad reset: GPIO9 = input, pull-up (Reset code 3) + its strapping warning; GPIO21 = output, pull-up (code 4); the UNO\'s D0 still reads '
          'its DDRD / PORTD fields', s9['direction'] == 'input, pull-up' and 'Reset code 3' in s9['reasons'] and 'strapping' in s9['reasons'] and s21['direction'] == 'output, pull-up'
          and 'DDRD.DDD0 = 0' in P.assess('arduino-uno-r3', 'D0')['stages'][0]['register_fields'], (s9['direction'], s21['direction']))
    order = [p['soc_pin'] for p in RV.pins('esp32c3')]
    check('rm-2b the pins list runs GPIO0, GPIO1, GPIO2 ... GPIO21 (natural order)', order == ['GPIO%d' % n for n in range(22)], order[:12])
    from moduleService.manifests import conform
    r = conform('board')
    check('MANIFEST: pol modules conform board is clean with registers_esp32c3 + this selftest listed', r['ok'], r.get('findings'))


def main():
    table()
    chain()
    views()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
