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


def _model(name, title, vendor, part_number, kind, tie_points, rows, rail_holes, rails, notes='', basis='', stated=None):
    """`stated` = (w_mm, h_mm) cited from a vendor page: recorded as the outline, but geometry_known stays False (the hole layout is not drawable
    from a stated outline alone; `basis` says why) - used when the derived outline disagrees with the stated one."""
    if stated:
        w, h, known, b = float(stated[0]), float(stated[1]), False, basis
    elif rows > 0 and rail_holes >= 0:
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
    _model('bud-bb-32650-w', 'BUD Industries BB-32650-W - double-strip solderless breadboard, 170 tie-points, white', 'BUD Industries', 'BB-32650-W',
           'mini', 170, 17, 0, 0, stated=(47.0, 36.1),
           basis='cited: BUD Industries product page "Breadboard Kits-White BB-32650-W" (https://www.budind.com/product/general-use-boxes/breadboard-series/breadboard-kits-3/, printed 2021-09-27; '
                 'BUD publishes no PDF datasheet for this family): "Double-strip", "170 tie-points", "External Size L x W x D: 1.85" x 1.42" x 0.33"" (= 47.0 x 36.1 x 8.4 mm). '
                 'DigiKey 377-BB-32650-W-ND attributes: Number of Terminal Strips 1, Number of 5-Tie Point Terminals 34, Number of Tie Points (Total) 170, 1.85" L x 1.42" W (47.0mm x 36.1mm). '
                 'Derived: 34 five-point terminals = 17 columns x (a-e, f-j) = 170, so rows 17, no power rails (rail_holes 0, rails 0); neither source mentions rails. '
                 'The hole layout is NOT drawable yet: pv_shapes.breadboard_geometry(17, 0) (no rail bands for a rail-less board) generates 48.26 x 35.56 mm vs the stated 47.0 x 36.1 mm - the height is within 0.6 mm but the width is 1.26 mm off (outline margin unknown), over the 1.0 mm tolerance.',
           notes='two on the bench 2026-10-24. The seed first said 70 tie points from the DigiKey title "BREADBRD DBL STRIP 70TIE-PTS WHT"; BUD and the DigiKey attribute table both say 170 (the title drops the 1). '
                 '"Double-strip" is BUD\'s word; no source states the row or column count, so rows 17 is derived from 34 terminals x 5 holes. '
                 'Generated 48.26 x 35.56 vs stated 47.0 x 36.1 mm (generator omits rail bands when rail_holes is 0): height is within 0.6 mm, width 1.26 mm off - margins unknown, so geometry_known stays False.'),
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
        {'board': 'elecrow-esp32-eval', 'label': 'ESP32-S3 e-paper #1', 'added': '2026-10-24',
         'note': 'order label; ESP32-S3 rev v0.2, 8 MB quad flash + 8 MB embedded PSRAM (N8R8 pairing), 40 MHz crystal - read by esptool over its CH340 bridge 2026-10-24; first derived from the header silk (IO20 + IO38)'},
    ]),
    'breadboards_json': json.dumps([
        {'model': 'bud-bb-32650-w', 'count': 2, 'note': 'order label'},
        {'model': 'starter-kit-breadboard', 'count': 1, 'note': 'the kit\'s'},
    ]),
    'notes': 'Seeded from what was on the bench 2026-10-24 (part names only). Add and remove from /display/bench.',
    'source': 'MISSION_GENERIC_PLAN.md section 13.1 (2026-10-24)',
}]
