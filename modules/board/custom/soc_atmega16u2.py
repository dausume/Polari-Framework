"""
@module board.custom.soc_atmega16u2

hsp-0 (HARDWARE_SYSTEM_PINS_PLAN.md L5, his D-hsp-3: "model all 32 contacts with citations, unused ones included"): THE ATmega16U2's I/O PINS as SocPin rows.
READ 2026-10-17 from the cached doc7799 (the file whose sha256 is uno_evidence.U2_SHA, matched; the page footer of the Figure 1-1 page prints
"7799E-AVR-09/2012", the later pages "7799D-AVR-11/10" — one file, two revision strings, said here rather than hidden):

  pins + QFN32 numbers      Figure 1-1 "Pinout", p.2 (QFN32 drawing, RENDERED and read — the number of every leg is read off the figure)
  alternate functions       Table 12-3 Port B p.74, Table 12-6 Port C p.77, Table 12-9 Port D p.79 (verbatim, table order)
  figure-only labels        the Figure 1-1 legs also print AIN2 (PC2), AIN3 (PD4), AIN4 (PD5), AIN5 (PD6), AIN6 (PD7) that the port tables do
                            not list — kept AFTER the table's functions and named in `notes`, never silently merged
23 I/O pins (PB0..PB7, PC0 PC1 PC2 PC4 PC5 PC6 PC7, PD0..PD7 — the 16U2 has no PC3). XTAL1 (leg 1) is not a port pin: it is a PackageContact only.
Not modelled: the registers / peripherals of the 16U2 (no PinFunction rows: the chain walks the ATmega328P only) — the SocPins carry
their functions as text, exactly the atmega328p SocPin shape.
"""
import json

from board.custom import uno_evidence as EV

SOC = EV.U2
FIG = 'Figure 1-1 Pinout (QFN32), p.2'
TABLES = {'B': 'Table 12-3 Port B Pins Alternate Functions, p.74', 'C': 'Table 12-6 Port C Pins Alternate Functions, p.77',
          'D': 'Table 12-9 Port D Pins Alternate Functions, p.79'}

#: pin -> (QFN32 leg number, functions as the port table lists them, labels only the figure prints)
PINS = {
    'PB0': (14, ['SS', 'PCINT0'], []), 'PB1': (15, ['SCLK', 'PCINT1'], []), 'PB2': (16, ['PDI', 'MOSI', 'PCINT2'], []),
    'PB3': (17, ['PDO', 'MISO', 'PCINT3'], []), 'PB4': (18, ['T1', 'PCINT4'], []), 'PB5': (19, ['PCINT5'], []), 'PB6': (20, ['PCINT6'], []),
    'PB7': (21, ['OC0A', 'OC1C', 'PCINT7'], []),
    'PC0': (2, ['XTAL2'], []), 'PC1': (24, ['RESET', 'dW'], []), 'PC2': (5, ['PCINT11'], ['AIN2']), 'PC4': (26, ['PCINT10'], []),
    'PC5': (25, ['PCINT9', 'OC1B'], []), 'PC6': (23, ['PCINT8', 'OC1A'], []), 'PC7': (22, ['ICP1', 'INT4', 'CLKO'], []),
    'PD0': (6, ['INT0', 'OC0B'], []), 'PD1': (7, ['INT1', 'AIN0'], []), 'PD2': (8, ['INT2', 'AIN1', 'RXD1'], []), 'PD3': (9, ['INT3', 'TXD1'], []),
    'PD4': (10, ['INT5'], ['AIN3']), 'PD5': (11, ['XCK1', 'PCINT12'], ['AIN4']), 'PD6': (12, ['INT6', 'RTS'], ['AIN5']),
    'PD7': (13, ['HWB', 'T0', 'INT7', 'CTS'], ['AIN6']),
}


def soc_facts():
    return [EV._f(EV.U2_DOC, EV.U2_REV, EV.U2_URL, 'pin.%s' % p, 'QFN32 leg %d; %s' % (n, '/'.join(fns + extra) or '(no alternate function)'), '',
                  '%s; %s' % (FIG, TABLES[p[1]]),
                  'figure-only labels (not in the port table): %s' % ', '.join(extra) if extra else '', board=SOC)
            for p, (n, fns, extra) in sorted(PINS.items())]


def soc_pins():
    out = []
    for p, (n, fns, extra) in sorted(PINS.items()):
        note = []
        if extra:
            note.append('%s are printed on the figure leg but not in %s' % (', '.join(extra), TABLES[p[1]].split(' Port')[0]))
        if p == 'PC1':
            note.append('Reset / debugWIRE per the RSTDISBL and DWEN fuses (§2.2.12): which one the bench part has is not read')
        if p == 'PC0':
            note.append('XTAL2 "if enabled by Fuse. Also serves as a generic I/O" (§2.2.14): the fuse state of the bench part is not read')
        out.append({'name': '%s:%s' % (SOC, p), 'soc': SOC, 'pin': p, 'port': p[1], 'bit': int(p[2]), 'package_pin': str(n),
                    'functions_json': json.dumps(fns + extra), 'default_function': 'RESET' if p == 'PC1' else '' if p == 'PC0' else 'GPIO',
                    'fact': '%s:pin.%s' % (SOC, p), 'notes': '; '.join(note)})
    return out
