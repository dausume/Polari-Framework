"""
@module board.custom.registers_esp32c3

rm-2b (REGISTER_MAPPING_PLAN.md D-rm-4 "the C3 drawing set"): THE ESP32-C3 REGISTERS his notebook drawing touches, read on 2026-10-29 from the SAME TRM file the C3's
pin-function rows cite (esp32c3_evidence: v1.4, sha256 90ef8256...7423 - re-fetched, matched; `pdftotext -layout`, printed page = PDF page index). Every bit position
was ALSO checked against ESP-IDF v5.5.5's own register headers (components/soc/esp32c3/register/soc/*.h, read from the prf-esp-engines image) - they agree
field for field; the TRM is the citation, the headers the cross-check.

  pins: output / enable / input  GPIO_OUT / _W1TS / _W1TC, GPIO_ENABLE / _W1TS / _W1TC, GPIO_IN (§5.15 Register 5.2-5.9, pp.179-182), one field per pad bit
  pins: interrupt                GPIO_PINn_REG x22 (Register 5.14 p.184), GPIO_STATUS / _W1TC (5.10 / 5.12, pp.182-183)
  pins: pad electrical           IO_MUX_GPIOn_REG x22 (Register 5.21, pp.187-188): MCU_SEL, FUN_DRV, FUN_IE, FUN_WPU/WPD, the sleep set, FILTER_EN; reset per pad from
                                 Table 5.12-1 p.174 (DRV + the Reset code, legend p.175)
  the GPIO matrix                GPIO_FUNCn_OUT_SEL_CFG_REG x22 (Register 5.17 pp.185-186); GPIO_FUNC6_IN_SEL_CFG_REG = U0RXD_in (Register 5.16 p.185; Table 5.11-1 p.169)
  reset / boot                   GPIO_STRAP_REG (5.8 pp.181-182: GPIO2 / GPIO8 / GPIO9), RTC_CNTL_RESET_STATE_REG (Register 9.12 p.239; codes Table 6.1-1 p.193)
  interrupts to the CPU          INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG (source 16) + _UART_INTR_MAP_REG (source 21) (Register 8.7 / 8.11, field p.214; Table 8.3-1 p.204)
  timestampHW (the IDF tick)     SYSTIMER_CONF / UNIT0_OP / UNIT0_VALUE_HI / _LO (Register 10.1 / 10.2 / 10.5 / 10.6, pp.277-279)
  clocks + resets (init)         SYSTEM_PERIP_CLK_EN0 / _RST_EN0 (Register 16.3 p.435 / 16.5 pp.437-438; Table 16.3-2 p.430): UART0, UART_MEM, TIMERGROUP, SYSTIMER only
  UART0                          UART_FIFO / CLKDIV / CONF0 / CONF1 / STATUS at UART0's base (Register 26.1 / 26.7 / 26.9 / 26.10 / 26.19, pp.571-586)
Absolute address = the module base (Table 3.3-3 Module/Peripheral Address Mapping, p.98) + the register's printed offset.

hal-3a (2026-11-13, econ) adds a second PART beside rm-2b's drawing set (each register's 'part': 'drawing' | 'hal-3a'; part(name) -> rows): the registers
the generated HAL's families need, starting with the pwm family's LEDC (Chapter 32, Registers 32.1-32.8, pp.836-839: CH0..5 CONF0 / HPOINT / DUTY / CONF1 /
DUTY_R, TIMER0..3 CONF / VALUE, LEDC_CONF); the adc family's SAR ADC1 one-time sampling (Chapter 34: CTRL, ONETIME_SAMPLE, 1_DATA_STATUS, the ADC1_DONE
interrupt bits, CLKM_CONF); the alarm family's SYSTIMER COMP0 (TARGET0_HI / LO / CONF, COMP0_LOAD, the TARGET0 interrupt bits); the LEDC / APB_SARADC
clock + reset bits (in the drawing set's SYSTEM registers: `part` is per field); and the LEDC / SYSTIMER_TARGET0 / APB_ADC interrupt maps. Its codes and sentences are accepted only where the TRM field name AND the register header agree; its bit
positions and register offsets come from Espressif's SVD and are checked against ESP-IDF v5.5.5's own soc/*_reg.h (301 / 301; LEDC's interrupt bits read from the TRM's rendered pages). Every field also carries
`trm_access`, the TRM code verbatim: the generated HAL's access table maps from it, never from the lossy `access` word. A field the TRM does not describe
(LEDC TICK_SEL) has an empty trm_access and says so, so the HAL treats it as missing.

The TRM's OWN access code (R/W, RO, R/W/SS, WT, WO, R/SS/WTC ..., legend "Access Types for Registers" p.893) is kept verbatim on every field (`notes`: "TRM access
...") beside Polari's access word (board.custom.register_access). A register the drawing does not touch is NOT here; a wide register lists only the fields the drawing
needs and says the rest is documented, not ingested. Where the TRM gives no value codes (UART frame format) the row quotes its words and says so - never a guess.
"""
from board.custom import esp32c3_evidence as EV

SOC = EV.SOC
PADS = range(22)
BASES = {'UART0': 0x60000000, 'GPIO': 0x60004000, 'RTC_CNTL': 0x60008000, 'IO_MUX': 0x60009000, 'LEDC': 0x60019000, 'SYSTIMER': 0x60023000,
         'APB_SARADC': 0x60040000, 'SYSTEM': 0x600C0000, 'INTMTX': 0x600C2000}
#: hal-3a: the ADC controller's base is printed on the table's continuation page (Table 3.3-3 cont'd, p.99: "ADC Controller 0x6004_0000")
BASE_CITE = 'Table 3.3-3 Module/Peripheral Address Mapping, p.98'
#: the block a register belongs to -> the Peripheral row (esp32c3_chain_meta): IO MUX registers belong to the GPIO block's chapter (TRM Chapter 5 "IO MUX and GPIO Matrix")
PERIPHERAL_OF = {'UART0': 'UART0', 'GPIO': 'GPIO', 'IO_MUX': 'GPIO', 'RTC_CNTL': 'RTC_CNTL', 'LEDC': 'LEDC', 'SYSTIMER': 'SYSTIMER', 'APB_SARADC': 'ADC1',
                 'SYSTEM': 'SYSTEM', 'INTMTX': 'INTMTX'}

#: Table 5.12-1 p.174: the pads whose drive codes 1 and 2 are swapped ("GPIO2, GPIO3, GPIO4, GPIO5, GPIO18, GPIO19"; Register 5.21's own text prints GPIO18 twice
#: and omits GPIO4 - the table is taken)
STRONG = (2, 3, 4, 5, 18, 19)
_DRV = {True: {'0': '~5 mA', '1': '~20 mA', '2': '~10 mA', '3': '~40 mA'}, False: {'0': '~5 mA', '1': '~10 mA', '2': '~20 mA', '3': '~40 mA'}}
#: Table 5.12-1 p.174, per pad: (DRV after reset, the Reset code) ; legend p.175
IOMUX_RESET = {0: (2, '0'), 1: (2, '0'), 2: (2, '1'), 3: (2, '1'), 4: (2, '1'), 5: (2, '1'), 6: (2, '1*'), 7: (2, '1'), 8: (2, '1'), 9: (2, '3'), 10: (2, '1'),
               11: (2, '0'), 12: (2, '3'), 13: (2, '3'), 14: (2, '3'), 15: (2, '3'), 16: (2, '3'), 17: (2, '3'), 18: (3, '0'), 19: (3, '0*'), 20: (2, '3'), 21: (2, '4')}
#: the Reset code -> (IE, WPU, WPD, OE) after reset, legend p.175 ('1*': MTCK's pull-up depends on eFuse EFUSE_DIS_PAD_JTAG; '0*': GPIO19's USB pull-up is 1 by default)
RESET_CODE = {'0': (0, 0, 0, 0), '1': (1, 0, 0, 0), '2': (1, 0, 1, 0), '3': (1, 1, 0, 0), '4': (0, 1, 0, 1), '0*': (0, 0, 0, 0), '1*': (1, 0, 0, 0)}
RESET_NOTE = {'1*': 'MTCK: with eFuse EFUSE_DIS_PAD_JTAG = 1 the pin floats after reset (IE = 1); with 0 it is pulled up (IE = 1, WPU = 1) - Table 5.12-1 legend p.175',
              '0*': 'GPIO19: IE = 0, WPU = 0, but its USB pull-up value is 1 by default, so the pull-up resistor IS enabled (USB_SERIAL_JTAG_DP_PULLUP) - legend p.175'}

#: Table 6.1-1 Reset Sources p.193 (RTC_CNTL_RESET_CAUSE_PROCPU's codes)
RESET_CAUSES = {'0x01': 'Chip reset (power-on or brown-out)', '0x0F': 'Brown-out system reset', '0x10': 'RWDT system reset', '0x12': 'Super Watchdog reset',
                '0x13': 'CLK GLITCH reset', '0x03': 'Software system reset (RTC_CNTL_SW_SYS_RST)', '0x05': 'Deep-sleep reset', '0x07': 'MWDT0 core reset',
                '0x08': 'MWDT1 core reset', '0x09': 'RWDT core reset', '0x14': 'eFuse reset (eFuse CRC error)', '0x15': 'USB (UART) reset - a command to the USB-Serial-JTAG serial interface',
                '0x16': 'USB (JTAG) reset', '0x17': 'Power glitch reset', '0x0B': 'MWDT0 CPU reset', '0x0C': 'Software CPU reset (RTC_CNTL_SW_PROCPU_RST)',
                '0x0D': 'RWDT CPU reset', '0x11': 'MWDT1 CPU reset'}

#: the TRM access code -> Polari's access word (board.custom.register_access); the code itself rides on every field
ACCESS = {'R/W': 'rw', 'R/W/SS': 'rw', 'R/W/SC': 'rw', 'RO': 'r', 'R/SS/WTC': 'r', 'R/WTC/SS': 'r', 'WT': 'w-strobe', 'WO': 'w-strobe', 'WT-set': 'w1-set', 'WT-clear': 'w1-clear', 'RO-fifo': 'fifo'}


def _f(register, field, hi, lo, code, reset, description, values, where, pin='', signal='', notes='', acts_on=''):
    trm = code.split('-')[0]
    return {'register': register, 'field': field, 'bit_hi': hi, 'bit_lo': lo, 'width': hi - lo + 1, 'access': ACCESS[code], 'reset_value': str(reset),
            'description': description, 'values': values, 'page_table': where, 'affects_pin': pin, 'affects_signal': signal,
            'part': _PART,
            'trm_access': trm,   # hal-3a: the TRM's own code, verbatim - hal-3b's access table maps from THIS, never from the lossy `access` word
            'acts_on': acts_on,  # hal-3b: the register a set / clear alias acts on (the TRM's own words name it: board_acts_on_selftest)
            'notes': ('TRM access %s' % trm) + ('; ' + notes if notes else '')}


