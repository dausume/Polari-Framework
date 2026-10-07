"""
@module board.custom.power_pins

fs-2d (his ask, verbatim: "the power pins have no definitions at all, they should at least have their target
sections reactively instead describe what they do and what they are for") — PURPOSE / ELECTRICAL / TYPICAL-USES for
a board's power and reference connector labels (IOREF, RESET, +3V3, +5V, GND x4, VIN, AREF on the UNO's POWER /
DIGITAL_H headers): these are never BoardPin rows (board.custom.board_uno only makes one per SoC-backed D/A signal
pin), so board.custom.board_object.pin_by_canonical() never finds them and GET /api/board/<board>/pins/<pin> 404s
today. `detail_for()` is this door's content — cited to the Arduino Starter Kit book ("The Arduino Board", p.11) and
the Arduino UNO R3 pinout PDF (board.custom.board_uno's own DOC/REV/URL and pinout.* DatasheetFacts) + the
ATmega328P datasheet where PC6/RESET crosses into it — never a new, uncited number.

board.custom.target_compat.NEVER_ASSIGNABLE already refuses every task kind on these labels; this module adds the
WHY a person reads when they click one — not a new compatibility rule.
"""
from board.custom.board_uno import URL as PINOUT_URL

BOOK = 'Arduino Starter Kit book'
BOARD_PAGE = '%s, The Arduino Board, p.11' % BOOK

#: a person-typed spelling -> the canonical connector label board_uno.py actually uses
ALIASES = {'5V': '+5V', '3.3V': '+3V3', '3V3': '+3V3', 'VCC': '+5V'}

NEVER_ASSIGNABLE_REASON = ("a power/reference rail is not a task target; tasks register to signal pins "
                           "(board.custom.target_compat.NEVER_ASSIGNABLE, his ruling 2026-10-06)")


def _pinout(note=''):
    return {'label': 'Arduino UNO R3 pinout (A000066), p.1%s' % (' — %s' % note if note else ''), 'url': PINOUT_URL}


def _kit(section, note=''):
    return {'label': '%s, %s%s' % (BOOK, section, ' (%s)' % note if note else ''), 'url': ''}


def _m328(where):
    from board.custom.uno_facts import M328_URL
    return {'label': 'ATmega328P datasheet — %s' % where, 'url': M328_URL}


POWER_PIN_FACTS = {
    'IOREF': {
        'purpose': "Tells a plugged-in shield what logic/supply voltage this board's I/O runs at, so the shield can adapt — present on the POWER header.",
        'electrical': {'voltage': 'undetermined', 'notes': "the UNO pinout names IOREF but states no voltage for it; the UNO is a 5V-logic "
                                                            "board in practice, but that number is not printed on the cited page"},
        'typical_uses': ["a shield reads this pin instead of assuming 5V (so the same shield design can sit on a 3.3V board too)"],
        'sources': [_pinout('POWER header'), _kit('The Arduino Board, p.11', 'the header is drawn; IOREF is not itemized by name in the prose')],
    },
    'RESET': {
        'purpose': "Resets the ATmega microcontroller — pull it LOW to restart the running sketch.",
        'electrical': {'voltage': 'undetermined', 'notes': "the active level/threshold is in the ATmega328P datasheet's electrical "
                                                            "characteristics, not re-paginated this session; PC6/RESET itself is Table 14-6, p.94"},
        'typical_uses': ['press the RESET button for the same effect (kit book p.11: "Reset button — Resets the ATmega microcontroller.")',
                        'an external circuit can pull this LOW to reset the board without the button'],
        'sources': [_kit('The Arduino Board, p.11', 'Reset button'), _m328('Table 14-6 Port C Pins Alternate Functions (PC6/RESET), p.94')],
    },
    '+3V3': {
        'purpose': "A regulated 3.3 V supply pin for powering 3.3 V-only circuits plugged into the board.",
        'electrical': {'voltage': 3.3, 'max_current_ma': 50, 'notes': 'UNO pinout p.1 legend: "MAXIMUM current per +3.3V pin is 50mA" '
                                                                      '(board_uno fact pinout.max_current_3v3)'},
        'typical_uses': ['power a 3.3 V sensor or module — never wire a 5 V part here'],
        'sources': [_pinout('POWER header, legend'), _kit('The Arduino Board, p.11')],
    },
    '+5V': {
        'purpose': "Supplies regulated 5 V to power external circuits.",
        'electrical': {'voltage': 5.0, 'max_current_ma': 'undetermined',
                       'notes': "the cited UNO pinout states per-I/O-pin (20 mA) and +3.3V-pin (50 mA) limits explicitly; it prints no "
                               "separate +5V-pin number (set by the on-board regulator's total budget, not a per-pin figure)"},
        'typical_uses': ['power your circuits\' + rail (kit book p.11: "GND and 5V pins — Use these pins to provide +5V power and ground to your circuits.")',
                        "the TMP36 temperature sensor's outer 'power' leg (kit book p.9: \"The outside legs connect to power and ground.\")",
                        "one end of a potentiometer, so its wiper reads a 0-5V divide (kit book p.8)",
                        'a servo motor\'s +5V (kit book p.9)'],
        'sources': [_kit('The Arduino Board, p.11', 'GND and 5V pins'), _pinout('POWER header')],
    },
    'GND': {
        'purpose': "The 0 V reference every signal and supply on the board is measured against.",
        'electrical': {'voltage': 0.0},
        'typical_uses': ['tie any external circuit\'s ground here before wiring a signal',
                        "the TMP36's other outer leg (kit book p.9)",
                        "a pushbutton's, potentiometer's or tilt sensor's ground end",
                        "an LED's cathode (short leg), directly or through its series resistor (kit book p.7)"],
        'sources': [_kit('The Arduino Board, p.11', 'GND and 5V pins'), _pinout('POWER + DIGITAL_H headers')],
    },
    'VIN': {
        'purpose': "The unregulated input voltage pin — feeds the board's on-board 5 V regulator from an external supply.",
        'electrical': {'voltage_range': '6-20', 'unit': 'V', 'notes': 'UNO pinout p.1 legend: "VIN 6-20V input to the board" (fact '
                                                                      "pinout.vin_range); the kit's own barrel connector is narrower (7-12V, below)"},
        'typical_uses': ['plug the 9V battery snap\'s + lead here (- to GND) to run the board off a battery (kit book p.6: "Battery Snap — '
                        'Used to connect a 9V battery to power leads that can be easily plugged into a breadboard or your Arduino.")',
                        'the same net the board\'s barrel power connector feeds (kit book p.11: "Power connector — This is how you power '
                        'your Arduino when it\'s not plugged into a USB port for power. Can accept voltages between 7-12V.")'],
        'sources': [_pinout('POWER header, legend'), _kit('The Arduino Board, p.11', 'Power connector'), _kit('Parts in your kit, p.6', 'Battery Snap')],
    },
    'AREF': {
        'purpose': "The ADC's external voltage reference input — swap in a different reference for analogRead() instead of the default AVcc/5V.",
        'electrical': {'voltage': 'undetermined', 'notes': "left unconnected, AREF defaults to AVcc (5V) internally; the allowed external-"
                                                           "reference voltage range is in the ATmega328P datasheet's ADC chapter (ch.24, "
                                                           "p.246), not re-paginated to a specific number this session"},
        'typical_uses': ['leave unconnected for the default 5 V reference',
                        'wire an external precision reference here only after calling analogReference(EXTERNAL) in the sketch'],
        'sources': [_m328('ADC chapter, ch.24, p.246'), _pinout('DIGITAL_H header')],
    },
}

