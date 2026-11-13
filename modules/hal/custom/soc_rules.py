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
        'arch': 'avr', 'title': 'Microchip ATmega328P (Arduino UNO R3)', 'reg_width': 8, 'boards': ('arduino-uno-r3',),
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
              'field_forms': {'fmask': '(uint8_t)0x{m:02X}', 'fval': '(uint8_t)({v}u << {lo})'},
              # rule 6/7 of mechanisms.choose: a window of addresses with single-bit instructions (AVR sbi / cbi below I/O 0x20), as DATA
              'bit_instr_window': {'space': 'io', 'below': 0x20, 'mechanism': 'avr-io-bit', 'byte_mechanism': 'avr-io-byte-rmw'},
              'header_includes': ['<stdint.h>'], 'prelude': [],
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
              'field_forms': {'fmask': '0x{m:X}UL', 'fval': '((uint32_t){v} << {lo})'},
              'header_includes': [],
              'prelude': ['#ifndef POLARI_HAL_ATOMIC', '/* {guard_why} */', '#define POLARI_HAL_ATOMIC(stmt) do {{ stmt }} while (0)', '#endif'],
              'guard': 'POLARI_HAL_ATOMIC(%s);',
              'guard_why': 'POLARI_HAL_ATOMIC defaults to the bare statement (one core, and no ISR of ours writes these registers); a firmware '
                           'whose ISR shares the register defines it as a critical section (FreeRTOS portENTER_CRITICAL / portEXIT_CRITICAL)',
              'init_rule': 'an _INIT form drops the guard: for code that runs before the register is shared with an ISR (pin setup before the handler is attached)',
              'init_cite': 'the caller decides (the context is the isotope\'s: catom.json interface context init)'},
    },
}


# ------------------------------------------------------------------ facts: one PROVIDER per SoC (econ's review 2026-11-13)
# Every fact the generator reads about a chip comes from that chip's provider, and an UNKNOWN soc is refused in words: there is no
# implicit "else" that would hand a third chip (our own RTL, a LiteX SoC) another chip's fields, addresses or pads. A chip
# description (board.custom.chipdesc_provider, econ) registers a provider the same way.

class SocUnknown(KeyError):
    pass


def _m328_register_facts(register):
    snap = R328.load('atmega328p')
    r = snap['registers'].get(register)
    if not r:
        return None
    addr = int(r['addr'], 16)
    data = addr + 0x20 if r['space'] == 'io' else addr
    return {'address': '0x%02X' % data, 'space': r['space'], 'io_addr': addr if r['space'] == 'io' else None,
            'source': 'board.custom.registers_atmega328p.json (avr-libc %s <avr/io.h>, -dM snapshot)' % snap.get('avr_libc', ''),
            'cite': '_SFR_%s8(0x%02X)%s' % ('IO' if r['space'] == 'io' else 'MEM', addr, ' = data address 0x%02X' % data if r['space'] == 'io' else '')}


def _m328_pin_parts(pin):
    if pin not in S328.PINS:
        return None
    return {'port': pin[1], 'bit': int(pin[2:]), 'n': int(pin[2:])}


def _m328_pin_caveat(pin):
    if 'RESET' in list((S328.PINS.get(pin) or ('', []))[1]):
        return ('%s is the RESET pin unless the RSTDISBL fuse is programmed (Table 14-6, p.94): the code is generated, '
                'but it only drives the pin on a chip with that fuse set' % pin)
    return ''


def _c3_register_facts(register):
    reg = next((r for r in RC3.REGISTERS if r['register'] == register), None)
    if reg is None:
        return None
    return {'address': RC3.address(reg), 'space': 'mem', 'io_addr': None, 'source': 'board.custom.registers_esp32c3 (REGISTERS + address())',
            'cite': '%s base 0x%08X (%s) + offset 0x%04X; %s' % (reg['block'], RC3.BASES[reg['block']], RC3.BASE_CITE, reg['offset'], reg['where'])}


def _c3_pin_parts(pin):
    if not pin.startswith('GPIO') or not pin[4:].isdigit() or int(pin[4:]) not in RC3.PADS:
        return None
    return {'port': '', 'bit': int(pin[4:]), 'n': int(pin[4:])}


# hal-3b: THE ACCESS TABLE (plan §4d): a field's cited source code -> the access word choose() reads. The lossy `access` word is read
# only where it is MORE specific than the code can be: a write-1-to-set / -clear alias register (the code says WT for both, the
# register name says which) and the FIFO data register (one RO field, by action). Anything unmapped is `missing` (fail closed).
TRM_ACCESS = {'R/W': 'rw', 'R/W/SS': 'rw', 'R/W/SC': 'rw-sc', 'RO': 'r', 'WO': 'w', 'WT': 'w-strobe',
              'R/SS/WTC': 'r-w1c', 'R/WTC/SS': 'r-w1c'}
_ALIAS_WORDS = ('w1-set', 'w1-clear', 'fifo')


def access_word(field):
    """-> (word, why) for one field row: access_word (own RTL / SVD-as-spec) > trm_access via TRM_ACCESS > the row's own word where it
    carries no source code at all (the 328P hand rows); an EMPTY trm_access (review-queued, or a field the manual never describes) is
    'missing'."""
    if field.get('access_word'):
        return field['access_word'], '%s: %s' % (field.get('access_source', ''), field.get('access_cite', ''))
    if 'trm_access' not in field:
        return field['access'], 'the row\'s own cited access word'
    code = field['trm_access']
    if field.get('access') in _ALIAS_WORDS:
        return field['access'], 'TRM %s, an alias / FIFO register: the row\'s specific word %s' % (code, field['access'])
    if not code:
        return 'missing', 'no cited access code (review queue, or not in the manual): fail closed'
    w = TRM_ACCESS.get(code)
    return (w, 'TRM %s' % code) if w else ('missing', 'TRM code %r is not in the access table: fail closed' % code)


