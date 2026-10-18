"""
@module board.custom.profile_overlap_periph

pp-1: the SAME-PERIPHERAL rules - two pin profiles served by ONE peripheral block (two compare channels of one timer, the receive and
transmit sides of the USART, two ADC channels ...). The firmware side already has the vocabulary and the cooperation rule, cited here
and not re-written: cmod.custom.claims.peripheral_claims - Timer0/Timer1 are claimed CHANNEL BY CHANNEL (OCRnA / OCRnB apart, the
mode and clock registers shared-config), USART0 / SPI / TWI / the interrupt units are claimed whole and exclusively, the ADC is
shared-read, the GPIO port registers shared-config.

Two profiles that live on DIFFERENT peripherals share nothing at this scope: the row says so (`applies` false, verdict compatible,
rule `periph.distinct`) so the table is complete without pretending a conflict.
"""
from board.custom import profile_overlap_kinds as K
from board.custom.profile_overlap_pin import Outcome


def _o(verdict, mode, rule, reason, cites, cond=''):
    return Outcome(verdict, mode, 'periph.' + rule, reason, cond, tuple(cites))


def shared_peripherals(a, b):
    return sorted(set(K.PERIPHERALS[a]) & set(K.PERIPHERALS[b]))


def _distinct(a, b):
    return Outcome('compatible', 'shared-config', 'periph.distinct',
                   '%s lives on %s and %s on %s: different blocks, nothing to share at this scope' % (a, '/'.join(K.PERIPHERALS[a]), b, '/'.join(K.PERIPHERALS[b])),
                   '', ('claims-usart',))


def applies(a, b):
    return bool(shared_peripherals(a, b))