REGISTERS = []   # (name, block, offset, title, where, reset, undetermined, part)
FIELDS = []
_PART = 'drawing'   # rm-2b's drawing set; hal-3a's rows (the HAL families' registers) are part 'hal-3a'


def _reg(name, block, offset, title, where, reset, undetermined=''):
    REGISTERS.append({'register': name, 'block': block, 'offset': offset, 'title': title, 'where': where, 'reset': reset, 'undetermined': undetermined, 'part': _PART})


def _per_pad(register, prefix, code, where, words, values, reset='0', notes='', acts_on=''):
    for n in PADS:
        FIELDS.append(_f(register, '%s%d' % (prefix, n), n, n, code, reset, words % n, values, where, pin='GPIO%d' % n, notes=notes, acts_on=acts_on))


_INVALID = 'bits 22-25 are invalid (the TRM: "bit22 ~ bit25 are invalid")'

# ---- pins: output, output enable, input (Register 5.2-5.9)
_reg('GPIO_OUT_REG', 'GPIO', 0x0004, 'GPIO0 ~ 21 output register', 'Register 5.2, p.179', '0x0000000', _INVALID)
_per_pad('GPIO_OUT_REG', 'OUT_DATA_ORIG_', 'R/W/SS', 'Register 5.2 GPIO_OUT_REG, p.179', 'GPIO%d output value in simple GPIO output mode',
         {'0': 'drive low', '1': 'drive high (when its output is enabled and FUNCn_OUT_SEL = 128)'}, notes='one bit of GPIO_OUT_DATA_ORIG')
_reg('GPIO_OUT_W1TS_REG', 'GPIO', 0x0008, 'GPIO0 ~ 21 output set register', 'Register 5.3, p.180', '0x0000000', _INVALID)
_per_pad('GPIO_OUT_W1TS_REG', 'OUT_W1TS_', 'WT-set', 'Register 5.3 GPIO_OUT_W1TS_REG, p.180', 'set GPIO%d\'s bit of GPIO_OUT_REG',
         {'1': 'the corresponding bit in GPIO_OUT_REG is set to 1 ("Recommended operation: use this register to set GPIO_OUT_REG")'}, acts_on='GPIO_OUT_REG')
_reg('GPIO_OUT_W1TC_REG', 'GPIO', 0x000C, 'GPIO0 ~ 21 output clear register', 'Register 5.4, p.180', '0x0000000', _INVALID)
_per_pad('GPIO_OUT_W1TC_REG', 'OUT_W1TC_', 'WT-clear', 'Register 5.4 GPIO_OUT_W1TC_REG, p.180', 'clear GPIO%d\'s bit of GPIO_OUT_REG',
         {'1': 'the corresponding bit in GPIO_OUT_REG is cleared'}, acts_on='GPIO_OUT_REG')
_reg('GPIO_ENABLE_REG', 'GPIO', 0x0020, 'GPIO output enable register', 'Register 5.5, p.180', '0x0000000', _INVALID)
_per_pad('GPIO_ENABLE_REG', 'ENABLE_DATA_', 'R/W/SS', 'Register 5.5 GPIO_ENABLE_REG, p.180', 'GPIO%d output enable', {'0': 'output disabled', '1': 'output enabled'},
         notes='one bit of GPIO_ENABLE_DATA; used when FUNCn_OEN_SEL forces the enable from here (Register 5.17)')
_reg('GPIO_ENABLE_W1TS_REG', 'GPIO', 0x0024, 'GPIO output enable set register', 'Register 5.6, p.181', '0x0000000', _INVALID)
_per_pad('GPIO_ENABLE_W1TS_REG', 'ENABLE_W1TS_', 'WT-set', 'Register 5.6 GPIO_ENABLE_W1TS_REG, p.181', 'set GPIO%d\'s bit of GPIO_ENABLE_REG',
         {'1': 'the corresponding bit in GPIO_ENABLE_REG is set to 1'}, acts_on='GPIO_ENABLE_REG')
_reg('GPIO_ENABLE_W1TC_REG', 'GPIO', 0x0028, 'GPIO output enable clear register', 'Register 5.7, p.181', '0x0000000', _INVALID)
_per_pad('GPIO_ENABLE_W1TC_REG', 'ENABLE_W1TC_', 'WT-clear', 'Register 5.7 GPIO_ENABLE_W1TC_REG, p.181', 'clear GPIO%d\'s bit of GPIO_ENABLE_REG',
         {'1': 'the corresponding bit in GPIO_ENABLE_REG is cleared'}, acts_on='GPIO_ENABLE_REG')
_reg('GPIO_IN_REG', 'GPIO', 0x003C, 'GPIO0 ~ 21 input register', 'Register 5.9, p.182', '0x0000000', _INVALID)
_per_pad('GPIO_IN_REG', 'IN_DATA_NEXT_', 'RO', 'Register 5.9 GPIO_IN_REG, p.182', 'GPIO%d input value', {'0': 'low level', '1': 'high level'}, notes='one bit of GPIO_IN_DATA_NEXT')

# ---- pins: interrupt (Register 5.10 / 5.12 / 5.14)
_reg('GPIO_STATUS_REG', 'GPIO', 0x0044, 'GPIO0 ~ 21 interrupt status register', 'Register 5.10, p.182', '0x0000000', _INVALID)
_per_pad('GPIO_STATUS_REG', 'STATUS_INTERRUPT_', 'R/W/SS', 'Register 5.10 GPIO_STATUS_REG, p.182', 'GPIO%d interrupt status',
         {'1': 'an interrupt is pending on this pad (hardware sets it; clear it through GPIO_STATUS_W1TC_REG)'}, notes='one bit of GPIO_STATUS_INTERRUPT')
_reg('GPIO_STATUS_W1TC_REG', 'GPIO', 0x004C, 'GPIO0 ~ 21 interrupt status clear register', 'Register 5.12, p.183', '0x0000000', _INVALID)
_per_pad('GPIO_STATUS_W1TC_REG', 'STATUS_W1TC_', 'WT-clear', 'Register 5.12 GPIO_STATUS_W1TC_REG, p.183', 'clear GPIO%d\'s interrupt status',
         {'1': 'the corresponding bit in GPIO_STATUS_INTERRUPT is cleared ("Recommended operation: use this register to clear GPIO_STATUS_INTERRUPT")'}, acts_on='GPIO_STATUS_REG')
_INT_TYPE = {'0': 'GPIO interrupt disabled', '1': 'rising edge trigger', '2': 'falling edge trigger', '3': 'any edge trigger', '4': 'low level trigger', '5': 'high level trigger'}
_SYNC = {'0': 'no synchronization', '1': 'synchronized on falling edge', '2': 'synchronized on rising edge', '3': 'synchronized on rising edge'}
for n in PADS:
    reg, w, pin, sig = 'GPIO_PIN%d_REG' % n, 'Register 5.14 GPIO_PINn_REG (n: 0-21), p.184', 'GPIO%d' % n, 'GPIO%d_INT' % n
    _reg(reg, 'GPIO', 0x0074 + 4 * n, 'GPIO pin %d configuration register' % n, 'Register 5.14, p.184', '0x00000000')
    FIELDS.extend([
        _f(reg, 'INT_ENA', 17, 13, 'R/W', 0, 'Interrupt enable bits', {'bit13': 'CPU interrupt enabled', 'bit14': 'CPU non-maskable interrupt enabled'}, w, pin, sig),
        _f(reg, 'CONFIG', 12, 11, 'R/W', 0, 'reserved', {'any': 'reserved (the TRM: "reserved")'}, w),
        _f(reg, 'WAKEUP_ENABLE', 10, 10, 'R/W', 0, 'GPIO wake-up enable bit', {'1': 'wakes the CPU from Light-sleep only'}, w, pin),
        _f(reg, 'INT_TYPE', 9, 7, 'R/W', 0, 'Interrupt type selection', _INT_TYPE, w, pin, sig),
        _f(reg, 'SYNC1_BYPASS', 4, 3, 'R/W', 0, 'first-stage synchronization of the input on the APB clock', _SYNC, w),
        _f(reg, 'PAD_DRIVER', 2, 2, 'R/W', 0, 'pin drive selection', {'0': 'normal output', '1': 'open drain output'}, w, pin),
        _f(reg, 'SYNC2_BYPASS', 1, 0, 'R/W', 0, 'second-stage synchronization of the input on the APB clock', _SYNC, w)])

# ---- pads: the IO MUX (Register 5.21) - per pad resets (Table 5.12-1 p.174, legend p.175)
for n in PADS:
    reg, w, pin = 'IO_MUX_GPIO%d_REG' % n, 'Register 5.21 IO_MUX_GPIOn_REG (n: 0-21), pp.187-188', 'GPIO%d' % n
    drv, code = IOMUX_RESET[n]
    ie, wpu, wpd, oe = RESET_CODE[code]
    reset_note = 'Table 5.12-1 p.174: DRV %d, Reset code %s (legend p.175)%s' % (drv, code, ('; ' + RESET_NOTE[code]) if code in RESET_NOTE else '')
    _reg(reg, 'IO_MUX', 0x0004 + 4 * n, 'IO MUX configuration of GPIO%d' % n, 'Register 5.21, pp.187-188; reset per pad Table 5.12-1 p.174',
         'per pad: %s; after reset the pad is %s' % (reset_note, ', '.join(w for w, on in (('input enabled', ie), ('pulled up', wpu), ('pulled down', wpd), ('output enabled', oe)) if on)
                                                     or 'input disabled, no pull'))
    dtab = dict(_DRV[n in STRONG])
    dnote = 'the drive codes of %s (Table 5.12-1 p.174 drive list%s)' % ('GPIO2/3/4/5/18/19' if n in STRONG else 'the other GPIOs', '; Register 5.21 prints GPIO18 twice and omits GPIO4' if n == 4 else '')
    FIELDS.extend([
        _f(reg, 'FILTER_EN', 15, 15, 'R/W', 0, 'Enable filter for pin input signals', {'0': 'filter disabled', '1': 'filter enabled'}, w, pin),
        _f(reg, 'MCU_SEL', 14, 12, 'R/W', '0x0', 'Select IO MUX function for this signal', {'0': 'Function 0', '1': 'Function 1', 'more': 'etc. (the functions of this pad: Table 5.12-1 p.174)'}, w, pin),
        _f(reg, 'FUN_DRV', 11, 10, 'R/W', drv, 'Select the drive strength of the pin', dtab, w, pin, notes=dnote),
        _f(reg, 'FUN_IE', 9, 9, 'R/W', ie, 'Input enable of the pin', {'0': 'input disabled', '1': 'input enabled'}, w, pin, notes=reset_note),
        _f(reg, 'FUN_WPU', 8, 8, 'R/W', wpu, 'Pull-up enable of the pin', {'0': 'internal pull-up disabled', '1': 'internal pull-up enabled'}, w, pin, notes=reset_note),
        _f(reg, 'FUN_WPD', 7, 7, 'R/W', wpd, 'Pull-down enable of the pin', {'0': 'internal pull-down disabled', '1': 'internal pull-down enabled'}, w, pin, notes=reset_note),
        _f(reg, 'MCU_DRV', 6, 5, 'R/W', 0, 'drive strength of the pin during sleep mode', dtab, w, pin, notes=dnote),
        _f(reg, 'MCU_IE', 4, 4, 'R/W', 0, 'Input enable of the pin during sleep mode', {'0': 'input disabled', '1': 'input enabled'}, w, pin),
        _f(reg, 'MCU_WPU', 3, 3, 'R/W', 0, 'Pull-up enable of the pin during sleep mode', {'0': 'internal pull-up disabled', '1': 'internal pull-up enabled'}, w, pin),
        _f(reg, 'MCU_WPD', 2, 2, 'R/W', 0, 'Pull-down enable of the pin in sleep mode', {'0': 'internal pull-down disabled', '1': 'internal pull-down enabled'}, w, pin),
        _f(reg, 'SLP_SEL', 1, 1, 'R/W', 0, 'Sleep mode selection of this pin', {'1': 'put the pin in sleep mode'}, w, pin),
        _f(reg, 'MCU_OE', 0, 0, 'R/W', 0, 'Output enable of the pin in sleep mode', {'0': 'output disabled', '1': 'output enabled'}, w, pin,
           notes='sleep mode only; the pad\'s run-mode output after reset is the Reset code\'s OE (on the register note), not this bit')])

