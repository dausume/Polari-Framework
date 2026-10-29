"""
@module board.custom.register_taxonomy

rm-0 (REGISTER_MAPPING_PLAN.md §1, his proposal P§2-P§4; D-rm-1 RULED 2026-10-28: "Rule table per chip that comes from a DataSheet"): every chip register CLASSIFIED
into hardware DOMAINS (a P§4 tree path: mcu-pin/direction, mcu-peripheral/uart, mcu-system/reset ...) and given FUNCTIONAL ROLES control | status | data, the read
roles apart from the write roles (PINx reads status, a write of 1 toggles: control). DERIVED by a rule table per chip - every rule cites the datasheet place it was
read from (the register's own section when board already cites it, else the chapter, said as such: "chapter start per the TOC, register section not re-read").
A register no rule matches is `unclassified`, by name - never guessed.

  classify(soc, register)        -> {domains[], roles{read[], write[]}, rule, cite, verification}
  field_roles(soc, register, f)  -> {read[], write[]} for one RegisterField (its access refines the register's roles)
  tree(soc, registers)           -> the P§4 tree with counts; the categories no register lands in are DEFERRED (count 0, "future scope")
"""
import re

DOMAINS = ('mcu-pin', 'mcu-internal', 'mcu-peripheral', 'mcu-system', 'soc-interconnect', 'soc-processor', 'soc-device', 'platform-virtual')
ROLES = ('control', 'status', 'data')
#: the P§4 tree's sub-categories (a category with no register is shown deferred, never hidden)
TREE = {
    'mcu-pin': ('direction', 'io-data', 'electrical', 'interrupt'),
    'mcu-internal': ('status', 'stack', 'general-purpose'),
    'mcu-peripheral': ('uart', 'timer', 'adc', 'comparator', 'spi', 'twi', 'eeprom'),
    'mcu-system': ('clock', 'power', 'reset', 'watchdog', 'self-programming', 'interrupt-vectors'),
    'soc-interconnect': ('bus', 'dma', 'matrix'),
    'soc-processor': ('cores', 'caches', 'mmu'),
    'soc-device': ('devicetree', 'drivers'),
    'platform-virtual': ('hypervisor', 'emulated'),
}
DS = 'Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B'
_CH = 'chapter start per the TOC (the register section not re-read today)'

C, S, D = 'control', 'status', 'data'


def _r(pattern, domains, read, write, cite, verification='cited'):
    return {'pattern': pattern, 'rx': re.compile('^(%s)$' % pattern), 'domains': domains, 'read': read, 'write': write, 'cite': cite, 'verification': verification}


