"""
@module board.objects.board.PackageContact

PackageContact — one class per file (design §7); fgm-2.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PackageContact(treeObject):
    """What it is: ONE PIN of ONE PACKAGE — leg 12 of the 28-pin SPDIP is PD6, leg 19 of the 32-pin TQFP is ADC6. Power, ground
    and analog-reference legs are contacts too (the SoC pin table holds only I/O pins), so VCC/GND/AVCC/AREF and the
    TQFP-only analog inputs are modelled, not omitted. `soc_pin` names the `SocPin` an I/O contact is (empty for power and
    analog-only legs).
    Related concepts: `PackageDefinition`, `SocPin.package_contacts_refs_json` (the reverse list), `ElectricalCharacteristic`
    (the pad class this contact belongs to), `PinGroupBudget` (the groups contacts count towards).
    """

    plain_words = 'A package contact is one leg of a chip package and what signal or supply it carries.'

    @treeObjectInit
    def __init__(self, name: str = '', package: str = '', number: int = 0, label: str = '', kind: str = '', soc_pin: str = '',
                 functions_json: str = '[]', electrical_class: str = '', page_table: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<package>:<number>'
        self.package = package  # the PackageDefinition row
        self.number = number
        self.label = label  # PD6 | VCC | GND | AVCC | AREF | ADC6
        self.kind = kind  # io | power | ground | analog-supply | analog-reference | analog-input
        self.soc_pin = soc_pin  # the SocPin row for an I/O contact ('' otherwise)
        self.functions_json = functions_json  # the figure's own labels for this leg, in its order
        self.electrical_class = electrical_class  # the ElectricalCharacteristic pad class ('' = none stated)
        self.page_table = page_table
        self.undetermined = undetermined
        self.notes = notes
