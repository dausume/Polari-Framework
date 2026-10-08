"""
@module board.objects.board.BoardPinNet

BoardPinNet — one class per file (design §7); ucd-0a defines it, ucd-0c populates it (UNO_CORE_DEMO_PLAN.md §5e Q2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardPinNet(treeObject):
    """What it is: ONE BOARD PIN PLACED ON ONE EXTERNAL CIRCUIT NET — "D6 is on net LED_CONTROL of circuit
    uno-button-clock". The ONE link between the board object (`BoardPin`) and the electrodevice circuit rows
    (`CircuitNetDefinition`, `CircuitComponentDefinition` — the breadboard as data, rendering to ngspice), so the same
    rows drive the electrical checks, the twin's pin-to-pin wiring and the wiring drawing. `role` says what the pin is
    on that net (driver = the pin drives it as an output; input = the pin reads it; power/ground = a rail). Authored
    with the circuit (a seed or the canvas), provenance says which; never a free string on either side.
    Related concepts: `BoardPin`, electrodevice's `CircuitNetDefinition` / `CircuitComponentDefinition` /
    `ComponentPlacement`, `BoardNet` (the board's OWN internal nets — a different thing, kept separate).
    """

    plain_words = ('A board-pin net link says which external wire (net) a board pin is connected to on the breadboard, '
                   'and whether the pin drives that wire or listens to it.')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', board_pin: str = '', circuit: str = '', circuit_net: str = '',
                 role: str = '', provenance: str = 'seed', notes: str = '', manager=None):
        self.name = name                    # '<board>:<canonical>@<circuit>:<net>' (arduino-uno-r3:D6@uno-button-clock:LED_CONTROL)
        self.board = board
        self.board_pin = board_pin          # the BoardPin row name ('<board>:<canonical>')
        self.circuit = circuit              # the CircuitDefinition row name
        self.circuit_net = circuit_net      # the CircuitNetDefinition row name
        self.role = role                    # driver | input | power | ground | undetermined
        self.provenance = provenance        # seed | canvas
        self.notes = notes