# ---- the GPIO matrix (Register 5.16 / 5.17)
for n in PADS:
    reg, w, pin = 'GPIO_FUNC%d_OUT_SEL_CFG_REG' % n, 'Register 5.17 GPIO_FUNCn_OUT_SEL_CFG_REG (n: 0-21), pp.185-186', 'GPIO%d' % n
    _reg(reg, 'GPIO', 0x0554 + 4 * n, 'GPIO matrix output selection for GPIO%d' % n, 'Register 5.17, pp.185-186', '0x00000080')
    FIELDS.extend([
        _f(reg, 'OEN_INV_SEL', 10, 10, 'R/W', 0, 'invert the output enable signal', {'0': 'do not invert', '1': 'invert'}, w, pin),
        _f(reg, 'OEN_SEL', 9, 9, 'R/W', 0, 'output enable source', {'0': 'the output enable signal from the peripheral', '1': 'forced from bit n of GPIO_ENABLE_REG'}, w, pin),
        _f(reg, 'OUT_INV_SEL', 8, 8, 'R/W', 0, 'invert the output value', {'0': 'do not invert', '1': 'invert'}, w, pin),
        _f(reg, 'OUT_SEL', 7, 0, 'R/W', '0x80', 'Selection control for GPIO output n',
           {'0..127': 'peripheral output signal Y (Table 5.11-1) drives GPIO output n', '128': 'bit n of GPIO_OUT_REG and GPIO_ENABLE_REG are the output value and output enable'},
           w, pin, notes='U0TXD_out is signal 6 (Table 5.11-1 p.169)')])
_reg('GPIO_FUNC6_IN_SEL_CFG_REG', 'GPIO', 0x0154 + 4 * 6, 'GPIO matrix input selection for peripheral input signal 6 = U0RXD_in (Table 5.11-1 p.169)',
     'Register 5.16, p.185', '0x00000000', 'only signal 6 (U0RXD_in, the drawing\'s UART RX) is ingested of the 128 input selection registers')
FIELDS.extend([
    _f('GPIO_FUNC6_IN_SEL_CFG_REG', 'SIG_IN_SEL', 6, 6, 'R/W', 0, 'Bypass GPIO matrix', {'0': 'connect directly to the peripheral configured in IO MUX', '1': 'route via the GPIO matrix'},
       'Register 5.16 GPIO_FUNCn_IN_SEL_CFG_REG, p.185', signal='U0RXD_in'),
    _f('GPIO_FUNC6_IN_SEL_CFG_REG', 'IN_INV_SEL', 5, 5, 'R/W', 0, 'Invert the input value', {'0': 'invert disabled', '1': 'invert enabled'}, 'Register 5.16 GPIO_FUNCn_IN_SEL_CFG_REG, p.185'),
    _f('GPIO_FUNC6_IN_SEL_CFG_REG', 'IN_SEL', 4, 0, 'R/W', '0x0', 'which pad drives peripheral input signal 6 (U0RXD_in)',
       {'0..21': 'that GPIO pad', '0x1e': 'a constantly high input', '0x1f': 'a constantly low input'}, 'Register 5.16 GPIO_FUNCn_IN_SEL_CFG_REG, p.185', signal='U0RXD_in',
       notes='the reset value is printed 0x0 in the register diagram')])

# ---- reset / boot
_reg('GPIO_STRAP_REG', 'GPIO', 0x0038, 'GPIO strapping values', 'Register 5.8, pp.181-182', '0x0000 (latched at reset)')
for bit, g in ((0, 2), (2, 8), (3, 9)):
    FIELDS.append(_f('GPIO_STRAP_REG', 'STRAPPING_GPIO%d' % g, bit, bit, 'RO', 0, 'GPIO%d strapping value (bit %d of GPIO_STRAPPING)' % (g, bit),
                     {'0': 'the pad was low when the chip came out of reset', '1': 'the pad was high'}, 'Register 5.8 GPIO_STRAP_REG, pp.181-182', pin='GPIO%d' % g,
                     notes='the boot mode is read from these (Table 7.2-1 Boot Mode Control)'))
