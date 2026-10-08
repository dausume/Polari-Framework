"""
@module board.custom.register_fields_atmega328p

THE CITED BIT FIELDS of the ATmega328P registers the UNO firmware configures (ucd-0a, UNO_CORE_DEMO_PLAN.md §5f/§5g):
the external-interrupt unit (EICRA/EIMSK/EIFR, the pin-change bank PCICR/PCIFR/PCMSK0-2), the I/O ports B and D
(PORTx/DDRx/PINx, MCUCR.PUD) and Timer/Counter2 (TCCR2A/TCCR2B/TIMSK2/TIFR2 — hal_millis's tick). READ on 2026-10-07
from the SAME datasheet file every other board fact cites (Microchip DS40002061B, sha256 b9b9d83c…9320e re-verified),
`pdftotext -layout`, the page numbers below are the PDF's own "DS40002061B-page N" footers:

  EICRA / Tables 13-1, 13-2          §13.2.1 p.80        PORTB / DDRB / PINB          §14.4.2-4 p.100
  EIMSK, EIFR                        §13.2.2-3 p.81      PORTD / DDRD / PIND          §14.4.8-10 p.101
  PCICR, PCIFR                       §13.2.4-5 p.82      configuring / toggling a pin §14.2.1-2 p.85
  PCMSK2 / PCMSK1 / PCMSK0           §13.2.6-8 p.83      MCUCR.PUD                    §14.4.1 p.100
  TCCR2A (COM2A Table 18-2 p.162, COM2B Table 18-5 p.163, WGM Table 18-8 p.164)   §18.11.1 p.162
  TCCR2B (CS2 Table 18-9 p.165-166)  §18.11.2 p.165      TIMSK2 §18.11.6 p.166 · TIFR2 §18.11.7 p.167

Every value's meaning is the datasheet's own sentence (shortened only by dropping "generates an interrupt request" where
the field title already says so is NOT done — the sentence is kept). `access` is typed (RegisterField docstring): rw |
r | w1c (write-one-to-clear) | w-strobe | rw-toggle. Registers NOT in this table have no RegisterField rows yet and say
so in `Register.undetermined` — never guessed. Nothing here is derived from the firmware's C.
"""
from board.custom.uno_facts import M328_DOC, M328_REV, M328_URL

SOC = 'atmega328p'
DOC = (M328_DOC, M328_REV, M328_URL)

#: register → (datasheet title, section+page, reset value as printed on the "Initial Value" line, the data-space address
#: the datasheet prints beside the I/O one when it does — evidence for the io+0x20 rule the chain applies)
REGISTER_CITES = {
    'EICRA': ('External Interrupt Control Register A', '§13.2.1, p.80', '0x00', ''),
    'EIMSK': ('External Interrupt Mask Register', '§13.2.2, p.81', '0x00', '0x3D'),
    'EIFR': ('External Interrupt Flag Register', '§13.2.3, p.81', '0x00', '0x3C'),
    'PCICR': ('Pin Change Interrupt Control Register', '§13.2.4, p.82', '0x00', ''),
    'PCIFR': ('Pin Change Interrupt Flag Register', '§13.2.5, p.82', '0x00', '0x3B'),
    'PCMSK2': ('Pin Change Mask Register 2', '§13.2.6, p.83', '0x00', ''),
    'PCMSK1': ('Pin Change Mask Register 1', '§13.2.7, p.83', '0x00', ''),
    'PCMSK0': ('Pin Change Mask Register 0', '§13.2.8, p.83', '0x00', ''),
    'MCUCR': ('MCU Control Register', '§14.4.1, p.100', '0x00', ''),
    'PORTB': ('The Port B Data Register', '§14.4.2, p.100', '0x00', '0x25'),
    'DDRB': ('The Port B Data Direction Register', '§14.4.3, p.100', '0x00', '0x24'),
    'PINB': ('The Port B Input Pins Address', '§14.4.4, p.100', 'N/A', '0x23'),
    'PORTD': ('The Port D Data Register', '§14.4.8, p.101', '0x00', '0x2B'),
    'DDRD': ('The Port D Data Direction Register', '§14.4.9, p.101', '0x00', '0x2A'),
    'PIND': ('The Port D Input Pins Address', '§14.4.10, p.101', 'N/A', '0x29'),
    'TCCR2A': ('Timer/Counter Control Register A', '§18.11.1, p.162', '0x00', ''),
    'TCCR2B': ('Timer/Counter Control Register B', '§18.11.2, p.165', '0x00', ''),
    'TIMSK2': ('Timer/Counter2 Interrupt Mask Register', '§18.11.6, p.166', '0x00', ''),
    'TIFR2': ('Timer/Counter2 Interrupt Flag Register', '§18.11.7, p.167', '0x00', '0x37'),
}

