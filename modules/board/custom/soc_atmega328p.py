"""
@module board.custom.soc_atmega328p

THE ATmega328P AS A SoC ROW (brd-bo, PCB_FROM_SCRATCH_PLAN §2b SoC layer) — every I/O pin of the 28-SPDIP package the UNO R3
carries, with its alternate functions, and the peripherals / memory / clocks. READ on 2026-10-03 from the datasheet the brd-1
facts already cite (Microchip DS40002061B — the SAME file: re-fetched, sha256 b9b9d83c…9320e matched):

  pins + package pin numbers   Figure 1-1 "Pinout", p.12 (the 28 SPDIP column)
  alternate functions          Table 14-3 p.91 (Port B), Table 14-6 p.94 (Port C), Table 14-9 p.97 (Port D) — datasheet order
  memories                     Table 2-1 p.16 (32 KB flash / 1 KB EEPROM / 2 KB SRAM), Figure 8-3 p.28 (SRAM 0x0100–0x08FF)
  peripherals                  the chapter titles + first pages (TOC): USART0 ch.20 p.179, Timer/Counter0 ch.15 p.102,
                               Timer/Counter1 ch.16 p.120, Timer/Counter2 ch.18 p.150, ADC ch.24 p.246, SPI ch.19 p.169, TWI ch.22 p.215

One DatasheetFact per pin (the pin's package number + its functions, with the figure and table it came from) — the KiCad
view's pin numbers and a future land pattern cite the same rows. The clock is the BOARD's (16 MHz, boards.txt build.f_cpu,
already a cited UNO fact) — the chip alone has no fixed clock, said in clocks_json.
"""
import json

from board.custom.uno_facts import M328_DOC, M328_REV, M328_URL

SOC = 'atmega328p'
FIG = 'Figure 1-1 Pinout (28 SPDIP), p.12'
TABLE = {'B': 'Table 14-3 Port B Pins Alternate Functions, p.91', 'C': 'Table 14-6 Port C Pins Alternate Functions, p.94',
         'D': 'Table 14-9 Port D Pins Alternate Functions, p.97'}

#: pin → (28-SPDIP pin number, alternate functions in the datasheet table's order). 23 I/O pins; the power pins
#: (VCC 7, GND 8/22, AVCC 20, AREF 21) are a package fact, not SocPin rows (no port, no function).
PINS = {
    'PB0': ('14', ['ICP1', 'CLKO', 'PCINT0']), 'PB1': ('15', ['OC1A', 'PCINT1']), 'PB2': ('16', ['SS', 'OC1B', 'PCINT2']),
    'PB3': ('17', ['MOSI', 'OC2A', 'PCINT3']), 'PB4': ('18', ['MISO', 'PCINT4']), 'PB5': ('19', ['SCK', 'PCINT5']),
    'PB6': ('9', ['XTAL1', 'TOSC1', 'PCINT6']), 'PB7': ('10', ['XTAL2', 'TOSC2', 'PCINT7']),
    'PC0': ('23', ['ADC0', 'PCINT8']), 'PC1': ('24', ['ADC1', 'PCINT9']), 'PC2': ('25', ['ADC2', 'PCINT10']),
    'PC3': ('26', ['ADC3', 'PCINT11']), 'PC4': ('27', ['ADC4', 'SDA', 'PCINT12']), 'PC5': ('28', ['ADC5', 'SCL', 'PCINT13']),
    'PC6': ('1', ['RESET', 'PCINT14']),
    'PD0': ('2', ['RXD', 'PCINT16']), 'PD1': ('3', ['TXD', 'PCINT17']), 'PD2': ('4', ['INT0', 'PCINT18']),
    'PD3': ('5', ['INT1', 'OC2B', 'PCINT19']), 'PD4': ('6', ['XCK', 'T0', 'PCINT20']), 'PD5': ('11', ['T1', 'OC0B', 'PCINT21']),
    'PD6': ('12', ['AIN0', 'OC0A', 'PCINT22']), 'PD7': ('13', ['AIN1', 'PCINT23']),
}
POWER_PINS = {'7': 'VCC', '8': 'GND', '20': 'AVCC', '21': 'AREF', '22': 'GND'}
#: function → (peripheral, signal) — the peripheral each alternate function belongs to (the datasheet's words in TABLE)
FUNCTION_PERIPHERAL = {'RXD': ('USART0', 'RXD'), 'TXD': ('USART0', 'TXD'), 'XCK': ('USART0', 'XCK'),
                       'OC0A': ('TIMER0', 'OC0A'), 'OC0B': ('TIMER0', 'OC0B'), 'T0': ('TIMER0', 'T0'),
                       'OC1A': ('TIMER1', 'OC1A'), 'OC1B': ('TIMER1', 'OC1B'), 'T1': ('TIMER1', 'T1'), 'ICP1': ('TIMER1', 'ICP1'),
                       'OC2A': ('TIMER2', 'OC2A'), 'OC2B': ('TIMER2', 'OC2B'), 'TOSC1': ('TIMER2', 'TOSC1'), 'TOSC2': ('TIMER2', 'TOSC2'),
                       'SS': ('SPI', 'SS'), 'MOSI': ('SPI', 'MOSI'), 'MISO': ('SPI', 'MISO'), 'SCK': ('SPI', 'SCK'),
                       'SDA': ('TWI', 'SDA'), 'SCL': ('TWI', 'SCL'), 'INT0': ('EXINT', 'INT0'), 'INT1': ('EXINT', 'INT1'),
                       'AIN0': ('AC', 'AIN0'), 'AIN1': ('AC', 'AIN1'), 'RESET': ('RESET', 'RESET'), 'CLKO': ('CLOCK', 'CLKO'),
                       'XTAL1': ('CLOCK', 'XTAL1'), 'XTAL2': ('CLOCK', 'XTAL2'),
                       **{'ADC%d' % i: ('ADC', 'ADC%d' % i) for i in range(8)},
                       **{'PCINT%d' % i: ('PCINT', 'PCINT%d' % i) for i in range(24)}}
