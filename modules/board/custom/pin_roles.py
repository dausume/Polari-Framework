"""
@module board.custom.pin_roles

The PIN ROLE VOCABULARY (brd-bo) — what each kind of pin IS, in plain words, with a CITED `learn_more` source per
role: Arduino's own UNO R3 docs page for the pin function on that board, the ATmega328P datasheet section for the
AVR peripheral behind it (Microchip DS40002061B — the same citation `board.custom.uno_facts`/`soc_atmega328p` use),
and Wikipedia for the general bus/signalling concept (PWM, ADC, I2C, SPI, UART). Texts are short and accurate —
this module makes no board-specific claims; a board's `role` column (BoardPin.function / a header pin's label,
`board.custom.pinmap_svg.role_of`) just looks a name up here.

ROLE_NAMES is the single vocabulary every board-pin view shares: the SVG legend (`pinmap_svg.ROLE_COLORS`), the
`GET /api/board/<board>/pin-roles` table, and `pol board pins <board>`'s `function` column all draw their role
names from this set — one dictionary, not three.
"""

import json

ARDUINO_UNO_DOCS = 'https://docs.arduino.cc/hardware/uno-rev3/'
M328_DOC_URL = 'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf'

ROLES = {
    'adc': {
        'description': 'An analog-to-digital input — reads a continuously-varying voltage (a sensor, a pot) as a number.',
        'usage': 'The board\'s A0-A5 pins feed the SoC\'s 10-bit ADC; firmware samples one with analogRead()-style code.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — Analog In pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — ADC: Analog to Digital Converter', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — Analog-to-digital converter', 'url': 'https://en.wikipedia.org/wiki/Analog-to-digital_converter'},
        ],
    },
    'button': {
        'description': 'A momentary push-button wired to a digital input — pressed = one logic level, released = the other.',
        'usage': 'Read as a plain GPIO input (usually pulled up); firmware debounces the edge to detect one press.',
        'sources': [
            {'label': 'Espressif ESP32-C3-DevKitM-1 user guide — BOOT/user button', 'url': 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html'},
            {'label': 'Wikipedia — Push-button', 'url': 'https://en.wikipedia.org/wiki/Push-button'},
        ],
    },
    'gpio': {
        'description': 'A general-purpose digital pin — firmware sets its direction (in/out) and drives or reads a 0/1 level.',
        'usage': 'The plain D-numbered header pins with no fixed peripheral role; any one can be a digital in or out.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — Digital pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — I/O-Ports', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — General-purpose input/output', 'url': 'https://en.wikipedia.org/wiki/General-purpose_input/output'},
        ],
    },
    'ground': {
        'description': 'The 0 V reference every signal and supply is measured against.',
        'usage': 'The header\'s GND pins — tie any external circuit\'s ground to one of these before wiring a signal.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — Power pins (GND)', 'url': ARDUINO_UNO_DOCS},
            {'label': 'Wikipedia — Ground (electricity)', 'url': 'https://en.wikipedia.org/wiki/Ground_(electricity)'},
        ],
    },
    'i2c': {
        'description': 'A 2-wire shared bus (SDA data + SCL clock) addressing many peripheral chips from the same two pins.',
        'usage': 'The UNO\'s A4/SDA and A5/SCL (also broken out on the DIGITAL_H header) — one bus, several devices.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — SDA/SCL pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — 2-wire Serial Interface (TWI)', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — I2C', 'url': 'https://en.wikipedia.org/wiki/I%C2%B2C'},
        ],
    },
    'led': {
        'description': 'A pin wired straight to an on-board LED, for a visible on/off or blink without any external part.',
        'usage': 'D13 drives the UNO\'s built-in "L" LED (also ICSP SCK) — set it high/low or PWM it to dim.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — Built-in LED (pin 13)', 'url': ARDUINO_UNO_DOCS},
            {'label': 'Wikipedia — Light-emitting diode', 'url': 'https://en.wikipedia.org/wiki/Light-emitting_diode'},
        ],
    },
    'power': {
        'description': 'A supply pin — brings voltage IN to the board or OUT to power something plugged into it.',
        'usage': 'The POWER header\'s +5V/+3V3/VIN/IOREF pins — check the voltage before wiring anything to them.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — Power pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'Wikipedia — Power supply', 'url': 'https://en.wikipedia.org/wiki/Power_supply'},
        ],
    },
    'pwm': {
        'description': 'A digital pin whose timer can switch it on/off fast enough to fake an analog output (dimming, speed).',
        'usage': 'The UNO\'s ~-marked pins (D3, D5, D6, D9, D10, D11) are each one timer\'s Output Compare pin.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — PWM (~) pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — Timer/Counter0/1/2 with PWM', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — Pulse-width modulation', 'url': 'https://en.wikipedia.org/wiki/Pulse-width_modulation'},
        ],
    },
    'spi': {
        'description': 'A 4-wire fast bus (clock + MOSI/COPI out + MISO/CIPO in + a per-device select) for one controller, several devices.',
        'usage': 'The UNO\'s ICSP header (also D11-D13) — used both for SPI peripherals and for flashing the chip itself.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — ICSP header', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — SPI: Serial Peripheral Interface', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — Serial Peripheral Interface', 'url': 'https://en.wikipedia.org/wiki/Serial_Peripheral_Interface'},
        ],
    },
    'uart': {
        'description': 'A 2-wire point-to-point serial link (TX out + RX in) for a byte stream between two devices.',
        'usage': 'The UNO\'s D0/D1 (RX/TX) go to the 16U2 USB bridge — the same link the Serial Monitor uses.',
        'sources': [
            {'label': 'Arduino UNO R3 docs — RX/TX (D0/D1) pins', 'url': ARDUINO_UNO_DOCS},
            {'label': 'ATmega328P datasheet — USART0', 'url': M328_DOC_URL},
            {'label': 'Wikipedia — Universal asynchronous receiver-transmitter', 'url': 'https://en.wikipedia.org/wiki/Universal_asynchronous_receiver-transmitter'},
        ],
    },
}
ROLE_NAMES = tuple(sorted(ROLES))


def rows_for_roles(roles_present):
    """`roles_present` = {role: [pin label, ...]} (board.custom.pinmap_svg.pins_by_role). -> table rows, one per
    role actually present on the board, each `learn_more` a list of {label, url} (several cited sources per role) —
    the frontend's `link` column format shows the first; every source still travels in the row for a person reading
    the raw payload."""
    out = []
    for role in ROLE_NAMES:
        pins = roles_present.get(role)
        if not pins:
            continue
        info = ROLES[role]
        sources = info['sources']
        out.append({
            'role': role,
            'description': info['description'],
            'usage': info['usage'],
            'pins': ', '.join(pins),
            'learn_more': sources[0]['url'],
            'learn_more_label': sources[0]['label'],
            'sources_json': json.dumps(sources),
        })
    return out
