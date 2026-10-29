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
    # rm-2a: reset values from each register's printed "Initial Value" row (UCSR0A 0 0 1 0 0 0 0 0 = 0x20; UCSR0C 0 0 0 0 0 1 1 0 = 0x06)
    'SREG': ('AVR Status Register', '§7.3.1, p.20', '0x00', '0x5F'),
    'CLKPR': ('Clock Prescale Register', '§9.12.2, p.46', 'see bit description (CLKPS from the CKDIV8 fuse)', ''),
    'PRR': ('Power Reduction Register', '§10.11.3, p.54', '0x00', ''),
    'MCUSR': ('MCU Status Register', '§11.9.1, p.63', 'see bit description (the flags of the reset source)', '0x54'),
    'WDTCSR': ('Watchdog Timer Control Register', '§11.9.2, p.63', '0x00 except WDE = X', ''),
    'UDR0': ('USART I/O Data Register 0', '§20.11.1, p.200', '0x00', ''),
    'UCSR0A': ('USART Control and Status Register 0 A', '§20.11.2, p.200', '0x20', ''),
    'UCSR0B': ('USART Control and Status Register 0 B', '§20.11.3, p.201', '0x00', ''),
    'UCSR0C': ('USART Control and Status Register 0 C', '§20.11.4, p.202', '0x06', ''),
    'UBRR0H': ('USART Baud Rate Register 0 High', '§20.11.5, p.204', '0x00', ''),
    'UBRR0L': ('USART Baud Rate Register 0 Low', '§20.11.5, p.204', '0x00', ''),
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

# rm-2a value tables (the datasheet's own words)
_CLKPS = {'%04d' % int(bin(n)[2:]): 'division factor %d' % (1 << n) for n in range(9)}
_CLKPS.update({'%04d' % int(bin(n)[2:]): 'Reserved' for n in range(9, 16)})
_WDP = {'000': '2K (2048) cycles, 16 ms typical at 5 V (WDP3=0) / 512K cycles, 4.0 s (WDP3=1)', '001': '4K (4096) cycles, 32 ms (WDP3=0) / 1024K cycles, 8.0 s (WDP3=1)',
        '010': '8K (8192) cycles, 64 ms (WDP3=0) / reserved (WDP3=1)', '011': '16K (16384) cycles, 0.125 s (WDP3=0) / reserved (WDP3=1)',
        '100': '32K (32768) cycles, 0.25 s (WDP3=0) / reserved (WDP3=1)', '101': '64K (65536) cycles, 0.5 s (WDP3=0) / reserved (WDP3=1)',
        '110': '128K (131072) cycles, 1.0 s (WDP3=0) / reserved (WDP3=1)', '111': '256K (262144) cycles, 2.0 s (WDP3=0) / reserved (WDP3=1)'}
_WDT_MODE = {'WDE=0 WDIE=0': 'Stopped (WDTON unprogrammed): no action on time-out', 'WDE=0 WDIE=1': 'Interrupt Mode: interrupt on time-out',
             'WDE=1 WDIE=0': 'System Reset Mode: reset on time-out', 'WDE=1 WDIE=1': 'Interrupt and System Reset Mode: interrupt, then System Reset Mode',
             'WDTON programmed': 'System Reset Mode whatever WDE / WDIE say'}


def _PR(module):
    return {'0': '%s runs' % module, '1': 'shuts down the %s by stopping its clock' % module}


