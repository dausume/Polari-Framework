"""
@module board.custom.kit_parts

fs-2d (his ask, verbatim: "there are still some unvalidated cases ... the power pins have no definitions at all" +
his follow-up, verbatim: "there are all the parts in our kit, we will be wanting to use these as reference for how
we make our sample firmwares") — THE KIT PARTS REGISTER for the Arduino Starter Kit, cited to the kit's own book
("Parts in your kit", pp. 6-9) + "The Arduino Board" (p.11) for the board itself, with the Arduino UNO R3 pinout
PDF / ATmega328P datasheet brought in only where a NUMBER crosses into one of those (board.custom.board_uno /
board.custom.uno_facts — never a new, uncited figure).

Every row names what a sample FirmwareSolution/Capability needs to USE this part (his follow-up): interface_kind,
driver_needed, pin_count/pin_roles, electrical_notes, polarity, kit_quantity, source — see KitPart's own docstring
for the full vocabulary. `sample_capabilities` (below, `_sample_capabilities`) is DERIVED by scanning the two seeded
CapabilityDefinition rows' own text (cmod.custom.capabilities.SEED_CAPABILITIES) for this part's name/role — never
hand-maintained, so a new capability that mentions a part starts showing up here without a second edit.
"""
import json

KIT = 'arduino-starter-kit'
BOOK = 'Arduino Starter Kit book'
BOARD_PAGE = '%s, The Arduino Board, p.11' % BOOK
PARTS_PAGES = '%s, Parts in your kit, pp. 6-9' % BOOK
SYMBOLS_PAGE = '%s, Circuit symbols, p.10' % BOOK


def _page(n):
    return '%s, Parts in your kit, p.%d' % (BOOK, n)


