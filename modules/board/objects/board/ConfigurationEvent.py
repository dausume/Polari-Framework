"""
@module board.objects.board.ConfigurationEvent

ConfigurationEvent — one class per file (design §7); pv-4 (PIN_VIEW_PLAN.md 2.4 / 2.9).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConfigurationEvent(treeObject):
    """What it is: ONE REAL-WORLD CHANGE that alters a board's pin states — a firmware flash, a wire added or removed, a shield attached or detached, another binding chosen,
    a reset — with its cause in plain words and who / when. ONLY real-world changes are rows: the per-phase pin states (power-up, reset, bootloader, init, runtime) are
    DERIVED on every read and never stored, and a flash that an `InstallRecord` already records or a wire drawn on the canvas (`BoardPinNet`, provenance canvas) is READ as an
    event by the door, never copied here as a second truth. This row is for what no other row records (a person's or a bridge's report). `pins_changed_json` is derived at
    write time from the pin view's own payload difference — never typed by the caller.
    Related concepts: `InstallRecord`, `BoardPinNet`, `BoardInstance`, `FirmwareBuild`, `PinLifecycleConstraint`.
    """

    plain_words = ('A configuration event is a note that something really changed on a board — it was flashed, a wire was added, a shield was put on — '
                   'with why it happened, who did it and when, and which pins it changed.')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', board_instance: str = '', kind: str = '', cause: str = '', refs_json: str = '[]',
                 pins_changed_json: str = '[]', pins_basis: str = '', who: str = '', when: str = '', provenance: str = 'recorded', notes: str = '',
                 manager=None):
        self.name = name  # '<board>:ev-<n>'
        self.board = board  # the board DESIGN (a BoardDefinition name)
        self.board_instance = board_instance  # the BoardInstance it happened to ('' = the design, i.e. every instance)
        self.kind = kind  # flash | wiring-added | wiring-removed | shield-attached | shield-detached | binding-chosen | reset
        self.cause = cause  # plain words: why it happened
        self.refs_json = refs_json  # ['InstallRecord:<n>', 'BoardPinNet:<n>', 'FirmwareBuild:<n>', 'Binding:<n>', ...] — validated when written
        self.pins_changed_json = pins_changed_json  # [{pin, label, level, before, after, what}] derived at write time from the payload diff
        self.pins_basis = pins_basis  # what the diff compared (plain words), or why it is undetermined
        self.who = who  # a person or a bridge
        self.when = when  # ISO time
        self.provenance = provenance  # recorded (a person) | bridge
        self.notes = notes
