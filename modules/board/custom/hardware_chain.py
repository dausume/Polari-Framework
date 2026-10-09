"""
@module board.custom.hardware_chain

THE HARDWARE CHAIN, materialized (ucd-0a, UNO_CORE_DEMO_PLAN.md §5f/§5g — his measure of success 2026-10-07: "a novice
can inspect the model and understand why that firmware configures the hardware the way it does"; navigable both ways:

    Board → BoardPin → SocPin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField

Every row here is DERIVED or CITED — nothing typed in that a source does not say:
  Peripheral        the ids the register snapshot's grouping rules give (board.custom.registers.PERIPHERAL_RULES) and
                    the alternate-function table gives (soc_atmega328p.FUNCTION_PERIPHERAL); chapter cites from the TOC
  PeripheralSignal  one per alternate-function name in the datasheet's port tables (+ one GPIO signal per port bit)
  PinFunction       one per (SocPin × function) + GPIO for every I/O pin
  Register          one per snapshot register (addr, io|mem, width), cited where register_fields_atmega328p names it
  RegisterField     board.custom.register_fields_atmega328p — cited bit by bit
and every row carries REVERSE links as "Class:name" strings in a `*_refs_json` column, so the generic object page
(/object/<Class>/<name>) walks both directions with no custom component (its collectRefs reads those lists), and the
configured tables use `column:ref:<Class>` / `:refs` for the forward hops. Row NAMES start with the soc id in lower
case ('atmega328p:…') on purpose: the object page treats a cell that starts with a Capitalised token + ':' as a
reference, so a plain name must not look like one.

Materialized at boot as code-owned seed rows (board.board_seed, `_register_owned` — converges on every boot, never
hand-edited; a disagreement with the source is a BoardConflict, the brd-bo posture). SoC covered: atmega328p (the
UNO). The ESP32-C3's SocPin rows exist but its functions are the GPIO matrix (routing 'matrix') — Phase 2, named in
`undetermined`, not guessed.

`chain_for(board, pin, tables)` is the walk itself (GET /api/board/<board>/chain/<pin>, `pol board chain`): the ordered
hops from a board pin down to the register fields that configure it, each hop a row with its Class:name link.
"""
import json
import sys

from board.custom import registers as R
from board.custom import register_fields_atmega328p as RF
from board.custom.soc_atmega328p import FUNCTION_PERIPHERAL, PINS, SOC
from board.custom.uno_facts import M328_DOC, M328_REV, M328_URL