_ISC = {'00': 'The low level of INT{n} generates an interrupt request.',
        '01': 'Any logical change on INT{n} generates an interrupt request.',
        '10': 'The falling edge of INT{n} generates an interrupt request.',
        '11': 'The rising edge of INT{n} generates an interrupt request.'}
_ENABLE = {'0': 'disabled', '1': 'enabled (when the I-bit in SREG is also set)'}
_FLAG_W1C = {'0': 'no request pending', '1': 'an interrupt request is pending; cleared by hardware when the interrupt routine is executed, '
                                             'or by writing a logical one to it'}
_PCMSK = {'0': 'pin change interrupt on this pin disabled', '1': 'pin change interrupt on this pin enabled (with the bank\'s PCIE bit in PCICR)'}
_DD = {'0': 'the pin is configured as an input pin', '1': 'the pin is configured as an output pin'}
_PORT = {'0': 'input: pull-up off · output: the pin is driven low', '1': 'input: the pull-up resistor is activated · output: the pin is driven high'}
_PIN = {'read': 'the logic level on the pin (independent of DDxn)', 'write 1': 'toggles the value of PORTxn (§14.2.2), independent of DDRxn'}
_COM_A = {'00': 'Normal port operation, OC2A disconnected (Table 18-2, non-PWM mode; PWM-mode meanings in Tables 18-3/18-4 not captured here)',
          '01': 'Toggle OC2A on Compare Match', '10': 'Clear OC2A on Compare Match', '11': 'Set OC2A on Compare Match'}
_COM_B = {'00': 'Normal port operation, OC2B disconnected (Table 18-5, non-PWM mode; PWM-mode meanings in Tables 18-6/18-7 not captured here)',
          '01': 'Toggle OC2B on Compare Match', '10': 'Clear OC2B on Compare Match', '11': 'Set OC2B on Compare Match'}
_WGM = {'000': 'mode 0 Normal, TOP 0xFF', '001': 'mode 1 PWM, Phase Correct, TOP 0xFF', '010': 'mode 2 CTC, TOP OCRA',
        '011': 'mode 3 Fast PWM, TOP 0xFF', '100': 'mode 4 reserved', '101': 'mode 5 PWM, Phase Correct, TOP OCRA',
        '110': 'mode 6 reserved', '111': 'mode 7 Fast PWM, TOP OCRA'}
_CS2 = {'000': 'No clock source (Timer/Counter stopped).', '001': 'clkT2S/(No prescaling)', '010': 'clkT2S/8 (From prescaler)',
        '011': 'clkT2S/32 (From prescaler)', '100': 'clkT2S/64 (From prescaler)', '101': 'clkT2S/128 (From prescaler)',
        '110': 'clkT2S/256 (From prescaler)', '111': 'clkT2S/1024 (From prescaler)'}


def _f(register, field, hi, lo, access, reset, description, values, where, signal='', pin='', notes=''):
    return {'register': register, 'field': field, 'bit_hi': hi, 'bit_lo': lo, 'width': hi - lo + 1, 'access': access,
            'reset_value': reset, 'description': description, 'values': values, 'page_table': where,
            'affects_signal': signal, 'affects_pin': pin, 'notes': notes}


def _port_bits(port, port_reg, dd_reg, pin_reg, where):
    out = []
    for n in range(8):
        pin = 'P%s%d' % (port, n)
        out.append(_f(port_reg, '%s%d' % (port_reg, n), n, n, 'rw', '0', 'Port %s data bit %d (PORT%s%d)' % (port, n, port, n), _PORT,
                      where[0], pin=pin))
        out.append(_f(dd_reg, 'DD%s%d' % (port, n), n, n, 'rw', '0', 'Port %s data direction bit %d (DD%s%d)' % (port, n, port, n), _DD,
                      where[1], pin=pin))
        out.append(_f(pin_reg, '%s%d' % (pin_reg, n), n, n, 'rw-toggle', 'N/A', 'Port %s input pin %d (PIN%s%d)' % (port, n, port, n), _PIN,
                      where[2], pin=pin, notes='writing a logic one toggles PORT%s%d (§14.2.2 p.85)' % (port, n)))
    return out


