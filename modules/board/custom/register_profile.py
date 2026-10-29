"""
@module board.custom.register_profile

rp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.4): THE REGISTER PROFILE of a SoC — every register field, then every register, classified:

  pin-configuration     a field that affects a pin or a signal, or enables an alternate function that takes over a pin
                        (DDRx/PORTx/PINx, COMnx, RXEN0/TXEN0, SPE, TWEN, DIDR0/1, ISCn/INTn, PCIEn/PCMSKn, PUD ...)
  peripheral-operation  counts, compare values, prescalers, baud, data registers, mode bits, status flags
  memory-nvm            EEPROM address/data/control, flash self-programming (SPMCSR), the stack pointer into SRAM
  cpu-system            SREG, sleep, power reduction, clock prescale/calibration, watchdog, reset status, GPIORn, vector-table bits
  mixed                 a register whose fields fall in more than one class (MCUCR: PUD pin-configuration, the rest cpu-system)

A DERIVED view over the cited rows, never a stored class and never a hand-typed list of register names as the source of truth:
  1. a RegisterField ROW classifies itself from its own columns — `affects_pin` / `affects_signal` set => pin-configuration; a
     write-one-to-clear status flag (access w1c) => peripheral-operation (it reports, it configures nothing); anything else takes the
     register's default;
  2. the register's default comes from the peripheral the register snapshot already groups it under (board.custom.registers
     .peripheral): GPIO PORTx => pin-configuration (one bit per pin), everything else on a peripheral => peripheral-operation;
     CPU / WDT / EEPROM registers carry a cited verdict (REGISTER_RULES below);
  3. fields with no RegisterField row are named from the datasheet's own Register Summary (section 36, pp.621-624, the committed
     snapshot register_summary_atmega328p.json) and take the default — except the few cited alternate-function ENABLE fields in
     PIN_ENABLE_RULES (each with its datasheet section and page, and the bit names checked against the summary) and FIELD_RULES
     (cited verdicts on fields that have rows but no pin tag: PCIEn, PUD, OCIE2x);
  4. a register with no field rows at all says so (`fields not modelled`) and is classified from 2-3.
Every verdict carries a reason and a citation (the row's own `page_table`, or the rule's, plus the Register Summary row).

    python3 -m board.custom.register_profile registers <soc> [--class pin|peripheral|memory|cpu] [--json]
    python3 -m board.custom.register_profile memory <soc> [--board B] [--sizes TEXT,DATA,BSS] [--json]
"""
import json
import os
import re
import sys

from board.custom import registers as R

HERE = os.path.dirname(os.path.abspath(__file__))
SOC = 'atmega328p'
DS = 'DS40002061B'
PIN, PER, MEM, CPU = 'pin-configuration', 'peripheral-operation', 'memory-nvm', 'cpu-system'
CLASSES = (PIN, PER, MEM, CPU)
SHORT = {'pin': PIN, 'peripheral': PER, 'memory': MEM, 'cpu': CPU}
MIXED = 'mixed'