#: ATmega328P - in the datasheet's order of chapters. `cite` = the register section (cited in board.custom.register_fields_atmega328p) or the chapter.
RULES = {'atmega328p': [
    _r('SREG', ['mcu-internal/status', 'mcu-system/interrupt-vectors'], [S, C], [C], '%s §7.3.1 SREG p.20 (I = global interrupt enable; T H S V N Z C flags) - read rm-2a' % DS),
    _r('SP|SPH|SPL', ['mcu-internal/stack'], [D], [D], '%s, AVR CPU Core - Stack Pointer: %s' % (DS, _CH), 'chapter'),
    _r('GPIOR[0-2]', ['mcu-internal/general-purpose'], [D], [D], '%s, I/O Memory - General Purpose I/O Registers: %s' % (DS, _CH), 'chapter'),
    _r('EEAR|EEARH|EEARL', ['mcu-peripheral/eeprom'], [C], [C], '%s §8 AVR Memories (EEPROM Data Memory): %s' % (DS, _CH), 'chapter'),
    _r('EEDR', ['mcu-peripheral/eeprom'], [D], [D], '%s §8 AVR Memories (EEPROM Data Memory): %s' % (DS, _CH), 'chapter'),
    _r('EECR', ['mcu-peripheral/eeprom'], [C, S], [C], '%s §8 AVR Memories (EEPROM Control Register: EERE/EEPE strobes): %s' % (DS, _CH), 'chapter'),
    _r('CLKPR', ['mcu-system/clock'], [C], [C], '%s §9.12.2 CLKPR p.46, Table 9-17 p.47 (CLKPCE + the CLKPS division factor) - read rm-2a' % DS),
    _r('OSCCAL', ['mcu-system/clock'], [C], [C], '%s §9 System Clock and Clock Options: %s' % (DS, _CH), 'chapter'),
    _r('PRR', ['mcu-system/power'], [C], [C], '%s §10.11.3 PRR pp.54-55 (a one stops the module\'s clock) - read rm-2a' % DS),
    _r('SMCR', ['mcu-system/power'], [C], [C], '%s §10 Power Management and Sleep Modes: %s' % (DS, _CH), 'chapter'),
    _r('MCUSR', ['mcu-system/reset'], [S], [C], '%s §11.9.1 MCUSR p.63 (WDRF / BORF / EXTRF / PORF reset-source flags, written 0 to clear) - read rm-2a' % DS),
    _r('WDTCSR', ['mcu-system/watchdog', 'mcu-system/reset'], [C, S], [C], '%s §11.9.2 WDTCSR pp.63-64, Tables 11-1 / 11-2 (WDIF flag; WDIE / WDE mode; WDCE; WDP prescale) - read rm-2a' % DS),
    _r('EICRA|EIMSK', ['mcu-pin/interrupt'], [C], [C], '%s §13.2 (EICRA §13.2.1 p.80, EIMSK §13.2.2 p.81)' % DS),
    _r('EIFR', ['mcu-pin/interrupt'], [S], [C], '%s §13.2.3 p.81 (flags; a logical one clears)' % DS),
    _r('PCICR|PCMSK[0-2]', ['mcu-pin/interrupt'], [C], [C], '%s §13.2.4 p.82, §13.2.6-13.2.8 p.83' % DS),
    _r('PCIFR', ['mcu-pin/interrupt'], [S], [C], '%s §13.2.5 p.82 (flags; a logical one clears)' % DS),
    _r('MCUCR', ['mcu-pin/electrical', 'mcu-system/interrupt-vectors', 'mcu-system/power'], [C], [C],
       '%s §14.4.1 p.100 (PUD = pull-up disable for every port); IVSEL/IVCE and BODS/BODSE sit in the same register (their chapters not re-read)' % DS),
    _r('DDR[BCD]', ['mcu-pin/direction'], [C], [C], '%s §14.4 Register Description pp.100-101 (DDRB §14.4.3, DDRD §14.4.9)' % DS),
    _r('PORT[BCD]', ['mcu-pin/io-data', 'mcu-pin/electrical'], [D, C], [D, C],
       '%s §14.4 pp.100-101 (PORTB §14.4.2, PORTD §14.4.8): the output level when DDxn = 1, the pull-up when DDxn = 0 (§14.2.1 Configuring the Pin)' % DS),
    _r('PIN[BCD]', ['mcu-pin/io-data'], [S], [C], '%s §14.4 pp.100-101 (PINB §14.4.4, PIND §14.4.10): reads the pin; writing 1 toggles PORTxn (§14.2.2)' % DS),
    _r('TCCR0[AB]|TIMSK0', ['mcu-peripheral/timer'], [C], [C], '%s ch.15 8-bit Timer/Counter0 with PWM, p.102: %s' % (DS, _CH), 'chapter'),
    _r('TIFR0', ['mcu-peripheral/timer'], [S], [C], '%s ch.15 Timer/Counter0, p.102 (flags; a logical one clears): %s' % (DS, _CH), 'chapter'),
    _r('TCNT0|OCR0[AB]', ['mcu-peripheral/timer'], [D], [D, C], '%s ch.15 Timer/Counter0, p.102 (count / compare values): %s' % (DS, _CH), 'chapter'),
    _r('TCCR1[ABC]|TIMSK1', ['mcu-peripheral/timer'], [C], [C], '%s ch.16 16-bit Timer/Counter1 with PWM, p.120: %s' % (DS, _CH), 'chapter'),
    _r('TIFR1', ['mcu-peripheral/timer'], [S], [C], '%s ch.16 Timer/Counter1, p.120 (flags; a logical one clears): %s' % (DS, _CH), 'chapter'),
    _r('TCNT1[HL]?|OCR1[AB][HL]?|ICR1[HL]?', ['mcu-peripheral/timer'], [D], [D, C], '%s ch.16 Timer/Counter1, p.120 (count / compare / capture values): %s' % (DS, _CH), 'chapter'),
    _r('TCCR2[AB]|TIMSK2', ['mcu-peripheral/timer'], [C], [C], '%s ch.18 Timer/Counter2 (TCCR2A §18.11.1 p.162, TCCR2B §18.11.2 p.165, TIMSK2 §18.11.6 p.166)' % DS),
    _r('TIFR2', ['mcu-peripheral/timer'], [S], [C], '%s §18.11.7 p.167 (flags; a logical one clears)' % DS),
    _r('TCNT2|OCR2[AB]', ['mcu-peripheral/timer'], [D], [D, C], '%s ch.18 Timer/Counter2, p.150 (count / compare values): %s' % (DS, _CH), 'chapter'),
    _r('ASSR', ['mcu-peripheral/timer', 'mcu-system/clock'], [C, S], [C], '%s ch.18 Timer/Counter2 - Asynchronous Status Register, p.150: %s' % (DS, _CH), 'chapter'),
    _r('GTCCR', ['mcu-peripheral/timer'], [C], [C], '%s General Timer/Counter Control (prescaler reset): %s' % (DS, _CH), 'chapter'),
    _r('SPCR', ['mcu-peripheral/spi'], [C], [C], '%s ch.19 SPI, p.169: %s' % (DS, _CH), 'chapter'),
    _r('SPSR', ['mcu-peripheral/spi'], [S, C], [C], '%s ch.19 SPI, p.169 (SPIF/WCOL status; SPI2X control): %s' % (DS, _CH), 'chapter'),
    _r('SPDR', ['mcu-peripheral/spi'], [D], [D], '%s ch.19 SPI, p.169: %s' % (DS, _CH), 'chapter'),
    _r('UCSR0A', ['mcu-peripheral/uart'], [S, C], [C], '%s §20.11.2 UCSRnA pp.200-201 (RXC0/TXC0/UDRE0/FE0/DOR0/UPE0 status; U2X0/MPCM0 control) - read rm-2a' % DS),
    _r('UCSR0[BC]|UBRR0[HL]?', ['mcu-peripheral/uart'], [C], [C], '%s §20.11.3 UCSRnB pp.201-202, §20.11.4 UCSRnC pp.202-204, §20.11.5 UBRRnL/H p.204 (enables, frame format, baud) - read rm-2a' % DS),
    _r('UDR0', ['mcu-peripheral/uart'], [D], [D], '%s §20.11.1 UDRn p.200 (TXB on write, RXB on read - a two-level receive FIFO) - read rm-2a' % DS),
    _r('TWBR|TWAR|TWAMR', ['mcu-peripheral/twi'], [C], [C], '%s ch.22 TWI, p.215: %s' % (DS, _CH), 'chapter'),
    _r('TWCR', ['mcu-peripheral/twi'], [C, S], [C], '%s ch.22 TWI, p.215 (TWINT flag + control): %s' % (DS, _CH), 'chapter'),
    _r('TWSR', ['mcu-peripheral/twi'], [S], [C], '%s ch.22 TWI, p.215 (status + prescaler bits): %s' % (DS, _CH), 'chapter'),
    _r('TWDR', ['mcu-peripheral/twi'], [D], [D], '%s ch.22 TWI, p.215: %s' % (DS, _CH), 'chapter'),
    _r('ACSR', ['mcu-peripheral/comparator'], [C, S], [C], '%s the Analog Comparator chapter (between TWI ch.22 p.215 and ADC ch.24 p.246 in the TOC; not read today)' % DS, 'chapter'),
    _r('DIDR1', ['mcu-peripheral/comparator', 'mcu-pin/electrical'], [C], [C], '%s the Analog Comparator chapter - Digital Input Disable (not read today)' % DS, 'chapter'),
    _r('ADMUX|ADCSRB', ['mcu-peripheral/adc'], [C], [C], '%s ch.24 ADC, p.246: %s' % (DS, _CH), 'chapter'),
    _r('ADCSRA', ['mcu-peripheral/adc'], [C, S], [C], '%s ch.24 ADC, p.246 (ADSC/ADIF + enables): %s' % (DS, _CH), 'chapter'),
    _r('ADC|ADCW|ADCL|ADCH', ['mcu-peripheral/adc'], [D], [], '%s ch.24 ADC, p.246 (the conversion result, read-only): %s' % (DS, _CH), 'chapter'),
    _r('DIDR0', ['mcu-peripheral/adc', 'mcu-pin/electrical'], [C], [C], '%s ch.24 ADC, p.246 (digital input disable on the ADC pins): %s' % (DS, _CH), 'chapter'),
    _r('SPMCSR', ['mcu-system/self-programming'], [C, S], [C], '%s the Boot Loader Support (Read-While-Write Self-Programming) chapter - what Optiboot writes flash with (not re-read)' % DS, 'chapter'),
]}