#: peripheral id → (kind, datasheet title, chapter citation ('' = not read this session, said in `undetermined`), plain words)
PERIPHERAL_META = {
    'EXINT': ('exint', 'External Interrupts (INT0/INT1)', 'chapter 13 External Interrupts, p.79; Register Description §13.2, p.80-81',
              'Wakes the firmware on an edge or a level on the INT0/INT1 pins; EICRA picks the edge, EIMSK enables, EIFR flags.'),
    'PCINT': ('pcint', 'Pin Change Interrupts (PCINT23..0)', 'chapter 13 External Interrupts, p.79; PCICR/PCIFR/PCMSKn §13.2.4-8, p.82-83',
              'Wakes the firmware when any enabled pin of a bank toggles (three banks: PCINT[7:0], [14:8], [23:16]).'),
    'GPIO PORTB': ('gpio-port', 'I/O-Ports — Port B', 'chapter 14 I/O-Ports, p.84; PORTB/DDRB/PINB §14.4.2-4, p.100',
                   'Eight general digital pins: DDRB picks direction, PORTB drives or pulls up, PINB reads.'),
    'GPIO PORTC': ('gpio-port', 'I/O-Ports — Port C', 'chapter 14 I/O-Ports, p.84; PORTC/DDRC/PINC §14.4.5-7, p.100-101',
                   'Seven general digital pins (PC6 is RESET): DDRC picks direction, PORTC drives or pulls up, PINC reads.'),
    'GPIO PORTD': ('gpio-port', 'I/O-Ports — Port D', 'chapter 14 I/O-Ports, p.84; PORTD/DDRD/PIND §14.4.8-10, p.101',
                   'Eight general digital pins: DDRD picks direction, PORTD drives or pulls up, PIND reads.'),
    'TIMER0': ('timer', '8-bit Timer/Counter0 with PWM', 'chapter 15, p.102', 'An 8-bit counter with two compare outputs (OC0A on PD6, OC0B on PD5) — PWM.'),
    'TIMER1': ('timer', '16-bit Timer/Counter1 with PWM', 'chapter 16, p.120', 'A 16-bit counter with two compare outputs (OC1A on PB1, OC1B on PB2) and input capture.'),
    'TIMER2': ('timer', '8-bit Timer/Counter2 with PWM and Asynchronous Operation', 'chapter 18, p.150; Register Description §18.11, p.162-167',
               'An 8-bit counter with two compare outputs (OC2A on PB3, OC2B on PD3); hal_millis runs its 1 ms tick here.'),
    'USART0': ('usart', 'USART0', 'chapter 20, p.179', 'The serial port: RXD on PD0, TXD on PD1 — the UNO\'s link to the USB bridge chip.'),
    'SPI': ('spi', 'SPI – Serial Peripheral Interface', 'chapter 19, p.169', 'The 4-wire bus on PB2..PB5 (also the ICSP header).'),
    'TWI': ('twi', '2-wire Serial Interface (I2C)', 'chapter 22, p.215', 'The 2-wire bus: SDA on PC4, SCL on PC5.'),
    'ADC': ('adc', 'Analog-to-Digital Converter', 'chapter 24, p.246', 'Reads a voltage on ADC0..ADC5 (PC0..PC5) as a 10-bit number.'),
    'AC': ('comparator', 'Analog Comparator', '', 'Compares the voltages on AIN0 (PD6) and AIN1 (PD7).'),
    'WDT': ('wdt', 'Watchdog Timer', '', 'Resets the chip unless the firmware keeps petting it.'),
    'EEPROM': ('eeprom', 'EEPROM Data Memory', '', '1 KB of non-volatile bytes.'),
    'CPU': ('cpu', 'AVR CPU core and MCU control registers', '', 'The status register, stack pointer, MCU control, power reduction, clock prescaler.'),
    'CLOCK': ('clock', 'System Clock and Clock Options', '', 'The crystal pins (XTAL1/2) and the clock output (CLKO).'),
    'RESET': ('reset', 'System Control and Reset', '', 'The RESET pin (PC6 unless the RSTDISBL fuse is programmed).'),
}
#: signal → direction, by the datasheet's role for the signal (derived from the name's family; undetermined where the
#: direction depends on a mode, e.g. SPI master vs slave, XCK, the crystal pins)
_DIRECTION = {'OC': 'out', 'T': 'in', 'ICP': 'in', 'INT': 'in', 'PCINT': 'in', 'RXD': 'in', 'TXD': 'out', 'ADC': 'in', 'AIN': 'in',
              'SDA': 'inout', 'SCL': 'inout', 'CLKO': 'out', 'RESET': 'in'}
_DIRECTION_WHY = 'derived from the signal family: compare outputs out; clock/capture/interrupt/ADC/comparator inputs in; bus lines inout'


def _cite(where):
    return {'document': M328_DOC, 'page_table': where, 'url': M328_URL}


def _direction(signal):
    for prefix in ('PCINT', 'ICP', 'INT', 'OC', 'ADC', 'AIN', 'CLKO', 'RESET', 'RXD', 'TXD', 'SDA', 'SCL'):
        if signal.startswith(prefix):
            return _DIRECTION[prefix]
    if signal in ('T0', 'T1'):
        return 'in'
    return 'undetermined'


def _channel(signal):
    for prefix in ('PCINT', 'INT', 'ADC', 'AIN'):
        if signal.startswith(prefix) and signal[len(prefix):].isdigit():
            return signal[len(prefix):]
    if signal.startswith('OC') and len(signal) == 4:
        return signal[3]        # OC2B → B
    if signal in ('T0', 'T1', 'ICP1', 'TOSC1', 'TOSC2', 'XTAL1', 'XTAL2'):
        return signal[-1]
    return ''


def _ref(cls, name):
    return '%s:%s' % (cls, name)


def _snapshot_origin():
    s = R.load(SOC)
    return 'derived:registers_%s.json (avr-libc %s, -dM sha256 %s…)' % (SOC, s.get('avr_libc', '?'), (s.get('dm_sha256') or '')[:12])


def _function_table():
    """(peripheral, signal) per alternate function + the GPIO pseudo-function per port → the one vocabulary."""
    return dict(FUNCTION_PERIPHERAL)


# ---------------------------------------------------------------- the rows

