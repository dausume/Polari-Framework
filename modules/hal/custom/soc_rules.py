"""
@module hal.custom.soc_rules

THE PER-SoC PART OF THE HAL, as data (hal-0, HAL_CATOM_CATALOGUE_PLAN.md §4a): for each SoC, which registers play each
HalOperation role, which setup an operation needs first, how a register and a bit are written in C, and the guard an
interruptible read-modify-write gets. Every fact the generator uses is READ from the board module's cited tables, never
copied here:

  atmega328p  fields   board.custom.register_fields_atmega328p.FIELDS   (DS40002061B, each field with its section and page)
              address  board.custom.registers_atmega328p.json           (avr-libc <avr/io.h> -dM snapshot; I/O vs memory space)
              pins     board.custom.soc_atmega328p.PINS                 (Figure 1-1 p.12; port + bit from the pin name)
  esp32c3     fields   board.custom.registers_esp32c3.FIELDS            (TRM v1.4, each field with its register and page)
              address  board.custom.registers_esp32c3.address()        (Table 3.3-3 p.98 base + the register's offset)
              pins     GPIO0-21 (board.custom.registers_esp32c3.PADS)

A role rule is a list of register-name patterns ({port} = the pin's port letter, {n} = its pad number), optionally with the
field name, and the cite of the datasheet place that says the register plays that role. A role a chip lacks is said, with
why, and the operation is unsupported there (never emulated silently).
"""
from board.custom import register_fields_atmega328p as F328
from board.custom import registers as R328
from board.custom import registers_esp32c3 as RC3
from board.custom import soc_atmega328p as S328
from board.custom import uno_facts as U
from board.custom import esp32c3_evidence as E

SOCS = ('atmega328p', 'esp32c3')

DOCS = {
    'atmega328p': '%s; %s' % (U.M328_DOC, U.M328_URL),
    'esp32c3': '%s %s; %s' % (E.TRM_DOC, E.TRM_REV, E.TRM_URL),
}