#: field access (board.custom.register_fields_atmega328p) -> roles; 'rw' keeps the register's roles
ACCESS_ROLES = {'rw-toggle': ([S], [C]), 'w1c': ([S], [C]), 'w0c': ([S], [C]), 'w-strobe': ([], [C]), 'r': ([S], [])}   # w0c: rm-2a (MCUSR's reset flags)


def classify(soc, register):
    """The rule a register matches (first in order), or `unclassified` by name."""
    for rule in RULES.get(soc, []):
        if rule['rx'].match(register):
            return {'domains': list(rule['domains']), 'roles': {'read': list(rule['read']), 'write': list(rule['write'])}, 'rule': rule['pattern'],
                    'cite': rule['cite'], 'verification': rule['verification']}
    return {'domains': ['unclassified'], 'roles': {'read': [], 'write': []}, 'rule': '',
            'cite': 'no rule in board.custom.register_taxonomy.RULES[%r] matches %s: unclassified (add a cited rule; never guessed)' % (soc, register),
            'verification': 'none'}


def field_roles(soc, register, field):
    """One RegisterField's roles: its access refines the register's (a flag reads status and is cleared by a write: control)."""
    base = classify(soc, register)['roles']
    hit = ACCESS_ROLES.get((field or {}).get('access', 'rw'))
    if hit is None:
        return {'read': list(base['read']), 'write': list(base['write'])}
    return {'read': list(hit[0]), 'write': list(hit[1])}


def tree(soc, registers):
    """[{domain, category, path, count, registers, state}] - every TREE branch; state supported (registers land) | future scope (none: deferred)."""
    by_path = {}
    for reg in registers:
        for path in classify(soc, reg)['domains']:
            by_path.setdefault(path, []).append(reg)
    out = []
    for dom in DOMAINS:
        for cat in TREE[dom]:
            path = '%s/%s' % (dom, cat)
            regs = sorted(by_path.get(path, []))
            out.append({'domain': dom, 'category': cat, 'path': path, 'count': len(regs), 'registers': ', '.join(regs),
                        'state': 'supported' if regs else 'future scope'})
    if by_path.get('unclassified'):
        out.append({'domain': 'unclassified', 'category': '', 'path': 'unclassified', 'count': len(by_path['unclassified']),
                    'registers': ', '.join(sorted(by_path['unclassified'])), 'state': 'unclassified: no cited rule'})
    return out