def peripherals():
    """One Peripheral row per id the snapshot's rules or the function table name — union, never a hand list."""
    ids = {R.peripheral(name) for name in R.load(SOC)['registers']}
    ids |= {p for p, _s in _function_table().values()}
    ids |= {'GPIO PORT%s' % p for p in 'BCD'}
    out = []
    for pid in sorted(ids):
        kind, title, chapter, words = PERIPHERAL_META.get(pid, ('', pid, '', ''))
        out.append({'name': '%s:%s' % (SOC, pid), 'soc': SOC, 'peripheral': pid, 'title': title, 'kind': kind or 'undetermined',
                    'chapter': chapter, 'description': words, 'registers_refs_json': '[]', 'signals_refs_json': '[]',
                    'pin_functions_refs_json': '[]', 'fact': ('%s:peripheral.%s' % (SOC, pid)) if pid in ('USART0', 'TIMER0', 'TIMER1', 'TIMER2', 'ADC', 'SPI', 'TWI') else '',
                    'origin': 'derived:registers.PERIPHERAL_RULES + soc_atmega328p.FUNCTION_PERIPHERAL (datasheet register-summary / port-table naming)',
                    'undetermined': '' if chapter else 'chapter page not read this session (register summary naming only)',
                    'notes': ''})
    return out


def signals():
    """One PeripheralSignal row per alternate-function name (the port tables) + one GPIO signal per port bit."""
    out = []
    for fn, (pid, sig) in sorted(_function_table().items()):
        out.append({'name': '%s:%s:%s' % (SOC, pid, sig), 'soc': SOC, 'peripheral': '%s:%s' % (SOC, pid), 'signal': sig,
                    'channel': _channel(sig), 'direction': _direction(sig),
                    'description': '%s signal %s of %s' % (PERIPHERAL_META.get(pid, ('', pid, '', ''))[1], sig, pid),
                    'pin_functions_refs_json': '[]', 'fact': '', 'origin': 'derived:soc_atmega328p.FUNCTION_PERIPHERAL (Tables 14-3/14-6/14-9); direction %s' % _DIRECTION_WHY,
                    'undetermined': 'direction depends on the mode (not fixed by the pin table)' if _direction(sig) == 'undetermined' else '',
                    'notes': ''})
    for pin in sorted(PINS):
        port, bit = pin[1], pin[2]
        pid = 'GPIO PORT%s' % port
        out.append({'name': '%s:%s:%s' % (SOC, pid, pin), 'soc': SOC, 'peripheral': '%s:%s' % (SOC, pid), 'signal': pin, 'channel': bit,
                    'direction': 'inout', 'description': 'general digital I/O bit %s of port %s (DD%s%s / PORT%s%s / PIN%s%s)' % (bit, port, port, bit, port, bit, port, bit),
                    'pin_functions_refs_json': '[]', 'fact': '%s:pin.%s' % (SOC, pin), 'origin': 'derived:§14.2 Ports as General Digital I/O (every port pin), p.85',
                    'undetermined': '', 'notes': ''})
    return out


def pin_functions(soc_pin_rows):
    """One PinFunction row per (SocPin × function) + GPIO per I/O pin, for the atmega328p SocPin rows given."""
    table = _function_table()
    out = []
    for sp in soc_pin_rows:
        if sp.get('soc') != SOC:
            continue
        pin = sp['pin']
        port = sp['port']
        fns = ['GPIO'] + list(json.loads(sp.get('functions_json') or '[]'))
        for fn in fns:
            if fn == 'GPIO':
                pid, sig = 'GPIO PORT%s' % port, pin
                words = 'plain digital input/output (the default after reset%s)' % ('' if sp.get('default_function') == 'GPIO' else '; %s is %s by default' % (pin, sp.get('default_function')))
                overrides = False
            else:
                pid, sig = table.get(fn, ('undetermined', fn))
                words = '%s of %s on %s' % (sig, pid, pin)
                overrides = True
            out.append({'name': '%s:%s:%s' % (SOC, pin, fn), 'soc': SOC, 'soc_pin': sp['name'], 'function': fn,
                        'signal': '%s:%s:%s' % (SOC, pid, sig), 'peripheral': '%s:%s' % (SOC, pid), 'routing': 'fixed',
                        'overrides_gpio': overrides, 'exclusive_group': '', 'description': words, 'board_pins_refs_json': '[]',
                        'fact': sp.get('fact', ''),
                        'origin': 'derived:SocPin.functions_json (%s)' % ('§14.2 every port pin is GPIO' if fn == 'GPIO' else 'the datasheet port table the SocPin fact cites'),
                        'undetermined': '' if fn == 'GPIO' else 'exclusive_group: which functions of this pin may be active together is not cited yet',
                        'notes': '§14.3 Alternate Port Functions (p.89): an enabled alternate function overrides DDR/PORT for the pin' if overrides else ''})
    return out