#: row fields beyond (name auto-built as '<kit>:<key>', kit=KIT, source default=PARTS_PAGES) — `terms` (not a KitPart
#: field; consumed only by _sample_capabilities below) are the case-insensitive words that tie a part to a Capability
_PARTS = [
    ('arduino-uno', 'Arduino Uno', {
        'what_it_is': "The microcontroller development board at the heart of your projects — a simple computer with "
                      "no built-in way to interact; you build the circuits and tell it how to interface with them.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "the board itself — every other kit part connects TO one of its pins",
        'connects_to_kinds': '', 'electrical_notes': "see the board's own power pins (GET /api/board/arduino-uno-r3/pins/<5V|GND|VIN|...>)",
        'polarity': '', 'kit_quantity': 'undetermined (the book lists it once; no count printed)',
        'source': _page(6),
    }),
    ('breadboard', 'Breadboard', {
        'what_it_is': "A board for building electronic circuits without soldering — rows of holes let you connect "
                      "wires and components together; solder-less (this kit) and solder versions both exist.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "mechanical only — no electrical interface of its own", 'connects_to_kinds': '',
        'electrical_notes': '', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(6),
    }),
    ('battery-snap', 'Battery Snap (9V)', {
        'what_it_is': "Connects a 9V battery to power leads that plug into a breadboard or the Arduino.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 2, 'pin_roles': 'red lead = +9V, black lead = GND (standard 9V-snap colour code, not itemized on the cited page)',
        'connects_to': "board power: VIN (+) and GND (-), or a breadboard power rail", 'connects_to_kinds': 'power,ground',
        'electrical_notes': "9V nominal (the battery itself); the board's VIN accepts 6-20V (board_uno fact pinout.vin_range) — a 9V battery is within range",
        'polarity': 'red = +, black = - (standard 9V-snap colour code)', 'kit_quantity': 'undetermined', 'source': _page(6),
    }),
    ('capacitors', 'Capacitors (ceramic, electrolytic, film)', {
        'what_it_is': "Store and release electrical energy in a circuit; often placed across power and ground near "
                      "a sensor or motor to smooth voltage fluctuations.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 2, 'pin_roles': 'two leads, no signal direction (the ceramic/film ones)',
        'connects_to': "across power and ground, close to a sensor or motor — not wired to a signal pin itself", 'connects_to_kinds': '',
        'electrical_notes': 'undetermined (no farad/voltage rating printed on the cited page)',
        'polarity': "the electrolytic (cylindrical) one is polarized — its own package drawing marks a - and + leg",
        'kit_quantity': 'undetermined', 'source': _page(6),
    }),
    ('dc-motor', 'DC Motor', {
        'what_it_is': "Converts electrical energy into mechanical energy — internal coils become magnetized when "
                      "current flows, spinning the shaft; reversing the current reverses the spin direction.",
        'interface_kind': 'via-driver',
        'driver_needed': "an H-bridge IC (or a transistor + flyback diode for one-direction control) — never wire a motor "
                         "directly to an Arduino pin (a motor draws well over the 20 mA/I-O-pin limit, board_uno fact pinout.max_current_io)",
        'pin_count': 2, 'pin_roles': 'two leads, reversible (no fixed polarity) — direction follows current direction',
        'connects_to': "digital-out/pwm-out through the H-bridge's control pins; the motor's own leads go to the driver's output, never the Arduino directly",
        'connects_to_kinds': 'via-driver',
        'electrical_notes': 'undetermined (no voltage/current rating printed on the cited page)',
        'polarity': "reversible by design (the book: \"If the direction of the electricity is reversed, the motor will spin in the opposite direction.\")",
        'kit_quantity': 'undetermined', 'source': _page(6),
    }),
    ('diode', 'Diode', {
        'what_it_is': "Ensures electricity flows in one direction only; useful across a motor or other high current/voltage load.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 2, 'pin_roles': 'anode (+) and cathode (banded end, -)',
        'connects_to': "often placed across a motor/relay/load for protection — not wired to a signal pin itself", 'connects_to_kinds': '',
        'electrical_notes': 'undetermined', 'polarity': "cathode = the banded end (the book: \"The cathode is usually marked with a band on one side of the component's body.\")",
        'kit_quantity': 'undetermined', 'source': _page(7),
    }),
    ('jumper-wires', 'Jumper Wires', {
        'what_it_is': "Connect components to each other on the breadboard, and to the Arduino.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "any pin — pure wiring, carries whatever signal or power is at its ends", 'connects_to_kinds': '',
        'electrical_notes': '', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(7),
    }),
    ('led', 'LED (Light Emitting Diode)', {
        'what_it_is': "A diode that illuminates when electricity passes through it; current flows one way only.",
        'interface_kind': 'digital-out',
        'driver_needed': "a series resistor to limit current (the kit's own projects commonly use 220 ohm for this LED; that exact "
                         "value is not printed on this page — see Resistors, p.9, for the colour-code table)",
        'pin_count': 2, 'pin_roles': 'anode (longer leg, to the resistor/signal side), cathode (shorter leg, to GND)',
        'connects_to': "digital-out (on/off) or pwm-out on a ~ pin (to dim/fade), + GND, through its series resistor",
        'connects_to_kinds': 'digital-out,pwm-out,ground',
        'electrical_notes': "undetermined (no forward-voltage/current rating printed on the cited page; the 20 mA/I-O-pin limit, "
                            "board_uno fact pinout.max_current_io, is why a series resistor is needed)",
        'polarity': "anode = longer leg, cathode = shorter leg (the book: \"The anode ... is usually the longer leg, and the cathode is the shorter leg.\")",
        'kit_quantity': 'undetermined (4 colours pictured: blue, green, red, yellow — not a stated count)', 'source': _page(7),
    }),
    ('gels', 'Gels (red, green, blue)', {
        'what_it_is': "Filter out different wavelengths of light; used with a phototransistor so it only reacts to the filtered colour.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "placed optically in front of a phototransistor — no electrical connection of its own", 'connects_to_kinds': '',
        'electrical_notes': '', 'polarity': '', 'kit_quantity': 'undetermined (3 colours pictured)', 'source': _page(7),
    }),
    ('h-bridge', 'H-Bridge', {
        'what_it_is': "A circuit that lets you control the polarity of the voltage applied to a load (usually a motor); "
                      "the kit's H-bridge is an integrated circuit, though it could be built from discrete parts.",
        'interface_kind': 'digital-out', 'driver_needed': '',
        'pin_count': 0, 'pin_roles': 'undetermined (the IC pinout is not printed on the cited page)',
        'connects_to': "digital-out (direction control, x2 typical) + pwm-out (speed) + 5V/GND, with the DC motor's leads on its output side",
        'connects_to_kinds': 'digital-out,pwm-out',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(7),
        'notes': 'this is the driver_needed part for "DC Motor", above',
    }),
    ('lcd-16x2', 'Liquid Crystal Display (LCD, 16x2)', {
        'what_it_is': "An alphanumeric/graphic display based on liquid crystals; this one has 2 rows of 16 characters each.",
        'interface_kind': 'digital-out', 'driver_needed': '',
        'pin_count': 6, 'pin_roles': 'typical 4-bit wiring: RS, E, D4, D5, D6, D7 (plus power/ground/contrast, which are not signal pins) '
                                     '— the exact pinout is not printed on the cited page',
        'connects_to': "6 digital-out pins typical (4-bit mode) + 5V/GND + a contrast pot", 'connects_to_kinds': 'digital-out',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(7),
    }),
    ('male-header-pins', 'Male Header Pins', {
        'what_it_is': "Pins that fit into female sockets, like those on a breadboard, making connections easier.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "mechanical only", 'connects_to_kinds': '', 'electrical_notes': '', 'polarity': '',
        'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('optocoupler', 'Optocoupler (4N35)', {
        'what_it_is': "Connects two circuits that do not share a common power supply; an internal LED, when lit, "
                      "closes an internal photoreceptor-driven switch that replaces a switch in the second circuit.",
        'interface_kind': 'via-driver', 'driver_needed': "a series resistor on the input (+) LED side",
        'pin_count': 0, 'pin_roles': "input side: the + pin lights the internal LED; output side: two pins act like a switch",
        'connects_to': "digital-out drives the input + pin through a resistor; the output pair wires into the second, isolated circuit",
        'connects_to_kinds': 'via-driver,digital-out',
        'electrical_notes': 'undetermined', 'polarity': "input side is polarized (the book: \"When you apply voltage to the + pin, the LED lights.\")",
        'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('piezo', 'Piezo', {
        'what_it_is': "An electrical component that can detect vibrations and create noises.",
        'interface_kind': 'digital-out', 'driver_needed': '', 'pin_count': 2, 'pin_roles': 'two leads, no polarity stated on the cited page',
        'connects_to': "digital-out (commonly driven with tone(), any digital pin — not limited to ~ PWM pins) + GND",
        'connects_to_kinds': 'digital-out,pwm-out', 'electrical_notes': 'undetermined', 'polarity': 'undetermined (not stated on the cited page)',
        'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('potentiometer', 'Potentiometer', {
        'what_it_is': "A variable resistor with three pins; the middle pin (wiper) divides the fixed resistor into two "
                      "halves, giving a voltage that changes as you turn the knob.",
        'interface_kind': 'analog-in', 'driver_needed': '', 'pin_count': 3, 'pin_roles': 'two end pins to 5V and GND, middle pin (wiper) = the analog-in signal',
        'connects_to': "analog-in (wiper) + 5V and GND (ends)", 'connects_to_kinds': 'analog-in,power,ground',
        'electrical_notes': "0-5V at the wiper when the ends are at 5V/GND (the book: \"the middle leg will give the difference in voltage as you turn the knob\")",
        'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('pushbutton', 'Pushbutton', {
        'what_it_is': "A momentary switch that closes a circuit when pressed; good for detecting on/off signals.",
        'interface_kind': 'digital-in', 'driver_needed': "a pull-down or pull-up resistor — a bare pushbutton leaves the pin floating when not pressed",
        'pin_count': 4, 'pin_roles': 'two legs per side, internally joined in pairs — one side to the signal (+ pull resistor), the other to GND or 5V',
        'connects_to': "digital-in + GND/5V through a pull resistor", 'connects_to_kinds': 'digital-in,power,ground',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('resistors', 'Resistors', {
        'what_it_is': "Resist the flow of electrical energy in a circuit, changing voltage and current; values are in "
                      "ohms, read from colour-coded stripes.",
        'interface_kind': '', 'driver_needed': '', 'pin_count': 2, 'pin_roles': 'two leads, no direction',
        'connects_to': "in series with an LED, or as a pull-up/pull-down for a button or sensor — never wired to a pin by itself", 'connects_to_kinds': '',
        'electrical_notes': "value read from the colour-code bands (a described table; exact ohm values of the kit's own resistors are not listed on the cited page)",
        'polarity': '', 'kit_quantity': 'undetermined (4 value-bands pictured, not a stated count)', 'source': _page(9),
    }),
    ('phototransistor', 'Phototransistor', {
        'what_it_is': "Generates a current proportional to the quantity of light absorbed.",
        'interface_kind': 'analog-in', 'driver_needed': "a pull-up or pull-down resistor to turn its light-dependent current into a readable voltage",
        'pin_count': 2, 'pin_roles': 'two leads (collector/emitter) — see a phototransistor reference for which is which; not itemized on the cited page',
        'connects_to': "analog-in through a pull resistor + 5V/GND", 'connects_to_kinds': 'analog-in,power,ground',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(8),
    }),
    ('servo', 'Servo Motor', {
        'what_it_is': "A type of geared motor that can only rotate 180 degrees; controlled by electrical pulses from "
                      "the Arduino that tell it what position to move to.",
        'interface_kind': 'servo-pwm', 'driver_needed': '', 'pin_count': 3, 'pin_roles': 'signal (pulses), +5V, GND',
        'connects_to': "servo-pwm (signal) + 5V/GND", 'connects_to_kinds': 'servo-pwm,power,ground',
        'electrical_notes': 'undetermined (no current rating printed on the cited page)', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(9),
    }),
    ('tmp36', 'Temperature Sensor (TMP36)', {
        'what_it_is': "Changes its voltage output depending on its temperature; the voltage on the centre pin changes "
                      "as it warms or cools.",
        'interface_kind': 'analog-in', 'driver_needed': '', 'pin_count': 3,
        'pin_roles': "left leg = power, centre pin = signal (analog-in), right leg = ground, as oriented flat-side-toward-you "
                     "in the book's drawing (the book: \"The outside legs connect to power and ground.\")",
        'connects_to': "analog-in (centre) + 5V and GND (outer legs)", 'connects_to_kinds': 'analog-in,power,ground',
        'electrical_notes': "10 mV/degC scale, 500 mV offset at 25 degC (board.custom.uno_facts tmp36.scale / tmp36.offset — cited to the "
                            "Analog Devices TMP35/36/37 datasheet; that datasheet itself was NOT re-fetched this session, uno_facts.TMP36_REV)",
        'polarity': '', 'kit_quantity': 'undetermined', 'source': '%s + Analog Devices TMP35/TMP36/TMP37 datasheet (not re-fetched; see board.custom.uno_facts.TMP36_REV)' % _page(9),
    }),
    ('tilt-sensor', 'Tilt Sensor', {
        'what_it_is': "A switch that opens or closes depending on its orientation; typically a hollow cylinder with a "
                      "metal ball that connects two leads when tilted the right way.",
        'interface_kind': 'digital-in', 'driver_needed': "a pull-down or pull-up resistor, same as a pushbutton",
        'pin_count': 2, 'pin_roles': 'two leads, no fixed polarity',
        'connects_to': "digital-in + GND/5V through a pull resistor", 'connects_to_kinds': 'digital-in,power,ground',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(9),
    }),
    ('transistor', 'Transistor', {
        'what_it_is': "A three-legged device that can operate as an electronic switch, useful for controlling high "
                      "current/high voltage components like motors.",
        'interface_kind': 'digital-out', 'driver_needed': "a base-current-limiting resistor, sized for the switched load — not the Arduino pin's own 20 mA rating",
        'pin_count': 3, 'pin_roles': "ground, load (the controlled component), Arduino pin (the switching signal) — the book: \"One pin connects "
                                     "to ground, another to the component being controlled, and the third connects to the Arduino.\"",
        'connects_to': "digital-out (base, through a resistor) + GND + the switched load", 'connects_to_kinds': 'digital-out,via-driver',
        'electrical_notes': 'undetermined', 'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(9),
    }),
    ('usb-cable', 'USB Cable', {
        'what_it_is': "Connects the Arduino Uno to a computer for programming; also provides power to the Arduino for "
                      "most of the kit's projects.",
        'interface_kind': 'uart', 'driver_needed': '', 'pin_count': 0, 'pin_roles': '',
        'connects_to': "the board's USB port (power + upload + Serial Monitor, via the 16U2 bridge — board_uno hardware().usb_bridge_chip)",
        'connects_to_kinds': 'uart,power', 'electrical_notes': "5V bus power (board_uno fact pinout.power_header reused; no separate USB-specific current fact cited)",
        'polarity': '', 'kit_quantity': 'undetermined', 'source': _page(9),
    }),
]

#: part key -> case-insensitive words that tie it to a seeded Capability's own text (cmod.custom.capabilities) —
#: NOT a KitPart field; consumed only by _sample_capabilities so a new capability mentioning a part is picked up
#: without a second, hand-maintained list drifting out of sync.
_SAMPLE_TERMS = {
    'tmp36': ('tmp36', 'temp sensor', 'temperature sensor'),
    'led': ('d13', 'led_builtin', 'led.on', "board's led"),
}


def _sample_capabilities(part_key):
    terms = _SAMPLE_TERMS.get(part_key)
    if not terms:
        return []
    try:
        from cmod.custom.capabilities import SEED_CAPABILITIES
    except Exception:  # pragma: no cover — cmod absent: no sample can be named, never guessed
        return []
    out = []
    for cap in SEED_CAPABILITIES:
        text = ' '.join(str(cap.get(k, '')) for k in ('title', 'goal', 'purpose', 'required_targets')).lower()
        if any(t in text for t in terms):
            out.append(cap['name'])
    return sorted(set(out))


_ROWS = None


def rows():
    """[KitPart dict, ...] — built once (sample_capabilities is derived from cmod, read fresh on first call)."""
    global _ROWS
    if _ROWS is None:
        out = []
        for key, title, fields in _PARTS:
            row = {'name': '%s:%s' % (KIT, key), 'kit': KIT, 'title': title, 'source': PARTS_PAGES, 'notes': '',
                   'connects_to_kinds': '', 'sample_capabilities': ','.join(_sample_capabilities(key))}
            row.update(fields)
            out.append(row)
        _ROWS = out
    return [dict(r) for r in _ROWS]


def parts_without_sample():
    """Names of every KitPart with no sample_capabilities yet — the backlog the kit-parts table itself names."""
    return [r['name'] for r in rows() if not r.get('sample_capabilities')]


def by_name(name):
    return next((r for r in rows() if r['name'] == name), None)


def _connects_to_kinds_set(row):
    return {k.strip() for k in (row.get('connects_to_kinds') or '').split(',') if k.strip()}


def pin_kinds(pin, r):
    """{kind, ...} this board pin (or power/reference label) satisfies — the same vocabulary connects_to_kinds uses:
    board.custom.target_compat.TASK_KINDS for a real BoardPin, or power/ground/reference for a connector-only label."""
    from board.custom import power_pins as PP
    label = PP.label_for(pin)
    if label == 'GND':
        return {'ground'}
    if label in ('+5V', '+3V3', 'VIN'):
        return {'power'}
    if label in ('IOREF', 'AREF', 'RESET'):
        return {'reference'}
    from board.custom import board_object as BO
    from board.custom import target_compat as TC
    bp = BO.pin_by_canonical(r, pin)
    if bp is None:
        return set()
    soc_by_pin = {s['pin']: s for s in r.get('soc_pins', [])}
    soc_pin = soc_by_pin.get(bp.get('soc_pin') or '')
    kinds = set()
    for kind in TC.TASK_KINDS:
        if kind in TC.NEVER_ASSIGNABLE:
            continue
        verdict, _reason = TC.compatible(kind, bp, soc_pin)
        if verdict == 'ok':
            kinds.add(kind)
    return kinds


def parts_for_pin(pin, r):
    """fs-2d item 3: [{name, title, interface_kind}, ...] — every KitPart whose connects_to_kinds intersects this
    pin's own kinds (pin_kinds, above). This is the "Parts that connect here" list (board.board_object_api,
    board.custom.power_pins) — derived, never a second hand-written per-pin list."""
    kinds = pin_kinds(pin, r)
    if not kinds:
        return []
    out = [{'name': row['name'], 'title': row['title'], 'interface_kind': row['interface_kind']}
           for row in rows() if _connects_to_kinds_set(row) & kinds]
    return sorted(out, key=lambda x: x['name'])
