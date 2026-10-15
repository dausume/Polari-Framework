"""
@module board.objects.board.PinGroupBudget

PinGroupBudget — one class per file (design §7); fgm-2 (REVIEW_R2 Part 3 item 5: budgets per GROUP).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PinGroupBudget(treeObject):
    """What it is: ONE CURRENT BUDGET SHARED BY A GROUP OF PINS — the ATmega328P datasheet limits the SUM of the output currents
    of whole groups of pins (for sinking: PC0-PC5 with ADC6/ADC7 <= 100 mA; PB0-PB5, PD5-PD7, XTAL1/XTAL2 <= 100 mA; PD0-PD4 with
    RESET <= 100 mA), plus a package-wide total through the VCC and GND pins. Membership is a list of pins; the limit carries
    its `limit_class` and `verification` exactly like `ElectricalCharacteristic` (abs-max totals are never a design target).
    Related concepts: `ElectricalCharacteristic` (per-pin numbers), `PackageContact`, `board.custom.electrical_check` rule (g).
    """

    plain_words = ('A power budget is the most current a whole group of pins may carry together — the datasheet limits the sum, '
                   'not just each pin.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', title: str = '', direction: str = '', members_json: str = '[]',
                 package_only_json: str = '[]', limit_ma: float = 0.0, limit_class: str = 'recommended',
                 verification: str = 'unverified', condition: str = '', document: str = '', datasheet: str = '',
                 page_table: str = '', url: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<soc>:<budget>' e.g. 'atmega328p:iol-pc-adc'
        self.soc = soc
        self.title = title
        self.direction = direction  # source (IOH) | sink (IOL) | supply (VCC/GND pins)
        self.members_json = members_json  # SocPin names (and supply-pin labels for the supply budget)
        self.package_only_json = package_only_json  # members that exist only on some packages (ADC6/ADC7: TQFP) — named, never dropped
        self.limit_ma = limit_ma
        self.limit_class = limit_class  # abs-max | recommended | guaranteed | typical
        self.verification = verification
        self.condition = condition
        self.document = document
        self.datasheet = datasheet
        self.page_table = page_table
        self.url = url
        self.undetermined = undetermined
        self.notes = notes
