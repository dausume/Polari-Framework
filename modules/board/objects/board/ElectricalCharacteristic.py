"""
@module board.objects.board.ElectricalCharacteristic

ElectricalCharacteristic — one class per file (design §7); fgm-2 (REVIEW_R2 Part 3 item 5: per PAD CLASS x condition, never per pin).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ElectricalCharacteristic(treeObject):
    """What it is: ONE DOCUMENTED ELECTRICAL NUMBER of one PAD CLASS under one condition — "a standard I/O pin of the ATmega328P
    at VCC = 5 V, sourcing 20 mA, outputs at least 4.2 V". Every ATmega328P I/O pin shares one driver, so the numbers live
    once on the class (`SocPin.electrical_class` names it) and not once per pin. Each row carries its `limit_class`
    (abs-max = destroy-it rating, NEVER a design target | recommended = what a design may rely on | guaranteed = what the
    datasheet promises at its stated test condition | typical = a mid-production value, not a promise) and its
    `verification` (verified = the number was read from the cited page | partial = read, but the document states it only at
    one condition or the class mapping is ours | unverified | conflicted). A number the sources do not give is a row with
    `undetermined` naming what is missing — never a guess.
    Related concepts: `SocPin.electrical_class`, `PackageContact.electrical_class`, `PinGroupBudget` (group totals),
    `board.custom.electrical_check` (rules f-i read these rows), `Datasheet`.
    """

    plain_words = ('An electrical characteristic is one number from a datasheet — a voltage or current limit for a kind of pin under '
                   'stated conditions — with how far it can be trusted and exactly where it was read.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', pad_class: str = '', parameter: str = '', condition: str = '',
                 vcc_min: float = 0.0, vcc_max: float = 0.0, temp_c: str = '', formula: str = '', min_value: str = '',
                 typ_value: str = '', max_value: str = '', unit: str = '', limit_class: str = 'guaranteed',
                 verification: str = 'unverified', document: str = '', datasheet: str = '', page_table: str = '',
                 url: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<soc>:<pad_class>:<parameter>:<condition-slug>'
        self.soc = soc
        self.pad_class = pad_class  # '<soc>:<class>' e.g. 'atmega328p:io-standard'
        self.parameter = parameter  # VOH | VOL | VIH | VIL | RPU | IIL | IIH | I_PIN | I_PIN_TOTAL | V_PIN
        self.condition = condition  # the datasheet's own words ('IOH = -20 mA, VCC = 5 V, TA = 85 C')
        self.vcc_min = vcc_min  # the supply range the row applies over (V)
        self.vcc_max = vcc_max
        self.temp_c = temp_c  # '85' | '105' | '' when not stated
        self.formula = formula  # '0.3 VCC' when the datasheet states a fraction of VCC
        self.min_value = min_value  # strings so 'undetermined' / a formula result both fit; numbers parse as float
        self.typ_value = typ_value
        self.max_value = max_value
        self.unit = unit
        self.limit_class = limit_class  # abs-max | recommended | guaranteed | typical
        self.verification = verification  # verified | partial | unverified | conflicted
        self.document = document
        self.datasheet = datasheet  # the Datasheet row (slug)
        self.page_table = page_table
        self.url = url
        self.undetermined = undetermined
        self.notes = notes