def registers():
    """One Register row per snapshot register; cited title/page/reset where register_fields_atmega328p names it.
    `addr`/`addr_mem`/`block`/`mappings_refs_json` are placeholders here — `build()` sets them FROM the
    RegisterAddressMapping/RegisterBlock rows (ucd-0b2a: one source, never computed twice)."""
    snap = R.load(SOC)
    origin = _snapshot_origin()
    fields_by_reg = {}
    for f in RF.FIELDS:
        fields_by_reg.setdefault(f['register'], []).append(_ref('RegisterField', '%s:%s.%s' % (SOC, f['register'], f['field'])))
    out = []
    for name, r in sorted(snap['registers'].items()):
        title, where, reset, _addr_mem_cite = RF.REGISTER_CITES.get(name, ('', '', '', ''))
        space = r.get('space', '')
        row = {'name': '%s:%s' % (SOC, name), 'soc': SOC, 'register': name, 'peripheral': '%s:%s' % (SOC, R.peripheral(name)),
               'block': '%s:%s-block' % (SOC, R.peripheral(name)), 'addr': r.get('addr', ''), 'addr_mem': '', 'space': space,
               'width_bytes': int(r.get('width_bytes') or 1), 'reset_value': reset, 'description': title,
               'fields_refs_json': json.dumps(fields_by_reg.get(name, [])), 'mappings_refs_json': '[]',
               'origin': origin + ('; io+0x20 = data-space address (the datasheet prints both, e.g. EIMSK 0x1D (0x3D) p.81)' if space == 'io' else ''),
               'undetermined': '' if name in fields_by_reg else 'bit fields not captured yet (ucd-0a cites EXINT, ports B/D, Timer2)',
               'notes': ''}
        row.update(_cite(where) if where else {'document': '', 'page_table': '', 'url': ''})
        out.append(row)
    return out


# ---------------------------------------------------------------- ucd-0b2a: address space as rows (§5h B3/D-ucd-9)
_IO_MEM_CITE = ('Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B, §8.5 "I/O Memory", p.30: '
                '"When using the I/O specific commands IN and OUT, the I/O addresses 0x00 - 0x3F must be used. '
                'When addressing I/O Registers as data space using LD and ST instructions, 0x20 must be added to '
                'these addresses ... For the Extended I/O space from 0x60 - 0xFF in SRAM, only the ST/STS/STD and '
                'LD/LDS/LDD instructions can be used."')


def address_spaces():
    """Two AddressSpace rows: `io` (IN/OUT, 0x00-0x3F) and `data` (LD/ST/LDS/STS/LDD/STD — the SAME registers at
    +0x20, plus the extended I/O 0x60-0xFF that has no io alias at all) — cited §8.5 p.30."""
    cite = _cite('§8.5 I/O Memory, p.30')
    out = [{'name': '%s:io' % SOC, 'soc': SOC, 'space': 'io', 'title': 'I/O space',
            'access_instructions': 'IN/OUT; SBI/CBI/SBIS/SBIC for 0x00–0x1F', 'range_lo': '0x00', 'range_hi': '0x3F',
            'offset_from_io': '', 'description': 'the short I/O address space every register below 0x40 is reachable through.',
            'origin': 'cited:' + _IO_MEM_CITE, 'undetermined': '', 'notes': ''},
           {'name': '%s:data' % SOC, 'soc': SOC, 'space': 'data', 'title': 'Data space',
            'access_instructions': 'LD/ST/LDS/STS/LDD/STD', 'range_lo': '0x20', 'range_hi': '0xFF', 'offset_from_io': '0x20',
            'description': 'the data address space: the I/O registers seen at +0x20 (0x20-0x5F) plus the extended '
                           'I/O space (0x60-0xFF) that has NO io alias — LD/ST/LDS/STS/LDD/STD only, never IN/OUT.',
            'origin': 'cited:' + _IO_MEM_CITE, 'undetermined': '', 'notes': ''}]
    for row in out:
        row.update(cite)
    return out