#: the cited fields, in datasheet order
FIELDS = [
    # EXINT — §13.2
    _f('EICRA', 'ISC1', 3, 2, 'rw', '0', 'Interrupt Sense Control 1 Bit 1 and Bit 0 (ISC11, ISC10)', {k: v.format(n=1) for k, v in _ISC.items()},
       '§13.2.1 EICRA, Table 13-1 Interrupt 1 Sense Control, p.80', signal='INT1'),
    _f('EICRA', 'ISC0', 1, 0, 'rw', '0', 'Interrupt Sense Control 0 Bit 1 and Bit 0 (ISC01, ISC00)', {k: v.format(n=0) for k, v in _ISC.items()},
       '§13.2.1 EICRA, Table 13-2 Interrupt 0 Sense Control, p.80', signal='INT0'),
    _f('EIMSK', 'INT1', 1, 1, 'rw', '0', 'External Interrupt Request 1 Enable', _ENABLE, '§13.2.2 EIMSK, p.81', signal='INT1'),
    _f('EIMSK', 'INT0', 0, 0, 'rw', '0', 'External Interrupt Request 0 Enable', _ENABLE, '§13.2.2 EIMSK, p.81', signal='INT0'),
    _f('EIFR', 'INTF1', 1, 1, 'w1c', '0', 'External Interrupt Flag 1', _FLAG_W1C, '§13.2.3 EIFR, p.81', signal='INT1',
       notes='always cleared when INT1 is configured as a level interrupt'),
    _f('EIFR', 'INTF0', 0, 0, 'w1c', '0', 'External Interrupt Flag 0', _FLAG_W1C, '§13.2.3 EIFR, p.81', signal='INT0',
       notes='always cleared when INT0 is configured as a level interrupt'),
    _f('PCICR', 'PCIE2', 2, 2, 'rw', '0', 'Pin Change Interrupt Enable 2 (PCINT[23:16], vector PCI2)', _ENABLE, '§13.2.4 PCICR, p.82'),
    _f('PCICR', 'PCIE1', 1, 1, 'rw', '0', 'Pin Change Interrupt Enable 1 (PCINT[14:8], vector PCI1)', _ENABLE, '§13.2.4 PCICR, p.82'),
    _f('PCICR', 'PCIE0', 0, 0, 'rw', '0', 'Pin Change Interrupt Enable 0 (PCINT[7:0], vector PCI0)', _ENABLE, '§13.2.4 PCICR, p.82'),
    _f('PCIFR', 'PCIF2', 2, 2, 'w1c', '0', 'Pin Change Interrupt Flag 2', _FLAG_W1C, '§13.2.5 PCIFR, p.82'),
    _f('PCIFR', 'PCIF1', 1, 1, 'w1c', '0', 'Pin Change Interrupt Flag 1', _FLAG_W1C, '§13.2.5 PCIFR, p.82'),
    _f('PCIFR', 'PCIF0', 0, 0, 'w1c', '0', 'Pin Change Interrupt Flag 0', _FLAG_W1C, '§13.2.5 PCIFR, p.83'),
] + [
    _f('PCMSK2', 'PCINT%d' % (16 + n), n, n, 'rw', '0', 'Pin Change Enable Mask %d' % (16 + n), _PCMSK, '§13.2.6 PCMSK2, p.83',
       signal='PCINT%d' % (16 + n), pin='PD%d' % n) for n in range(8)
] + [
    _f('PCMSK1', 'PCINT%d' % (8 + n), n, n, 'rw', '0', 'Pin Change Enable Mask %d' % (8 + n), _PCMSK, '§13.2.7 PCMSK1, p.83',
       signal='PCINT%d' % (8 + n), pin='PC%d' % n) for n in range(7)
] + [
    _f('PCMSK0', 'PCINT%d' % n, n, n, 'rw', '0', 'Pin Change Enable Mask %d' % n, _PCMSK, '§13.2.8 PCMSK0, p.83',
       signal='PCINT%d' % n, pin='PB%d' % n) for n in range(8)
] + [
    # I/O ports — §14
    _f('MCUCR', 'PUD', 4, 4, 'rw', '0', 'Pull-up Disable', {'0': 'pull-ups as PORTxn/DDxn select', '1': 'the pull-ups in the I/O ports are disabled '
       'even if the DDxn and PORTxn Registers are configured to enable them'}, '§14.4.1 MCUCR, p.100; §14.1 p.84'),
] + _port_bits('B', 'PORTB', 'DDRB', 'PINB', ('§14.4.2 PORTB, p.100; §14.2.1 p.85', '§14.4.3 DDRB, p.100; §14.2.1 p.85', '§14.4.4 PINB, p.100; §14.2.2 p.85')) \
  + _port_bits('D', 'PORTD', 'DDRD', 'PIND', ('§14.4.8 PORTD, p.101; §14.2.1 p.85', '§14.4.9 DDRD, p.101; §14.2.1 p.85', '§14.4.10 PIND, p.101; §14.2.2 p.85')) + [
    # Timer/Counter2 — §18.11
    _f('TCCR2A', 'COM2A', 7, 6, 'rw', '0', 'Compare Match Output A Mode (COM2A1:0)', _COM_A, '§18.11.1 TCCR2A, Table 18-2, p.162', signal='OC2A'),
    _f('TCCR2A', 'COM2B', 5, 4, 'rw', '0', 'Compare Match Output B Mode (COM2B1:0)', _COM_B, '§18.11.1 TCCR2A, Table 18-5, p.163', signal='OC2B'),
    _f('TCCR2A', 'WGM2_10', 1, 0, 'rw', '0', 'Waveform Generation Mode bits 1:0 (WGM21, WGM20) — with TCCR2B.WGM22 the 3-bit mode',
       {k[1:]: 'with WGM22=%s: %s' % (k[0], v) for k, v in _WGM.items()}, '§18.11.1 TCCR2A, Table 18-8, p.164'),
    _f('TCCR2B', 'FOC2A', 7, 7, 'w-strobe', '0', 'Force Output Compare A', {'1': 'an immediate Compare Match is forced on the Waveform Generation '
       'unit (non-PWM modes only); always read as zero'}, '§18.11.2 TCCR2B, p.165', signal='OC2A'),
    _f('TCCR2B', 'FOC2B', 6, 6, 'w-strobe', '0', 'Force Output Compare B', {'1': 'an immediate Compare Match is forced on the Waveform Generation '
       'unit (non-PWM modes only); always read as zero'}, '§18.11.2 TCCR2B, p.165', signal='OC2B'),
    _f('TCCR2B', 'WGM22', 3, 3, 'rw', '0', 'Waveform Generation Mode bit 2 — with TCCR2A.WGM21:20 the 3-bit mode',
       {'0': 'modes 0-3 (see TCCR2A.WGM2_10)', '1': 'modes 4-7 (see TCCR2A.WGM2_10)'}, '§18.11.2 TCCR2B, Table 18-8, p.164-165'),
    _f('TCCR2B', 'CS2', 2, 0, 'rw', '0', 'Clock Select (CS22:0)', _CS2, '§18.11.2 TCCR2B, Table 18-9, p.165-166'),
    _f('TIMSK2', 'OCIE2B', 2, 2, 'rw', '0', 'Timer/Counter2 Output Compare Match B Interrupt Enable', _ENABLE, '§18.11.6 TIMSK2, p.166', signal='OC2B'),
    _f('TIMSK2', 'OCIE2A', 1, 1, 'rw', '0', 'Timer/Counter2 Output Compare Match A Interrupt Enable', _ENABLE, '§18.11.6 TIMSK2, p.166-167', signal='OC2A'),
    _f('TIMSK2', 'TOIE2', 0, 0, 'rw', '0', 'Timer/Counter2 Overflow Interrupt Enable', _ENABLE, '§18.11.6 TIMSK2, p.167'),
    _f('TIFR2', 'OCF2B', 2, 2, 'w1c', '0', 'Output Compare Flag 2 B', _FLAG_W1C, '§18.11.7 TIFR2, p.167', signal='OC2B'),
    _f('TIFR2', 'OCF2A', 1, 1, 'w1c', '0', 'Output Compare Flag 2 A', _FLAG_W1C, '§18.11.7 TIFR2, p.167', signal='OC2A'),
    _f('TIFR2', 'TOV2', 0, 0, 'w1c', '0', 'Timer/Counter2 Overflow Flag', _FLAG_W1C, '§18.11.7 TIFR2, p.167'),
]

ACCESS_KINDS = ('rw', 'r', 'w1c', 'w-strobe', 'rw-toggle')
