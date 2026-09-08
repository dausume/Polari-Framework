"""@module electrodevice.objects.breadboard._shared — what the breadboard row classes share (constants, seeds, helpers); split from breadboard_basis.py (sap-2c)."""

SEED_BREADBOARDS = [
    {'name': 'bb-demo-a', 'rows': 30,
     'description': 'single-board LED branch demo'},
    {'name': 'bb-split-1', 'rows': 30,
     'description': 'two-board demo: source + resistor board'},
    {'name': 'bb-split-2', 'rows': 30,
     'description': 'two-board demo: LED board'},
]
SEED_PLACEMENTS = [
    # bb-demo-a: FPGA pin (vsource) r1L, resistor r1L->r5L,
    # LED r5L->gnd rail.
    {'name': 'bba-vpin', 'board_name': 'bb-demo-a',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'tiepoints_json': '["r1L", "gnd"]',
     'description': 'FPGA pin as a driven rail'},
    {'name': 'bba-rlimit', 'board_name': 'bb-demo-a',
     'kind': 'device', 'params_json': '{}',
     'tiepoints_json': '["r1L", "r5L"]',
     'device_name': 'cnt-solgel-led-resistor',
     'description': 'derived CNT sol-gel resistor'},
    {'name': 'bba-led', 'board_name': 'bb-demo-a',
     'kind': 'led', 'params_json': '{}',
     'tiepoints_json': '["r5L", "gnd"]', 'description': ''},
    # The split version: source + resistor on board 1, LED on
    # board 2, joined by a jumper.
    {'name': 'bb1-vpin', 'board_name': 'bb-split-1',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'tiepoints_json': '["r1L", "gnd"]', 'description': ''},
    {'name': 'bb1-rlimit', 'board_name': 'bb-split-1',
     'kind': 'device', 'params_json': '{}',
     'tiepoints_json': '["r1L", "r9R"]',
     'device_name': 'cnt-solgel-led-resistor', 'description': ''},
    {'name': 'bb2-led', 'board_name': 'bb-split-2',
     'kind': 'led', 'params_json': '{}',
     'tiepoints_json': '["r2L", "gnd"]', 'description': ''},
]
SEED_JUMPERS = [
    {'name': 'jmp-split-signal', 'board_a': 'bb-split-1',
     'tie_a': 'r9R', 'board_b': 'bb-split-2', 'tie_b': 'r2L',
     'description': 'resistor output over to the LED board'},
]