def register_address_mappings():
    """One or two RegisterAddressMapping rows per snapshot register: an io-space register gets BOTH an io mapping
    (its own address) and a data mapping (io + 0x20, cited §8.5); a mem-space register gets a data mapping only
    (its own address — the snapshot's `mem` IS the data-space address; no io alias is ever invented for it, and an
    address below 0x60 would be NOTED rather than aliased — none exist on the atmega328p today)."""
    snap = R.load(SOC)
    origin = _snapshot_origin()
    out = []
    for name, r in sorted(snap['registers'].items()):
        space, addr = r.get('space', ''), r.get('addr', '')
        reg_name = '%s:%s' % (SOC, name)
        if space == 'io':
            out.append({'name': '%s:%s@io' % (SOC, name), 'soc': SOC, 'register': reg_name, 'address_space': '%s:io' % SOC,
                        'address': addr, 'how': 'IN/OUT; SBI/CBI/SBIS/SBIC for 0x00–0x1F' if int(addr, 16) <= 0x1F else 'IN/OUT',
                        'origin': origin, 'undetermined': '', 'notes': ''})
            data_addr = '0x%02X' % (int(addr, 16) + 0x20)
            out.append({'name': '%s:%s@data' % (SOC, name), 'soc': SOC, 'register': reg_name, 'address_space': '%s:data' % SOC,
                        'address': data_addr, 'how': 'LD/ST/LDS/STS/LDD/STD', 'origin': origin + '; io+0x20 per §8.5 p.30',
                        'undetermined': '', 'notes': ''})
        elif space == 'mem':
            note = '' if int(addr, 16) >= 0x60 else ('the snapshot says mem at %s (below the 0x60 extended-I/O start) '
                                                       '— no io alias invented' % addr)
            out.append({'name': '%s:%s@data' % (SOC, name), 'soc': SOC, 'register': reg_name, 'address_space': '%s:data' % SOC,
                        'address': addr, 'how': 'LD/ST/LDS/STS/LDD/STD', 'origin': origin, 'undetermined': note, 'notes': ''})
    return out


#: the one shared block this slice derives (cited, never guessed further): MCUCR.PUD (Pull-up Disable) configures
#: every GPIO port's pull-ups, not just the CPU's own registers — DS40002061B §14.4.1 MCUCR, p.100 ("...even if the
#: DDxn and PORTxn Registers are configured to enable them")
_SHARED_BLOCKS = {'CPU': ('GPIO PORTB', 'GPIO PORTC', 'GPIO PORTD')}
_SHARED_WHY = ('MCUCR.PUD (RegisterField atmega328p:MCUCR.PUD) disables the pull-ups of every I/O port regardless '
              'of DDxn/PORTxn, cited §14.4.1 MCUCR, p.100; §14.1 p.84')


def register_blocks():
    """One RegisterBlock row per Peripheral id (the datasheet's own register-summary grouping) — `registers_refs_json`
    filled by `link()`; `shared_with_refs_json` filled here for the one cited case (`_SHARED_BLOCKS`)."""
    out = []
    for p in peripherals():
        pid = p['peripheral']
        shared = [_ref('Peripheral', '%s:%s' % (SOC, other)) for other in _SHARED_BLOCKS.get(pid, ())]
        out.append({'name': '%s:%s-block' % (SOC, pid), 'soc': SOC, 'peripheral': p['name'], 'title': p['title'],
                    'registers_refs_json': '[]', 'shared_with_refs_json': json.dumps(shared),
                    'origin': 'derived: one register block per peripheral = the datasheet\'s register-summary grouping '
                              '(board.custom.registers.PERIPHERAL_RULES / soc_atmega328p.FUNCTION_PERIPHERAL)',
                    'undetermined': '', 'notes': _SHARED_WHY if shared else ''})
    return out


#: region -> (AddressSpace row name or '', the undetermined note when it has none) — flash is program memory (fetched
#: by the instruction unit, not addressed through io/data at all, §8.1); eeprom is addressed through its OWN EEAR/EEDR
#: register pair, never LD/ST (§8.4); sram IS the data space's general-purpose part
_REGION_SPACE = {'flash': ('', 'program memory (§8.1 Program Memory) — not addressed through the io/data space'),
                 'sram': ('%s:data' % SOC, ''),
                 'eeprom': ('', 'EEPROM is addressed through EEAR/EEDR, not the data space (§8.4 EEPROM Data Memory)')}