RULES = {
    'atmega328p': {
        'arch': 'avr', 'title': 'Microchip ATmega328P (Arduino UNO R3)', 'reg_width': 8,
        'roles': {
            'direction': {'registers': ['DDR{port}'], 'cite': 'DS40002061B section 14.2.1 Configuring the Pin, p.85: DDxn selects the direction'},
            'output': {'registers': ['PORT{port}', 'PIN{port}'],
                       'cite': 'section 14.2.1 p.85 (PORTxn drives the output); section 14.2.2 p.85 (writing PINxn toggles PORTxn)'},
            'input': {'registers': ['PIN{port}'], 'cite': 'section 14.2.4 Reading the Pin Value (PINxn); field rows section 14.4.4 p.100'},
            'pull_up': {'registers': ['PORT{port}'],
                        'cite': 'section 14.2.1 p.85: PORTxn written 1 while the pin is an input activates the pull-up (and MCUCR.PUD = 0)',
                        'condition': 'the pin must be an input (gpio.input) and MCUCR.PUD must be 0 (its reset value)'},
            'pull_down': {'registers': [], 'cite': '',
                          'missing': 'no cited ATmega328P register field offers an internal pull-down (the port pins have a pull-up only)'},
            # hal-1 interrupts: the pin-change unit (3 banks of 8) and the two dedicated external interrupts
            'pcint_mask': {'registers': ['PCMSK0', 'PCMSK1', 'PCMSK2'], 'match': 'pin', 'yields': {'bank': (r'^PCMSK(\d)$', 'register')},
                           'cite': 'DS40002061B section 13.2.6-13.2.8 PCMSK2/1/0, p.83: one mask bit per pin; the register number is the bank'},
            'pcint_flag': {'registers': ['PCIFR'], 'match': 'name', 'field': 'PCIF{bank}', 'cite': 'section 13.2.5 PCIFR, p.82 (cleared by writing one)'},
            'pcint_bank': {'registers': ['PCICR'], 'match': 'name', 'field': 'PCIE{bank}', 'cite': 'section 13.2.4 PCICR, p.82 (one enable per bank)'},
            'pcint_vector': {'vector': 'PCINT{bank}_vect', 'cite': 'avr-libc <avr/io.h> vector table (PCINT0_vect .. PCINT2_vect, one per bank)'},
            'edge_sense': {'registers': ['EICRA'], 'match': 'signal', 'signal_re': r'^INT\d$', 'values': {'any_edge': 1, 'falling': 2, 'rising': 3},
                           'yields': {'signum': (r'^INT(\d)$', 'signal')},
                           'cite': 'section 13.2.1 EICRA, Tables 13-1 / 13-2 p.80: ISCn1:0 = 01 any logical change, 10 the falling edge, 11 the rising edge of INTn'},
            'edge_flag': {'registers': ['EIFR'], 'match': 'signal', 'signal_re': r'^INT\d$', 'cite': 'section 13.2.3 EIFR, p.81 (cleared by writing one)'},
            'edge_mask': {'registers': ['EIMSK'], 'match': 'signal', 'signal_re': r'^INT\d$', 'yields': {'signum': (r'^INT(\d)$', 'signal')},
                          'cite': 'section 13.2.2 EIMSK, p.81'},
            'edge_vector': {'vector': 'INT{signum}_vect', 'cite': 'avr-libc <avr/io.h> vector table (INT0_vect, INT1_vect)'},
            # hal-3b, pwm family: the pin's OCnx alternate function names the timer (t) and the channel (ch)
            'pwm_output': {'registers': ['TCCR0A', 'TCCR1A', 'TCCR2A'], 'match': 'signal', 'signal_re': r'^OC\d[AB]$',
                           'yields': {'t': (r'^OC(\d)[AB]$', 'signal'), 'ch': (r'^OC\d([AB])$', 'signal')},
                           'values': {'disconnected': 0, 'non_inverting': 2, 'inverting': 3},
                           'cite': 'DS40002061B section 15.9.1 TCCR0A Tables 15-3/15-4 p.114, section 16.11.1 TCCR1A Tables 16-2/16-3 p.141, '
                                   'section 18.11.1 TCCR2A p.162: COMnx1:0 = 10 clear on match (non-inverting), 11 set on match (inverting), 00 disconnected'},
            'pwm_duty': {'registers': ['OCR{t}{ch}', 'OCR{t}{ch}L'], 'match': 'signal', 'signal_re': r'^OC\d[AB]$', 'wide': 'OCR{t}{ch}',
                         'cite': 'section 15.9.4/15.9.5 OCR0A/B p.117, section 16.11.5/16.11.6 OCR1A/B p.144 (16-bit: the wide symbol), '
                                 'section 18.11.4 OCR2A p.166'},
            'pwm_mode': {'fields': [{'register': 'TCCR{t}A', 'field': 'WGM{t}_10', 'lo': 0},
                                    {'register': 'TCCR{t}B', 'field': ['WGM{t}2', 'WGM{t}_32'], 'lo': 2}],
                         'modes': {'fast_pwm_8bit': [['Fast PWM', 'TOP 0xFF'], ['Fast PWM', '8-bit']],
                                   'phase_correct_8bit': [['PWM, Phase Correct', 'TOP 0xFF'], ['PWM, Phase Correct, 8-bit']],
                                   'ctc_top_ocra': [['CTC', 'TOP OCRA'], ['CTC', 'TOP OCR1A']]},
                         'cite': 'section 15.9.1/15.9.2 Table 15-8 p.115, section 16.11.1/16.11.2 Table 16-4 p.141, section 18.11.1/18.11.2 Table 18-8 p.164: '
                                 'the mode number is split WGMn1:0 in TCCRnA and WGMn2 (WGMn3:2 on Timer1) in TCCRnB'},
            'pwm_clock': {'registers': ['TCCR{t}B'], 'match': 'name', 'field': 'CS{t}',
                          'cite': 'section 15.9.2 Table 15-9 p.117, section 16.11.2 Table 16-5 p.143, section 18.11.2 Table 18-9 p.165: the clock select codes'},
            'pwm_update': {'inherent': {'words': 'the ATmega328P double-buffers OCRnx itself (updated at TOP / BOTTOM by the timer): no update strobe exists',
                                        'cite': 'section 15.9.4 OCR0A p.117; Table 15-8 "Update of OCRx at"'}},
            # routing roles (C3 GPIO matrix / IO MUX): fixed by silicon on the 328P - each pin's functions are hard-wired
            'route_out': {'inherent': {'words': 'no output routing matrix: an alternate function drives its pin directly once enabled',
                                       'cite': 'DS40002061B section 14.3 Alternate Port Functions p.88'}},
            'route_in': {'inherent': {'words': 'no input routing matrix: a peripheral reads its pin directly',
                                      'cite': 'DS40002061B section 14.3 Alternate Port Functions p.88'}},
            'io_mux_func': {'inherent': {'words': 'no pad function select: the enabled peripheral overrides the port function',
                                         'cite': 'DS40002061B section 14.3 Alternate Port Functions p.88'}},
        },
        'peripherals': {},
        'signal_vars': [(r'^OC(\d)([AB])$', {'t': 1, 'ch': 2})],   # a compare output names its timer and channel (OC0A: Timer0, channel A)
        'facts': {'f_cpu': 'F_CPU'},
        'setups': {},
        'c': {'includes': ['<avr/io.h>'], 'mask': '_BV({bit})', 'guard_include': '<util/atomic.h>', 'ctype': 'uint8_t', 'wide_ctype': 'uint16_t',
              'access_style': 'symbol',
              'guard': 'ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { %s }',
              'guard_why': 'avr-libc util/atomic.h: interrupts off for the statement, the previous state restored after',
              'init_rule': 'an _INIT form drops the guard: init code runs before global interrupts are enabled (every UNO app calls sei() after its *_init calls), so nothing can split the write',
              'init_cite': 'DS40002061B SREG.I is 0 after reset (section 7.3.1, not re-read this session); the app order: board/custom/firmware/uno/apps/*.c'},
    },
    'esp32c3': {
        'arch': 'riscv', 'title': 'Espressif ESP32-C3', 'reg_width': 32,
        'roles': {
            'direction': {'registers': ['GPIO_ENABLE_W1TS_REG', 'GPIO_ENABLE_W1TC_REG', 'GPIO_ENABLE_REG'],
                          'cite': 'TRM Register 5.5-5.7 pp.180-181: GPIO_ENABLE_REG and its set / clear aliases'},
            'output': {'registers': ['GPIO_OUT_W1TS_REG', 'GPIO_OUT_W1TC_REG', 'GPIO_OUT_REG'],
                       'cite': 'TRM Register 5.2-5.4 pp.179-180: GPIO_OUT_REG and its set / clear aliases'},
            'input': {'registers': ['GPIO_IN_REG'], 'cite': 'TRM Register 5.9 GPIO_IN_REG p.182'},
            'pull_up': {'registers': ['IO_MUX_GPIO{n}_REG'], 'field': 'FUN_WPU', 'cite': 'TRM Register 5.21 IO_MUX_GPIOn_REG pp.187-188: FUN_WPU'},
            'pull_down': {'registers': ['IO_MUX_GPIO{n}_REG'], 'field': 'FUN_WPD', 'cite': 'TRM Register 5.21 IO_MUX_GPIOn_REG pp.187-188: FUN_WPD'},
            # hal-1 interrupts: every pad has its own edge / level interrupt (no separate pin-change unit): the pin-change and the
            # edge operations land on the same GPIO_PINn_REG fields
            'pcint_mask': {'registers': ['GPIO_PIN{n}_REG'], 'field': 'INT_TYPE', 'values': {'set': 3, 'clear': 0},
                           'cite': 'TRM Register 5.14 GPIO_PINn_REG p.184: INT_TYPE 3 = any edge trigger, 0 = GPIO interrupt disabled'},
            'pcint_flag': {'registers': ['GPIO_STATUS_W1TC_REG'], 'cite': 'TRM Register 5.12 GPIO_STATUS_W1TC_REG p.183'},
            'pcint_bank': {'registers': ['GPIO_PIN{n}_REG'], 'field': 'INT_ENA', 'values': {'set': 1},
                           'cite': 'TRM Register 5.14 GPIO_PINn_REG p.184: INT_ENA bit13 = CPU interrupt enabled (value 1 at the field\'s low bit)'},
            'pcint_vector': {'registers': [], 'cite': 'TRM chapter Interrupt Matrix (INTMTX): not ingested',
                             'missing': 'the ESP32-C3 has no per-pin vector: GPIO interrupts reach a CPU interrupt through the interrupt matrix '
                                        '(INTMTX, not ingested); an isotope attaches its handler through ESP-IDF (gpio_isr_handler_add) instead'},
            'edge_sense': {'registers': ['GPIO_PIN{n}_REG'], 'field': 'INT_TYPE', 'values': {'any_edge': 3, 'rising': 1, 'falling': 2},
                           'cite': 'TRM Register 5.14 GPIO_PINn_REG p.184: INT_TYPE 1 = rising edge, 2 = falling edge, 3 = any edge trigger'},
            'edge_flag': {'registers': ['GPIO_STATUS_W1TC_REG'], 'cite': 'TRM Register 5.12 GPIO_STATUS_W1TC_REG p.183'},
            'edge_mask': {'registers': ['GPIO_PIN{n}_REG'], 'field': 'INT_ENA', 'values': {'set': 1, 'clear': 0, 'lookup': 1},
                          'cite': 'TRM Register 5.14 GPIO_PINn_REG p.184: INT_ENA'},
            'edge_vector': {'registers': [], 'cite': 'TRM chapter Interrupt Matrix (INTMTX): not ingested',
                            'missing': 'the ESP32-C3 has no per-pin vector: GPIO interrupts reach a CPU interrupt through the interrupt matrix '
                                       '(INTMTX, not ingested); an isotope attaches its handler through ESP-IDF (gpio_isr_handler_add) instead'},
        },
        # setup = bindings written BEFORE the operation's own, each a field write (mechanism signal-routing-matrix -> rmw-field)
        'setups': {
            'gpio-out': [
                {'register': 'GPIO_FUNC{n}_OUT_SEL_CFG_REG', 'field': 'OUT_SEL', 'value': 128,
                 'purpose': 'route the pad\'s output to GPIO_OUT / GPIO_ENABLE (signal 128) instead of a peripheral',
                 'cite': 'TRM Register 5.17 GPIO_FUNCn_OUT_SEL_CFG_REG pp.185-186 (OUT_SEL 128)'},
                {'register': 'IO_MUX_GPIO{n}_REG', 'field': 'MCU_SEL', 'value': 1,
                 'purpose': 'select the pad\'s GPIO function (function 1)',
                 'cite': 'TRM Register 5.21 IO_MUX_GPIOn_REG pp.187-188 (MCU_SEL); datasheet Table 2-4: F1 = GPIOn (board.custom.soc_functions)'},
            ],
            'gpio-in': [
                {'register': 'IO_MUX_GPIO{n}_REG', 'field': 'MCU_SEL', 'value': 1, 'purpose': 'select the pad\'s GPIO function (function 1)',
                 'cite': 'TRM Register 5.21 IO_MUX_GPIOn_REG pp.187-188 (MCU_SEL); datasheet Table 2-4: F1 = GPIOn (board.custom.soc_functions)'},
                {'register': 'IO_MUX_GPIO{n}_REG', 'field': 'FUN_IE', 'value': 1, 'purpose': 'enable the pad\'s input buffer',
                 'cite': 'TRM Register 5.21 IO_MUX_GPIOn_REG pp.187-188 (FUN_IE)'},
            ],
        },
        'c': {'includes': ['<stdint.h>'], 'mask': '(1UL << {bit})', 'guard_include': '', 'ctype': 'uint32_t', 'access_style': 'address',
              'guard': 'POLARI_HAL_ATOMIC(%s);',
              'guard_why': 'POLARI_HAL_ATOMIC defaults to the bare statement (one core, and no ISR of ours writes these registers); a firmware '
                           'whose ISR shares the register defines it as a critical section (FreeRTOS portENTER_CRITICAL / portEXIT_CRITICAL)',
              'init_rule': 'an _INIT form drops the guard: for code that runs before the register is shared with an ISR (pin setup before the handler is attached)',
              'init_cite': 'the caller decides (the context is the isotope\'s: catom.json interface context init)'},
    },
}