_reg('RTC_CNTL_RESET_STATE_REG', 'RTC_CNTL', 0x0038, 'the CPU reset state', 'Register 9.12, p.239', '0x00003000 (STAT_VECTOR_SEL_PROCPU and bit 12 printed 1)')
_RW = 'Register 9.12 RTC_CNTL_RESET_STATE_REG, p.239'
FIELDS.extend([
    _f('RTC_CNTL_RESET_STATE_REG', 'DRESET_MASK_PROCPU', 25, 25, 'R/W', 0, 'Set this bit to bypass D-reset (the TRM: "bybass")', {'1': 'bypass D-reset'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'JTAG_RESET_FLAG_CLR_PROCPU', 22, 22, 'WO', 0, 'the JTAG reset flag clear (the TRM prints "Sets the JTAG reset flag")', {'1': 'clear the JTAG reset flag'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'JTAG_RESET_FLAG_PROCPU', 20, 20, 'RO', 0, 'Indicates the JTAG reset flag', {'1': 'the last reset came over JTAG'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'OCD_HALT_ON_RESET_PROCPU', 19, 19, 'R/W', 0, 'send the CPU into halt state upon CPU reset', {'1': 'halt on reset'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'ALL_RESET_FLAG_CLR_PROCPU', 16, 16, 'WO', 0, 'Clears the CPU reset flag', {'1': 'clear the CPU reset flag'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'ALL_RESET_FLAG_PROCPU', 14, 14, 'RO', 0, 'Indicates the CPU reset flag', {'1': 'a CPU reset happened'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'STAT_VECTOR_SEL_PROCPU', 13, 13, 'R/W', 1, 'Selects the CPU static vector', {'any': 'the CPU static vector selection (meaning per value not printed)'}, _RW),
    _f('RTC_CNTL_RESET_STATE_REG', 'RESET_CAUSE_PROCPU', 5, 0, 'RO', 0, 'Stores the CPU reset cause', RESET_CAUSES, _RW + '; codes Table 6.1-1 Reset Sources p.193')])

# ---- interrupts to the CPU (Register 8.7 / 8.11 share the field described on p.214)
for name, off, src, what in (('INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG', 0x0040, 16, 'GPIO_PROCPU_INTR (the GPIO interrupt)'),
                             ('INTERRUPT_CORE0_UART_INTR_MAP_REG', 0x0054, 21, 'UART_INTR (UART0)')):
    _reg(name, 'INTMTX', off, 'interrupt matrix: map source %d, %s' % (src, what), 'Register %s; source Table 8.3-1 p.204' % ('8.7, p.213' if src == 16 else '8.11'), '0x00000000')
    FIELDS.append(_f(name, 'MAP', 4, 0, 'R/W', 0, 'Map the interrupt source (SOURCE_X) into one CPU interrupt', {'any': 'the CPU interrupt this source is mapped to (a 5-bit field)'},
                     'the INTERRUPT_CORE0_SOURCE_X_MAP field, p.214; Table 8.3-1 p.204 (source %d)' % src))

# ---- timestampHW: the system timer (Register 10.1 / 10.2 / 10.5 / 10.6)
_reg('SYSTIMER_CONF_REG', 'SYSTIMER', 0x0000, 'system timer configuration register', 'Register 10.1, pp.277-278', '0x46000000')
_SC = 'Register 10.1 SYSTIMER_CONF_REG, pp.277-278'
for name, bit, reset, words in (('CLK_EN', 31, 0, 'Register clock gating (1: always enabled for read/write; 0: only when a register is accessed)'),
                                ('TIMER_UNIT0_WORK_EN', 30, 1, 'UNIT0 work enable bit'), ('TIMER_UNIT1_WORK_EN', 29, 0, 'UNIT1 work enable bit'),
                                ('TIMER_UNIT0_CORE0_STALL_EN', 28, 0, 'UNIT0 is stalled when CPU stalled'), ('TIMER_UNIT1_CORE0_STALL_EN', 26, 1, 'UNIT1 is stalled when CPU stalled'),
                                ('TARGET0_WORK_EN', 24, 0, 'COMP0 work enable bit'), ('TARGET1_WORK_EN', 23, 0, 'COMP1 work enable bit'), ('TARGET2_WORK_EN', 22, 0, 'COMP2 work enable bit')):
    FIELDS.append(_f('SYSTIMER_CONF_REG', name, bit, bit, 'R/W', reset, words, {'0': 'off', '1': 'on'}, _SC,
                     notes='reset read from the printed reset row (0 1 0 0 0 1 1 0 ... for bits 31..24)'))
_reg('SYSTIMER_UNIT0_OP_REG', 'SYSTIMER', 0x0004, 'system timer UNIT0 operation', 'Register 10.2, p.278', '0x00000000')
FIELDS.extend([
    _f('SYSTIMER_UNIT0_OP_REG', 'TIMER_UNIT0_UPDATE', 30, 30, 'WT', 0, 'Update timer UNIT0: latch the count into VALUE_HI / VALUE_LO', {'1': 'latch now'}, 'Register 10.2 SYSTIMER_UNIT0_OP_REG, p.278'),
    _f('SYSTIMER_UNIT0_OP_REG', 'TIMER_UNIT0_VALUE_VALID', 29, 29, 'R/SS/WTC', 0, 'Timer value is synchronized and valid', {'1': 'VALUE_HI / VALUE_LO hold a valid count'},
       'Register 10.2 SYSTIMER_UNIT0_OP_REG, p.278', notes='WTC: cleared by hardware when TIMER_UNIT0_UPDATE is written 1 (legend p.893)')])
_reg('SYSTIMER_UNIT0_VALUE_HI_REG', 'SYSTIMER', 0x0040, 'system timer UNIT0 value, high', 'Register 10.5, p.279', '0x00000')
FIELDS.append(_f('SYSTIMER_UNIT0_VALUE_HI_REG', 'TIMER_UNIT0_VALUE_HI', 19, 0, 'RO', 0, 'UNIT0 read value, high 20 bits', {'any': 'the latched count, bits 51..32'}, 'Register 10.5, p.279'))
_reg('SYSTIMER_UNIT0_VALUE_LO_REG', 'SYSTIMER', 0x0044, 'system timer UNIT0 value, low', 'Register 10.6, p.279', '0x00000000')
FIELDS.append(_f('SYSTIMER_UNIT0_VALUE_LO_REG', 'TIMER_UNIT0_VALUE_LO', 31, 0, 'RO', 0, 'UNIT0 read value, low 32 bits', {'any': 'the latched count, bits 31..0'}, 'Register 10.6, p.279'))

# ---- clocks + resets (Register 16.3 / 16.5; Table 16.3-2 p.430: "it is mandatory to enable the clock for the given peripheral and release the peripheral from reset")
_NOT_ALL = 'only the UART0 / UART_MEM / TIMERGROUP / SYSTIMER bits the drawing needs are ingested; the other enables are documented in the TRM, not ingested'
_reg('SYSTEM_PERIP_CLK_EN0_REG', 'SYSTEM', 0x0010, 'peripheral clock enable register 0', 'Register 16.3, p.435', '0xF9C1E06F', _NOT_ALL)
_reg('SYSTEM_PERIP_RST_EN0_REG', 'SYSTEM', 0x0018, 'peripheral reset register 0', 'Register 16.5, pp.437-438', '0x00000000', _NOT_ALL)
for bit, what, rst_name in ((29, 'SYSTIMER', 'SYSTIMER'), (24, 'UART_MEM', 'UART_MEM'), (13, 'TIMERGROUP', 'TIMERGROUP'), (2, 'UART', 'UART')):
    who = 'UART0' if what == 'UART' else what
    FIELDS.append(_f('SYSTEM_PERIP_CLK_EN0_REG', '%s_CLK_EN' % what, bit, bit, 'R/W', 1, 'Set this bit to enable %s clock' % who, {'0': 'clock gated', '1': 'clock enabled'},
                     'Register 16.3 SYSTEM_PERIP_CLK_EN0_REG, p.435; Table 16.3-2 p.430', notes='reset 1 from the printed reset row (bit %d)' % bit))
    FIELDS.append(_f('SYSTEM_PERIP_RST_EN0_REG', '%s_RST' % rst_name, bit, bit, 'R/W', 0, 'Set this bit to reset %s' % who, {'0': 'released', '1': 'held in reset'},
                     'Register 16.5 SYSTEM_PERIP_RST_EN0_REG, pp.437-438; Table 16.3-2 p.430'))

# ---- UART0 (Chapter 26 registers at UART0's base)
_NOT_ALL_U = 'only the frame format, FIFO, line and clock fields the drawing needs are ingested; the rest is documented in the TRM, not ingested'
_reg('UART0_FIFO_REG', 'UART0', 0x0000, 'UART_FIFO_REG of UART Controller 0: FIFO data', 'Register 26.1, p.571', '0x00000000')
FIELDS.append(_f('UART0_FIFO_REG', 'RXFIFO_RD_BYTE', 7, 0, 'RO-fifo', 0, 'UARTn accesses FIFO via this field',
                 {'read': 'the next byte of the RX FIFO ("Reading UART_RXFIFO_RD_BYTE retrieves the data from the RX FIFO")',
                  'write': 'the byte is pushed into the TX FIFO ("Writing to UART_RXFIFO_RD_BYTE stores the data into the TX FIFO")'},
                 'Register 26.1 UART_FIFO_REG, p.571; §26.4.2 UART RAM, pp.552-553',
                 notes='every read moves the RX FIFO (the FIFO is the data path, §26.4); hal-3a: BY ACTION - §26.4.2: "As UART_RXFIFO_RD_BYTE is a read-only '
                       'register field, the hardware does not actually perform a write operation on UART_RXFIFO_RD_BYTE; instead, upon detecting a write request '
                       'to this field\'s address, it passes the corresponding write data to the TX FIFO via a separate bypass." Never read-modify-written'))
_reg('UART0_CLKDIV_REG', 'UART0', 0x0014, 'UART_CLKDIV_REG of UART Controller 0: the baud divisor', 'Register 26.7, p.579', '0x000002B6')
FIELDS.extend([
    _f('UART0_CLKDIV_REG', 'CLKDIV_FRAG', 23, 20, 'R/W', 0, 'The fractional part of the frequency divisor', {'any': 'fractional divisor'}, 'Register 26.7 UART_CLKDIV_REG, p.579'),
    _f('UART0_CLKDIV_REG', 'CLKDIV', 11, 0, 'R/W', '0x2b6', 'The integral part of the frequency divisor', {'any': 'integral divisor'}, 'Register 26.7 UART_CLKDIV_REG, p.579')])
_reg('UART0_CONF0_REG', 'UART0', 0x0020, 'UART_CONF0_REG of UART Controller 0: frame format and control', 'Register 26.9, pp.580-581', '0x1000001C', _NOT_ALL_U)
_C0 = 'Register 26.9 UART_CONF0_REG, pp.580-581'
_FRAME = '; the TRM gives the range ("5 ~ 8 bit", stop bits "1, 1.5, or 2", even or odd parity, §26.4.3) but not the code of each value'
FIELDS.extend([
    _f('UART0_CONF0_REG', 'MEM_CLK_EN', 28, 28, 'R/W', 1, 'The signal to enable UART RAM clock gating', {'1': 'enabled'}, _C0),
    _f('UART0_CONF0_REG', 'ERR_WR_MASK', 26, 26, 'R/W', 0, 'store wrong data or not', {'0': 'the receiver stores the data even if it is wrong', '1': 'stops storing data into FIFO when data is wrong'}, _C0),
    _f('UART0_CONF0_REG', 'CLK_EN', 25, 25, 'R/W', 0, 'register clock', {'0': 'clock only when the application writes registers', '1': 'force clock on for register'}, _C0),
    _f('UART0_CONF0_REG', 'TXD_INV', 22, 22, 'R/W', 0, 'invert the level value of UART TXD', {'1': 'invert'}, _C0, signal='U0TXD_out'),
    _f('UART0_CONF0_REG', 'RXD_INV', 19, 19, 'R/W', 0, 'invert the level value of UART RXD', {'1': 'invert'}, _C0, signal='U0RXD_in'),
    _f('UART0_CONF0_REG', 'TXFIFO_RST', 18, 18, 'R/W', 0, 'reset the UART TX FIFO', {'1': 'reset'}, _C0),
    _f('UART0_CONF0_REG', 'RXFIFO_RST', 17, 17, 'R/W', 0, 'reset the UART RX FIFO', {'1': 'reset'}, _C0),
    _f('UART0_CONF0_REG', 'LOOPBACK', 14, 14, 'R/W', 0, 'UART loopback test mode', {'1': 'enabled'}, _C0),
    _f('UART0_CONF0_REG', 'STOP_BIT_NUM', 5, 4, 'R/W', 1, 'the length of stop bit', {'any': '1, 1.5 or 2 stop bits (§26.4.3)'}, _C0, notes='reset 1 per the printed reset row' + _FRAME),
    _f('UART0_CONF0_REG', 'BIT_NUM', 3, 2, 'R/W', 3, 'the length of data', {'any': '5 ~ 8 data bits (§26.4.3)'}, _C0, notes='reset 3 per the printed reset row' + _FRAME),
    _f('UART0_CONF0_REG', 'PARITY_EN', 1, 1, 'R/W', 0, 'enable UART parity check', {'0': 'no parity bit', '1': 'a parity bit after the data bits'}, _C0),
    _f('UART0_CONF0_REG', 'PARITY', 0, 0, 'R/W', 0, 'the parity check mode', {'any': 'even or odd parity (§26.4.3)'}, _C0, notes=_FRAME[2:])])
_reg('UART0_CONF1_REG', 'UART0', 0x0024, 'UART_CONF1_REG of UART Controller 0: FIFO thresholds', 'Register 26.10, pp.581-582', '0x0000C060', _NOT_ALL_U)
FIELDS.extend([
    _f('UART0_CONF1_REG', 'TXFIFO_EMPTY_THRHD', 17, 9, 'R/W', '0x60', 'UART_TXFIFO_EMPTY_INT when the TX FIFO holds fewer bytes than this', {'any': 'byte count'}, 'Register 26.10 UART_CONF1_REG, pp.581-582'),
    _f('UART0_CONF1_REG', 'RXFIFO_FULL_THRHD', 8, 0, 'R/W', '0x60', 'UART_RXFIFO_FULL_INT when the receiver holds more bytes than this', {'any': 'byte count'}, 'Register 26.10 UART_CONF1_REG, pp.581-582')])
_reg('UART0_STATUS_REG', 'UART0', 0x001C, 'UART_STATUS_REG of UART Controller 0', 'Register 26.19, pp.585-586', '0xE000C000', _NOT_ALL_U)
FIELDS.extend([
    _f('UART0_STATUS_REG', 'TXD', 31, 31, 'RO', 1, 'the level of the internal UART TXD signal', {'0': 'low', '1': 'high'}, 'Register 26.19 UART_STATUS_REG, pp.585-586'),
    _f('UART0_STATUS_REG', 'TXFIFO_CNT', 25, 16, 'RO', 0, 'the number of data bytes in TX FIFO', {'any': 'byte count'}, 'Register 26.19 UART_STATUS_REG, pp.585-586'),
    _f('UART0_STATUS_REG', 'RXD', 15, 15, 'RO', 1, 'the level of the internal UART RXD signal', {'0': 'low', '1': 'high'}, 'Register 26.19 UART_STATUS_REG, pp.585-586'),
    _f('UART0_STATUS_REG', 'RXFIFO_CNT', 9, 0, 'RO', 0, 'the number of valid data bytes in RX FIFO', {'any': 'byte count'}, 'Register 26.19 UART_STATUS_REG, pp.585-586')])


# ---- LEDC: the LED PWM controller (Chapter 32; hal-3a for the pwm family). Base Table 3.3-3 p.98 (0x6001_9000).
# Codes and sentences: TRM v1.4 Registers 32.1-32.8, pp.836-839, accepted only where the field name AND the register header agree (econ's TRM/SVD
# overlay; two-register pages print out of order in pdftotext). Bit positions + register offsets: Espressif's SVD (espressif/svd be20aa12
# esp32c3.svd v18), each checked against ESP-IDF v5.5.5 soc/ledc_reg.h (sha256 10983be1...) - 120 / 120 field instances agree. Resets: the SVD's
# register resetValue (the TRM prints each reset row as a bit diagram pdftotext cannot read), cross-checked against the TRM where the TRM's
# words state it (DUTY_INC "1: Increase" with reset 1; RST "the counter will show 0 after reset" with reset 1 = held).
_PART = 'hal-3a'
_LEDC_SVD = 'Espressif SVD esp32c3.svd v18 (espressif/svd be20aa12) resetValue; bits checked against ESP-IDF v5.5.5 soc/ledc_reg.h'
_LEDC_UPDATE = ('takes effect only after LEDC_PARA_UP_CHn is set (Register 32.1 p.836 lists HPOINT, DUTY_START, SIG_OUT_EN, TIMER_SEL, DUTY_NUM, '
                'DUTY_CYCLE, DUTY_SCALE, DUTY_INC, OVF_CNT_EN)')
_LEDC_CH = 6
_LEDC_TIMERS = 4
for n in range(_LEDC_CH):
    base, sig = 0x14 * n, 'ledc_ls_sig_out%d' % n
    w0, w1, wh, wd, wr = ('Register 32.%d LEDC_CHn_%s_REG (n: 0-5), p.%d' % (t, nm, pg)
                          for t, nm, pg in ((1, 'CONF0', 836), (2, 'CONF1', 837), (4, 'HPOINT', 838), (5, 'DUTY', 838), (6, 'DUTY_R', 838)))
    _reg('LEDC_CH%d_CONF0_REG' % n, 'LEDC', base + 0x00, 'LEDC channel %d configuration 0' % n, 'Register 32.1, p.836', '0x00000000')
    FIELDS.extend([
        _f('LEDC_CH%d_CONF0_REG' % n, 'TIMER_SEL', 1, 0, 'R/W', 0, 'This field is used to select one of the timers for channel n.',
           {'0': 'select Timer0', '1': 'select Timer1', '2': 'select Timer2', '3': 'select Timer3'}, w0, signal=sig, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF0_REG' % n, 'SIG_OUT_EN', 2, 2, 'R/W', 0, 'Set this bit to enable signal output on channel n.',
           {'0': 'output off (the line holds LEDC_IDLE_LV_CHn)', '1': 'signal output enabled'}, w0, signal=sig, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF0_REG' % n, 'IDLE_LV', 3, 3, 'R/W', 0, 'This bit is used to control the output value when channel n is inactive (when LEDC_SIG_OUT_EN_CHn is 0).',
           {'0': 'low while inactive', '1': 'high while inactive'}, w0, signal=sig),
        _f('LEDC_CH%d_CONF0_REG' % n, 'PARA_UP', 4, 4, 'WT', 0, 'This bit is used to update the listed fields below for channel n, and will be automatically cleared by hardware.',
           {'1': 'latch the listed channel fields (HPOINT, DUTY_START, SIG_OUT_EN, TIMER_SEL, DUTY_NUM, DUTY_CYCLE, DUTY_SCALE, DUTY_INC, OVF_CNT_EN)'}, w0),
        _f('LEDC_CH%d_CONF0_REG' % n, 'OVF_NUM', 14, 5, 'R/W', 0, 'This field is used to configure the maximum times of overflow minus 1. The LEDC_OVF_CNT_CHn_INT '
           'interrupt will be triggered when channel n overflows for (LEDC_OVF_NUM_CHn + 1) times.', {'any': 'overflow count minus 1'}, w0),
        _f('LEDC_CH%d_CONF0_REG' % n, 'OVF_CNT_EN', 15, 15, 'R/W', 0, 'This bit is used to count the number of times when the timer selected by channel n overflows.',
           {'0': 'not counted', '1': 'counted'}, w0, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF0_REG' % n, 'OVF_CNT_RESET', 16, 16, 'WT', 0, 'Set this bit to reset the timer-overflow counter of channel n.', {'1': 'reset the counter'}, w0)])
    _reg('LEDC_CH%d_HPOINT_REG' % n, 'LEDC', base + 0x04, 'LEDC channel %d high point' % n, 'Register 32.4, p.838', '0x00000000')
    FIELDS.append(_f('LEDC_CH%d_HPOINT_REG' % n, 'HPOINT', 13, 0, 'R/W', 0, 'The output value changes to high when the selected timer for this channel has reached the value '
                     'specified by this field.', {'any': 'the timer count at which the output goes high'}, wh, signal=sig, notes=_LEDC_UPDATE))
    _reg('LEDC_CH%d_DUTY_REG' % n, 'LEDC', base + 0x08, 'LEDC channel %d initial duty' % n, 'Register 32.5, p.838', '0x00000000')
    FIELDS.append(_f('LEDC_CH%d_DUTY_REG' % n, 'DUTY', 18, 0, 'R/W', 0, 'This field is used to change the output duty by controlling the Lpoint. The output value turns to '
                     'low when the selected timer for this channel has reached the Lpoint.', {'any': 'the Lpoint (the TRM gives no fixed-point split of these 19 bits here)'},
                     wd, signal=sig, notes='applied with DUTY_START (Register 32.2)'))
    _reg('LEDC_CH%d_CONF1_REG' % n, 'LEDC', base + 0x0C, 'LEDC channel %d configuration 1 (fading)' % n, 'Register 32.2, p.837', '0x40000000')
    FIELDS.extend([
        _f('LEDC_CH%d_CONF1_REG' % n, 'DUTY_START', 31, 31, 'R/W/SC', 0, 'If this bit is set to 1, other configured fields in LEDC_CHn_CONF1_REG will take effect upon the next '
           'timer overflow.', {'1': 'apply the CONF1 fields at the next overflow (cleared by hardware: SC)'}, w1, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF1_REG' % n, 'DUTY_INC', 30, 30, 'R/W', 1, 'This bit determines whether the duty cycle of the output signal on channel n increases or decreases.',
           {'0': 'Decrease', '1': 'Increase'}, w1, notes=_LEDC_UPDATE + '; reset 1 (SVD resetValue 0x40000000)'),
        _f('LEDC_CH%d_CONF1_REG' % n, 'DUTY_NUM', 29, 20, 'R/W', 0, 'This field controls the number of times the duty cycle will be changed.', {'any': 'number of fade steps'},
           w1, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF1_REG' % n, 'DUTY_CYCLE', 19, 10, 'R/W', 0, 'The duty will change every LEDC_DUTY_CYCLE_CHn cycle on channel n.', {'any': 'cycles per fade step'},
           w1, notes=_LEDC_UPDATE),
        _f('LEDC_CH%d_CONF1_REG' % n, 'DUTY_SCALE', 9, 0, 'R/W', 0, 'This field configures the step size of the duty cycle change during fading.', {'any': 'fade step size'},
           w1, notes=_LEDC_UPDATE)])
    _reg('LEDC_CH%d_DUTY_R_REG' % n, 'LEDC', base + 0x10, 'LEDC channel %d current duty' % n, 'Register 32.6, p.838', '0x00000000')
    FIELDS.append(_f('LEDC_CH%d_DUTY_R_REG' % n, 'DUTY_R', 18, 0, 'RO', 0, 'This field stores the current duty cycle of the output signal on channel n.',
                     {'read': 'the duty now in effect'}, wr, notes='ESP-IDF names this field LEDC_DUTY_LSCHn, the same macro as DUTY\'s (shift 0, mask 0x7FFFF)'))
_LEDC_TICK = ('bit 24 TICK_SEL: in Espressif\'s SVD and ESP-IDF v5.5.5 (LEDC_TICK_SEL_LSTIMERn, shift 24) but not in TRM v1.4 - its row carries no TRM code '
              '(trm_access empty), so hal-3b treats it as missing and fails closed')
for x in range(_LEDC_TIMERS):
    wt, wv = 'Register 32.7 LEDC_TIMERx_CONF_REG (x: 0-3), p.839', 'Register 32.8 LEDC_TIMERx_VALUE_REG (x: 0-3), p.839'
    _reg('LEDC_TIMER%d_CONF_REG' % x, 'LEDC', 0xA0 + 8 * x, 'LEDC timer %d configuration' % x, 'Register 32.7, p.839', '0x00800000', _LEDC_TICK)
    FIELDS.extend([
        _f('LEDC_TIMER%d_CONF_REG' % x, 'PARA_UP', 25, 25, 'WT', 0, 'Set this bit to update LEDC_CLK_DIV_TIMERx and LEDC_TIMERx_DUTY_RES.', {'1': 'latch CLK_DIV and DUTY_RES'}, wt),
        _f('LEDC_TIMER%d_CONF_REG' % x, 'RST', 23, 23, 'R/W', 1, 'This bit is used to reset timer x. The counter will show 0 after reset.',
           {'0': 'timer runs', '1': 'timer held in reset (counter 0)'}, wt, notes='reset 1 (SVD resetValue 0x00800000): every timer starts held in reset'),
        _f('LEDC_TIMER%d_CONF_REG' % x, 'PAUSE', 22, 22, 'R/W', 0, 'This bit is used to suspend the counter in timer x.', {'0': 'counting', '1': 'suspended'}, wt),
        _f('LEDC_TIMER%d_CONF_REG' % x, 'CLK_DIV', 21, 4, 'R/W', 0, 'This field is used to configure the divisor for the divider in timer x. The least significant eight bits '
           'represent the fractional part.', {'any': 'divisor: bits 21..12 integer, bits 11..4 fraction (the TRM\'s "least significant eight bits")'}, wt,
           notes='applied with PARA_UP'),
        _f('LEDC_TIMER%d_CONF_REG' % x, 'DUTY_RES', 3, 0, 'R/W', 0, 'This field is used to control the range of the counter in timer x.',
           {'any': 'the counter range (the TRM states no bit-count formula in this register\'s words)'}, wt, notes='applied with PARA_UP')])
    # no TRM code exists for this bit: the row is built by hand so nothing in it claims one ('access' is the SVD's read-write, marked as such)
    FIELDS.append({'register': 'LEDC_TIMER%d_CONF_REG' % x, 'field': 'TICK_SEL', 'bit_hi': 24, 'bit_lo': 24, 'width': 1, 'access': 'rw', 'reset_value': '0',
                   'description': 'not described in TRM v1.4',
                   'values': {'any': 'no meaning given: the TRM does not describe this bit; the SVD and ESP-IDF only name it TICK_SEL'}, 'page_table': 'not in TRM v1.4; ' + _LEDC_SVD, 'affects_pin': '', 'affects_signal': '',
                   'part': _PART, 'trm_access': '', 'notes': 'NO TRM access code; access rw = the SVD\'s read-write, not the TRM\'s; ' + _LEDC_TICK})
    _reg('LEDC_TIMER%d_VALUE_REG' % x, 'LEDC', 0xA4 + 8 * x, 'LEDC timer %d current count' % x, 'Register 32.8, p.839', '0x00000000')
    FIELDS.append(_f('LEDC_TIMER%d_VALUE_REG' % x, 'CNT', 13, 0, 'RO', 0, 'This field stores the current counter value of timer x.', {'read': 'the counter now'}, wv))
_reg('LEDC_CONF_REG', 'LEDC', 0xD0, 'LEDC global configuration', 'Register 32.3, p.837', '0x00000000')
FIELDS.extend([
    _f('LEDC_CONF_REG', 'CLK_EN', 31, 31, 'R/W', 0, 'This bit is used to control the clock.',
       {'0': 'Support clock only when application writes registers', '1': 'Force clock on for register'}, 'Register 32.3 LEDC_CONF_REG, p.837'),
    _f('LEDC_CONF_REG', 'APB_CLK_SEL', 1, 0, 'R/W', 0, 'This field is used to select the common clock source for all the 4 timers.',
       {'1': 'APB_CLK', '2': 'RC_FAST_CLK', '3': 'XTAL_CLK'}, 'Register 32.3 LEDC_CONF_REG, p.837',
       notes='0 (the reset value) is given no meaning by the TRM: no clock selected until software writes 1-3')])


# ---- hal-3a, LEDC's interrupt bits (Registers 32.9-32.12, pp.840-841). pdftotext prints these two-register pages out of order, so the overlay could
# not accept them: each code and sentence below was READ FROM THE RENDERED PAGE (2026-11-13, econ), and the bit layout from its bit diagram - bits 0-3
# TIMERx_OVF, 4-9 DUTY_CHNG_END_CHn, 10-15 OVF_CNT_CHn, 16-31 reserved, every reset 0 - agrees with the SVD and ESP-IDF v5.5.5 (they call them LSTIMERx /
# LSCHn). The TRM's own names are kept.
_LEDC_INT = (('LEDC_INT_RAW_REG', 0x00C0, '32.9', 840, 'RAW', 'R/WTC/SS',
              ('Triggered when the timer%d has reached its maximum counter value.', 'Interrupt raw bit for channel %d. Triggered when the gradual change of duty has finished.',
               'Interrupt raw bit for channel %d. Triggered when the ovf_cnt has reached the value specified by LEDC_OVF_NUM_CH%d.'),
              {'1': 'the event occurred (set by hardware; cleared through LEDC_INT_CLR_REG)'}),
             ('LEDC_INT_ST_REG', 0x00C4, '32.10', 840, 'ST', 'RO',
              ('This is the masked interrupt status bit for the LEDC_TIMER%d_OVF_INT interrupt when LEDC_TIMER%d_OVF_INT_ENA is set to 1.',
               'This is the masked interrupt status bit for the LEDC_DUTY_CHNG_END_CH%d_INT interrupt when LEDC_DUTY_CHNG_END_CH%d_INT_ENA is set to 1.',
               'This is the masked interrupt status bit for the LEDC_OVF_CNT_CH%d_INT interrupt when LEDC_OVF_CNT_CH%d_INT_ENA is set to 1.'),
              {'1': 'raw and enabled'}),
             ('LEDC_INT_ENA_REG', 0x00C8, '32.11', 841, 'ENA', 'R/W',
              ('The interrupt enable bit for the LEDC_TIMER%d_OVF_INT interrupt.', 'The interrupt enable bit for the LEDC_DUTY_CHNG_END_CH%d_INT interrupt.',
               'The interrupt enable bit for the LEDC_OVF_CNT_CH%d_INT interrupt.'), {'0': 'disabled', '1': 'enabled'}),
             ('LEDC_INT_CLR_REG', 0x00CC, '32.12', 841, 'CLR', 'WT',
              ('Set this bit to clear the LEDC_TIMER%d_OVF_INT interrupt.', 'Set this bit to clear the LEDC_DUTY_CHNG_END_CH%d_INT interrupt.',
               'Set this bit to clear the LEDC_OVF_CNT_CH%d_INT interrupt.'), {'1': 'clear'}))
for name, off, t, pg, kind, code, (w_tim, w_end, w_ovf), vals in _LEDC_INT:
    where = 'Register %s %s, p.%d (read from the rendered page)' % (t, name, pg)
    _reg(name, 'LEDC', off, 'LEDC interrupt %s' % kind.lower(), 'Register %s, p.%d' % (t, pg), '0x00000000', 'bits 16-31 reserved')
    for x in range(_LEDC_TIMERS):
        FIELDS.append(_f(name, 'TIMER%d_OVF_INT_%s' % (x, kind), x, x, code, 0, w_tim.replace('%d', str(x)), vals, where))
    for n in range(_LEDC_CH):
        FIELDS.append(_f(name, 'DUTY_CHNG_END_CH%d_INT_%s' % (n, kind), 4 + n, 4 + n, code, 0, w_end.replace('%d', str(n)), vals, where))
    for n in range(_LEDC_CH):
        FIELDS.append(_f(name, 'OVF_CNT_CH%d_INT_%s' % (n, kind), 10 + n, 10 + n, code, 0, w_ovf.replace('%d', str(n)), vals, where))

# ---- hal-3a, the uart family: UART0's interrupt registers (Registers 26.3-26.6, pp.572-579), all 20 events each. Codes + sentences name-and-header accepted
# (RAW R/WTC/SS, ST RO, ENA R/W, CLR WT); bits / offsets / resets from the SVD, checked against ESP-IDF v5.5.5 soc/uart_reg.h. Line-break hyphens of the
# pdftotext text are rejoined ("com- pletes"); the TRM's own slips are kept verbatim and flagged [sic] in notes.
_UART_INT_EVENTS = (   # (bit, event, ((code, page, the TRM sentence) for RAW, ST, ENA, CLR)) - Registers 26.3-26.6, pp.572-579
    (0, 'RXFIFO_FULL', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver receives more data than what UART_RXFIFO_FULL_THRHD specifies.'),
        ('RO', 574, 'This is the status bit for UART_RXFIFO_FULL_INT when UART_RXFIFO_FULL_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_RXFIFO_FULL_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_THE RXFIFO_FULL_INT interrupt.'),
    )),
    (1, 'TXFIFO_EMPTY', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the amount of data in TX FIFO is less than what UART_TXFIFO_EMPTY_THRHD specifies.'),
        ('RO', 574, 'This is the status bit for UART_TXFIFO_EMPTY_INT when UART_TXFIFO_EMPTY_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_TXFIFO_EMPTY_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_TXFIFO_EMPTY_INT interrupt.'),
    )),
    (2, 'PARITY_ERR', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects a parity error in the data.'),
        ('RO', 574, 'This is the status bit for UART_PARITY_ERR_INT when UART_PARITY_ERR_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_PARITY_ERR_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_PARITY_ERR_INT interrupt.'),
    )),
    (3, 'FRM_ERR', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects a data frame error.'),
        ('RO', 574, 'This is the status bit for UART_FRM_ERR_INT when UART_FRM_ERR_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_FRM_ERR_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_FRM_ERR_INT interrupt.'),
    )),
    (4, 'RXFIFO_OVF', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver receives more data than the capacity of RX FIFO.'),
        ('RO', 574, 'This is the status bit for UART_RXFIFO_OVF_INT when UART_RXFIFO_OVF_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_RXFIFO_OVF_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_UART_RXFIFO_OVF_INT interrupt.'),
    )),
    (5, 'DSR_CHG', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects the edge change of DSRn signal.'),
        ('RO', 574, 'This is the status bit for UART_DSR_CHG_INT when UART_DSR_CHG_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_DSR_CHG_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_DSR_CHG_INT interrupt.'),
    )),
    (6, 'CTS_CHG', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects the edge change of CTSn signal.'),
        ('RO', 574, 'This is the status bit for UART_CTS_CHG_INT when UART_CTS_CHG_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_CTS_CHG_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_CTS_CHG_INT interrupt.'),
    )),
    (7, 'BRK_DET', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects a 0 after the stop bit.'),
        ('RO', 574, 'This is the status bit for UART_BRK_DET_INT when UART_BRK_DET_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_BRK_DET_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_BRK_DET_INT interrupt.'),
    )),
    (8, 'RXFIFO_TOUT', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver takes more time than UART_RX_TOUT_THRHD to receive a byte.'),
        ('RO', 574, 'This is the status bit for UART_RXFIFO_TOUT_INT when UART_RXFIFO_TOUT_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_RXFIFO_TOUT_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_RXFIFO_TOUT_INT interrupt.'),
    )),
    (9, 'SW_XON', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver receives an XON character and UART_SW_FLOW_CON_EN is set to 1.'),
        ('RO', 574, 'This is the status bit for UART_SW_XON_INT when UART_SW_XON_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_SW_XON_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_SW_XON_INT interrupt.'),
    )),
    (10, 'SW_XOFF', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver receives an XOFF character and UART_SW_FLOW_CON_EN is set to 1.'),
        ('RO', 574, 'This is the status bit for UART_SW_XOFF_INT when UART_SW_XOFF_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_SW_XOFF_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_SW_XOFF_INT interrupt.'),
    )),
    (11, 'GLITCH_DET', (
        ('R/WTC/SS', 572, 'This interrupt raw bit turns to high level when the receiver detects a glitch in the middle of a start bit.'),
        ('RO', 574, 'This is the status bit for UART_GLITCH_DET_INT when UART_GLITCH_DET_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_GLITCH_DET_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_GLITCH_DET_INT interrupt.'),
    )),
    (12, 'TX_BRK_DONE', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the transmitter completes sending NULL characters, after all data in TX FIFO are sent.'),
        ('RO', 574, 'This is the status bit for UART_TX_BRK_DONE_INT when UART_TX_BRK_DONE_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_TX_BRK_DONE_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_TX_BRK_DONE_INT interrupt.'),
    )),
    (13, 'TX_BRK_IDLE_DONE', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the transmitter has kept the shortest duration after sending the last data.'),
        ('RO', 575, 'This is the status bit for UART_TX_BRK_IDLE_DONE_INT when UART_TX_BRK_IDLE_DONE_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_TX_BRK_IDLE_DONE_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_TX_BRK_IDLE_DONE_INT interrupt.'),
    )),
    (14, 'TX_DONE', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the transmitter has sent out all data in FIFO.'),
        ('RO', 575, 'This is the status bit for UART_TX_DONE_INT when UART_TX_DONE_INT_ENA is set to 1.'),
        ('R/W', 576, 'This is the enable bit for UART_TX_DONE_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_TX_DONE_INT interrupt.'),
    )),
    (15, 'RS485_PARITY_ERR', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the receiver detects a parity error from the echo of the transmitter in RS485 mode.'),
        ('RO', 575, 'This is the status bit for UART_RS485_PARITY_ERR_INT when UART_RS485_PARITY_INT_ENA is set to 1.'),
        ('R/W', 577, 'This is the enable bit for UART_RS485_PARITY_ERR_INT.'),
        ('WT', 578, 'Set this bit to clear the UART_RS485_PARITY_ERR_INT interrupt.'),
    )),
    (16, 'RS485_FRM_ERR', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the receiver detects a data frame error from the echo of the transmitter in RS485 mode.'),
        ('RO', 575, 'This is the status bit for UART_RS485_FRM_ERR_INT when UART_RS485_FRM_ERR_INT_ENA is set to 1.'),
        ('R/W', 577, 'This is the enable bit for UART_RS485_PARITY_ERR_INT.'),
        ('WT', 579, 'Set this bit to clear the UART_RS485_FRM_ERR_INT interrupt.'),
    )),
    (17, 'RS485_CLASH', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when a collision is detected between the transmitter and the receiver in RS485 mode.'),
        ('RO', 575, 'This is the status bit for UART_RS485_CLASH_INT when UART_RS485_CLASH_INT_ENA is set to 1.'),
        ('R/W', 577, 'This is the enable bit for UART_RS485_CLASH_INT.'),
        ('WT', 579, 'Set this bit to clear the UART_RS485_CLASH_INT interrupt.'),
    )),
    (18, 'AT_CMD_CHAR_DET', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the receiver detects the configured UART_AT_CMD_CHAR.'),
        ('RO', 575, 'This is the status bit for UART_AT_CMD_CHAR_DET_INT when UART_AT_CMD_CHAR_DET_INT_ENA is set to 1.'),
        ('R/W', 577, 'This is the enable bit for UART_AT_CMD_CHAR_DET_INT.'),
        ('WT', 579, 'Set this bit to clear the UART_AT_CMD_CHAR_DET_INT interrupt.'),
    )),
    (19, 'WAKEUP', (
        ('R/WTC/SS', 573, 'This interrupt raw bit turns to high level when the input RXD edge changes more times than what (UART_ACTIVE_THRESHOLD + 3) specifies in Light-sleep mode.'),
        ('RO', 575, 'This is the status bit for UART_WAKEUP_INT when UART_WAKEUP_INT_ENA is set to 1.'),
        ('R/W', 577, 'This is the enable bit for UART_WAKEUP_INT.'),
        ('WT', 579, 'Set this bit to clear the UART_WAKEUP_INT interrupt.'),
    )),
)
_UART_INT_SIC = {(0, 'CLR'): 'the TRM prints "UART_THE RXFIFO_FULL_INT"', (4, 'CLR'): 'the TRM prints "UART_UART_RXFIFO_OVF_INT"',
                 (15, 'ST'): 'the TRM names the enable "UART_RS485_PARITY_INT_ENA"; the field is UART_RS485_PARITY_ERR_INT_ENA',
                 (16, 'ENA'): 'the TRM\'s sentence names UART_RS485_PARITY_ERR_INT; this bit (16) enables UART_RS485_FRM_ERR_INT (its RAW / ST / CLR at bit 16 and the SVD / ESP-IDF agree)'}