def _RF(event, also):
    return {'1': 'set if %s occurs' % event, '0': 'cleared by writing a logic zero%s' % (' (or by a Power-on Reset)' if also else ' only')}


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
    # rm-2a (REGISTER_MAPPING_PLAN D-rm-4): the UNO's owed fields - USART0 (§20.11), CLKPR (§9.12.2), PRR (§10.11.3), MCUSR / WDTCSR (§11.9), SREG (§7.3.1);
    # read 2026-10-29 from the same file (sha256 b9b9d83c…9320e re-verified), pages from its own footers
    _f('SREG', 'I', 7, 7, 'rw', '0', 'Global Interrupt Enable', {'0': 'none of the interrupts are enabled, independent of the individual interrupt enable settings',
       '1': 'interrupts enabled; the individual enables are in their own control registers'}, '§7.3.1 SREG, p.20',
       notes='cleared by hardware after an interrupt has occurred, set by RETI; SEI / CLI set and clear it (the masked windows of ipb-7)'),
    _f('SREG', 'T', 6, 6, 'rw', '0', 'Bit Copy Storage', {'any': 'source / destination of the BLD and BST instructions'}, '§7.3.1 SREG, p.20'),
    _f('SREG', 'H', 5, 5, 'rw', '0', 'Half Carry Flag', {'1': 'a Half Carry in some arithmetic operations (useful in BCD arithmetic)'}, '§7.3.1 SREG, p.20'),
    _f('SREG', 'S', 4, 4, 'rw', '0', 'Sign Bit, S = N xor V', {'any': 'always an exclusive or between the Negative Flag N and the Two\'s Complement Overflow Flag V'},
       '§7.3.1 SREG, p.20'),
    _f('SREG', 'V', 3, 3, 'rw', '0', 'Two\'s Complement Overflow Flag', {'1': 'two\'s complement overflow'}, '§7.3.1 SREG, p.20'),
    _f('SREG', 'N', 2, 2, 'rw', '0', 'Negative Flag', {'1': 'a negative result in an arithmetic or logic operation'}, '§7.3.1 SREG, p.20'),
    _f('SREG', 'Z', 1, 1, 'rw', '0', 'Zero Flag', {'1': 'a zero result in an arithmetic or logic operation'}, '§7.3.1 SREG, p.20'),
    _f('SREG', 'C', 0, 0, 'rw', '0', 'Carry Flag', {'1': 'a carry in an arithmetic or logic operation'}, '§7.3.1 SREG, p.20'),
    _f('CLKPR', 'CLKPCE', 7, 7, 'rw', '0', 'Clock Prescaler Change Enable', {'1': 'enables a change of the CLKPS bits; only updated when the other bits are '
       'written to zero at the same time; cleared by hardware four cycles after it is written or when CLKPS is written'}, '§9.12.2 CLKPR, p.46'),
    _f('CLKPR', 'CLKPS', 3, 0, 'rw', 'fuse', 'Clock Prescaler Select Bits 3 - 0 (division factor, clock source -> system clock)', _CLKPS, '§9.12.2 CLKPR, Table 9-17, p.46-47',
       notes='reset value from the CKDIV8 fuse: unprogrammed -> 0000, programmed -> 0011 (divide by 8); shipped programmed'),
    _f('PRR', 'PRTWI', 7, 7, 'rw', '0', 'Power Reduction TWI', _PR('TWI'), '§10.11.3 PRR, p.54'),
    _f('PRR', 'PRTIM2', 6, 6, 'rw', '0', 'Power Reduction Timer/Counter2', _PR('Timer/Counter2 (synchronous mode, AS2 = 0)'), '§10.11.3 PRR, p.54'),
    _f('PRR', 'PRTIM0', 5, 5, 'rw', '0', 'Power Reduction Timer/Counter0', _PR('Timer/Counter0'), '§10.11.3 PRR, p.54'),
    _f('PRR', 'PRTIM1', 3, 3, 'rw', '0', 'Power Reduction Timer/Counter1', _PR('Timer/Counter1'), '§10.11.3 PRR, p.54'),
    _f('PRR', 'PRSPI', 2, 2, 'rw', '0', 'Power Reduction Serial Peripheral Interface', _PR('SPI'), '§10.11.3 PRR, p.55',
       notes='with debugWIRE, this bit should not be written to one'),
    _f('PRR', 'PRUSART0', 1, 1, 'rw', '0', 'Power Reduction USART0', _PR('USART0'), '§10.11.3 PRR, p.55',
       notes='the USART should be re-initialized when woken'),
    _f('PRR', 'PRADC', 0, 0, 'rw', '0', 'Power Reduction ADC', _PR('ADC (it must be disabled first)'), '§10.11.3 PRR, p.55'),
    _f('MCUSR', 'WDRF', 3, 3, 'w0c', 'reset source', 'Watchdog System Reset Flag', _RF('a Watchdog System Reset', 'a Power-on Reset'), '§11.9.1 MCUSR, p.63',
       notes='forces WDTCSR.WDE set while it is set (§11.9.2): clear WDRF first'),
    _f('MCUSR', 'BORF', 2, 2, 'w0c', 'reset source', 'Brown-out Reset Flag', _RF('a Brown-out Reset', 'a Power-on Reset'), '§11.9.1 MCUSR, p.63'),
    _f('MCUSR', 'EXTRF', 1, 1, 'w0c', 'reset source', 'External Reset Flag', _RF('an External Reset', 'a Power-on Reset'), '§11.9.1 MCUSR, p.63',
       notes='the UNO\'s DTR auto-reset pulls RESET low: an external reset (lifecycle_uno)'),
    _f('MCUSR', 'PORF', 0, 0, 'w0c', 'reset source', 'Power-on Reset Flag', _RF('a Power-on Reset', ''), '§11.9.1 MCUSR, p.63',
       notes='read and then reset MCUSR as early as possible in the program to identify the reset source'),
    _f('WDTCSR', 'WDIF', 7, 7, 'w1c', '0', 'Watchdog Interrupt Flag', {'1': 'a time-out occurred with the Watchdog Timer configured for interrupt; cleared by '
       'hardware when the vector executes, or by writing a logic one'}, '§11.9.2 WDTCSR, p.63'),
    _f('WDTCSR', 'WDIE', 6, 6, 'rw', '0', 'Watchdog Interrupt Enable', _WDT_MODE, '§11.9.2 WDTCSR, Table 11-1, p.63-64'),
    _f('WDTCSR', 'WDP3', 5, 5, 'rw', '0', 'Watchdog Timer Prescaler 3 - with WDP2:0 the 4-bit prescale', {'0': 'WDP 0xxx (see WDP2_0)', '1': 'WDP 1xxx (see WDP2_0)'},
       '§11.9.2 WDTCSR, Table 11-2, p.64'),
    _f('WDTCSR', 'WDCE', 4, 4, 'rw', '0', 'Watchdog Change Enable', {'1': 'needed in the timed sequence that clears WDE and / or changes the prescaler; hardware '
       'clears it after four clock cycles'}, '§11.9.2 WDTCSR, p.64'),
    _f('WDTCSR', 'WDE', 3, 3, 'rw', 'X', 'Watchdog System Reset Enable', _WDT_MODE, '§11.9.2 WDTCSR, Table 11-1, p.64',
       notes='overridden by MCUSR.WDRF: always set while WDRF is set (initial value X)'),
    _f('WDTCSR', 'WDP2_0', 2, 0, 'rw', '0', 'Watchdog Timer Prescaler 2, 1, 0 - with WDP3 the 4-bit prescale', _WDP, '§11.9.2 WDTCSR, Table 11-2, p.64'),
    _f('UDR0', 'UDR0', 7, 0, 'fifo', '0', 'USART I/O Data: RXB (receive buffer) on read, TXB (transmit buffer) on write', {'read': 'the Receive Data Buffer (a two-level FIFO)',
       'write': 'the Transmit Data Buffer - ignored unless UCSR0A.UDRE0 is set'}, '§20.11.1 UDRn, p.200',
       notes='do not use read-modify-write (SBI / CBI) on it: any access moves the receive FIFO'),
    _f('UCSR0A', 'RXC0', 7, 7, 'r', '0', 'USART Receive Complete', {'1': 'unread data in the receive buffer', '0': 'the receive buffer is empty (flushed when the receiver is '
       'disabled)'}, '§20.11.2 UCSRnA, p.200'),
    _f('UCSR0A', 'TXC0', 6, 6, 'w1c', '0', 'USART Transmit Complete', {'1': 'the whole frame has shifted out and the transmit buffer is empty; cleared when the '
       'transmit-complete interrupt executes, or by writing a one'}, '§20.11.2 UCSRnA, p.200'),
    _f('UCSR0A', 'UDRE0', 5, 5, 'r', '1', 'USART Data Register Empty', {'1': 'the transmit buffer is empty, ready to be written', '0': 'the transmit buffer is full'},
       '§20.11.2 UCSRnA, p.200', notes='set after a reset: the transmitter is ready'),
    _f('UCSR0A', 'FE0', 4, 4, 'r', '0', 'Frame Error', {'1': 'the next character in the receive buffer had its first stop bit zero'}, '§20.11.2 UCSRnA, p.201', notes='valid until UDR0 is read; always write it zero'),
    _f('UCSR0A', 'DOR0', 3, 3, 'r', '0', 'Data OverRun', {'1': 'the receive buffer was full (two characters), one more waited in the shift register and a new start bit '
       'came'}, '§20.11.2 UCSRnA, p.201', notes='valid until UDR0 is read; always write it zero'),
    _f('UCSR0A', 'UPE0', 2, 2, 'r', '0', 'USART Parity Error', {'1': 'the next character in the receive buffer had a parity error (parity checking on)'},
       '§20.11.2 UCSRnA, p.201', notes='valid until UDR0 is read; always write it zero'),
    _f('UCSR0A', 'U2X0', 1, 1, 'rw', '0', 'Double the USART Transmission Speed', {'0': 'baud divisor 16', '1': 'baud divisor 8: the asynchronous rate doubles'},
       '§20.11.2 UCSRnA, p.201', notes='asynchronous only; write zero in synchronous mode. The UNO HAL runs 115200 Bd with U2X0 = 1 (UBRR0 16, Table 20-7 p.199)'),
    _f('UCSR0A', 'MPCM0', 0, 0, 'rw', '0', 'Multi-processor Communication Mode', {'1': 'incoming frames without address information are ignored by the receiver'},
       '§20.11.2 UCSRnA, p.201'),
    _f('UCSR0B', 'RXCIE0', 7, 7, 'rw', '0', 'RX Complete Interrupt Enable', _ENABLE, '§20.11.3 UCSRnB, p.201',
       notes='the USART_RX vector (the HAL\'s ring buffer ISR) runs when this, SREG.I and RXC0 are set'),
    _f('UCSR0B', 'TXCIE0', 6, 6, 'rw', '0', 'TX Complete Interrupt Enable', _ENABLE, '§20.11.3 UCSRnB, p.201'),
    _f('UCSR0B', 'UDRIE0', 5, 5, 'rw', '0', 'USART Data Register Empty Interrupt Enable', _ENABLE, '§20.11.3 UCSRnB, p.202'),
    _f('UCSR0B', 'RXEN0', 4, 4, 'rw', '0', 'Receiver Enable', {'0': 'receiver off (disabling flushes the receive buffer)', '1': 'receiver on: it overrides normal port '
       'operation of the RxD pin'}, '§20.11.3 UCSRnB, p.202', signal='RXD', pin='PD0'),
    _f('UCSR0B', 'TXEN0', 3, 3, 'rw', '0', 'Transmitter Enable', {'0': 'transmitter off once pending transmissions complete; it stops overriding the TxD pin',
       '1': 'transmitter on: it overrides normal port operation of the TxD pin'}, '§20.11.3 UCSRnB, p.202', signal='TXD', pin='PD1'),
    _f('UCSR0B', 'UCSZ02', 2, 2, 'rw', '0', 'Character Size bit 2 - with UCSR0C.UCSZ01:00 the 3-bit size', {'0': 'sizes 5-8 bit (see UCSR0C.UCSZ0)', '1': '9-bit (with UCSZ01:00 = 11)'},
       '§20.11.3 UCSRnB, Table 20-11, p.202-203'),
    _f('UCSR0B', 'RXB80', 1, 1, 'r', '0', 'Receive Data Bit 8', {'any': 'the ninth data bit of a received 9-bit character; read before UDR0'}, '§20.11.3 UCSRnB, p.202'),
    _f('UCSR0B', 'TXB80', 0, 0, 'rw', '0', 'Transmit Data Bit 8', {'any': 'the ninth data bit of a 9-bit character to send; write before UDR0'}, '§20.11.3 UCSRnB, p.202'),
    _f('UCSR0C', 'UMSEL0', 7, 6, 'rw', '0', 'USART Mode Select (UMSEL01:00)', {'00': 'Asynchronous USART', '01': 'Synchronous USART', '10': '(Reserved)',
       '11': 'Master SPI (MSPIM)'}, '§20.11.4 UCSRnC, Table 20-8, p.202'),
    _f('UCSR0C', 'UPM0', 5, 4, 'rw', '0', 'Parity Mode (UPM01:00)', {'00': 'Disabled', '01': 'Reserved', '10': 'Enabled, Even Parity', '11': 'Enabled, Odd Parity'},
       '§20.11.4 UCSRnC, Table 20-9, p.203'),
    _f('UCSR0C', 'USBS0', 3, 3, 'rw', '0', 'Stop Bit Select', {'0': '1-bit', '1': '2-bit (the receiver ignores this setting)'}, '§20.11.4 UCSRnC, Table 20-10, p.203'),
    _f('UCSR0C', 'UCSZ0', 2, 1, 'rw', '3', 'Character Size (UCSZ01:00) - with UCSR0B.UCSZ02 the 3-bit size', {'00': '5-bit (UCSZ02=0)', '01': '6-bit (UCSZ02=0)',
       '10': '7-bit (UCSZ02=0)', '11': '8-bit (UCSZ02=0) / 9-bit (UCSZ02=1)'}, '§20.11.4 UCSRnC, Table 20-11, p.203', notes='initial value 11: 8-bit frames'),
    _f('UCSR0C', 'UCPOL0', 0, 0, 'rw', '0', 'Clock Polarity', {'0': 'TxD changes on the rising XCK edge, RxD sampled on the falling edge', '1': 'TxD changes on the '
       'falling XCK edge, RxD sampled on the rising edge'}, '§20.11.4 UCSRnC, Table 20-12, p.203-204', notes='synchronous mode only; write zero in asynchronous mode'),
    _f('UBRR0H', 'UBRR0_11_8', 3, 0, 'rw', '0', 'USART Baud Rate Register bits 11:8 (the four most significant bits)', {'any': 'with UBRR0L the 12-bit baud rate setting'},
       '§20.11.5 UBRRnL and UBRRnH, p.204', notes='bits 15:12 reserved: write zero when UBRR0H is written'),
    _f('UBRR0L', 'UBRR0_7_0', 7, 0, 'rw', '0', 'USART Baud Rate Register bits 7:0', {'any': 'with UBRR0H the 12-bit baud rate setting; writing UBRR0L updates the prescaler '
       'at once'}, '§20.11.5 UBRRnL and UBRRnH, p.204', notes='changing the baud rate corrupts ongoing transmissions'),
]

#: rm-2a: the access words are rows of their own (board.custom.register_access.ACCESS_KINDS -> RegisterAccessKind): what a read and a write do, the UVM / SVD names
from board.custom.register_access import WORDS as ACCESS_KINDS  # noqa: E402
