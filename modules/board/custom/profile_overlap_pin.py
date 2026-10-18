"""
@module board.custom.profile_overlap_pin

pp-1: the SAME-PIN rules - two pin profiles that would sit on ONE physical pin of the ATmega328P. One function, `rule(a, b)`, answers
for a pair of kinds (any order) with an Outcome: verdict (compatible | exclusive | conditional | undetermined), mode (exclusive |
shared-read | shared-config | time-multiplexed-later), the rule's id, the plain-words reason, the condition (conditional only) and the
CITES keys it stands on. The model is the datasheet's own: Figure 14-2 (the general pin: DDxn, PORTxn, PINxn) and Figure 14-5 (an
alternate function OVERRIDES those signals through PUOE/DDOE/PVOE ...; the input buffer and its PINxn read stay unless an override
says otherwise).

Order of reasoning: (1) no pin offers both kinds -> exclusive (the pin tables); (2) the transport reservation; (3) the alternate
function that owns the pin's direction/value (pwm, uart, spi, i2c) against a plain output or another alternate function; (4) what
may only OBSERVE the pin (digital-in, interrupts, ADC, comparator, clock-in); (5) the rest.
"""
from collections import namedtuple

from board.custom import profile_overlap_kinds as K

Outcome = namedtuple('Outcome', 'verdict mode rule reason condition cites')

OVERRIDERS = ('pwm-out', 'uart-rx', 'uart-tx', 'spi-sck', 'spi-mosi', 'spi-miso', 'i2c-sda', 'i2c-scl')
OBSERVERS = ('digital-in', 'interrupt-in', 'pin-change-in')
#: what ends the override (the alternate function is disabled), per overrider - the way back to a plain pin
_OWN = {'pwm-out': ('oc0', 'oc1', 'oc2'), 'uart-rx': ('usart-rx', 'tbl-d-uart'), 'uart-tx': ('usart-tx', 'tbl-d-uart'),
        'spi-sck': ('spi-override', 'spi-pins'), 'spi-mosi': ('spi-override', 'spi-pins'), 'spi-miso': ('spi-override', 'spi-pins'),
        'i2c-sda': ('alt-c-twi', 'tbl-c-twi'), 'i2c-scl': ('alt-c-twi', 'tbl-c-twi')}
_OFF = {'pwm-out': ('oc0',), 'uart-rx': ('usart-rx-off',), 'uart-tx': ('usart-tx-off',), 'spi-sck': ('spi-override',),
        'spi-mosi': ('spi-override',), 'spi-miso': ('spi-override',), 'i2c-sda': ('tbl-c-twi',), 'i2c-scl': ('tbl-c-twi',)}
_OFF_WORDS = {'pwm-out': 'the Compare Output bits (COMnx1:0) are cleared', 'uart-rx': 'the receiver is disabled (RXEN0 = 0)',
              'uart-tx': 'the transmitter is disabled (TXEN0 = 0)', 'spi-sck': 'the SPI is disabled (SPE = 0)', 'spi-mosi': 'the SPI is disabled (SPE = 0)',
              'spi-miso': 'the SPI is disabled (SPE = 0)', 'i2c-sda': 'the TWI is disabled (TWEN = 0)', 'i2c-scl': 'the TWI is disabled (TWEN = 0)'}


def _o(verdict, mode, rule, reason, cites, cond=''):
    return Outcome(verdict, mode, 'pin.' + rule, reason, cond, tuple(cites))


def _no_common(a, b):
    return _o('exclusive', 'exclusive', 'no-common-pin',
              'no ATmega328P pin offers both %s and %s, so one pin cannot serve the two' % (a, b), ('pin-tables', 'compat'))