_UART_INT_VALUES = {'RAW': {'1': 'the event occurred (set by hardware; write 1 to UART_INT_CLR_REG to clear)'}, 'ST': {'1': 'raw and enabled'},
                    'ENA': {'0': 'disabled', '1': 'enabled'}, 'CLR': {'1': 'clear'}}
for k, (name, off, t, pg, reset) in enumerate((('UART0_INT_RAW_REG', 0x0004, '26.3', '572-573', '0x00000002'), ('UART0_INT_ST_REG', 0x0008, '26.4', '574-575', '0x00000000'),
                                              ('UART0_INT_ENA_REG', 0x000C, '26.5', '576-577', '0x00000000'), ('UART0_INT_CLR_REG', 0x0010, '26.6', '578-579', '0x00000000'))):
    kind = name.split('_INT_')[1][:-4]
    _reg(name, 'UART0', off, 'UART_INT_%s_REG of UART Controller 0' % kind, 'Register %s, pp.%s' % (t, pg), reset, 'bits 20-31 reserved')
    for bit, event, parts in _UART_INT_EVENTS:
        code, page, words = parts[k]
        sic = _UART_INT_SIC.get((bit, kind))
        FIELDS.append(_f(name, '%s_INT_%s' % (event, kind), bit, bit, code, 1 if (kind == 'RAW' and event == 'TXFIFO_EMPTY') else 0, words, _UART_INT_VALUES[kind],
                         'Register %s UART_INT_%s_REG, p.%d' % (t, kind, page), notes=('[sic] ' + sic) if sic else ''))

