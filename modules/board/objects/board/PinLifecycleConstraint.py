"""
@module board.objects.board.PinLifecycleConstraint

PinLifecycleConstraint — one class per file (design §7); fgm-2 (REVIEW_R2 Part 3 items 6/7; overrides stay with DerivedOverride).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PinLifecycleConstraint(treeObject):
    """What it is: WHAT A PIN MAY DO AT ONE PHASE OF A BOARD'S LIFE — pin x phase (power-up | reset | bootloader | init |
    runtime | programming | debug) x policy (prohibited = never | conditional = only when `condition` holds or the design
    acknowledges the `reason` | reserved = belongs to something else (a person may not claim it for GPIO while `condition`
    holds) | preserve = leave it as found | free = nothing to say), with the reason and the citation. Example: D0/D1 are the
    USB-serial transport AND the bootloader link, so they are `reserved` whenever the transport is USB-serial. The row never
    carries an override policy: a person's override is a `DerivedOverride` (who / when / why), and nothing overrides an
    ELECTRICAL refusal.
    Related concepts: `BoardPin`, `SocPin`, `UsbInterfaceDefinition` (RESET <- DTR), `board.custom.electrical_check` rule (j),
    `cmod.custom.overrides` (DerivedOverride).
    """

    plain_words = ('A pin lifecycle constraint says what a pin may be used for at one moment of the board\'s life — for example '
                   'that D0 and D1 are the USB cable\'s serial line and must not be used for anything else while it is connected.')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', pin: str = '', soc_pin: str = '', phase: str = '', policy: str = 'free',
                 condition: str = '', reason: str = '', acknowledgment: str = '', verification: str = 'unverified',
                 document: str = '', datasheet: str = '', page_table: str = '', url: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<board>:<pin>:<phase>'
        self.board = board
        self.pin = pin  # a BoardPin canonical (D0, D13, A5) | RESET | AREF | the SoC pin for pins the board does not expose (PB6)
        self.soc_pin = soc_pin  # the SocPin row ('' when the pin is a connector label)
        self.phase = phase  # power-up | reset | bootloader | init | runtime | programming | debug
        self.policy = policy  # prohibited | conditional | reserved | preserve | free
        self.condition = condition  # machine-readable: 'transport=usb-serial' | '' (always) | 'icsp=connected'
        self.reason = reason  # plain words
        self.acknowledgment = acknowledgment  # the token a design supplies to accept a `conditional` ('l-led', 'dtr-reset')
        self.verification = verification
        self.document = document
        self.datasheet = datasheet
        self.page_table = page_table
        self.url = url
        self.undetermined = undetermined
        self.notes = notes