#: (register, field label, bit_hi, bit_lo, [bit names as the Register Summary prints them], why, cite) — alternate-function ENABLE fields
#: whose registers have no RegisterField row (or none for these bits). The bit names are cross-checked against the summary snapshot.
PIN_ENABLE_RULES = (
    ('UCSR0B', 'RXEN0', 4, 4, ['RXEN0'], 'Receiver Enable: the receiver overrides normal port operation of the RxD pin (PD0) when enabled', '§20.11.3 UCSR0B bit 4, p.202'),
    ('UCSR0B', 'TXEN0', 3, 3, ['TXEN0'], 'Transmitter Enable: the transmitter overrides normal port operation of the TxD pin (PD1) when enabled', '§20.11.3 UCSR0B bit 3, p.202'),
    ('SPCR', 'SPE', 6, 6, ['SPE'], 'SPI Enable: when the SPI is enabled the data direction of the MOSI, MISO, SCK and SS pins is overridden (Table 19-1)', '§19.3, p.170; Table 19-1, p.171; §19.5.1 SPCR bit 6, p.176'),
    ('TWCR', 'TWEN', 2, 2, ['TWEN'], 'TWI Enable: the TWI takes control over the I/O pins connected to SCL and SDA', '§22.9.2 TWCR bit 2, p.240'),
    ('TCCR0A', 'COM0A', 7, 6, ['COM0A1', 'COM0A0'], 'Compare Output Mode A: when non-zero the OC0A output overrides the normal port functionality of its pin', '§15.9.1 TCCR0A, p.113'),
    ('TCCR0A', 'COM0B', 5, 4, ['COM0B1', 'COM0B0'], 'Compare Output Mode B: when non-zero the OC0B output overrides the normal port functionality of its pin', '§15.9.1 TCCR0A, p.114'),
    ('TCCR0B', 'FOC0A', 7, 7, ['FOC0A'], 'Force Output Compare A: a strobe that forces a compare match on the waveform generator, i.e. acts on the OC0A pin per COM0A1:0', '§15.9.2 TCCR0B bit 7, p.116'),
    ('TCCR0B', 'FOC0B', 6, 6, ['FOC0B'], 'Force Output Compare B: a strobe that forces a compare match on the waveform generator, i.e. acts on the OC0B pin per COM0B1:0', '§15.9.2 TCCR0B bit 6, p.116'),
    ('TCCR1A', 'COM1A', 7, 6, ['COM1A1', 'COM1A0'], 'Compare Output Mode A: when non-zero the OC1A output overrides the normal port functionality of its pin', '§16.11.1 TCCR1A, p.140'),
    ('TCCR1A', 'COM1B', 5, 4, ['COM1B1', 'COM1B0'], 'Compare Output Mode B: when non-zero the OC1B output overrides the normal port functionality of its pin', '§16.11.1 TCCR1A, p.140'),
    ('TCCR1C', 'FOC1A', 7, 7, ['FOC1A'], 'Force Output Compare for Channel A: forces a compare match, i.e. acts on the OC1A pin per COM1A1:0', '§16.11.3 TCCR1C bit 7, p.143'),
    ('TCCR1C', 'FOC1B', 6, 6, ['FOC1B'], 'Force Output Compare for Channel B: forces a compare match, i.e. acts on the OC1B pin per COM1B1:0', '§16.11.3 TCCR1C bit 6, p.143'),
    ('DIDR0', 'ADC5D..ADC0D', 5, 0, ['ADC5D', 'ADC4D', 'ADC3D', 'ADC2D', 'ADC1D', 'ADC0D'], 'Digital Input Disable: turns the digital input buffer on the ADC pin off (the PINx bit then reads 0)', '§24.9.5 DIDR0, p.260-261'),
    ('DIDR1', 'AIN1D..AIN0D', 1, 0, ['AIN1D', 'AIN0D'], 'Digital Input Disable: turns the digital input buffer on the AIN1/AIN0 pin off (the PINx bit then reads 0)', '§23.3.3 DIDR1, p.245'),
)
#: (register, field) of a field that HAS a RegisterField row -> (class, why, cite): verdicts the row's own tags do not give
FIELD_RULES = {
    ('PCICR', 'PCIE2'): (PIN, 'Pin Change Interrupt Enable 2: enables pin-change sensing on PCINT[23:16] (the bank\'s pins; PCMSK2 picks which)', '§13.2.4 PCICR, p.82'),
    ('PCICR', 'PCIE1'): (PIN, 'Pin Change Interrupt Enable 1: enables pin-change sensing on PCINT[14:8] (PCMSK1 picks which)', '§13.2.4 PCICR, p.82'),
    ('PCICR', 'PCIE0'): (PIN, 'Pin Change Interrupt Enable 0: enables pin-change sensing on PCINT[7:0] (PCMSK0 picks which)', '§13.2.4 PCICR, p.82'),
    ('MCUCR', 'PUD'): (PIN, 'Pull-up Disable: disables the pull-ups of every I/O port pin even when DDxn/PORTxn enable them', '§14.4.1 MCUCR bit 4, p.100; §14.1 p.84'),
    ('TIMSK2', 'OCIE2B'): (PER, 'Output Compare Match B Interrupt Enable: enables the on-chip compare interrupt only; the OC2B pin is driven by COM2B (TCCR2A), not by this bit', '§18.11.6 TIMSK2, p.166'),
    ('TIMSK2', 'OCIE2A'): (PER, 'Output Compare Match A Interrupt Enable: enables the on-chip compare interrupt only; the OC2A pin is driven by COM2A (TCCR2A), not by this bit', '§18.11.6 TIMSK2, p.166-167'),
}
#: register -> (class, why, cite): the registers that are not peripheral operation or GPIO (derived from their peripheral id is NOT enough:
#: the CPU block mixes the stack pointer, flash self-programming and system control)
REGISTER_RULES = {
    'EEAR': (MEM, 'EEPROM Address Register (16-bit view of EEARH:EEARL): addresses the EEPROM', '§8.6.1 EEARH and EEARL, p.31'),
    'EEARH': (MEM, 'EEPROM Address Register, high byte: addresses the EEPROM', '§8.6.1 EEARH and EEARL, p.31'),
    'EEARL': (MEM, 'EEPROM Address Register, low byte: addresses the EEPROM', '§8.6.1 EEARH and EEARL, p.31'),
    'EEDR': (MEM, 'EEPROM Data Register: the byte read from / written to the EEPROM', '§8.6.2 EEDR, p.31'),
    'EECR': (MEM, 'EEPROM Control Register: read/write enables and programming mode of the EEPROM', '§8.6.3 EECR, p.31'),
    'SPMCSR': (MEM, 'Store Program Memory Control and Status Register: flash page erase/write (self-programming) and boot lock bits', '§26.3.1 SPMCSR, p.270; §27.9.1 SPMCSR, p.287'),
    'SP': (MEM, 'Stack Pointer (16-bit view of SPH:SPL): points into the stack, which lives in the internal data SRAM', '§7.5 Stack Pointer, p.22'),
    'SPH': (MEM, 'Stack Pointer, high byte: points into the stack, which lives in the internal data SRAM', '§7.5.1 SPH and SPL, p.22'),
    'SPL': (MEM, 'Stack Pointer, low byte: points into the stack, which lives in the internal data SRAM', '§7.5.1 SPH and SPL, p.22'),
    'SREG': (CPU, 'AVR Status Register: the CPU\'s status flags (I, T, H, S, V, N, Z, C)', '§7.3.1 SREG, p.20'),
    'SMCR': (CPU, 'Sleep Mode Control Register: sleep enable and sleep mode select', '§10.11.1 SMCR, p.53'),
    'PRR': (CPU, 'Power Reduction Register: shuts down peripheral clocks to save power', '§10.11.3 PRR, p.54'),
    'CLKPR': (CPU, 'Clock Prescale Register: divides the system clock', '§9.12.2 CLKPR, p.46'),
    'OSCCAL': (CPU, 'Oscillator Calibration Register: trims the calibrated RC oscillator', '§9.12.1 OSCCAL, p.46'),
    'WDTCSR': (CPU, 'Watchdog Timer Control Register: the system watchdog reset/interrupt', '§11.9.2 WDTCSR, p.63'),
    'MCUSR': (CPU, 'MCU Status Register: which reset source caused the last reset', '§11.9.1 MCUSR, p.63'),
    'MCUCR': (CPU, 'MCU Control Register: interrupt vector select (IVSEL/IVCE) and brown-out disable (BODS/BODSE); PUD is classified separately', '§14.4.1 MCUCR, p.100; Register Summary lists p.54/77/100'),
    'GPIOR0': (CPU, 'General Purpose I/O Register 0: a free byte in I/O space for the program (not tied to any pin despite the name)', '§8.6.6 GPIOR0, p.35'),
    'GPIOR1': (CPU, 'General Purpose I/O Register 1: a free byte in I/O space for the program (not tied to any pin despite the name)', '§8.6.5 GPIOR1, p.35'),
    'GPIOR2': (CPU, 'General Purpose I/O Register 2: a free byte in I/O space for the program (not tied to any pin despite the name)', '§8.6.4 GPIOR2, p.35'),
}