def _c3_fields():
    """the C3 rows with `access` = the access table's word (the lossy word kept as access_lossy, the TRM code as trm_access)"""
    global _C3_CACHE
    if _C3_CACHE is None:
        _C3_CACHE = [dict(f, access=access_word(f)[0], access_lossy=f.get('access', ''), access_why=access_word(f)[1]) for f in RC3.FIELDS]
    return _C3_CACHE


_C3_CACHE = None


PROVIDERS = {
    'atmega328p': {
        'fields': lambda: F328.FIELDS, 'fields_source': 'board.custom.register_fields_atmega328p.FIELDS',
        'register_facts': _m328_register_facts, 'pin_parts': _m328_pin_parts,
        'pin_functions': lambda pin: list((S328.PINS.get(pin) or ('', []))[1]),
        'pin_source': ('board.custom.soc_atmega328p.PINS', '%s %s' % (U.M328_DOC, S328.FIG)),
        'pin_caveat': _m328_pin_caveat,
        'vectors': lambda: dict(R328.load('atmega328p').get('vectors') or {}),
        'vectors_source': 'board.custom.registers_atmega328p.json vectors (avr-libc <avr/io.h> _VECTOR(n))',
        'c_register': lambda register, facts: register,   # avr-libc's own name (its <avr/io.h> defines it)
        'datasheet_address': lambda register: ((F328.REGISTER_CITES.get(register) or ('', '', '', ''))[3:4] or [''])[0] or '',
    },
    'esp32c3': {
        'fields': _c3_fields, 'fields_source': 'board.custom.registers_esp32c3.FIELDS (access via the access table)',
        'register_facts': _c3_register_facts, 'pin_parts': _c3_pin_parts,
        'pin_functions': lambda pin: [],
        'pin_source': ('board.custom.registers_esp32c3.PADS', '%s: GPIO0-21' % E.TRM_DOC),
        'pin_caveat': lambda pin: '',
        'vectors': lambda: {}, 'vectors_source': 'none (ESP32-C3 interrupt matrix not ingested)',
        'c_register': lambda register, facts: '(*(volatile uint32_t *)%su)' % facts['address'],   # a volatile pointer at the address
        'datasheet_address': lambda register: '',
    },
}

#: the RULES[soc]['c'] facts the generator REQUIRES (a missing one is refused, never defaulted to an 8-bit form)
REQUIRED_C = ('ctype', 'mask', 'field_forms')


def provider(soc):
    p = PROVIDERS.get(soc)
    if p is None or soc not in RULES:
        raise SocUnknown('soc %r has no HAL provider (known: %s): register one (rules + provider), never a default' % (soc, ', '.join(sorted(PROVIDERS))))
    missing = [k for k in REQUIRED_C if k not in RULES[soc].get('c', {})] + ([] if 'reg_width' in RULES[soc] else ['reg_width'])
    if missing:
        raise SocUnknown('soc %r rules lack required C facts: %s' % (soc, ', '.join(missing)))
    return p


def chip_facts(soc):
    """hal-3b: the named facts a role's value_expr may use, as C ({f_cpu} -> F_CPU: the build's own -DF_CPU, which the board facts cite
    as 16000000 for the arduino-uno-r3, uno_facts build.f_cpu)."""
    provider(soc)
    return dict(RULES[soc].get('facts') or {})


def pin_parts(soc, pin):
    """-> {port, bit, n} or None. ATmega328P: PB5 -> port B, bit 5 (the pin name IS the port + bit, Figure 1-1); ESP32-C3: GPIO8 -> n 8."""
    return provider(soc)['pin_parts'](pin)


def pin_source(soc):
    return provider(soc)['pin_source']


def fields_source(soc):
    return provider(soc)['fields_source']


def fields(soc):
    return provider(soc)['fields']()


def register_facts(soc, register):
    """-> {address, space, io_addr, source, cite} or None."""
    return provider(soc)['register_facts'](register)


def c_register(soc, register, facts):
    return provider(soc)['c_register'](register, facts)


def c_mask(soc, bit):
    provider(soc)
    return RULES[soc]['c']['mask'].format(bit=bit)


def datasheet_data_address(register, soc='atmega328p'):
    """The data-space address the datasheet prints beside a register, or '' (the cross-check's second source)."""
    return provider(soc)['datasheet_address'](register)


def pin_functions(soc, pin):
    return provider(soc)['pin_functions'](pin)


def pin_caveat(soc, pin):
    return provider(soc)['pin_caveat'](pin)


def vectors(soc):
    return provider(soc)['vectors']()


def vectors_source(soc):
    return provider(soc)['vectors_source']


def c_field(soc, lo, width, value):
    """{fmask, fval} for a field write, in the chip's own C forms (RULES c.field_forms: data, not a width test)."""
    provider(soc)
    forms = RULES[soc]['c']['field_forms']
    fmask = ((1 << width) - 1) << lo
    return {'fmask': forms['fmask'].format(m=fmask), 'fval': forms['fval'].format(v=value, lo=lo)}
