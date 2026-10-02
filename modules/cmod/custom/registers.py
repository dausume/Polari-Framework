"""
@module cmod.custom.registers

WHICH IDENTIFIERS ARE REGISTERS (C_MODULARIZATION_PLAN.md §2: an atom's resources). DERIVED, never typed in: avr-libc's
own <avr/io.h> for the MCU, read with `avr-gcc -mmcu=<mcu> -E -dM` through the board engines seam — every
`#define NAME _SFR_(IO|MEM)(8|16)(addr)` is a register, every `#define NAME _VECTOR(n)` an interrupt vector. The result
is a committed SNAPSHOT (`registers_<mcu>.json`, carrying the avr-libc version and the sha256 of the -dM text it came
from) so the parser needs no engine; `pol cmod registers --refresh` re-derives it.

The one judgement here is the PERIPHERAL a register belongs to (a register name → USART0 / TIMER2 / ADC / GPIO PORTB …):
PERIPHERAL_RULES, by the datasheet's own naming (ATmega328P DS40002061B register summary §36: UCSRnA/UDRn/UBRRn = USARTn,
TCCRnA/TCNTn/OCRnA/TIMSKn/TIFRn = Timer/Counter n, PORTx/DDRx/PINx = I/O port x, ADMUX/ADCSRA/ADC = the ADC, …). A
register no rule names is reported as its own name, never guessed into a group.
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
_REG = re.compile(r'^#define ([A-Z][A-Z0-9_]*) _SFR_(IO|MEM)(8|16)\((0x[0-9A-Fa-f]+)\)\s*$')
_VEC = re.compile(r'^#define ([A-Z][A-Z0-9_]*_vect) _VECTOR\((\d+)\)\s*$')
_LIBC = re.compile(r'^#define __AVR_LIBC_VERSION_STRING__ "([^"]+)"')
#: (regex over the register name, peripheral template) — first match wins; DS40002061B §36 naming
PERIPHERAL_RULES = (
    (r'^(UCSR|UDR|UBRR)(\d)', 'USART{1}'),
    (r'^(TCCR|TCNT|OCR|TIMSK|TIFR|ICR)(\d)', 'TIMER{1}'),
    (r'^(ASSR|GTCCR)$', 'TIMER2'),
    (r'^(PORT|DDR|PIN)([B-D])$', 'GPIO PORT{1}'),
    (r'^(ADMUX|ADCSRA|ADCSRB|ADCL|ADCH|ADC|ADCW|DIDR0)$', 'ADC'),
    (r'^(ACSR|DIDR1)$', 'ANALOG COMPARATOR'),
    (r'^(EICRA|EIMSK|EIFR)$', 'EXTINT'),
    (r'^(PCICR|PCIFR|PCMSK\d)$', 'PCINT'),
    (r'^(WDTCSR|MCUSR)$', 'WDT'),
    (r'^(EEAR|EEARL|EEARH|EEDR|EECR)$', 'EEPROM'),
    (r'^(SPCR|SPSR|SPDR)$', 'SPI'),
    (r'^TW', 'TWI'),
    (r'^(SREG|SP|SPL|SPH|MCUCR|SMCR|PRR|OSCCAL|CLKPR|SPMCSR|GPIOR\d)$', 'CPU'),
)


def snapshot_path(mcu='atmega328p'):
    return os.path.join(HERE, 'registers_%s.json' % mcu)


def parse_dm(text, mcu):
    regs, vecs, libc = {}, {}, ''
    for line in text.splitlines():
        m = _REG.match(line)
        if m:
            regs[m.group(1)] = {'addr': m.group(4).lower(), 'width_bytes': int(m.group(3)) // 8, 'space': m.group(2).lower()}
            continue
        m = _VEC.match(line)
        if m:
            vecs[m.group(1)] = int(m.group(2))
            continue
        m = _LIBC.match(line)
        if m:
            libc = m.group(1)
    return {'schema': 'cmod-registers/1', 'mcu': mcu, 'avr_libc': libc,
            'derived_by': 'avr-gcc -mmcu=%s -E -dM <file including avr/io.h> (board engines seam)' % mcu,
            'dm_sha256': hashlib.sha256(text.encode()).hexdigest(), 'registers': dict(sorted(regs.items())),
            'vectors': dict(sorted(vecs.items(), key=lambda kv: kv[1]))}


def refresh(mcu='atmega328p', run=None):
    """Re-derive the snapshot through the engine (avr-gcc -E -dM) and write it; returns the dict."""
    if run is None:
        from board.custom import engine_run
        run = engine_run.run
    r = run('avr-gcc', ['-mmcu=%s' % mcu, '-E', '-dM', 'io.c'], {'io.c': b'#include <avr/io.h>\n'})
    if not r.get('ok'):
        raise RuntimeError('avr-gcc -E -dM failed: %s' % (r.get('stderr') or '')[-400:])
    snap = parse_dm(r['stdout'], mcu)
    snap['engine'] = {'how': r.get('how', ''), 'where': r.get('where', '')}
    with open(snapshot_path(mcu), 'w') as fh:
        json.dump(snap, fh, indent=1)
        fh.write('\n')
    return snap


_CACHE = {}


def load(mcu='atmega328p'):
    if mcu not in _CACHE:
        p = snapshot_path(mcu)
        _CACHE[mcu] = json.load(open(p)) if os.path.isfile(p) else {'registers': {}, 'vectors': {}, 'avr_libc': '', 'dm_sha256': ''}
    return _CACHE[mcu]


def peripheral(name):
    for rx, tpl in PERIPHERAL_RULES:
        m = re.match(rx, name)
        if m:
            return tpl.format(*m.groups())
    return name