_SUMMARY = {}


def summary():
    """The datasheet Register Summary snapshot (section 36, pp.621-624)."""
    if not _SUMMARY:
        _SUMMARY.update(json.load(open(os.path.join(HERE, 'register_summary_atmega328p.json'))))
    return _SUMMARY


def _entry(reg):
    regs = summary()['registers']
    for cand in (reg, reg + 'L', reg[:-1] + 'L' if reg.endswith('W') else reg + 'L'):
        if cand in regs:
            return cand, regs[cand]
    return '', None


def clean_bit(name):
    """A summary bit cell -> its bare name: footnote marks ('BODS(6)', '(SP10) 5.') and a '/' spacing are dropped; '–' (reserved) -> ''."""
    n = name.strip()
    if n == '–':
        return ''
    n = re.sub(r'\(\d\)$', '', n).strip()
    n = re.sub(r'\s*\d\.$', '', n).strip().strip('()').strip()
    return re.sub(r'\s*/\s*', '/', n)


def bit_names(entry):
    """[bit7 .. bit0] names as the summary prints them ('' = reserved/unused); [] for a data register (one description cell)."""
    return [clean_bit(c) for c in entry['bits']] if entry and entry['bits'] else []


def summary_cite(reg):
    key, e = _entry(reg)
    if not e:
        return 'Register Summary (no row for %s: a 16-bit view or a pair)' % reg
    return 'Register Summary §36 p.%s (row %s%s); described p.%s' % (e['summary_page'], key, '' if key == reg else ', the low byte of %s' % reg, e['described_page'] or '?')