# ------------------------------------------------------------------ facts (read from board, with where they came from)

def chip_facts(soc):
    """hal-3b: the named facts a role's value_expr may use, as C ({f_cpu} -> F_CPU: the build's own -DF_CPU, which the board facts cite
    as 16000000 for the arduino-uno-r3, uno_facts build.f_cpu)."""
    return dict(RULES[soc].get('facts') or {})


def pin_parts(soc, pin):
    """-> {port, bit, n} or None. ATmega328P: PB5 -> port B, bit 5 (the pin name IS the port + bit, Figure 1-1); ESP32-C3: GPIO8 -> n 8."""
    if soc == 'atmega328p':
        if pin not in S328.PINS:
            return None
        return {'port': pin[1], 'bit': int(pin[2:]), 'n': int(pin[2:])}
    if soc == 'esp32c3':
        if not pin.startswith('GPIO') or not pin[4:].isdigit() or int(pin[4:]) not in RC3.PADS:
            return None
        return {'port': '', 'bit': int(pin[4:]), 'n': int(pin[4:])}
    return None


def pin_source(soc):
    if soc == 'atmega328p':
        return 'board.custom.soc_atmega328p.PINS', '%s %s' % (U.M328_DOC, S328.FIG)
    return 'board.custom.registers_esp32c3.PADS', '%s: GPIO0-21' % E.TRM_DOC


