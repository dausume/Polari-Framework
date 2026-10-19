"""
@module electrodevice.objects.layout.LayoutEdit

Row class LayoutEdit of the electrodevice module (lay-1) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LayoutEdit(treeObject):
    """What it is: ONE CHANGE a person made to a derived build (a part in a different hole, a wire in a different colour), kept BESIDE the derived value —
    the derived layout is recomputed every time and never overwritten; the edit is applied on top and the netlist gate re-checks the result.
    `subject` names the part or wire (`part:LED1`, `wire:w-gnd-rail`), `field` is `holes` (value: the list of holes, in the part's pin order) or `colour`
    (value: a colour name), and `value_json` is the new value. Deleting the row (or clearing it) returns to the derived value.
    Related concepts: `BenchBoard` (the board the build is on), `WireColorScheme` (the derived colour), `BoardJumper.colour_override`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', board: str = '', subject: str = '', field: str = 'holes',
                 value_json: str = 'null', who: str = '', note: str = '', created_at: str = '', manager=None):
        self.name = name
        self.config = config            # the built config (a firmware variant), e.g. uno-light
        self.board = board              # the BenchBoard the build is on
        self.subject = subject          # part:<ref> | wire:<name>
        self.field = field              # holes | colour
        self.value_json = value_json
        self.who = who
        self.note = note
        self.created_at = created_at
