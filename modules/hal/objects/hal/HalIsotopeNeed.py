"""
@module hal.objects.hal.HalIsotopeNeed

HalIsotopeNeed — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalIsotopeNeed(treeObject):
    """What the hardware gives ONE isotope for ONE of its needs on one chip pin (hal-iso, 2026-11-14).

    What it is: the HAL's answer to an isotope, not a yes/no. A need = one (variable, operation) of the isotope's `requires`.
    `verdict` fits | chip-lacks (cited chip fact) | not-recorded (a gap in our tables) | refused. `need_name` = the isotope's own
    word (HAL_BUTTON_EDGE_ENABLE_FALLING), the same on every chip; `settings` = register.field = value via mechanism; `yields` = what
    the hardware told the generator (signum, the vector); `cites` = the datasheet places. `proof` = how the record was proved
    ('' = generated only; twin runs set it later).
    Related concepts: HalCodeUnit (the unit it points at), the isotope's isotope.json `requires`, hal.custom.isotopes fit.
    How it is derived: hal.custom.needs.rows, on every read; never stored by hand.
    """

    @treeObjectInit
    def __init__(self, name: str = '', catom: str = '', isotope: str = '', soc: str = '', pin: str = '', variable: str = '', role: str = '',
                 operation: str = '', need_name: str = '', unit: str = '', verdict: str = '', settings: str = '', yields: str = '',
                 cites: str = '', why: str = '', proof: str = '', manager=None):
        self.name = name
        self.catom = catom
        self.isotope = isotope
        self.soc = soc
        self.pin = pin
        self.variable = variable
        self.role = role
        self.operation = operation
        self.need_name = need_name
        self.unit = unit
        self.verdict = verdict
        self.settings = settings
        self.yields = yields
        self.cites = cites
        self.why = why
        self.proof = proof