def rule(a, b):
    """Outcome for two kinds served by the SAME peripheral (symmetric)."""
    if K.KINDS.index(a) > K.KINDS.index(b):
        a, b = b, a
    shared = shared_peripherals(a, b)
    if not shared:
        return _distinct(a, b)
    s = {a, b}
    if shared == ['GPIO']:
        return _o('conditional', 'shared-config', 'gpio-port', 'the two pins share a port (PORTx/DDRx/PINx) only if they sit on the same port; every pin has its own DDxn/PORTxn/PINxn bit, so the roles are independent '
                  'as long as a register is changed one bit at a time (SBI/CBI)', ('pin-config', 'pin-toggle', 'claims-usart'), 'the pins sit on one port and the firmware changes single bits (SBI/CBI), not whole-register writes')
    if 'transport' in s:
        return _o('exclusive', 'time-multiplexed-later', 'transport-owns-usart', 'the host link claims USART0 whole (claims: USART0 is exclusive); another role may use it only once the link is released',
                  ('lifecycle', 'claims-usart'))
    if 'pwm-out' in s and a == b:
        return _o('conditional', 'shared-config', 'timer-channels', 'two compare channels of ONE timer are compatible as channels (A and B have their own OCRnx) and exclusive on the timer\'s mode: '
                  'the waveform generation mode, TOP and clock prescaler are shared, so both PWMs run at one frequency and one shape (claims: channels apart, TCCRnB shared-config)',
                  ('claims-timer', 'timer-mode', 'timer-prescaler'), 'the two channels are different (A and B), and both want the same timer mode and frequency')
    if 'pwm-out' in s and 'clock-in' in s:
        return _o('conditional', 'shared-config', 'timer-external-clock', 'a timer that counts the external T0/T1 pin has its PWM frequency set by that signal, not by the prescaler; this applies only when the PWM channel and the clock pin '
                  'belong to the same timer (T0 with Timer0, T1 with Timer1)', ('timer-ext-clock', 'claims-timer', 'timer-prescaler'), 'the PWM is happy to run at the external clock\'s rate')
    if a == b == 'clock-in':
        return _o('conditional', 'shared-config', 'two-clock-pins', 'T0 and T1 are different timers (they only share the prescaler), XCK belongs to the USART; two roles on the SAME pin\'s clock would be one timer, '
                  'counted once', ('timer-ext-clock', 'timer-prescaler'), 'the two roles use different clock pins')
    if shared == ['USART0'] or set(shared) == {'USART0'}:
        if {a, b} == {'uart-rx', 'uart-tx'}:
            return _o('conditional', 'shared-config', 'usart-sides', 'the receiver and the transmitter have their own enable bits (RXEN0/TXEN0) but one baud rate and one frame format, set up once for the USART',
                      ('usart-tx', 'usart-rx', 'claims-usart'), 'both sides use the same baud rate and frame format')
        if a == b:
            return _o('exclusive', 'exclusive', 'usart-one-side', 'USART0 has one %s side; claims hold USART0 exclusively, so two roles cannot both own it' % ('receive' if a == 'uart-rx' else 'transmit'),
                      ('claims-usart', 'usart-rx', 'usart-tx'))
        if 'clock-in' in s:
            return _o('conditional', 'shared-config', 'usart-xck', 'the XCK pin is the USART\'s synchronous clock: its direction follows the mode (UMSEL, DDR_XCK), one mode for the whole USART',
                      ('usart-xck', 'claims-usart'), 'the USART runs in synchronous mode as the transmit/receive role expects')
    if 'SPI' in shared:
        if a == b:
            return _o('exclusive', 'exclusive', 'spi-one-signal', 'the SPI has one %s signal; claims hold the SPI whole and exclusively' % a, ('claims-usart', 'spi-pins'))
        return _o('conditional', 'shared-config', 'spi-bus', 'the four SPI signals are one bus: they belong together, with one master/slave mode that sets every pin\'s direction (Table 19-1)', ('spi-pins', 'claims-usart'),
                  'the roles agree on one master/slave mode and one clock rate')
    if 'TWI' in shared:
        if a == b:
            return _o('exclusive', 'exclusive', 'twi-one-signal', 'the TWI has one %s signal; claims hold the TWI whole and exclusively' % a, ('claims-usart', 'alt-c-twi'))
        return _o('compatible', 'shared-config', 'twi-bus', 'SDA and SCL are the two lines of one bus: they belong together', ('twi-wired-and', 'claims-usart'))
    if s == {'comparator-in', 'analog-in'}:
        return _o('conditional', 'time-multiplexed-later', 'ac-uses-adc-mux', 'the comparator can take its negative input from the ADC multiplexer, but only while the ADC is switched off (ADEN = 0); with the ADC on, AIN1 is the negative input',
                  ('ac-mux', 'adc-mux'), 'the ADC is off while the comparator reads the multiplexed input, or the comparator uses its AIN0/AIN1 pins only')
    if 'AC' in shared:
        return _o('conditional', 'shared-read', 'ac-two-inputs', 'the comparator has two inputs (AIN0 and AIN1) and one result; two roles use it together only when they are its two inputs, or want the same result',
                  ('ac-mux', 'tbl-d-ain'), 'one role is the positive and the other the negative input, or both want the same comparison')
    if 'ADC' in shared:
        return _o('conditional', 'time-multiplexed-later', 'adc-one-converter', 'one converter reads one channel per conversion (ADMUX MUX3:0); two roles take turns, and claims mark the ADC shared-read',
                  ('adc-mux', 'claims-usart'), 'the roles take turns - one channel per conversion')
    if 'EXINT' in shared:
        return _o('compatible', 'shared-config', 'exint-pins', 'INT0 and INT1 have their own sense bits (ISCn1:0) and mask bits; two different INT pins do not interact', ('exint-sense', 'claims-usart'))
    if 'PCINT' in shared:
        return _o('conditional', 'shared-config', 'pcint-bank', 'pins of one pin-change bank share one vector and one enable (PCICR bit); each pin has its own mask bit (PCMSK)', ('pcint-mask', 'claims-usart'),
                  'the two pins are in different banks, or one handler serves both')
    return Outcome('undetermined', 'exclusive', 'periph.unwritten', 'no rule is written for %s + %s on %s; not guessed' % (a, b, '/'.join(shared)), '', ('claims-usart',))
