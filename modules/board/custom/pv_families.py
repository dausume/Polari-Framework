"""
@module board.custom.pv_families

pv-0 (PIN_VIEW_PLAN.md 2.2): THE PROTOCOL-FAMILY VOCABULARY of the pin view — ONE map from a pin function / package-contact kind to a family, the protocol SETS with their child
signals, and the token NAME a front end paints each family with (`--pin-<family>`). The server sends the family + the token name + a fallback hex; the colours themselves are theme tokens
in the front end (styling rule: tokenized by property). The six families that `board.custom.pinmap_svg.ROLE_COLORS` already colours reuse its hex (one vocabulary); the four it has no
colour for (interrupt, usb, clock, reset-programming) carry a fallback hex that is a DRAWING KNOB (only distinctness matters, never a measurement).

This module makes no electrical claim and holds no number. SIGNAL words only (a pin OUTPUTS or INPUTS a signal); the electricity of a connection is the drive side (pin_view_conn).
"""
import re

from board.custom import pinmap_svg as PM

FAMILIES = ('gpio', 'interrupt', 'pwm-timer', 'analog', 'uart', 'spi', 'i2c', 'usb', 'clock', 'reset-programming', 'power', 'ground')

#: pinmap_svg.ROLE_COLORS role -> family (the colours reused); the rest are DRAWING KNOBS
_FROM_ROLE = {'gpio': 'gpio', 'pwm': 'pwm-timer', 'adc': 'analog', 'uart': 'uart', 'spi': 'spi', 'i2c': 'i2c', 'power': 'power', 'ground': 'ground'}
_KNOB_HEX = {'interrupt': PM.ROLE_COLORS['button'], 'usb': '#5d4037', 'clock': '#9e9d24', 'reset-programming': '#6d4c41'}
FALLBACK_HEX = dict({fam: PM.ROLE_COLORS[role] for role, fam in _FROM_ROLE.items()}, **_KNOB_HEX)
assert set(FALLBACK_HEX) == set(FAMILIES)


def token(family):
    """The theme-token NAME a front end paints this family with (its text pair is `<token>-text`)."""
    return '--pin-%s' % family


def family_rows():
    """One row per family: name, token, text token, fallback hex, whether the hex is a drawing knob, and (osc-6) the family's signal KIND -
    analog | digital | differential | undetermined (board.custom.signal_kinds: the one axis on this one vocabulary)."""
    from board.custom import signal_kinds as SK
    return [{'family': f, 'token': token(f), 'text_token': token(f) + '-text', 'fallback_hex': FALLBACK_HEX[f], 'hex_is_drawing_knob': f in _KNOB_HEX,
             'signal_kind': SK.kind_of_family(f)} for f in FAMILIES]


#: protocol SETS -> their child signals (his words: SPI -> SCK, MOSI, MISO, SS; I2C -> SDA, SCL; UART -> RX, TX; USB -> D+, D-); the child signal's function names per chip family of names
SETS = {
    'spi': {'SCK': ('SCK', 'SCLK', 'FSPICLK', 'SPICLK'), 'MOSI': ('MOSI', 'PDI', 'FSPID', 'SPID'), 'MISO': ('MISO', 'PDO', 'FSPIQ', 'SPIQ'), 'SS': ('SS', 'FSPICS0', 'SPICS0')},
    'i2c': {'SDA': ('SDA',), 'SCL': ('SCL',)},
    'uart': {'RXD': ('RXD', 'RXD1', 'U0RXD'), 'TXD': ('TXD', 'TXD1', 'U0TXD')},
    'usb': {'D+': ('D+', 'USB_D+'), 'D-': ('D-', 'USB_D-')},
}

