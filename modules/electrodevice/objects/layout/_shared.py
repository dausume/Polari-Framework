"""@module electrodevice.objects.layout._shared — what the layout row classes share (constants, seeds, helpers) (lay-0)."""

# ---------------------------------------------------------------- the board family (D-bob-3: the models and their composed rows live in _board_seeds)
from electrodevice.objects.layout._board_seeds import (BREADBOARD_SOURCE, MODEL_ALIASES, PITCH_MM, SEED_BOARD_MODELS, SEED_BOARD_OUTLINES,  # noqa: F401,E402
                                                       SEED_BOARD_RATINGS, SEED_BREADBOARD_LAYOUTS)

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
