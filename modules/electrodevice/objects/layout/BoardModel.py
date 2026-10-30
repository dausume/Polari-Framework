"""
@module electrodevice.objects.layout.BoardModel

Row class BoardModel of the electrodevice module (lay-0; D-bob-3 2026-10-30) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardModel(treeObject):
    """What it is: ONE KIND OF BOARD - its identity only: what kind it is, who makes it, whether it is usable yet, and where its definition lives. Every
    physical board on a bench (`BenchBoard`) is one of these. The facts that only some boards have are their own rows, each naming this model by
    `board_model`, so a model never carries fields that mean nothing for its kind:
      `BreadboardLayout`  the strips and rails of a breadboard (rows, holes per side, rail holes, pitch, sold tie points)
      `BoardOutline`      a cited physical outline (width x height) and whether the derived drawing fits it
      `BoardRating`       a vendor-rated limit (the rail voltage / current a breadboard's contacts are rated for)
    kind `breadboard`: defined by its `BreadboardLayout` (definition kind geometry). kind `devboard`: defined by `board_definition` (its BoardPin rows -
    definition kind datasheet). kinds `protoboard` and `pcb` are RESERVED (status says so); an ingested PCB is a Board on the Bench through its own
    stored footholds (pcb module), not through a model.
    One model = the merge of the older board.BreadboardModel (the bench's selection list) and this class's breadboard geometry (D-bob-3).
    Related concepts: `BenchBoard` (a physical board of this model), `Bench` (breadboards_json names models), `BoardFoothold` (what the bench sees).
    """

    plain_words = 'One kind of board - a half breadboard, the UNO - with its maker and whether it is ready to use; its layout, size and ratings are separate rows.'

    KINDS = ('breadboard', 'devboard', 'protoboard', 'pcb')
    STATUSES = ('built', 'unverified', 'reserved')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'breadboard', vendor: str = '', part_number: str = '', status: str = 'built',
                 board_definition: str = '', description: str = '', notes: str = '', manager=None):
        self.name = name                      # kebab-case, e.g. 'breadboard-half', 'bud-bb-32650-w', 'uno-r3'
        self.title = title
        self.kind = kind                      # breadboard | devboard | protoboard (reserved) | pcb (reserved)
        self.vendor = vendor                  # 'generic' when no maker is known
        self.part_number = part_number
        self.status = status                  # built | unverified (only a vendor label is known) | reserved (no geometry yet)
        self.board_definition = board_definition   # devboard: the BoardDefinition whose BoardPin rows are the header pins
        self.description = description
        self.notes = notes
