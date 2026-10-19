"""@module electrodevice.objects.layout._shared — what the layout row classes share (constants, seeds, helpers) (lay-0)."""

# ---------------------------------------------------------------- the board family (BoardModel seeds)
#: Hole pitch of a solderless breadboard: 0.1 in = 2.54 mm, the standard grid of DIP parts and header pins.
PITCH_MM = 2.54
BREADBOARD_SOURCE = ('the common industry layout of the 400- and 830-tie-point solderless breadboards: numbered strips of 5+5 holes split by the centre trench, '
                     'two power-rail pairs (top and bottom) of 25 (half) or 50 (full) holes each; NO datasheet read for this kit (KitPart arduino-starter-kit:breadboard '
                     'lists the part with its size and quantity undetermined)')

SEED_BOARD_MODELS = [
    {'name': 'breadboard-half', 'kind': 'breadboard', 'size': 'half', 'rows': 30, 'holes_per_side': 5, 'rail_holes': 25, 'pitch_mm': PITCH_MM,
     'nominal_ties': 400, 'board_definition': '', 'status': 'built', 'source': BREADBOARD_SOURCE,
     'description': 'Half-size breadboard: 30 strips x 10 holes = 300 terminal ties + 4 rails x 25 = 100 bus ties = 400 ties.'},
    {'name': 'breadboard-full', 'kind': 'breadboard', 'size': 'full', 'rows': 63, 'holes_per_side': 5, 'rail_holes': 50, 'pitch_mm': PITCH_MM,
     'nominal_ties': 830, 'board_definition': '', 'status': 'built', 'source': BREADBOARD_SOURCE,
     'description': 'Full-size breadboard: 63 strips x 10 holes = 630 terminal ties + 4 rails x 50 = 200 bus ties = 830 ties.'},
    {'name': 'uno-r3', 'kind': 'devboard', 'size': '', 'rows': 0, 'holes_per_side': 0, 'rail_holes': 0, 'pitch_mm': PITCH_MM,
     'nominal_ties': 0, 'board_definition': 'arduino-uno-r3', 'status': 'built',
     'source': 'the header pins are the BoardPin rows of arduino-uno-r3 plus the connector power labels (board.custom.board_uno.CONNECTORS); nothing is stored here',
     'description': 'The Arduino UNO R3 as a board in a layout: its headers are the places a wire can start.'},
    {'name': 'protoboard', 'kind': 'protoboard', 'size': '', 'rows': 0, 'holes_per_side': 0, 'rail_holes': 0, 'pitch_mm': PITCH_MM,
     'nominal_ties': 0, 'board_definition': '', 'status': 'reserved', 'source': 'reserved: no geometry yet (a soldered board, enclosure stage S2)',
     'description': 'RESERVED. A protoboard model has no geometry yet; layouts on it are refused in words until it is built.'},
    {'name': 'pcb', 'kind': 'pcb', 'size': '', 'rows': 0, 'holes_per_side': 0, 'rail_holes': 0, 'pitch_mm': PITCH_MM,
     'nominal_ties': 0, 'board_definition': '', 'status': 'reserved', 'source': 'reserved: no geometry yet (a printed board, from the pcb module)',
     'description': 'RESERVED. A PCB model has no geometry yet; layouts on it are refused in words until it is built.'},
]

# ---------------------------------------------------------------- the boards on the bench (BenchBoard seeds)
#: The default bench: a half breadboard (his answer 2026-10-19: the kit page does not say which, so the default is half and the size stays undetermined).
BENCH_DEFAULT = 'bench-half-1'
SEED_BENCH_BOARDS = [
    {'name': 'bench-half-1', 'model_name': 'breadboard-half', 'label': 'half breadboard', 'owner': '',
     'notes': 'The default bench board. The kit lists a breadboard without a size; half (400 ties) is the default until the owner says which is on the bench.', 'migrated_from': ''},
    {'name': 'bench-full-1', 'model_name': 'breadboard-full', 'label': 'full breadboard', 'owner': '',
     'notes': 'A full-size breadboard (830 ties), for builds that need more room.', 'migrated_from': ''},
    {'name': 'bench-uno-1', 'model_name': 'uno-r3', 'label': 'Arduino UNO', 'owner': '',
     'notes': 'The UNO the breadboard is wired to.', 'migrated_from': ''},
]


def migrated_bench_boards(breadboards):
    """BenchBoard seed dicts for the older BreadboardDefinition seeds (converge by name: same name, the model chosen by rows; the old rows are kept)."""
    out = []
    for b in breadboards:
        model = 'breadboard-full' if int(b.get('rows', 30)) >= 63 else 'breadboard-half'
        out.append({'name': b['name'], 'model_name': model, 'label': b.get('description', ''), 'owner': '',
                    'notes': 'Converged from the older BreadboardDefinition row of the same name (the row is kept).', 'migrated_from': 'BreadboardDefinition:%s' % b['name']})
    return out


# ---------------------------------------------------------------- wire colours
#: Colour NAMES a wire can be, with the drawing hex of each. A drawing knob (only distinctness matters), except that every pin-view family hex maps to the nearest name
#: (colour_name_of_hex) so the seeded scheme and the pin view agree.
WIRE_COLOURS = {'red': '#d32f2f', 'black': '#212121', 'orange': '#e65100', 'blue': '#1565c0', 'green': '#2e7d32', 'purple': '#6a1b9a', 'pink': '#ad1457',
                'yellow': '#f9a825', 'grey': '#78909c', 'white': '#f5f5f5', 'brown': '#5d4037', 'olive': '#9e9d24', 'teal': '#00838f'}
#: A hex whose brightest channel is below this is drawn and named black (a dark grey wire is a black wire: the pin view paints ground #424242).
BLACK_BELOW = 0x50

SCHEME_DEFAULT = 'wires-pin-view'
#: The seeded scheme, VALUES = colour_name_of_hex(board.custom.pv_families.FALLBACK_HEX[family]) (the selftest re-derives them and fails on any drift).
SEED_WIRE_COLOR_SCHEMES = [
    {'name': SCHEME_DEFAULT, 'display_name': 'Pin view colours', 'seeded': True, 'copy_of': '',
     'follows': 'board.custom.pv_families.FALLBACK_HEX (the pin view family tokens --pin-<family>), each hex named by its nearest wire colour',
     'description': 'Red is 5 V (and other supply), black is GND, and a signal wire takes the colour the pin view paints its pin family. Copy it to change it.',
     'colors_json': '{"power": "red", "ground": "black", "gpio": "grey", "pwm-timer": "orange", "analog": "blue", "uart": "green", "spi": "pink", "i2c": "purple", '
                    '"interrupt": "teal", "usb": "brown", "clock": "olive", "reset-programming": "brown", "default": "grey"}',
     'notes': 'Seeded: never edited in place; copy before editing.'},
]


def colour_name_of_hex(hexstr):
    """The wire colour name nearest a hex (squared RGB distance); a very dark hex is black."""
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))   # noqa: E731
    c = rgb(hexstr)
    if max(c) < BLACK_BELOW:
        return 'black'
    return min(sorted(WIRE_COLOURS), key=lambda n: sum((a - b) ** 2 for a, b in zip(rgb(WIRE_COLOURS[n]), c)))
