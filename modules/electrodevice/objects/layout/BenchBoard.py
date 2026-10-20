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
    Related concepts: `BoardModel` (the geometry), `BreadboardDefinition` (the older row), `LayoutEdit` (a person's change to a build on this board).
    """

    @treeObjectInit
    def __init__(self, name: str = '', model_name: str = 'breadboard-half', label: str = '', owner: str = '', notes: str = '',
                 migrated_from: str = '', manager=None):
        self.name = name
        self.model_name = model_name      # a BoardModel name
        self.label = label                # what it is called on the bench (a person's words)
        self.owner = owner
        self.notes = notes                # owner notes: where it lives, what is wrong with it, how it was bought
        self.migrated_from = migrated_from   # 'BreadboardDefinition:<name>' when converged from the older row