def memory_regions():
    """The three MemoryRegion rows, from `soc_atmega328p.soc_definition()`'s own cited `memory_map_json` — one
    source, never re-typed."""
    from board.custom import soc_atmega328p as SA
    mm = {r['region']: r for r in json.loads(SA.soc_definition()['memory_map_json'])}
    out = []
    for region in ('flash', 'sram', 'eeprom'):
        r = mm[region]
        address_space, undetermined = _REGION_SPACE[region]
        out.append({'name': '%s:%s' % (SOC, region), 'soc': SOC, 'region': region, 'start': r['start'], 'size': r['size'],
                    'address_space': address_space, 'fact': r['fact'], 'origin': 'derived:soc_atmega328p.soc_definition().memory_map_json',
                    'undetermined': undetermined, 'notes': ''})
    return out


def register_fields():
    out = []
    for f in RF.FIELDS:
        sig = f['affects_signal']
        pid = _function_table().get(sig, ('', ''))[0] if sig else ''
        out.append({'name': '%s:%s.%s' % (SOC, f['register'], f['field']), 'soc': SOC, 'register': '%s:%s' % (SOC, f['register']),
                    'field': f['field'], 'bit_hi': f['bit_hi'], 'bit_lo': f['bit_lo'], 'width': f['width'], 'access': f['access'],
                    'reset_value': f['reset_value'], 'description': f['description'], 'values_json': json.dumps(f['values']),
                    'affects_signal': ('%s:%s:%s' % (SOC, pid, sig)) if sig and pid else '',
                    'affects_pin': ('%s:%s' % (SOC, f['affects_pin'])) if f['affects_pin'] else '',
                    'origin': 'cited', 'undetermined': '', 'notes': f['notes'], **_cite(f['page_table'])})
    return out


# ---------------------------------------------------------------- the reverse links

def link(rows):
    """Fill every `*_refs_json` reverse column from the forward references the rows already carry. `rows` =
    {class: [dict]} holding Peripheral, PeripheralSignal, PinFunction, Register, RegisterField, SocPin, BoardPin,
    RegisterBlock, RegisterAddressMapping (ucd-0b2a)."""
    P = {r['name']: r for r in rows.get('Peripheral', [])}
    S = {r['name']: r for r in rows.get('PeripheralSignal', [])}
    F = {r['name']: r for r in rows.get('PinFunction', [])}
    G = {r['name']: r for r in rows.get('Register', [])}
    SP = {r['name']: r for r in rows.get('SocPin', [])}
    RB = {r['name']: r for r in rows.get('RegisterBlock', [])}
    back = {}

    def add(target, cls, name):
        back.setdefault(target, []).append(_ref(cls, name))

    for s in S.values():
        add(s['peripheral'], 'PeripheralSignal', s['name'])
    for f in F.values():
        add(f['signal'], 'PinFunction', f['name'])
        add(f['peripheral'], 'PinFunction', f['name'])
        add(f['soc_pin'], 'PinFunction', f['name'])
    for g in G.values():
        add(g['peripheral'], 'Register', g['name'])
        add(g['block'], 'Register', g['name'])
    for m in rows.get('RegisterAddressMapping', []):
        add(m['register'], 'RegisterAddressMapping', m['name'])
    for fld in rows.get('RegisterField', []):
        if fld.get('affects_signal'):
            add(fld['affects_signal'], 'RegisterField', fld['name'])
        if fld.get('affects_pin'):
            add(fld['affects_pin'], 'RegisterField', fld['name'])
    for bp in rows.get('BoardPin', []):
        sp = '%s:%s' % (SOC, bp.get('soc_pin')) if bp.get('soc_pin') and ('%s:%s' % (SOC, bp.get('soc_pin'))) in SP else ''
        if sp:
            add(sp, 'BoardPin', bp['name'])
            for f in F.values():
                if f['soc_pin'] == sp:
                    add(f['name'], 'BoardPin', bp['name'])
    for p in P.values():
        refs = back.get(p['name'], [])
        p['registers_refs_json'] = json.dumps(sorted(x for x in refs if x.startswith('Register:')))
        p['signals_refs_json'] = json.dumps(sorted(x for x in refs if x.startswith('PeripheralSignal:')))
        p['pin_functions_refs_json'] = json.dumps(sorted(x for x in refs if x.startswith('PinFunction:')))
    for rb in RB.values():
        rb['registers_refs_json'] = json.dumps(sorted(x for x in back.get(rb['name'], []) if x.startswith('Register:')))
    for g in G.values():
        g['mappings_refs_json'] = json.dumps(sorted(x for x in back.get(g['name'], []) if x.startswith('RegisterAddressMapping:')))
    for s in S.values():
        refs = back.get(s['name'], [])
        s['pin_functions_refs_json'] = json.dumps(sorted(x for x in refs if x.startswith('PinFunction:')))
        fields = sorted(x for x in refs if x.startswith('RegisterField:'))
        if fields:
            s['notes'] = (s['notes'] + ' ' if s['notes'] else '') + 'configured by: ' + ', '.join(x.split(':', 1)[1] for x in fields)
    for f in F.values():
        f['board_pins_refs_json'] = json.dumps(sorted(x for x in back.get(f['name'], []) if x.startswith('BoardPin:')))
    for sp in SP.values():
        refs = back.get(sp['name'], [])
        sp['links_refs_json'] = json.dumps(sorted(x for x in refs if x.startswith('BoardPin:')) + sorted(x for x in refs if x.startswith('PinFunction:'))
                                           + sorted(x for x in refs if x.startswith('RegisterField:')))
    for bp in rows.get('BoardPin', []):
        sp = '%s:%s' % (SOC, bp.get('soc_pin'))
        if sp in SP:
            bp['links_refs_json'] = json.dumps([_ref('SocPin', sp)] + sorted(x for x in back.get(sp, []) if x.startswith('PinFunction:')))
        else:
            bp.setdefault('links_refs_json', '[]')
    return rows


