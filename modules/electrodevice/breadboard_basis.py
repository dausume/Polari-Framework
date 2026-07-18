"""
@module electrodevice.breadboard_basis

ncg-5: the BREADBOARD level — the circuit-diagram no-code humans
physically recognize. A board's connectivity IS its netlist: every
tie-point row is one net (left/right of the center trench are
separate strips), the power rails run the board's length, and a
placed component's pins land ON tie points instead of abstract nets.
Larger circuits = MORE BOARDS: BoardJumper rows join nets across
boards, and a populated board can re-wrap as a .subckt with named
external pins — the circuit-world mirror of SolutionInvocation
(board-as-component).

Tie-point grammar (tiepoints_json entries):
  'r<N>L' / 'r<N>R'  row N, left/right of the trench
  'vplus' / 'gnd'    the power rails ('gnd' is SPICE ground 0)

MCU and FPGA pins need no special kind at this level: a driven pin
IS a voltage source placement ('vsource'); ncg-6 binds those sources
to a LogicBlockDesign's evaluated outputs.

@consumers
  - electrodevice.breadboard_netlist (connectivity compiler)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class BreadboardDefinition(treeObject):
    """One physical board (rows of tie strips + two rails)."""

    @treeObjectInit
    def __init__(self, name: str = '', rows: int = 30,
                 description: str = '', manager=None):
        self.name = name
        self.rows = rows
        self.description = description


class ComponentPlacement(treeObject):
    """One component PLUGGED INTO a board — same electrical fields
    as CircuitComponentDefinition, but wired by tie points."""

    @treeObjectInit
    def __init__(self, name: str = '', board_name: str = '',
                 kind: str = 'resistor', params_json: str = '{}',
                 # Ordered tie points (element node order), e.g.
                 # '["r5L", "r7L"]' or '["vplus", "r3R"]'.
                 tiepoints_json: str = '[]',
                 device_name: str = '',
                 description: str = '', manager=None):
        self.name = name
        self.board_name = board_name
        self.kind = kind
        self.params_json = params_json
        self.tiepoints_json = tiepoints_json
        self.device_name = device_name
        self.description = description


class BoardJumper(treeObject):
    """One wire between two boards (or two strips of one board) —
    the nets it touches become ONE net."""

    @treeObjectInit
    def __init__(self, name: str = '', board_a: str = '',
                 tie_a: str = '', board_b: str = '',
                 tie_b: str = '', description: str = '',
                 manager=None):
        self.name = name
        self.board_a = board_a
        self.tie_a = tie_a
        self.board_b = board_b
        self.tie_b = tie_b
        self.description = description


#: Seeds: the LED branch REBUILT AS PLACEMENTS, twice —
#: single-board, and split across two jumpered boards. Identical
#: currents between the two (and vs the ncg-4 row circuit) is the
#: acceptance bar.
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
