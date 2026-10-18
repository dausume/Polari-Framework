"""
@module board.custom.profile_overlap_kinds

pp-1: the pin-profile KINDS the overlap table covers and what the ATmega328P offers each one. Nothing is re-derived: a kind that is a
board.custom.target_compat.TASK_KINDS entry asks `target_compat.compatible()` (the SocPin alternate functions) which pins offer it;
the kinds target_compat does not name get their function set here, read off the same Tables 14-3 / 14-6 / 14-9
(board.custom.soc_atmega328p.PINS).

  interrupt-in    a DEDICATED external interrupt pin (INT0 / INT1)       - target_compat 'interrupt-in' (ok on INT0/INT1 only)
  pin-change-in   a pin-change interrupt pin (PCINT0..23)                - every port pin but none of the power pins
  comparator-in   an analog comparator input (AIN0 / AIN1)
  clock-in        an external clock INTO a peripheral (T0, T1, XCK)
  transport       the RESERVATION of the host link (the USB-serial lines) - not a function, a claim on RXD/TXD for the board's lifecycle

pp-0 calls both INT0/INT1 and PCINTn pins `interrupt-in`; the table keeps them apart because the two units differ (one sense register
per INTn vs one mask per pin and one vector per bank). Mission co-location tries both and reports which it used.
"""
from board.custom import target_compat as TC
from board.custom.soc_atmega328p import PINS, SOC

KINDS = ('digital-out', 'digital-in', 'interrupt-in', 'pin-change-in', 'analog-in', 'pwm-out', 'uart-rx', 'uart-tx',
         'spi-sck', 'spi-mosi', 'spi-miso', 'spi-ss', 'i2c-sda', 'i2c-scl', 'comparator-in', 'clock-in', 'transport')

TITLES = {
    'digital-out': 'Digital output', 'digital-in': 'Digital input', 'interrupt-in': 'External interrupt input (INT0/INT1)',
    'pin-change-in': 'Pin-change interrupt input', 'analog-in': 'Analog input (ADC)', 'pwm-out': 'PWM output',
    'uart-rx': 'UART receive', 'uart-tx': 'UART transmit', 'spi-sck': 'SPI clock', 'spi-mosi': 'SPI MOSI', 'spi-miso': 'SPI MISO',
    'spi-ss': 'SPI slave select', 'i2c-sda': 'I2C data', 'i2c-scl': 'I2C clock', 'comparator-in': 'Analog comparator input',
    'clock-in': 'External clock input', 'transport': 'Transport reservation (the host link)',
}

#: kind -> the SocPin alternate functions that offer it (kinds target_compat does not know)
_OWN_FUNCTIONS = {'comparator-in': ('AIN0', 'AIN1'), 'clock-in': ('T0', 'T1', 'XCK'), 'transport': ('RXD', 'TXD')}

#: which side of a wire the kind is on: driver | listener | bus (open-drain, both ways) | by-mode (SPI: master drives, slave listens) | reservation
SIDE = {'digital-out': 'driver', 'pwm-out': 'driver', 'uart-tx': 'driver', 'digital-in': 'listener', 'interrupt-in': 'listener',
        'pin-change-in': 'listener', 'analog-in': 'listener', 'uart-rx': 'listener', 'comparator-in': 'listener', 'clock-in': 'listener',
        'spi-sck': 'by-mode', 'spi-mosi': 'by-mode', 'spi-miso': 'by-mode', 'spi-ss': 'by-mode', 'i2c-sda': 'bus', 'i2c-scl': 'bus',
        'transport': 'reservation'}

#: kind -> the peripheral instances it can sit on (None = not a peripheral at all: a plain port bit)
PERIPHERALS = {'digital-out': ('GPIO',), 'digital-in': ('GPIO',), 'interrupt-in': ('EXINT',), 'pin-change-in': ('PCINT',),
               'analog-in': ('ADC',), 'pwm-out': ('TIMER0', 'TIMER1', 'TIMER2'), 'uart-rx': ('USART0',), 'uart-tx': ('USART0',),
               'spi-sck': ('SPI',), 'spi-mosi': ('SPI',), 'spi-miso': ('SPI',), 'spi-ss': ('SPI',), 'i2c-sda': ('TWI',), 'i2c-scl': ('TWI',),
               'comparator-in': ('AC', 'ADC'),   # its negative input can come from the ADC multiplexer (23.2 p.243)
               'clock-in': ('TIMER0', 'TIMER1', 'USART0'), 'transport': ('USART0',)}


def _stub(pin):
    return {'canonical': pin, 'function': '', 'soc_pin': pin}


def _soc_pin(pin):
    fns = PINS[pin][1]
    import json
    return {'pin': pin, 'functions_json': json.dumps(fns), 'fact': '%s:pin.%s' % (SOC, pin)}


def pins_for(kind):
    """The ATmega328P pins that can serve `kind` -> a sorted list (port order). Never empty for a known kind."""
    out = []
    for pin in sorted(PINS):
        fns = PINS[pin][1]
        if kind in _OWN_FUNCTIONS:
            ok = any(f in fns for f in _OWN_FUNCTIONS[kind])
        elif kind == 'pin-change-in':
            ok = any(f.startswith('PCINT') for f in fns)
        elif kind in TC.TASK_KINDS:
            ok = TC.compatible(kind, _stub(pin), _soc_pin(pin))[0] == 'ok'
        else:
            raise KeyError('unknown overlap kind %r' % kind)
        if ok:
            out.append(pin)
    return out


def common_pins(a, b):
    sa = set(pins_for(a))
    return [p for p in pins_for(b) if p in sa]


def distinct_pairs(a, b):
    """True when two DIFFERENT pins exist, one offering `a` and the other `b` (two pins wired together)."""
    pa, pb = pins_for(a), pins_for(b)
    return any(x != y for x in pa for y in pb)