# ---- hal-3a, the adc family: SAR ADC1 one-time sampling (Chapter 34 Registers 34.1 / 34.6 / 34.9 / 34.14-34.17 / 34.19, pp.879-888; base Table 3.3-3
# cont'd p.99). Same acceptance and checks as LEDC: codes + sentences name-and-header accepted; bits / offsets / resets from the SVD, checked against
# ESP-IDF v5.5.5 soc/apb_saradc_reg.h. The SVD spells three of these bits differently (APB_SARADC1_DONE_INT_*, SARADC1_ONETIME_SAMPLE); the TRM and
# ESP-IDF agree (APB_SARADC_ADC1_DONE_INT_*, APB_SARADC1_ONETIME_SAMPLE), so the TRM's names are kept.
_NOT_ALL_A = 'only the one-time-sampling (ADC1) and clock fields the adc family needs are ingested; the rest is documented in the TRM, not ingested'
_reg('APB_SARADC_CTRL_REG', 'APB_SARADC', 0x0000, 'SAR ADC control register 1', 'Register 34.1, p.879', '0x40038240', _NOT_ALL_A)
_A1 = 'Register 34.1 APB_SARADC_CTRL_REG, p.879'
FIELDS.extend([
    _f('APB_SARADC_CTRL_REG', 'XPD_SAR_FORCE', 28, 27, 'R/W', 0, 'Force select XPD SAR.', {'any': 'the SAR power select (the TRM gives no value codes here)'}, _A1),
    _f('APB_SARADC_CTRL_REG', 'SAR_CLK_DIV', 14, 7, 'R/W', 4, 'SAR ADC clock divider. This value should be no less than 2.', {'any': 'the divider (>= 2)'}, _A1),
    _f('APB_SARADC_CTRL_REG', 'SAR_CLK_GATED', 6, 6, 'R/W', 1, 'SAR ADC clock gate enable bit.', {'0': 'gate off', '1': 'gate enabled'}, _A1),
    _f('APB_SARADC_CTRL_REG', 'START', 1, 1, 'R/W', 0, 'Write 1 here to start the SAR ADC by software. Valid only when APB_SARADC_START_FORCE = 1.',
       {'1': 'start (with START_FORCE = 1)'}, _A1),
    _f('APB_SARADC_CTRL_REG', 'START_FORCE', 0, 0, 'R/W', 0, 'Select who starts the SAR ADC.',
       {'0': 'select FSM to start SAR ADC', '1': 'select software to start SAR ADC'}, _A1)])