#: the PWM-capable Output Compare functions (Timer0/1/2) — what a PWM assignment is checked against (derived, never listed)
PWM_FUNCTIONS = ('OC0A', 'OC0B', 'OC1A', 'OC1B', 'OC2A', 'OC2B')


def _fact(key, value, unit, where, notes=''):
    return {'name': '%s:%s' % (SOC, key), 'board': SOC, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': M328_DOC,
            'revision': M328_REV, 'page_table': where, 'url': M328_URL, 'notes': notes}


def soc_facts():
    out = [_fact('pin.%s' % p, '28-SPDIP pin %s; %s' % (n, '/'.join(fns)), '', '%s; %s' % (FIG, TABLE[p[1]]))
           for p, (n, fns) in sorted(PINS.items())]
    out += [_fact('package.power_pins', ', '.join('%s %s' % (n, v) for n, v in sorted(POWER_PINS.items(), key=lambda x: int(x[0]))), '', FIG),
            _fact('memory.flash', 32768, 'bytes', 'Table 2-1 Memory Size Summary, p.16 (ATmega328P: 32KBytes)'),
            _fact('memory.eeprom', 1024, 'bytes', 'Table 2-1 Memory Size Summary, p.16 (ATmega328P: 1KBytes)'),
            _fact('memory.sram', 2048, 'bytes', 'Table 2-1 Memory Size Summary, p.16 (ATmega328P: 2KBytes)'),
            _fact('memory.sram_range', '0x0100-0x08FF', '', 'Figure 8-3 Data Memory Map, p.28'),
            _fact('peripheral.USART0', 'USART0', '', 'chapter 20 USART0, p.179'),
            _fact('peripheral.TIMER0', '8-bit Timer/Counter0 with PWM', '', 'chapter 15, p.102'),
            _fact('peripheral.TIMER1', '16-bit Timer/Counter1 with PWM', '', 'chapter 16, p.120'),
            _fact('peripheral.TIMER2', '8-bit Timer/Counter2 with PWM and Asynchronous Operation', '', 'chapter 18, p.150'),
            _fact('peripheral.ADC', '10-bit ADC, 6 channels in SPDIP', '', 'chapter 24, p.246; features list p.1 (6-channel 10-bit ADC in SPDIP Package)'),
            _fact('peripheral.SPI', 'SPI', '', 'chapter 19, p.169'), _fact('peripheral.TWI', '2-wire Serial Interface', '', 'chapter 22, p.215')]
    return out


def soc_pins():
    return [{'name': '%s:%s' % (SOC, p), 'soc': SOC, 'pin': p, 'port': p[1], 'bit': int(p[2]), 'package_pin': n,
             'functions_json': json.dumps(fns), 'default_function': 'RESET' if p == 'PC6' else 'GPIO', 'fact': '%s:pin.%s' % (SOC, p),
             'notes': 'PC6 is RESET unless the RSTDISBL fuse is programmed (Table 14-6)' if p == 'PC6' else ''}
            for p, (n, fns) in sorted(PINS.items())]


def soc_definition():
    fk = lambda k: '%s:%s' % (SOC, k)  # noqa: E731
    return {'name': SOC, 'title': 'Microchip ATmega328P', 'vendor': 'Microchip (Atmel)', 'package': '28-SPDIP (28P3)', 'isa': 'AVR8',
            'cpu_clock_hz': 16000000,
            'memory_map_json': json.dumps([{'region': 'flash', 'start': '0x0000', 'size': 32768, 'fact': fk('memory.flash')},
                                           {'region': 'sram', 'start': '0x0100', 'size': 2048, 'fact': fk('memory.sram_range')},
                                           {'region': 'eeprom', 'start': '0x000', 'size': 1024, 'fact': fk('memory.eeprom')}]),
            'peripherals_json': json.dumps([{'name': n, 'fact': fk('peripheral.%s' % n)} for n in ('USART0', 'TIMER0', 'TIMER1', 'TIMER2', 'ADC', 'SPI', 'TWI')]),
            'clocks_json': json.dumps([{'name': 'F_CPU (the UNO)', 'hz': 16000000, 'fact': 'arduino-uno-r3:build.f_cpu',
                                        'note': 'the chip has no fixed clock; 16 MHz is the board\'s (boards.txt build.f_cpu)'}]),
            'pin_count': len(PINS), 'facts_json': json.dumps([f['name'] for f in soc_facts()]),
            'source': 'datasheet %s' % M328_REV.split(',')[0], 'zephyr_soc': '', 'vendor_target': 'avr-gcc -mmcu=atmega328p',
            'undetermined': 'drive strength per pin not typed (the UNO pinout\'s 20 mA per I/O pin is a board fact)',
            'notes': 'Zephyr v4.4.2 has no AVR architecture (arch/: arc arm arm64 mips openrisc posix riscv rx sparc x86 xtensa) — no Zephyr SoC'}


def pwm_functions(soc_pin_rows, pin):
    """The Output Compare functions of a SoC pin (derived from its SocPin row) — [] = not a PWM pin."""
    for r in soc_pin_rows:
        if r['pin'] == pin:
            return [f for f in json.loads(r['functions_json']) if f in PWM_FUNCTIONS]
    return []