def _bits(hi, lo):
    return set(range(lo, hi + 1))


def _label(hi, lo):
    return '[%d]' % hi if hi == lo else '[%d:%d]' % (hi, lo)


def default_for(reg, periph):
    """(class, reason, cite) the register takes for every field without its own verdict."""
    if reg in REGISTER_RULES:
        c, why, cite = REGISTER_RULES[reg]
        return c, why, '%s, %s' % (DS, cite)
    if periph.startswith('GPIO PORT'):
        return (PIN, 'a port register: one bit per pin of %s (data, direction or input level)' % periph, '%s, §14.4 Register Description, pp.100-101' % DS)
    return (PER, 'a %s register: mode, count, compare, baud, data or status of the peripheral - it does not itself claim a pin or touch memory/CPU state' % periph, summary_cite(reg))


def classify_row_field(f):
    """(class, reason, cite) of one RegisterField row, from its own columns (rules above only where the row has no tag)."""
    cite = '%s, %s' % (DS, f.get('page_table', ''))
    key = (f['register'].partition(':')[2], f['field'])
    if key in FIELD_RULES:
        c, why, rc = FIELD_RULES[key]
        return c, why, '%s, %s' % (DS, rc)
    tags = [t for t in (('affects_pin', f.get('affects_pin')), ('affects_signal', f.get('affects_signal'))) if t[1]]
    reg = key[0]
    if reg in REGISTER_RULES and not tags:
        # rm-2a: a flag inside a register with its own cited verdict (MCUSR's reset flags, WDTCSR.WDIF) belongs to that register's class, not the generic flag rule
        c, why, rc = REGISTER_RULES[reg]
        return c, '%s (the register\'s cited verdict; a %s field of it)' % (why, f.get('access')), '%s, %s' % (DS, rc)
    if f.get('access') in ('w1c', 'w0c'):
        return PER, 'a write-%s-to-clear status flag:' % ('one' if f['access'] == 'w1c' else 'zero') + ' it reports%s, it configures nothing' % (' (the row tags %s)' % ', '.join('%s=%s' % (k, v.rpartition(':')[2]) for k, v in tags) if tags else ''), cite
    if tags:
        return PIN, 'the field row says %s' % ' and '.join('%s %s' % (k, v.rpartition(':')[2]) for k, v in tags), cite
    return None, '', cite


