"""
@module board.custom.bench_seed

bench-0: the BreadboardModel rows and the one seeded Bench. Breadboard geometry is DERIVED from the row and hole counts at the 2.54 mm pitch
by `board.custom.pv_shapes.breadboard_geometry` (the same function that draws the breadboard in the pin view) - a model with only a vendor label
says `unverified` and has no dimensions. The seeded bench is what he showed on 2026-10-24 (part names only); its boards and breadboards are
NOT converged (a person's additions stay).
"""
import json


def _geo(rows, rail_holes):
    try:
        from board.custom import pv_shapes as PV
        g = PV.breadboard_geometry(rows, rail_holes)
        return float(g['w']), float(g['h']), True, 'derived: pv_shapes.breadboard_geometry(rows=%d, rail_holes=%d) at the 2.54 mm pitch' % (rows, rail_holes)
    except Exception:  # noqa: BLE001 - the geometry helper is the pin view's; without it the model says so
        return -1.0, -1.0, False, 'undetermined: pv_shapes.breadboard_geometry unavailable'


def _model(name, title, vendor, part_number, kind, tie_points, rows, rail_holes, rails, notes='', basis=''):
    if rows > 0 and rail_holes >= 0:
        w, h, known, b = _geo(rows, rail_holes)
    else:
        w, h, known, b = -1.0, -1.0, False, basis or 'unverified: only the vendor label is known; the datasheet is needed for the geometry'
    return {'name': name, 'title': title, 'vendor': vendor, 'part_number': part_number, 'kind': kind, 'tie_points': tie_points, 'rows': rows,
            'rail_holes': rail_holes, 'rails': rails, 'width_mm': w, 'height_mm': h, 'geometry_known': known, 'basis': basis or b, 'notes': notes}


SEED_BREADBOARD_MODELS = [
    _model('half-400', 'Half-size breadboard, 400 tie points', 'generic', '', 'half', 400, 30, 25, 4,
           notes='30 rows x 10 (a-e, f-j) = 300 + 4 rails x 25 = 100; the layout engine\'s default board (rows 30, rail_holes 25)'),
    _model('full-830', 'Full-size breadboard, 830 tie points', 'generic', '', 'full', 830, 63, 50, 4,
           notes='63 rows x 10 = 630 + 4 rails x 50 = 200'),
    _model('mini-170', 'Mini breadboard, 170 tie points, no rails', 'generic', '', 'mini', 170, 17, 0, 0, notes='17 rows x 10; no power rails'),
    _model('bud-bb-32650-w', 'BUD Industries BB-32650-W - "breadboard, double strip, 70 tie points, white" (as labelled)', 'BUD Industries', 'BB-32650-W',
           'unverified', 70, -1, -1, -1,
           notes='two on the bench 2026-10-24 (DigiKey 377-BB-32650-W-ND). Whether "double strip" means two terminal strips or two bus strips is unverified: read the BUD datasheet before drawing it.'),
    _model('starter-kit-breadboard', 'The Arduino Starter Kit\'s breadboard', 'Arduino', '', 'unverified', -1, -1, -1, -1,
           notes='the kit book lists "Breadboard" without a tie count (KitPart arduino-starter-kit:breadboard); count the rows on the real one before drawing it.'),
]

HOME_BENCH = 'home-bench'

SEED_BENCHES = [{
    'name': HOME_BENCH, 'title': 'The home bench',
    'boards_json': json.dumps([
        {'board': 'arduino-uno-r3', 'label': 'UNO #1', 'added': '2026-10-24', 'note': 'the Starter Kit\'s UNO R3 (box)'},
        {'board': 'arduino-zero', 'label': 'Zero #1', 'added': '2026-10-24', 'note': 'box'},
        {'board': 'adafruit-feather-m0-express', 'label': 'Feather M0 #1', 'added': '2026-10-24', 'note': 'order, with headers and two LiPo cells'},
        {'board': 'elecrow-esp32-eval', 'label': 'ESP32 eval #1', 'added': '2026-10-24', 'note': 'order label; module unverified'},
    ]),
    'breadboards_json': json.dumps([
        {'model': 'bud-bb-32650-w', 'count': 2, 'note': 'order label'},
        {'model': 'starter-kit-breadboard', 'count': 1, 'note': 'the kit\'s'},
    ]),
    'notes': 'Seeded from what was on the bench 2026-10-24 (part names only). Add and remove from /display/bench.',
    'source': 'MISSION_GENERIC_PLAN.md section 13.1 (2026-10-24)',
}]