def fields_source(soc):
    return ('board.custom.register_fields_atmega328p.FIELDS' if soc == 'atmega328p' else 'board.custom.registers_esp32c3.FIELDS')


def fields(soc):
    return F328.FIELDS if soc == 'atmega328p' else RC3.FIELDS


def register_facts(soc, register):
    """-> {address, space, io_addr, source, cite} or None."""
    if soc == 'atmega328p':
        snap = R328.load('atmega328p')
        regs = snap['registers']
        r = regs.get(register)
        if not r:
            return None
        addr = int(r['addr'], 16)
        data = addr + 0x20 if r['space'] == 'io' else addr
        libc = snap.get('avr_libc', '')
        return {'address': '0x%02X' % data, 'space': r['space'], 'io_addr': addr if r['space'] == 'io' else None,
                'source': 'board.custom.registers_atmega328p.json (avr-libc %s <avr/io.h>, -dM snapshot)' % libc,
                'cite': '_SFR_%s8(0x%02X)%s' % ('IO' if r['space'] == 'io' else 'MEM', addr,
                                                 ' = data address 0x%02X' % data if r['space'] == 'io' else '')}
    reg = next((r for r in RC3.REGISTERS if r['register'] == register), None)
    if reg is None:
        return None
    return {'address': RC3.address(reg), 'space': 'mem', 'io_addr': None,
            'source': 'board.custom.registers_esp32c3 (REGISTERS + address())',
            'cite': '%s base 0x%08X (%s) + offset 0x%04X; %s' % (reg['block'], RC3.BASES[reg['block']], RC3.BASE_CITE, reg['offset'], reg['where'])}


