"""
@module board.objects.board.EnclosureContact

EnclosureContact — one class per file (design §7); hsp-0 (HARDWARE_SYSTEM_PINS_PLAN.md L3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class EnclosureContact(treeObject):
    """What it is: ONE CROSSING OF ONE ENCLOSURE — a line from `inner_ref` (inside) to `outer_ref` (outside) and HOW it gets there (`via`): direct,
    through a series resistor, a buffer, a capacitor, a jumper, a series inductor or fuse — or not bonded at all (the chip has the pin, this
    package does not bring it out) or internal-only (the line stops at a part on the board: the 16 MHz clock, an LED). `exposed` says whether the
    line reaches outside this enclosure; `consumed_by` names what takes an internal-only line. At the chip package (E1) inner = the chip's pin
    and outer = the package leg; at the board (E2) inner = a package leg and outer = a header pin, a rail, or another chip's leg. All crossings of
    one enclosure are its exposure map; tracing from an outer pin inward walks them level by level. Derived from the existing pin, package,
    header and schematic rows — never typed twice; what the sources do not show is `undetermined`.
    Related concepts: `HardwareEnclosure`, `PackageContact`, `SocPin`, `ConnectorPin`, `BoardPin`, `PinLifecycleConstraint`.
    """

    plain_words = ('An enclosure contact is one wire through the wall of a case: which inner pin it comes from, which outer pin it reaches, '
                   'and what sits in the way (nothing, a resistor, a buffer, a capacitor) — or that it goes nowhere outside at all.')

    @treeObjectInit
    def __init__(self, name: str = '', enclosure: str = '', level: str = '', inner_ref: str = '', outer_ref: str = '', via: str = 'direct',
                 via_part: str = '', via_value: str = '', exposed: bool = False, consumed_by: str = '', label: str = '',
                 verification: str = 'unverified', document: str = '', datasheet: str = '', page_table: str = '', url: str = '',
                 fact: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<enclosure>:<inner>=<outer>' (refs without their class prefix)
        self.enclosure = enclosure  # the HardwareEnclosure row
        self.level = level  # E1 | E2
        self.inner_ref = inner_ref  # 'SocPin:atmega328p:PD6' | 'PackageContact:<pkg>:<n>' | 'Supply:<soc>:<label>' | 'SocSignal:...' ('' when undetermined)
        self.outer_ref = outer_ref  # 'PackageContact:...' | 'ConnectorPin:...' | 'BoardNet:...' | 'SchematicPart:<ref>:<pin>' ('' when not bonded / internal)
        self.via = via  # direct | series-resistor | buffer | capacitor | jumper | series-inductor | series-fuse | not-bonded | internal-only
        self.via_part = via_part  # 'RN4B' | 'U5B LMV358IDGKR' | 'C5' | 'CSTCE16M0V53-R0' ('' = nothing in the way)
        self.via_value = via_value  # '1 kOhm' | '100 nF' ('' when not cited)
        self.exposed = exposed  # the line reaches outside this enclosure
        self.consumed_by = consumed_by  # for internal-only: what onboard part takes the line
        self.label = label  # the signal in plain words ('D13 / PB5 / SCK')
        self.verification = verification  # verified | partial | unverified | conflicted
        self.document = document
        self.datasheet = datasheet
        self.page_table = page_table
        self.url = url
        self.fact = fact  # the DatasheetFact name behind the crossing, when one exists
        self.undetermined = undetermined
        self.notes = notes
