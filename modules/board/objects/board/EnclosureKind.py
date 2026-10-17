"""
@module board.objects.board.EnclosureKind

EnclosureKind — one class per file (design §7); hsp-0 (HARDWARE_SYSTEM_PINS_PLAN.md L1).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class EnclosureKind(treeObject):
    """What it is: ONE KIND OF ENCLOSURE the design may need, by level — E0 die, E1 component (chip packages, connector shells ...), E2 board,
    E3 sub-assembly, E4 device housing, E5 installation — and the functions it serves (mechanical, thermal, ingress, emi, electrical-safety,
    exposure, optical). A catalogue of WORDS: every row is `tentative` and carries no physics number (no thermal resistance, no IP rating) — that
    belongs to the Embedded Device work, not built yet. `pin_relevant` says whether the kind exposes or carries electrical pins/contacts (a chip
    package does, a heat sink does not): those are the kinds the exposure maps are built for first.
    Related concepts: `HardwareEnclosure` (an instance of a kind in a design), `EnclosureContact` (one pin crossing of an enclosure),
    `PackageDefinition` (an E1 chip package's own row).
    """

    plain_words = ('An enclosure kind is a sort of case or cover a part, board or device can sit inside — a chip package, a board, a housing, a cabinet. '
                   'The list is a draft of the words we will need; none of it is measured yet.')

    @treeObjectInit
    def __init__(self, name: str = '', level: str = '', slug: str = '', title: str = '', level_name: str = '', functions_json: str = '[]',
                 pin_relevant: bool = False, description: str = '', status: str = 'tentative', source: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<level>:<slug>' e.g. 'E1:dip'
        self.level = level  # E0 | E1 | E2 | E3 | E4 | E5
        self.slug = slug
        self.title = title
        self.level_name = level_name  # die | component | board | sub-assembly | device housing | installation
        self.functions_json = functions_json  # subset of: mechanical thermal ingress emi electrical-safety exposure optical
        self.pin_relevant = pin_relevant  # exposes or carries electrical pins/contacts
        self.description = description  # plain words
        self.status = status  # tentative (every row, hsp-0)
        self.source = source  # the terminology section the kind comes from
        self.undetermined = undetermined
        self.notes = notes  # why these functions