def _field_entry(field, hi, lo, cls, why, cite, source):
    return {'field': field, 'bit_hi': hi, 'bit_lo': lo, 'bits': _label(hi, lo), 'class': cls, 'reason': why, 'cite': cite, 'source': source}


def classify_register(reg_row, field_rows):
    """One register's verdict: its fields (rows, rules, summary names), the roll-up (pure class or mixed), reason, cite."""
    reg = reg_row['register']
    periph = reg_row['peripheral'].partition(':')[2]
    d_cls, d_why, d_cite = default_for(reg, periph)
    fields, covered = [], set()
    for f in sorted(field_rows, key=lambda x: -x['bit_hi']):
        c, why, cite = classify_row_field(f)
        if c is None:
            c, why, cite = d_cls, d_why, cite
        fields.append(_field_entry(f['field'], f['bit_hi'], f['bit_lo'], c, why, cite, 'RegisterField'))
        covered |= _bits(f['bit_hi'], f['bit_lo'])
    key, ent = _entry(reg)
    names = bit_names(ent) if key == reg else []   # a 16-bit view (SP, ADC ...) is classified as a whole, not by its low byte's bits
    for (r, label, hi, lo, bnames, why, cite) in PIN_ENABLE_RULES:
        if r == reg and not (_bits(hi, lo) & covered):
            fields.append(_field_entry(label, hi, lo, PIN, why, '%s, %s' % (DS, cite), 'rule'))
            covered |= _bits(hi, lo)
    if names:
        for b in range(7, -1, -1):
            if names[7 - b] and b not in covered:
                fields.append(_field_entry(names[7 - b], b, b, d_cls, d_why, d_cite if 'Register Summary' in d_cite else '%s; %s' % (d_cite, summary_cite(reg)), 'register-summary'))
                covered.add(b)
    elif not fields:   # a data register / 16-bit view: one whole-register field
        width = int(reg_row.get('width_bytes') or 1) * 8
        fields.append(_field_entry('(whole register)', width - 1, 0, d_cls, d_why, d_cite, 'register-summary'))
    fields.sort(key=lambda x: (-x['bit_hi'], -x['bit_lo']))
    by = {}
    for f in fields:
        by.setdefault(f['class'], []).append(f)
    cls = next(iter(by)) if len(by) == 1 else MIXED
    parts = []
    for c in CLASSES:
        if c in by:
            nm = [f['field'] for f in by[c]]
            parts.append('%s: %s - %s' % (c, ', '.join(nm if len(nm) <= 4 else nm[:3] + ['... (%d fields)' % len(nm)]), by[c][0]['reason']))
    modelled = [f for f in fields if f['source'] == 'RegisterField']
    note = ('fields modelled as RegisterField rows (%d)' % len(modelled)) if modelled and len(modelled) == len(fields) else \
        ('fields partly modelled: RegisterField rows for %s; the rest named from the Register Summary' % ', '.join(f['field'] for f in modelled)) if modelled else \
        'fields not modelled (no RegisterField rows; %s)' % ('field names from the datasheet Register Summary' if names else 'a data register, classified as a whole')
    cites = []
    for c in CLASSES:
        for f in by.get(c, [])[:1]:
            if f['cite'] not in cites:
                cites.append(f['cite'])
    return {'register': reg, 'name': reg_row['name'], 'address': reg_row.get('addr_mem') or reg_row.get('addr', ''), 'io_address': reg_row.get('addr', '') if reg_row.get('space') == 'io' else '',
            'space': reg_row.get('space', ''), 'peripheral': periph, 'width_bytes': int(reg_row.get('width_bytes') or 1), 'class': cls, 'mixed': cls == MIXED,
            'classes': sorted(by, key=CLASSES.index), 'fields_note': note, 'reason': ' | '.join(parts), 'cite': '; '.join(cites + [summary_cite(reg)]),
            'fields': fields, 'field_counts': {c: len(by.get(c, [])) for c in CLASSES}}