def build(soc_pin_rows, board_pin_rows):
    """The chain rows for the seed: {class: [dict]} with the reverse links filled; the SocPin/BoardPin rows given
    gain their `links_refs_json` in place. ucd-0b2a: + AddressSpace/RegisterAddressMapping/RegisterBlock/
    MemoryRegion — `Register.addr`/`addr_mem` are then OVERWRITTEN from the mapping rows (one source)."""
    rows = {'Peripheral': peripherals(), 'PeripheralSignal': signals(), 'PinFunction': pin_functions(soc_pin_rows),
            'Register': registers(), 'RegisterField': register_fields(), 'SocPin': soc_pin_rows, 'BoardPin': board_pin_rows,
            'AddressSpace': address_spaces(), 'RegisterAddressMapping': register_address_mappings(),
            'RegisterBlock': register_blocks(), 'MemoryRegion': memory_regions()}
    link(rows)
    mapping_by_register = {}
    for m in rows['RegisterAddressMapping']:
        mapping_by_register.setdefault(m['register'], {})[m['address_space']] = m['address']
    for g in rows['Register']:
        addrs = mapping_by_register.get(g['name'], {})
        g['addr'] = addrs.get('%s:io' % SOC) or addrs.get('%s:data' % SOC) or g['addr']
        g['addr_mem'] = addrs.get('%s:data' % SOC, '') if g['space'] == 'io' else ''
    for sp in soc_pin_rows:
        sp.setdefault('links_refs_json', '[]')
    for bp in board_pin_rows:
        bp.setdefault('links_refs_json', '[]')
    return {k: rows[k] for k in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField',
                                 'AddressSpace', 'RegisterAddressMapping', 'RegisterBlock', 'MemoryRegion')}


CHAIN_CLASSES = ('Peripheral', 'PeripheralSignal', 'PinFunction', 'SignalRoute', 'Register', 'RegisterField', 'RegisterSetting',
                 'RegisterFieldSetting', 'BoardPinNet')


# ---------------------------------------------------------------- the walk

def _hop(hop, cls, name, what, detail=''):
    return {'hop': hop, 'kind': cls, 'name': name, 'what': what, 'detail': detail, 'ref': _ref(cls, name)}