_RULES = (   # (regex on the function name, family) — first match wins
    (r'^GPIO\d*$', 'gpio'), (r'^(INT\d+|PCINT\d+)$', 'interrupt'), (r'^(OC\d[A-C]?|T\d|ICP\d)$', 'pwm-timer'), (r'^(ADC\d?.*|AIN\d|AREF)$', 'analog'),
    (r'^(RXD\d?|TXD\d?|XCK\d?|RTS|CTS|U0RXD|U0TXD)$', 'uart'), (r'^(MOSI|MISO|SCK|SCLK|SS|FSPI.*|SPI.*)$', 'spi'), (r'^(SDA|SCL)$', 'i2c'),
    (r'^(XTAL\d?|TOSC\d|CLKO|XTAL_32K_[NP])$', 'clock'), (r'^(RESET|dW|HWB|PDI|PDO|MT(CK|DI|DO|MS))$', 'reset-programming'), (r'^USB_D[+-]$|^D[+-]$', 'usb'))
_KIND = {'power': 'power', 'analog-supply': 'power', 'usb-supply': 'power', 'regulator-output': 'power', 'ground': 'ground', 'usb-ground': 'ground', 'thermal-pad': 'ground',
         'analog-reference': 'analog', 'analog-input': 'analog', 'usb-data': 'usb', 'clock-input': 'clock'}
#: direction of a function that no PeripheralSignal row carries (the 16U2's): read from the function NAME's own convention (RX in, TX out) — undetermined when the name does not say
_NAME_DIR = {'RXD1': 'in', 'TXD1': 'out', 'RXD': 'in', 'TXD': 'out', 'CTS': 'in', 'RTS': 'out', 'MOSI': 'inout', 'MISO': 'inout', 'SCLK': 'inout', 'SCK': 'inout', 'SS': 'inout'}
PDI_PDO_NOTE = 'PDI / PDO share MOSI / MISO on the 16U2: both families are listed, the spi one comes first on the pin'


def family_of(function):
    """The family of one pin function name (the vocabulary's one map); '' when no rule names it."""
    for rx, fam in _RULES:
        if re.match(rx, function or ''):
            return fam
    return ''


def families_of_function(function):
    """PDI/PDO are both a programming signal and the SPI data lines: list every family a function belongs to (spi first for the shared ones)."""
    if function in ('PDI', 'PDO'):
        return ['spi', 'reset-programming']
    f = family_of(function)
    return [f] if f else []


def family_of_kind(kind):
    """The family of a PackageContact kind that is not a plain io leg ('' for io)."""
    return _KIND.get(kind, '')


def role_family(role):
    """pinmap_svg role (BoardPin.function: gpio pwm adc uart spi i2c led button usb power ground) -> family."""
    return {'led': 'gpio', 'button': 'gpio', 'usb': 'usb'}.get(role) or _FROM_ROLE.get(role, '')


def direction_of(function, signal_rows):
    """in | out | inout | undetermined — from the PeripheralSignal row when one exists, else the name's own convention (the 16U2), else undetermined."""
    for s in signal_rows:
        if s.get('direction') in ('in', 'out', 'inout'):
            return s['direction']
    return _NAME_DIR.get(function, 'undetermined')


def set_children(protocol):
    """('spi') -> ['SCK','MOSI','MISO','SS'] (a family without a set: its own name)."""
    return list(SETS[protocol]) if protocol in SETS else [protocol]


def function_matches(protocol, function):
    """Which child signal of the set (or the family itself) one function name carries: '' when none. For a family without children any function of that family matches ('*')."""
    if protocol in SETS:
        return next((child for child, names in SETS[protocol].items() if function in names), '')
    return '*' if protocol in FAMILIES and protocol in families_of_function(function) else ''


def vocabulary():
    """The whole vocabulary as one payload (the door serves it beside the view)."""
    from board.custom import signal_kinds as SK
    return {'families': family_rows(), 'sets': {k: list(v) for k, v in SETS.items()}, 'signal_kinds': SK.kind_rows(),
            'note': 'colour = family (token name + fallback hex; the colours are theme tokens); a set expands to its child signals; each family carries its signal kind '
                    '(analog / digital / differential) and so does every per-pin signal row'}