def profile(tables, soc=SOC):
    """The whole register profile of `soc` over `tables` ({class: [dict]}: Register, RegisterField)."""
    if soc != SOC:
        raise KeyError('%s has no register rows - modelled SoCs: %s' % (soc, SOC))
    by_reg = {}
    for f in tables.get('RegisterField', []):
        if f.get('soc') == soc:
            by_reg.setdefault(f['register'], []).append(f)
    regs = [classify_register(g, by_reg.get(g['name'], [])) for g in sorted(tables.get('Register', []), key=lambda g: (g['space'] != 'io', int(g.get('addr_mem') or g['addr'] or '0', 16), g['register'])) if g.get('soc') == soc]
    fields = [dict(f, register=r['register'], register_class=r['class']) for r in regs for f in r['fields']]
    pure = {c: sum(1 for r in regs if r['class'] == c) for c in CLASSES}
    touching = {c: sum(1 for r in regs if c in r['classes']) for c in CLASSES}
    return {'soc': soc, 'registers': regs, 'fields': fields,
            'totals': {'registers': len(regs), 'pure': pure, 'mixed': sum(1 for r in regs if r['mixed']), 'touching': touching,
                       'fields': {c: sum(1 for f in fields if f['class'] == c) for c in CLASSES},
                       'fields_from_rows': sum(1 for f in fields if f['source'] == 'RegisterField'), 'fields_from_rules': sum(1 for f in fields if f['source'] == 'rule'),
                       'fields_from_summary': sum(1 for f in fields if f['source'] == 'register-summary'),
                       'registers_without_field_rows': sum(1 for r in regs if r['fields_note'].startswith('fields not modelled')),
                       'mixed_registers': [r['register'] for r in regs if r['mixed']]},
            'rules': {'summary': summary()['derived_from'], 'classes': list(CLASSES)}}


def register_rows(prof, cls=None):
    """Flat rows for a configured table (one per register)."""
    out = []
    for r in prof['registers']:
        if cls and cls not in r['classes']:
            continue
        out.append({'register': r['register'], 'address': r['address'], 'io_address': r['io_address'], 'peripheral': r['peripheral'], 'width_bytes': r['width_bytes'],
                    'class': r['class'], 'classes': ', '.join('%s (%d)' % (c, r['field_counts'][c]) for c in r['classes']), 'fields_note': r['fields_note'],
                    'reason': r['reason'], 'cite': r['cite'], 'ref': 'Register:%s' % r['name']})
    return out


_CLASS_WORDS = {
    PIN: 'fields that configure a pin or a signal, or enable an alternate function that takes the pin over (direction, level, pull-up, timer compare output, UART/SPI/TWI enable, digital-input disable, external and pin-change interrupt sense)',
    PER: 'counts, compare values, prescalers, baud rates, data registers, mode bits and status flags of a peripheral',
    MEM: 'the EEPROM address/data/control registers, flash self-programming (SPMCSR) and the stack pointer into SRAM',
    CPU: 'the CPU status register, sleep, power reduction, clock prescale and calibration, watchdog, reset status, the free GPIOR bytes and the vector-table bits',
}


def class_rows(prof):
    """One row per class: registers that are purely that class, registers that touch it (incl. mixed), fields, and what the class means."""
    t = prof['totals']
    rows = [{'class': c, 'registers_pure': t['pure'][c], 'registers_touching': t['touching'][c], 'fields': t['fields'][c], 'means': _CLASS_WORDS[c]} for c in CLASSES]
    rows.append({'class': MIXED, 'registers_pure': t['mixed'], 'registers_touching': t['mixed'], 'fields': '', 'means': 'registers whose fields fall in more than one class: ' + ', '.join(t['mixed_registers'])})
    return rows


