"""
@module board.objects.board.HardwareEnclosure

HardwareEnclosure — one class per file (design §7); hsp-0 (HARDWARE_SYSTEM_PINS_PLAN.md L2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareEnclosure(treeObject):
    """What it is: ONE ENCLOSURE THAT EXISTS IN A DESIGN — the UNO's ATmega328P 28-pin package (E1), its ATmega16U2 QFN package (E1), the modelled
    32-pin TQFP variant of the 328P (E1, on no UNO), and the UNO board itself (E2). It names its `kind` (an `EnclosureKind`), the level, the
    enclosure it sits inside (`parent`: both chips sit inside the board), what it contains, and which board / chip row / package row it IS.
    Its pin side is its `EnclosureContact` rows (the exposure map); its body (heat, stress, ingress) is not modelled yet.
    Related concepts: `EnclosureKind`, `EnclosureContact`, `PackageDefinition`, `BoardComponent`, `BoardDefinition`.
    """

    plain_words = ('A hardware enclosure is one actual case in a design — the chip\'s package, or the board it sits on. '
                   'It says what kind of case it is, what it sits inside and which of its pins reach the outside.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = '', level: str = '', parent: str = '', contains_json: str = '[]',
                 board: str = '', component: str = '', package: str = '', status: str = 'modelled', verification: str = 'unverified',
                 document: str = '', datasheet: str = '', page_table: str = '', url: str = '', undetermined: str = '', notes: str = '',
                 manager=None):
        self.name = name  # e.g. 'arduino-uno-r3:U1:package'
        self.title = title
        self.kind = kind  # the EnclosureKind row ('E1:dip')
        self.level = level  # E1 | E2 ...
        self.parent = parent  # the HardwareEnclosure this one sits inside ('' = none on the modelled boards)
        self.contains_json = contains_json  # ["HardwareEnclosure:<name>" | "BoardComponent:<name>", ...]
        self.board = board  # the BoardDefinition this enclosure is, or sits on ('' for the unplaced TQFP variant)
        self.component = component  # the BoardComponent row this enclosure packages
        self.package = package  # the PackageDefinition row this enclosure IS (E1)
        self.status = status  # modelled | variant-not-on-a-board
        self.verification = verification  # verified | partial | unverified | conflicted
        self.document = document
        self.datasheet = datasheet
        self.page_table = page_table
        self.url = url
        self.undetermined = undetermined
        self.notes = notes
