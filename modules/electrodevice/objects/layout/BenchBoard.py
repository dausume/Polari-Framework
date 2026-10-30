"""
@module electrodevice.objects.layout.BenchBoard

Row class BenchBoard of the electrodevice module (lay-0) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchBoard(treeObject):
    """What it is: ONE PHYSICAL BOARD ON A BENCH — an instance of a `BoardModel` (a half breadboard, a full breadboard, the UNO). A build names which one it
    is on. (Not the board module's `BoardInstance`, which is a USB device `pol board detect` saw plugged in; this is the thing on the table, whether or not
    anything is plugged into it.) The older `BreadboardDefinition` rows are converged onto this class by name (each keeps its row; each gets a BenchBoard of
    the half model), so the breadboard compiler reads the model's geometry when a BenchBoard of that name exists and the old row's `rows` otherwise.
    bob-1 (his ruling 2026-10-30: dev boards, breadboards and PCBs are equally Boards on the Bench): `bench` + (`definition_kind`, `definition`) put any board
    on a Bench - this is how an ingested PCB joins one (board.custom.bench_boards).
    Related concepts: `BoardModel` (the geometry), `BreadboardDefinition` (the older row), `LayoutEdit` (a person's change to a build on this board),
    `BoardFoothold` (what the Bench sees of any board).
    """

    @treeObjectInit
    def __init__(self, name: str = '', model_name: str = 'breadboard-half', label: str = '', owner: str = '', notes: str = '',
                 migrated_from: str = '', bench: str = '', definition_kind: str = '', definition: str = '', manager=None):
        self.name = name
        self.model_name = model_name      # a BoardModel name
        self.label = label                # what it is called on the bench (a person's words)
        self.owner = owner
        self.notes = notes                # owner notes: where it lives, what is wrong with it, how it was bought
        self.migrated_from = migrated_from   # 'BreadboardDefinition:<name>' when converged from the older row
        # bob-1 (BENCH_BOARDS_PLAN.md): a Board on the Bench names its Bench and HOW the board is defined - datasheet (a BoardDefinition),
        # geometry (a breadboard model), layers (a PcbBoard, e.g. a KiCad import). '' = the older layout rows (they name only a model)
        self.bench = bench
        self.definition_kind = definition_kind   # datasheet | geometry | layers | ''
        self.definition = definition