def rule(a, b):
    """Outcome for two kinds on ONE pin (symmetric: rule(a, b) == rule(b, a))."""
    if K.KINDS.index(a) > K.KINDS.index(b):
        a, b = b, a
    if not K.common_pins(a, b):
        return _no_common(a, b)
    s = {a, b}
    # ---- the transport reservation: the host link owns the line (lifecycle), whatever the datasheet would allow
    if 'transport' in s:
        other = b if a == 'transport' else a
        if other == 'transport':
            return _o('exclusive', 'exclusive', 'transport-owns', 'one host link owns the RXD/TXD lines; a second reservation of the same pin is the same claim twice',
                      ('lifecycle',))
        if other in ('uart-rx', 'uart-tx'):
            return _o('conditional', 'shared-config', 'transport-is-uart',
                      'the host link IS a use of the USART line; a uart profile on that pin is the same thing only when it is the transport\'s own role',
                      ('lifecycle', 'usart-rx', 'usart-tx'), 'the uart profile belongs to the transport\'s own role (the host link), not another role')
        return _o('exclusive', 'time-multiplexed-later', 'transport-reserved',
                  'the board reserves the transport pins for the USB-serial link: always in the bootloader phase, and in init/runtime while transport=usb-serial; '
                  'the reservation is released only when the link is not in use',
                  ('lifecycle', 'usart-rx-off', 'usart-tx-off'))
    # ---- two plain outputs
    if a == b == 'digital-out':
        return _o('exclusive', 'exclusive', 'one-output', 'one pin has one direction bit and one output bit (DDxn, PORTxn); two roles cannot both set the level',
                  ('pin-config', 'pin-table'))
    # ---- an overrider (the peripheral owns direction/value) against another overrider / a plain output
    if a in OVERRIDERS and b in OVERRIDERS:
        return _o('exclusive', 'time-multiplexed-later' if a != b else 'exclusive', 'alt-vs-alt',
                  'each alternate function overrides the pin\'s direction/value signals (Figure 14-5); two enabled at once would both drive the same override, so only one can own the pin '
                  '(it can be handed over when the first peripheral is disabled: %s)' % _OFF_WORDS[a], ('alt-override', 'alt-signals') + _OWN[a] + _OWN[b] + _OFF[a])
    if (a == 'digital-out' and b in OVERRIDERS) or (b == 'digital-out' and a in OVERRIDERS):
        ov = b if a == 'digital-out' else a
        return _o('exclusive', 'time-multiplexed-later', 'alt-overrides-port',
                  'while the %s function is enabled it overrides the PORT/DDR control of the pin (datasheet section 14.3), so a plain output cannot also set the level; '
                  'the pin is a plain output again once %s' % (ov, _OFF_WORDS[ov]), ('alt-override', 'alt-signals') + _OWN[ov] + _OFF[ov])
    # ---- SPI slave select: a plain pin in master mode, forced input in slave mode
    if 'spi-ss' in s:
        other = b if a == 'spi-ss' else a
        if other == 'spi-ss':
            return _o('exclusive', 'exclusive', 'one-function', 'one SS pin is one SPI select line; two roles cannot both own it', ('spi-pins', 'spi-ss-master'))
        if other == 'digital-out':
            return _o('conditional', 'shared-config', 'ss-master-gpio',
                      'in master mode SS is a general output that does not affect the SPI, so it is just a chip-select line a task sets; in slave mode it is an input (Table 19-1)',
                      ('spi-ss-master', 'spi-pins'), 'the SPI is a master and the pin stays an output (a low input would turn the master into a slave)')
        if other == 'pwm-out':
            return _o('exclusive', 'time-multiplexed-later', 'ss-vs-pwm',
                      'a chip select needs a steady level the task sets; the timer\'s Output Compare override replaces the PORT value with the PWM waveform on PB2',
                      ('oc1', 'alt-override', 'spi-ss-master'))
        if other in ('uart-rx', 'uart-tx') or other in OVERRIDERS:
            return _o('exclusive', 'exclusive', 'alt-vs-alt', 'SS and %s are two alternate functions of different peripherals' % other, ('alt-override', 'spi-pins'))
        if other in OBSERVERS:
            return _o('conditional', 'shared-read', 'ss-observe', 'the pin value can be read (PINxn) and sensed while SS is in use; the SPI owns direction and pull-up',
                      ('pinx-read', 'spi-pins'), 'the other role only observes the line; it does not set direction or pull-up')
    # ---- plain output against what only reads the pin
    if 'digital-out' in s:
        other = b if a == 'digital-out' else a
        if other == 'digital-in':
            return _o('compatible', 'shared-read', 'pinx-reads-back',
                      'the pin can be read through PINxn whatever its direction, so a role that reads the pin works while another role drives it (it reads back the level the pin really has)',
                      ('pinx-read',))
        if other in ('interrupt-in', 'pin-change-in'):
            return _o('conditional', 'shared-read', 'interrupt-on-output',
                      'an enabled external or pin-change interrupt triggers even when its pin is an output - the datasheet calls this a way of generating a software interrupt',
                      ('exint-output', 'pcint-mask'), 'the firmware accepts that its own writes to the pin raise the interrupt')
        if other == 'analog-in':
            return _o('conditional', 'shared-read', 'adc-reads-output',
                      'the ADC multiplexer can sample a pin that is also a digital output; the datasheet only asks that ADC3:0 outputs do not switch during a conversion',
                      ('adc-output', 'didr0'), 'on ADC3:0 the output does not change while a conversion runs (ADC5:4 are not named by that rule)')
        if other == 'comparator-in':
            return _o('conditional', 'shared-read', 'ac-reads-output',
                      'the comparator input is read on the pin\'s analog path (AIO), which Table 14-10 does not gate by the direction bit, so it sees the level the output drives',
                      ('tbl-d-ain', 'didr1'), 'the comparison against the pin\'s own output is what the role wants (a self-test)')
        if other == 'clock-in':
            return _o('conditional', 'shared-read', 'clock-from-output',
                      'the T0/T1 input is read through the pin\'s input path, so a timer can count edges the firmware itself drives (a software clock); XCK in synchronous mode '
                      'overrides the port value (PVOE = UMSEL), so only T0/T1 qualify',
                      ('tbl-d-ain', 'timer-ext-clock', 'usart-xck'), 'the clock is the T0 or T1 input, with the USART not in synchronous mode')
    # ---- overrider against an observer: the input buffer and PINxn stay, the peripheral owns direction and pull-up
    if a in OVERRIDERS or b in OVERRIDERS:
        ov, other = (a, b) if a in OVERRIDERS else (b, a)
        if other == 'digital-in':
            return _o('conditional', 'shared-read', 'observe-alt-pin',
                      'the pin value can still be read through PINxn while %s owns the pin (Tables 14-7/14-10/14-11 keep the digital input path); the peripheral controls direction and pull-up' % ov,
                      ('pinx-read', 'alt-signals') + _OWN[ov], 'the digital-in role only observes - it does not set direction or pull-up')
        if other in ('interrupt-in', 'pin-change-in'):
            return _o('conditional', 'shared-read', 'interrupt-on-alt',
                      'an enabled interrupt triggers whatever drives the pin (section 13), so it fires on the %s signal\'s own edges' % ov,
                      ('exint-output', 'pcint-mask') + _OWN[ov], 'the interrupt is meant to fire on the peripheral\'s own signal edges')
        if other == 'analog-in':   # only PC4 / PC5 (SDA / SCL) carry both
            return _o('conditional', 'shared-read', 'adc-on-twi-pin',
                      'PC4/PC5 can be ADC channels while the TWI uses them (the datasheet says the TWI then only affects the conversion on ADC4 and ADC5)',
                      ('alt-c-adc-twi', 'adc-twi', 'tbl-c-twi'), 'only the conversion on that one channel is disturbed by the bus traffic')
        if other == 'comparator-in':   # only PD6: AIN0 + OC0A
            return _o('undetermined', 'exclusive', 'ac-on-driven-pin',
                      'Table 14-10 routes AIN0 to the comparator while OC0A can drive the same pin, but the datasheet gives no rule or limit for comparing a pin the chip itself drives with PWM',
                      ('tbl-d-ain', 'oc0'))
        if other == 'clock-in':
            return _o('conditional', 'shared-read', 'clock-from-alt',
                      'T0/T1 are read through the input path (Table 14-10 DI row) while %s owns the pin: a timer can count the edges of another peripheral\'s signal' % ov,
                      ('tbl-d-ain', 'timer-ext-clock') + _OWN[ov], 'the timer counts the peripheral\'s own signal, and only T0/T1 are used (not XCK)')
    # ---- observers and the analog / clock inputs among themselves
    pair = tuple(sorted(s, key=K.KINDS.index))
    if a == b:
        if a == 'digital-in':
            return _o('conditional', 'shared-read', 'pull-is-one-bit', 'any number of roles can read one pin (PINxn), but the pull-up is one PORTxn bit for all of them',
                      ('pinx-read', 'pin-config'), 'every reader wants the same pull-up setting')
        if a == 'interrupt-in':
            return _o('conditional', 'shared-read', 'one-sense', 'one INTn pin has one sense setting (ISCn1:0), shared by every role that listens to it',
                      ('exint-sense',), 'every role wants the same edge/level')
        if a == 'pin-change-in':
            return _o('conditional', 'shared-read', 'one-vector', 'pin-change interrupts of one bank share one vector (PCI0/1/2); the roles tell their pins apart by reading PINx in the handler',
                      ('pcint-mask', 'pinx-read'), 'one handler serves both roles and reads PINx to tell them apart')
        if a == 'analog-in':
            return _o('conditional', 'time-multiplexed-later', 'one-adc-channel', 'a pin is one ADC channel; two roles read it by taking turns on the one converter',
                      ('adc-mux',), 'the roles take turns (one ADMUX channel per conversion)')
        if a == 'comparator-in':
            return _o('conditional', 'shared-read', 'ac-input', 'two roles reading one comparator input see the same comparison',
                      ('tbl-d-ain',), 'both roles want the same comparison result')
        if a == 'clock-in':
            return _o('conditional', 'shared-read', 'clock-edges', 'one T0/T1 pin has one input path; two timers cannot count one pin\'s edges except through a shared signal',
                      ('timer-ext-clock', 'tbl-d-ain'), 'both roles want the same external clock edges')
    if pair in (('digital-in', 'interrupt-in'), ('digital-in', 'pin-change-in'), ('interrupt-in', 'pin-change-in')):
        return _o('compatible', 'shared-read', 'observers',
                  'the pin is read through PINxn and sensed by its interrupt at the same time: Table 14-11 lists the interrupt input and the plain read side by side',
                  ('pinx-read', 'tbl-d-uart', 'exint-output'))
    if 'analog-in' in s and (set(pair) & {'digital-in'}):
        return _o('conditional', 'shared-read', 'didr-buffer',
                  'the ADC reads the pin, and the digital read works only while the digital input buffer is on: DIDR0 turns it off (the PINx bit then reads zero), and with it on the '
                  'buffer wastes power for an analog level near half the supply',
                  ('didr0', 'adc-didr-power'), 'the signal is a clean digital level (DIDR0 bit clear), or the digital role is given up (bit set)')
    if 'analog-in' in s and 'pin-change-in' in s:
        return _o('conditional', 'shared-read', 'pcint-keeps-buffer',
                  'an enabled pin-change interrupt keeps the digital input buffer on even when the DIDR0 bit is set (Table 14-8: the digital input enable is overridden to the PCINT enable)',
                  ('tbl-c-adc', 'didr0', 'adc-didr-power'), 'the extra power of the digital buffer and a noisy interrupt from an analog level are acceptable')
    if 'comparator-in' in s and set(pair) & {'digital-in'}:
        return _o('conditional', 'shared-read', 'didr1-buffer',
                  'the comparator reads the pin, and DIDR1 (AIN1D/AIN0D) turns the digital input buffer off, after which PINx reads zero',
                  ('didr1', 'tbl-d-ain'), 'the signal is a clean digital level (DIDR1 bit clear), or the digital role is given up (bit set)')
    if 'comparator-in' in s and 'pin-change-in' in s:
        return _o('conditional', 'shared-read', 'pcint-keeps-buffer',
                  'an enabled pin-change interrupt on PD6/PD7 keeps the digital input path on (Table 14-10: DIEOV = 1)', ('tbl-d-ain', 'didr1'),
                  'the extra digital-buffer power and chatter from an analog level are acceptable')
    if 'clock-in' in s and set(pair) & {'digital-in', 'pin-change-in'}:
        return _o('compatible', 'shared-read', 'observers', 'the timer clock input (T0/T1) is read through the same input path as PINxn and the pin-change interrupt (Table 14-10 DI row)',
                  ('tbl-d-ain', 'pinx-read'))
    return Outcome('undetermined', 'exclusive', 'pin.unwritten', 'no rule is written for %s + %s on one pin; not guessed' % (a, b), '', ('compat',))