#: board-level power SOURCES named in the kit book that are not themselves board.custom.board_uno Connector rows
#: today (the board object has no barrel-jack/USB Connector yet) — named here so the purpose/electrical/typical_uses
#: vocabulary still exists for them even though no pin-detail door resolves a canonical name to one (honest gap,
#: not a guessed Connector row).
BOARD_POWER_SOURCES = {
    'barrel-jack': {
        'title': 'Power connector (barrel jack)', 'feeds_net': 'VIN', 'modeled_as_connector': False,
        'purpose': 'Powers the board from an external supply when it is not on USB.',
        'electrical': {'voltage_range': '7-12', 'unit': 'V', 'notes': 'kit book p.11: "Can accept voltages between 7-12V." — narrower than '
                                                                      "the UNO pinout's 6-20V VIN rating (the book states the recommended "
                                                                      "input, the pinout the pin's rated range)"},
        'typical_uses': ['plug a 9V-battery-snap lead (via a barrel adapter) or a wall adapter here instead of USB'],
        'sources': [_kit('The Arduino Board, p.11', 'Power connector'), _pinout('POWER header, legend')],
    },
    'usb-port': {
        'title': 'USB port', 'feeds_net': '+5V', 'modeled_as_connector': False,
        'purpose': 'Powers the board, uploads sketches, and carries the Serial Monitor link to a computer.',
        'electrical': {'voltage': 5.0, 'notes': 'USB bus power; no separate current-limit fact cited for this port'},
        'typical_uses': ['power + program the board for most of the kit\'s projects (kit book p.9: "USB cable — This allows you to connect '
                        'your Arduino Uno to your personal computer for programming. It also provides power to the Arduino for most of '
                        'the projects in the kit.")',
                        'the TX/RX LEDs flicker here during upload and Serial communication (kit book p.11)'],
        'sources': [_kit('Parts in your kit, p.9', 'USB cable'), _kit('The Arduino Board, p.11', 'USB port')],
    },
}


def label_for(pin):
    return ALIASES.get(pin, pin)


def is_power_reference_label(pin):
    return label_for(pin) in POWER_PIN_FACTS


def role_of(label):
    if label == 'GND':
        return 'ground'
    if label in ('IOREF', 'AREF'):
        return 'reference'
    if label == 'RESET':
        return 'control'
    return 'power'


def locations_for(label, r):
    """[{connector, number}] — every ConnectorPin row on this board carrying this label (GND has 4 on the UNO:
    POWER:6, POWER:7, DIGITAL_H:7, ICSP:6)."""
    return [{'connector': cp['connector'], 'number': cp['number']} for cp in r.get('connector_pins', []) if cp.get('label') == label]


def detail_for(pin, r, parts_that_connect_here=None):
    """None when `pin` is not a known power/reference label; else the fs-2d pin-detail payload: purpose, electrical,
    typical_uses, assignable=False (+ why), every physical location this label appears at, its citations, and
    (board.custom.kit_parts) the kit parts that wire here."""
    label = label_for(pin)
    facts = POWER_PIN_FACTS.get(label)
    if facts is None:
        return None
    net = next((n['net'] for n in r.get('nets', []) if n['net'] == label), label)
    return {
        'label': label, 'role': role_of(label), 'purpose': facts['purpose'], 'electrical': facts['electrical'],
        'typical_uses': facts['typical_uses'], 'assignable': False, 'assignable_reason': NEVER_ASSIGNABLE_REASON,
        'locations': locations_for(label, r), 'net': net, 'sources': facts['sources'],
        'parts_that_connect_here': parts_that_connect_here or [],
    }