def c_register(soc, register, facts):
    """The register as C: avr-libc's own name on the AVR (its <avr/io.h> defines it), a volatile pointer at the address on the C3."""
    if soc == 'atmega328p':
        return register
    return '(*(volatile uint32_t *)%su)' % facts['address']


def c_mask(soc, bit):
    return RULES[soc]['c']['mask'].format(bit=bit)


def datasheet_data_address(register):
    """The data-space address the ATmega328P datasheet prints beside a register (REGISTER_CITES), or '' — the cross-check's second source."""
    c = F328.REGISTER_CITES.get(register)
    return (c[3] if c and len(c) > 3 else '') or ''


def pin_functions(soc, pin):
    """The pin's alternate-function names (ATmega328P: Table 14-3/6/9 via soc_atmega328p.PINS; ESP32-C3: none needed by the rules)."""
    if soc == 'atmega328p':
        return list((S328.PINS.get(pin) or ('', []))[1])
    return []


def pin_caveat(soc, pin):
    """A cited fact that makes a pin's GPIO use conditional, or ''. ATmega328P PC6: RESET by default (Table 14-6, p.94)."""
    if soc == 'atmega328p' and 'RESET' in pin_functions(soc, pin):
        return ('%s is the RESET pin unless the RSTDISBL fuse is programmed (Table 14-6, p.94): the code is generated, '
                'but it only drives the pin on a chip with that fuse set' % pin)
    return ''


def vectors(soc):
    """{vector name: number} — avr-libc's own table on the AVR (the -dM snapshot); none modelled on the C3 (interrupt matrix)."""
    if soc == 'atmega328p':
        return dict(R328.load('atmega328p').get('vectors') or {})
    return {}


def vectors_source(soc):
    return 'board.custom.registers_atmega328p.json vectors (avr-libc <avr/io.h> _VECTOR(n))' if soc == 'atmega328p' else 'none (ESP32-C3 interrupt matrix not ingested)'


def c_field(soc, lo, width, value):
    """{fmask, fval} for a field write, in the register's own width (uint8_t on the AVR, uint32_t on the C3)."""
    fmask = ((1 << width) - 1) << lo
    if RULES[soc]['reg_width'] == 8:
        return {'fmask': '(uint8_t)0x%02X' % fmask, 'fval': '(uint8_t)(%du << %d)' % (value, lo)}
    return {'fmask': '0x%XUL' % fmask, 'fval': '((uint32_t)%d << %d)' % (value, lo)}