_reg('APB_SARADC_ONETIME_SAMPLE_REG', 'APB_SARADC', 0x0020, 'SAR ADC one-time sampling configuration', 'Register 34.6, p.881', '0x1A000000')
_A6 = 'Register 34.6 APB_SARADC_ONETIME_SAMPLE_REG, p.881'
FIELDS.extend([
    _f('APB_SARADC_ONETIME_SAMPLE_REG', 'SARADC1_ONETIME_SAMPLE', 31, 31, 'R/W', 0, 'Enable SAR ADC1 one-time sampling.', {'0': 'off', '1': 'enabled'}, _A6,
       notes='TRM / ESP-IDF name APB_SARADC1_ONETIME_SAMPLE; the SVD calls it SARADC1_ONETIME_SAMPLE'),
    _f('APB_SARADC_ONETIME_SAMPLE_REG', 'SARADC2_ONETIME_SAMPLE', 30, 30, 'R/W', 0, 'Enable SAR ADC2 one-time sampling.', {'0': 'off', '1': 'enabled'}, _A6,
       notes='TRM / ESP-IDF name APB_SARADC2_ONETIME_SAMPLE; ADC2: see the Peripheral row (the TRM notes its DIG controller does not work properly)'),
    _f('APB_SARADC_ONETIME_SAMPLE_REG', 'ONETIME_START', 29, 29, 'R/W', 0, 'Start SAR ADC one-time sampling.', {'1': 'start one sample'}, _A6),
    _f('APB_SARADC_ONETIME_SAMPLE_REG', 'ONETIME_CHANNEL', 28, 25, 'R/W', 13, 'Configure the channel for a one-time sampling.', {'any': 'the channel'}, _A6,
       notes='reset 13 (SVD resetValue 0x1A000000)'),
    _f('APB_SARADC_ONETIME_SAMPLE_REG', 'ONETIME_ATTEN', 24, 23, 'R/W', 0, 'Configure the attenuation for a one-time sampling.',
       {'any': 'the attenuation (the TRM gives no code-to-dB table in this register)'}, _A6)])
_reg('APB_SARADC_1_DATA_STATUS_REG', 'APB_SARADC', 0x002C, 'SAR ADC1 sampling data register', 'Register 34.9, p.883', '0x00000000')
FIELDS.append(_f('APB_SARADC_1_DATA_STATUS_REG', 'ADC1_DATA', 16, 0, 'RO', 0, 'SAR ADC1 conversion data.', {'read': 'the last ADC1 conversion'},
                 'Register 34.9 APB_SARADC_1_DATA_STATUS_REG, p.883', notes='the SVD calls it APB_SARADC1_DATA'))
