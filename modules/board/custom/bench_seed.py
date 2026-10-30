"""
@module board.custom.bench_seed

bench-0: the one seeded Bench. Its breadboards name BoardModel rows (D-bob-3 2026-10-30: the older BreadboardModel seeds moved to
electrodevice.objects.layout._board_seeds - one model + its BreadboardLayout / BoardOutline / BoardRating). The seeded bench is what he showed on 2026-10-24 (part names only); its boards and breadboards are
NOT converged (a person's additions stay).
"""
import json


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