def chain_for(board, pin, tables):
    """The ordered hops from one board pin down the chain, over `tables` = {class: [dict]} (seed or live). Raises
    KeyError when the board has no such pin. Each hop: {hop, kind, name, what, detail, ref}."""
    from board.custom import board_object as BO
    r = BO.rows_for(board, tables)
    bp = BO.pin_by_canonical(r, pin)
    if bp is None:
        raise KeyError('%s has no pin %s' % (r['board'], pin))
    by = {c: {x['name']: x for x in tables.get(c, [])} for c in ('SocPin', 'PinFunction', 'PeripheralSignal', 'Peripheral', 'Register', 'RegisterField')}
    hops = [_hop(0, 'BoardPin', bp['name'], 'board pin %s' % bp['canonical'], 'net %s · connector %s · C symbol %s' % (bp.get('net') or '—', bp.get('connector_pin') or '—', bp.get('firmware_symbol') or '—'))]
    sp = by['SocPin'].get('%s:%s' % (SOC, bp.get('soc_pin')))
    if sp is None:
        hops.append(_hop(1, 'SocPin', '%s:%s' % (bp.get('board'), bp.get('soc_pin')), 'SoC pin not in the chain (only the atmega328p is materialized)', ''))
        return hops
    hops.append(_hop(1, 'SocPin', sp['name'], 'SoC pin %s — port %s bit %s, package pin %s' % (sp['pin'], sp['port'], sp['bit'], sp['package_pin']),
                     'functions ' + '/'.join(['GPIO'] + json.loads(sp.get('functions_json') or '[]')) + ' · ' + sp.get('fact', '')))
    pfs = [f for f in by['PinFunction'].values() if f['soc_pin'] == sp['name']]
    pfs.sort(key=lambda f: (f['function'] != 'GPIO', f['function']))
    sigs, pers, regs, fields = [], [], [], []
    for f in pfs:
        hops.append(_hop(2, 'PinFunction', f['name'], 'can be %s' % f['function'], f['description'] + (' · overrides GPIO when enabled' if f['overrides_gpio'] else '')))
        s = by['PeripheralSignal'].get(f['signal'])
        if s and s not in sigs:
            sigs.append(s)
    for s in sigs:
        hops.append(_hop(3, 'PeripheralSignal', s['name'], 'signal %s of %s (%s)' % (s['signal'], s['peripheral'].split(':', 1)[1], s['direction']), s['description']))
        p = by['Peripheral'].get(s['peripheral'])
        if p and p not in pers:
            pers.append(p)
    for p in pers:
        hops.append(_hop(4, 'Peripheral', p['name'], p['title'], (p['chapter'] or p['undetermined']) + ' · ' + p['description']))
    sig_names = {s['name'] for s in sigs}
    own_fields = [x for x in by['RegisterField'].values() if x.get('affects_pin') == sp['name'] or x.get('affects_signal') in sig_names]
    own_regs = {x['register'] for x in own_fields}
    per_names = {p['name'] for p in pers}
    for g in sorted(by['Register'].values(), key=lambda g: (g['name'] not in own_regs, g['name'])):
        if g['peripheral'] in per_names:
            regs.append(g)
    for g in regs:
        hops.append(_hop(5, 'Register', g['name'], '%s — %s' % (g['register'], g['description'] or g['peripheral'].split(':', 1)[1]),
                         '%s %s%s · %s' % (g['space'], g['addr'], (' (%s)' % g['addr_mem']) if g['addr_mem'] else '',
                                           ('fields for this pin: %d' % sum(1 for x in own_fields if x['register'] == g['name'])) if g['name'] in own_regs
                                           else (g['page_table'] or g['undetermined']))))
    for x in sorted(own_fields, key=lambda x: (x['register'], -x['bit_hi'])):
        vals = json.loads(x['values_json'])
        hops.append(_hop(6, 'RegisterField', x['name'], '%s.%s bits %s — %s' % (x['register'].split(':', 1)[1], x['field'],
                                                                           ('%d:%d' % (x['bit_hi'], x['bit_lo'])) if x['width'] > 1 else str(x['bit_lo']), x['description']),
                         'access %s · ' % x['access'] + ' | '.join('%s = %s' % (k, v) for k, v in vals.items()) + ' · ' + x['page_table']))
    return hops


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print('usage: python3 -m board.custom.hardware_chain chain <board> <pin> [--json]   e.g. chain arduino-uno-r3 D3')
        return 0
    if argv[0] == 'chain' and len(argv) >= 3:
        import contextlib
        import io
        from board.custom import board_object as BO
        with contextlib.redirect_stdout(io.StringIO()):   # the framework prints a manager notice per row built without a server; not news here
            tables = BO.seed_tables()
        try:
            hops = chain_for(argv[1], argv[2], tables)
        except (KeyError, BO.BoardObjectRefused) as e:
            print('refused: %s' % e)
            return 2
        if '--json' in argv:
            print(json.dumps({'ok': True, 'board': argv[1], 'pin': argv[2], 'rows': hops}, indent=1))
            return 0
        print('%s %s — the hardware chain (%d hops)' % (argv[1], argv[2], len(hops)))
        for h in hops:
            print('%s%-16s %-36s %s' % ('  ' * h['hop'], h['kind'], h['name'], h['what']))
            if h['detail']:
                print('%s%-16s %s' % ('  ' * h['hop'], '', h['detail'][:160]))
        return 0
    print('unknown: %s' % ' '.join(argv))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