for name, off, t, pg, code, what, vals in (
        ('APB_SARADC_INT_ENA_REG', 0x0040, '34.14', 885, 'R/W', 'Enable bit of APB_SARADC_ADC1_DONE_INT interrupt.', {'0': 'disabled', '1': 'enabled'}),
        ('APB_SARADC_INT_RAW_REG', 0x0044, '34.15', 886, 'RO', 'Raw bit of APB_SARADC_ADC1_DONE_INT interrupt.', {'1': 'ADC1 completed one conversion'}),
        ('APB_SARADC_INT_ST_REG', 0x0048, '34.16', 886, 'RO', 'Status of APB_SARADC_ADC1_DONE_INT interrupt.', {'1': 'pending and enabled'}),
        ('APB_SARADC_INT_CLR_REG', 0x004C, '34.17', 887, 'WO', 'Clear bit of APB_SARADC_ADC1_DONE_INT interrupt.', {'1': 'clear'})):
    _reg(name, 'APB_SARADC', off, 'SAR ADC interrupt %s' % name.split('_INT_')[1][:-4].lower(), 'Register %s, p.%d' % (t, pg), '0x00000000',
         'only ADC1_DONE (bit 31) is ingested; ADC2_DONE and the threshold bits are documented in the TRM, not ingested')
    FIELDS.append(_f(name, 'ADC1_DONE_INT_' + name.split('_INT_')[1][:-4], 31, 31, code, 0, what, vals, 'Register %s %s, p.%d' % (t, name, pg),
                     notes='APB_SARADC_ADC1_DONE_INT: "Triggered when SAR ADC1 completes one data conversion" (§34.5 p.877); the SVD spells it APB_SARADC1_DONE_INT_*'))
_reg('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'APB_SARADC', 0x0054, 'SAR ADC clock (CLKM) configuration', 'Register 34.19, p.888', '0x00000004')
_A19 = 'Register 34.19 APB_SARADC_APB_ADC_CLKM_CONF_REG, p.888'
FIELDS.extend([
    _f('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'CLK_SEL', 22, 21, 'R/W', 0, 'Select the ADC clock source.',
       {'0': 'Use APB_CLK as clock source', '1': 'use divided-down PLL_240 as clock source'}, _A19, notes='codes 2 and 3 are given no meaning by the TRM'),
    _f('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'CLK_EN', 20, 20, 'R/W', 0, 'Enable the SAR ADC register clock.', {'0': 'off', '1': 'enabled'}, _A19),
    _f('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'CLKM_DIV_A', 19, 14, 'R/W', 0, 'The denominator value of fractional clock divider.', {'any': 'denominator'}, _A19),
    _f('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'CLKM_DIV_B', 13, 8, 'R/W', 0, 'The numerator value of fractional clock divider.', {'any': 'numerator'}, _A19),
    _f('APB_SARADC_APB_ADC_CLKM_CONF_REG', 'CLKM_DIV_NUM', 7, 0, 'R/W', 4, 'The integer part of ADC clock divider. Divider value = APB_SARADC_CLKM_DIV_NUM + '
       'APB_SARADC_CLKM_DIV_B/APB_SARADC_CLKM_DIV_A.', {'any': 'the integer divider'}, _A19)])

# ---- hal-3a, the alarm family: SYSTIMER comparator 0 (Registers 10.14-10.17 / 10.26-10.29, pp.282-287), the same checks against soc/systimer_reg.h
_reg('SYSTIMER_TARGET0_HI_REG', 'SYSTIMER', 0x001C, 'system timer COMP0 alarm value, high', 'Register 10.14, p.282', '0x00000000')
FIELDS.append(_f('SYSTIMER_TARGET0_HI_REG', 'TIMER_TARGET0_HI', 19, 0, 'R/W', 0, 'The alarm value to be loaded to COMP0, high 20 bits.', {'any': 'alarm bits 51..32'},
                 'Register 10.14 SYSTIMER_TARGET0_HI_REG, p.282', notes='loaded into COMP0 by TIMER_COMP0_LOAD'))
_reg('SYSTIMER_TARGET0_LO_REG', 'SYSTIMER', 0x0020, 'system timer COMP0 alarm value, low', 'Register 10.15, p.282', '0x00000000')
FIELDS.append(_f('SYSTIMER_TARGET0_LO_REG', 'TIMER_TARGET0_LO', 31, 0, 'R/W', 0, 'The alarm value to be loaded to COMP0, low 32 bits.', {'any': 'alarm bits 31..0'},
                 'Register 10.15 SYSTIMER_TARGET0_LO_REG, p.282', notes='loaded into COMP0 by TIMER_COMP0_LOAD'))
_reg('SYSTIMER_TARGET0_CONF_REG', 'SYSTIMER', 0x0034, 'system timer COMP0 configuration', 'Register 10.16, p.282', '0x00000000')
_T16 = 'Register 10.16 SYSTIMER_TARGET0_CONF_REG, p.282'
FIELDS.extend([
    _f('SYSTIMER_TARGET0_CONF_REG', 'TARGET0_TIMER_UNIT_SEL', 31, 31, 'R/W', 0, 'Select which unit to compare for COMP0.',
       {'any': 'which unit (UNIT0 / UNIT1) COMP0 compares against - the TRM names no code for each'}, _T16),
    _f('SYSTIMER_TARGET0_CONF_REG', 'TARGET0_PERIOD_MODE', 30, 30, 'R/W', 0, 'Set COMP0 to period mode.', {'0': 'target (one-shot) mode', '1': 'period mode'}, _T16),
    _f('SYSTIMER_TARGET0_CONF_REG', 'TARGET0_PERIOD', 25, 0, 'R/W', 0, 'COMP0 alarm period.', {'any': 'the period in timer ticks (period mode)'}, _T16)])
_reg('SYSTIMER_COMP0_LOAD_REG', 'SYSTIMER', 0x0050, 'system timer COMP0 synchronization', 'Register 10.17, p.283', '0x00000000')
FIELDS.append(_f('SYSTIMER_COMP0_LOAD_REG', 'TIMER_COMP0_LOAD', 0, 0, 'WT', 0, 'COMP0 synchronization enable signal. Set this bit to reload the alarm value/period to COMP0.',
                 {'1': 'reload TARGET0_HI / LO / PERIOD into COMP0'}, 'Register 10.17 SYSTIMER_COMP0_LOAD_REG, p.283'))
for name, off, t, pg, code, what, vals in (
        ('SYSTIMER_INT_ENA_REG', 0x0064, '10.26', 286, 'R/W', 'SYSTIMER_TARGET0_INT enable bit.', {'0': 'disabled', '1': 'enabled'}),
        ('SYSTIMER_INT_RAW_REG', 0x0068, '10.27', 286, 'R/WTC/SS', 'SYSTIMER_TARGET0_INT raw bit.', {'1': 'COMP0 alarm occurred (set by hardware; write 1 to clear)'}),
        ('SYSTIMER_INT_CLR_REG', 0x006C, '10.28', 287, 'WT', 'SYSTIMER_TARGET0_INT clear bit.', {'1': 'clear'}),
        ('SYSTIMER_INT_ST_REG', 0x0070, '10.29', 287, 'RO', 'SYSTIMER_TARGET0_INT status bit.', {'1': 'pending and enabled'})):
    _reg(name, 'SYSTIMER', off, 'system timer interrupt %s' % name.split('_INT_')[1][:-4].lower(), 'Register %s, p.%d' % (t, pg), '0x00000000',
         'only TARGET0 (bit 0) is ingested; TARGET1 / TARGET2 are documented in the TRM, not ingested')
    FIELDS.append(_f(name, 'TARGET0_INT_' + name.split('_INT_')[1][:-4], 0, 0, code, 0, what, vals, 'Register %s %s, p.%d' % (t, name, pg)))

# ---- hal-3a: the clocks + resets of LEDC and the ADC controller, in the drawing set's SYSTEM registers (Register 16.3 p.435 / 16.5 p.437)
for bit, what, reset in ((11, 'LEDC', 0), (28, 'APB_SARADC', 1)):
    FIELDS.append(_f('SYSTEM_PERIP_CLK_EN0_REG', '%s_CLK_EN' % what, bit, bit, 'R/W', reset, 'Set this bit to enable %s clock' % what, {'0': 'clock gated', '1': 'clock enabled'},
                     'Register 16.3 SYSTEM_PERIP_CLK_EN0_REG, p.435; Table 16.3-2 p.430', notes='reset %d (SVD resetValue 0xF9C1E06F, bit %d)' % (reset, bit)))
    FIELDS.append(_f('SYSTEM_PERIP_RST_EN0_REG', '%s_RST' % what, bit, bit, 'R/W', 0, 'Set this bit to reset %s' % what, {'0': 'released', '1': 'held in reset'},
                     'Register 16.5 SYSTEM_PERIP_RST_EN0_REG, p.437; Table 16.3-2 p.430'))

# ---- hal-3a: the three sources the families interrupt through (Registers 8.13 / 8.27 / 8.33; the shared SOURCE_X_MAP field p.214; Table 8.3-1 pp.204-205)
for name, off, src, what, t, tp in (('INTERRUPT_CORE0_LEDC_INT_MAP_REG', 0x005C, 23, 'LEDC_INTR', '8.13', 'p.213', ),
                                    ('INTERRUPT_CORE0_SYSTIMER_TARGET0_INT_MAP_REG', 0x0094, 37, 'SYSTIMER_TARGET0_INTR', '8.27', 'p.213'),
                                    ('INTERRUPT_CORE0_APB_ADC_INT_MAP_REG', 0x00AC, 43, 'APB_ADC_INTR (the TRM prints "vDIGTAL_ADC_INTR")', '8.33', 'p.214')):
    tbl = 'p.204' if src < 37 else 'p.205'
    _reg(name, 'INTMTX', off, 'interrupt matrix: map source %d, %s' % (src, what), 'Register %s, %s; source Table 8.3-1 %s' % (t, tp, tbl), '0x00000000')
    FIELDS.append(_f(name, 'MAP', 4, 0, 'R/W', 0, 'Map the interrupt source (SOURCE_X) into one CPU interrupt', {'any': 'the CPU interrupt this source is mapped to (a 5-bit field)'},
                     'the INTERRUPT_CORE0_SOURCE_X_MAP field, p.214; Table 8.3-1 %s (source %d)' % (tbl, src)))


def part(name):
    """the rows of one part: 'drawing' (rm-2b) or 'hal-3a' -> (registers, fields). A part's fields may sit in the other part's registers
    (hal-3a adds LEDC / APB_SARADC bits to the drawing set's SYSTEM_PERIP_CLK_EN0 / _RST_EN0)."""
    return [r for r in REGISTERS if r['part'] == name], [f for f in FIELDS if f['part'] == name]


def address(r):
    return '0x%08X' % (BASES[r['block']] + r['offset'])