def field_rows(prof, cls=None):
    return [{'register': f['register'], 'field': f['field'], 'bits': f['bits'], 'class': f['class'], 'register_class': f['register_class'], 'source': f['source'],
             'reason': f['reason'], 'cite': f['cite']} for f in prof['fields'] if not cls or f['class'] == cls]


def tables_from_manager(manager):
    out = {}
    for cls in ('Register', 'RegisterField', 'RegisterAddressMapping', 'MemoryRegion', 'DatasheetFact', 'AddressSpace', 'FirmwareBuild', 'BoardDefinition'):
        out[cls] = [{k: v for k, v in (r if isinstance(r, dict) else vars(r)).items() if not k.startswith('_') and k != 'manager'}
                    for r in ((manager.objectTables or {}).get(cls, {}) or {}).values()]
    return out


def seed_tables():
    from board.custom import board_object as BO
    return BO.seed_tables()


def _resolve_soc(arg):
    return SOC if str(arg).lower() in ('uno', 'arduino-uno-r3', 'atmega328p', 'atmega328') else str(arg)


def render(prof, cls=None):
    t = prof['totals']
    lines = ['%s - %d registers: %s; mixed %d (%s)' % (prof['soc'], t['registers'], ', '.join('%d %s' % (t['pure'][c], c) for c in CLASSES), t['mixed'], ', '.join(t['mixed_registers'])),
             '  fields: %s  (%d from RegisterField rows, %d from cited rules, %d named from the Register Summary); %d registers have no field rows (fields not modelled)'
             % (', '.join('%d %s' % (t['fields'][c], c) for c in CLASSES), t['fields_from_rows'], t['fields_from_rules'], t['fields_from_summary'], t['registers_without_field_rows'])]
    for r in prof['registers']:
        if cls and cls not in r['classes']:
            continue
        lines.append('  %-8s %-5s %-14s %-21s %s' % (r['register'], r['address'], r['peripheral'][:14], r['class'], r['fields_note']))
        if r['mixed'] or cls:
            for f in r['fields']:
                if not cls or f['class'] == cls:
                    lines.append('      %-14s %-7s %-21s %s' % (f['field'], f['bits'], f['class'], f['reason'][:100]))
    return '\n'.join(lines)


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__[__doc__.index('    python3'):])
        return 0
    import contextlib
    import io
    as_json = '--json' in argv
    args = [a for a in argv if a != '--json']
    opts, pos, i = {}, [], 1
    while i < len(args):
        if args[i].startswith('--') and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if not pos:
        print('usage: registers <soc> [--class pin|peripheral|memory|cpu] [--json]  |  memory <soc> [--board B] [--sizes TEXT,DATA,BSS] [--json]')
        return 2
    with contextlib.redirect_stdout(io.StringIO()):
        tables = seed_tables()
    soc = _resolve_soc(pos[0])
    try:
        if args[0] == 'registers':
            cls = None
            if opts.get('class'):
                cls = SHORT.get(opts['class'], opts['class'])
                if cls not in CLASSES:
                    print('refused: --class is one of %s' % ', '.join(SHORT))
                    return 2
            prof = profile(tables, soc)
            if as_json:
                print(json.dumps(dict(prof, ok=True, rows=register_rows(prof, cls)), indent=1))
            else:
                print(render(prof, cls))
            return 0
        if args[0] == 'memory':
            from board.custom import memory_map_view as MV
            sizes = None
            if opts.get('sizes'):
                t, d, b = (int(x) for x in opts['sizes'].split(','))
                sizes = {'size_text': t, 'size_data': d, 'size_bss': b, 'name': 'sizes given on the command line'}
            mm = MV.memory_map(tables, soc, board=opts.get('board'), build=sizes)
            if as_json:
                print(json.dumps(dict(mm, ok=True), indent=1))
            else:
                print(MV.render(mm))
            return 0
    except KeyError as e:
        print('refused: %s' % e.args[0])
        return 2
    print('unknown: %s' % ' '.join(argv))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
