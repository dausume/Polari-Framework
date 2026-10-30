"""
BoardFoothold - one class per file (design section 7); bob-0 (AI-Notes/plans/BENCH_BOARDS_PLAN.md section 3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardFoothold(treeObject):
    """What it is: ONE PLACE ON A BOARD WHERE SOMETHING CAN LAND - a dev board's header pin, a breadboard tie point, a PCB connector pad, a test pad -
    with the ABSTRACTED DRIVE AND SIGNAL data the Bench works with (his ruling 2026-10-30: dev boards, breadboards and PCBs are equally Boards on the
    Bench; how a board is DEFINED is its own level). Every board definition kind yields footholds through its own adapter (board.custom.footholds):
    `datasheet` (BoardPin / ConnectorPin / the cited electrical numbers), `geometry` (a breadboard's strips and rails from its counts and pitch),
    `layers` (a PCB's connector pads and their nets, from the pcb rows). Footholds of a datasheet or geometry board are derived on read; a layers
    board's are stored by its ingest.

    `node`: footholds with the same node are joined INSIDE the board (a breadboard strip a-e, a PCB net, a dev board's GND pins) - the inside detail
    stays at the definition level. Drive: `rail_volts` (a supply foothold's voltage), `logic_volts` (the chip pin's logic level), `source_ma` /
    `sink_ma` (the limit, with `drive_basis` saying whether it is a maximum or a typical value); -1 = undetermined. Signal: `families_json` (the pin
    view's families: gpio, uart, analog ...), `chip_pin` (the SoC pin behind it, '' when none), `direction` (in | out | inout | passive | supply |
    undetermined). Every number names its source in `drive_basis` / `signal_basis` or is said in `undetermined`.
    Related concepts: `BenchBoard` (a Board on the Bench, which names a definition), `BoardPin` (the chip-facing pin of a datasheet board),
    `EnclosureContact` (the die -> package -> board chain behind a header pin).
    """

    @treeObjectInit
    def __init__(self, name: str = '', definition_kind: str = '', definition: str = '', foothold: str = '', kind: str = '', label: str = '',
                 x_mm: float = 0.0, y_mm: float = 0.0, position_basis: str = '', side: str = 'top', node: str = '', net: str = '',
                 rail_volts: float = -1.0, logic_volts: float = -1.0, source_ma: float = -1.0, sink_ma: float = -1.0, drive_basis: str = '',
                 families_json: str = '[]', chip_pin: str = '', direction: str = 'undetermined', signal_basis: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<definition_kind>:<definition>:<foothold>'
        self.definition_kind = definition_kind  # datasheet | geometry | layers
        self.definition = definition  # the BoardDefinition / BoardModel / PcbBoard name
        self.foothold = foothold  # J1:9 | r17a | rail:top:+:3 | J2:1
        self.kind = kind  # header-pin | tie-point | rail-hole | connector-pin | test-pad | pad
        self.label = label  # what is printed beside it (IO0, 5V, GND) or ''
        self.x_mm = x_mm  # in the definition's own frame (top-left origin, y down)
        self.y_mm = y_mm
        self.position_basis = position_basis  # cited | derived | drawing knob — and from what
        self.side = side
        self.node = node  # same node = joined inside the board
        self.net = net  # the definition's net name, '' when none
        self.rail_volts = rail_volts
        self.logic_volts = logic_volts
        self.source_ma = source_ma
        self.sink_ma = sink_ma
        self.drive_basis = drive_basis
        self.families_json = families_json
        self.chip_pin = chip_pin
        self.direction = direction
        self.signal_basis = signal_basis
        self.undetermined = undetermined
        self.notes = notes
