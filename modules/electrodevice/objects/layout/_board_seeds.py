"""@module electrodevice.objects.layout._board_seeds — the board models and their composed rows (D-bob-3 2026-10-30).

One model per kind of board (the older board.BreadboardModel seeds and lay-0's BoardModel seeds merged), and beside it only the rows that apply:
a BreadboardLayout per breadboard, a BoardOutline where a vendor STATES a size, a BoardRating where a vendor states (or explicitly does not state) a rating.
"""

#: Hole pitch of a solderless breadboard: 0.1 in = 2.54 mm, the standard grid of DIP parts and header pins.
PITCH_MM = 2.54
BREADBOARD_SOURCE = ('the common industry layout of the 400- and 830-tie-point solderless breadboards: numbered strips of 5+5 holes split by the centre trench, '
                     'two power-rail pairs (top and bottom) of 25 (half) or 50 (full) holes each; NO datasheet read for this kit (KitPart arduino-starter-kit:breadboard '
                     'lists the part with its size and quantity undetermined)')
#: the older board.BreadboardModel names -> the merged model (a Bench saved before the merge still resolves)
MODEL_ALIASES = {'half-400': 'breadboard-half', 'full-830': 'breadboard-full'}

_BUD = 'bud-bb-32650-w'

SEED_BOARD_MODELS = [
    {'name': 'breadboard-half', 'title': 'Half-size breadboard, 400 tie points', 'kind': 'breadboard', 'vendor': 'generic', 'part_number': '', 'status': 'built',
     'board_definition': '', 'description': 'Half-size breadboard: 30 strips x 10 holes = 300 terminal ties + 4 rails x 25 = 100 bus ties = 400 ties.',
     'notes': 'the layout engine\'s default board'},
    {'name': 'breadboard-full', 'title': 'Full-size breadboard, 830 tie points', 'kind': 'breadboard', 'vendor': 'generic', 'part_number': '', 'status': 'built',
     'board_definition': '', 'description': 'Full-size breadboard: 63 strips x 10 holes = 630 terminal ties + 4 rails x 50 = 200 bus ties = 830 ties.', 'notes': ''},
    {'name': 'mini-170', 'title': 'Mini breadboard, 170 tie points, no rails', 'kind': 'breadboard', 'vendor': 'generic', 'part_number': '', 'status': 'built',
     'board_definition': '', 'description': 'Mini breadboard: 17 strips x 10 holes = 170 ties; no power rails.', 'notes': ''},
    {'name': _BUD, 'title': 'BUD Industries BB-32650-W - double-strip solderless breadboard, 170 tie-points, white', 'kind': 'breadboard', 'vendor': 'BUD Industries',
     'part_number': 'BB-32650-W', 'status': 'built', 'board_definition': '', 'description': 'A 170-tie-point double-strip breadboard with no power rails.',
     'notes': 'two on the bench 2026-10-24. The seed first said 70 tie points from the DigiKey title "BREADBRD DBL STRIP 70TIE-PTS WHT"; BUD and the DigiKey attribute '
              'table both say 170 (the title drops the 1).'},
    {'name': 'starter-kit-breadboard', 'title': 'The Arduino Starter Kit\'s breadboard', 'kind': 'breadboard', 'vendor': 'Arduino', 'part_number': '', 'status': 'unverified',
     'board_definition': '', 'description': 'The kit\'s breadboard; its size is not stated anywhere read.',
     'notes': 'the kit book lists "Breadboard" without a tie count (KitPart arduino-starter-kit:breadboard); count the rows on the real one before drawing it.'},
    {'name': 'uno-r3', 'title': 'Arduino UNO R3', 'kind': 'devboard', 'vendor': 'Arduino', 'part_number': '', 'status': 'built', 'board_definition': 'arduino-uno-r3',
     'description': 'The Arduino UNO R3 as a board in a layout: its headers are the places a wire can start.',
     'notes': 'the header pins are the BoardPin rows of arduino-uno-r3 plus the connector power labels (board.custom.board_uno.CONNECTORS); nothing is stored here'},
    {'name': 'protoboard', 'title': 'Protoboard', 'kind': 'protoboard', 'vendor': '', 'part_number': '', 'status': 'reserved', 'board_definition': '',
     'description': 'RESERVED. A protoboard model has no geometry yet; layouts on it are refused in words until it is built.',
     'notes': 'reserved: no geometry yet (a soldered board, enclosure stage S2)'},
    {'name': 'pcb', 'title': 'Printed circuit board', 'kind': 'pcb', 'vendor': '', 'part_number': '', 'status': 'reserved', 'board_definition': '',
     'description': 'RESERVED. A PCB model has no geometry yet; layouts on it are refused in words until it is built.',
     'notes': 'reserved: an ingested PCB is a Board on the Bench through its own stored footholds (pcb module), not through a model'},
]


def _layout(model, size, rows, rails, rail_holes, ties, basis, holes_per_side=5):
    return {'name': model, 'board_model': model, 'size': size, 'rows': rows, 'holes_per_side': holes_per_side, 'rails': rails, 'rail_holes': rail_holes,
            'pitch_mm': PITCH_MM, 'tie_points': ties, 'basis': basis}


SEED_BREADBOARD_LAYOUTS = [
    _layout('breadboard-half', 'half', 30, 4, 25, 400, BREADBOARD_SOURCE),
    _layout('breadboard-full', 'full', 63, 4, 50, 830, BREADBOARD_SOURCE),
    _layout('mini-170', 'mini', 17, 0, 0, 170, 'the common mini layout: 17 strips x 10 holes, no rails; no datasheet read'),
    _layout(_BUD, 'mini', 17, 0, 0, 170,
            'cited: BUD Industries product page "Breadboard Kits-White BB-32650-W" (https://www.budind.com/product/general-use-boxes/breadboard-series/breadboard-kits-3/, '
            'printed 2021-09-27; BUD publishes no PDF datasheet for this family): "Double-strip", "170 tie-points". DigiKey 377-BB-32650-W-ND attributes: Number of '
            'Terminal Strips 1, Number of 5-Tie Point Terminals 34, Number of Tie Points (Total) 170. Derived: 34 five-point terminals = 17 columns x (a-e, f-j) = 170, '
            'so rows 17, no power rails (rails 0, rail_holes 0); neither source mentions rails. "Double-strip" is BUD\'s word; no source states the row count.'),
    _layout('starter-kit-breadboard', 'unverified', -1, -1, -1, -1, 'unverified: only the vendor label is known; count the real board before drawing it'),
]

SEED_BOARD_OUTLINES = [
    {'name': _BUD, 'board_model': _BUD, 'width_mm': 47.0, 'height_mm': 36.1, 'drawable': False,
     'basis': 'cited: BUD product page "External Size L x W x D: 1.85" x 1.42" x 0.33"" (= 47.0 x 36.1 x 8.4 mm); DigiKey 1.85" L x 1.42" W (47.0mm x 36.1mm). '
              'NOT drawable yet: pv_shapes.breadboard_geometry(17, 0) generates 48.26 x 35.56 mm - the height is within 0.6 mm but the width is 1.26 mm off '
              '(outline margin unknown), over the 1.0 mm tolerance.'},
]

SEED_BOARD_RATINGS = [
    {'name': _BUD, 'board_model': _BUD, 'rail_voltage_max_v': -1.0, 'rail_current_max_a': -1.0,
     'basis': 'n/a: no power rails; BUD product page (fetched 2026-10-25) states no voltage/current rating'},
]
