"""
@module board.objects.board.HardwareSystem

HardwareSystem — one class per file (design §7); hsp-1 (HARDWARE_SYSTEM_PINS_PLAN.md L6).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareSystem(treeObject):
    """What it is: ONE HARDWARE SYSTEM — the boards, chips, bench circuit and the host runtime (software and the person) that together make one working
    thing, at one development stage (S1 breadboard · S2 protoboard · S3 pcb · S4 vendor-soc · S5 blcnc-soc). Its `participants_json` uses the same
    shape as a cmod Purpose's participants ({role, kind, ref, variant}) with the kinds hardware · software · person; `ref` is Class:name. It lists the
    boards, components and circuits it is made of, the `SystemLink` rows that join two participants (derived, never typed twice) and the Cross-Domain
    Solution it realises. Its `SignalPath` rows walk a signal end to end across it.
    Related concepts: `SystemLink`, `SignalPath`, `HardwareEnclosure`, `BoardDefinition`, `CircuitDefinition`, `SolutionDefinition`.
    """

    plain_words = ('A hardware system is the whole working thing: the board and its chips, the parts on the bench, the computer program that talks to it '
                   'and the person who uses it — and how far along the build is (breadboard, protoboard, printed board, bought chip, our own chip).')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', stage: str = 'S1-breadboard', participants_json: str = '[]', boards_json: str = '[]',
                 components_json: str = '[]', circuits_json: str = '[]', links_refs_json: str = '[]', task_plan: str = '', solution: str = '',
                 verification: str = 'unverified', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # e.g. 'uno-light-system'
        self.title = title
        self.stage = stage  # S1-breadboard | S2-protoboard | S3-pcb | S4-vendor-soc | S5-blcnc-soc
        self.participants_json = participants_json  # [{role, kind: hardware|software|person, ref: Class:name, variant?}]
        self.boards_json = boards_json  # ["BoardDefinition:..."]
        self.components_json = components_json  # ["BoardComponent:..." | "CircuitComponentDefinition:..." ...]
        self.circuits_json = circuits_json  # ["CircuitDefinition:..."]
        self.links_refs_json = links_refs_json  # DERIVED: ["SystemLink:<name>"]
        self.task_plan = task_plan  # fgm-5b: the recorded Task Plan of this system ('<mission>:<system>'; '' until one is recorded) - set when the plan is stored, derived again on every door read
        self.solution = solution  # the Cross-Domain Solution it realises (SolutionDefinition name)
        self.verification = verification  # verified | partial | unverified | conflicted
        self.undetermined = undetermined
        self.notes = notes
