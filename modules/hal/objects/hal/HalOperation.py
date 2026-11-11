"""
@module hal.objects.hal.HalOperation

HalOperation — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalOperation(treeObject):
    """One chip-independent HAL operation in the generalized vocabulary (hal-0, HAL_CATOM_CATALOGUE_PLAN.md §4a).

    What it is: what an isotope asks the hardware to do, in words that hold on every chip: make a pin an output, set it high,
    read it. `role` names the register ROLE it acts on (direction / output / input / pull_up / pull_down) and `action` what it
    does to that role's bit (set / clear / toggle / read). `setup` names the per-SoC setup an operation needs first (a signal
    routing matrix), or ''. `c_name` is the macro stem the generator writes (HAL_GPIO_SET_HIGH -> HAL_GPIO_SET_HIGH_PB5()).
    Related concepts: HalBinding (this operation on one SoC pin), HalAccessMechanism (how each binding is written),
    HalCodeUnit (the generated C), the isotopes that call it (catom.json `requires`, hal-1).
    How it is derived: seeded vocabulary (hal.custom.operations); the names follow the API shape of Zephyr's gpio API and
    Arduino's digitalWrite / pinMode, cited in `basis` (shape only, no code copied).
    """

    @treeObjectInit
    def __init__(self, name: str = '', family: str = '', title: str = '', intent: str = '', role: str = '', action: str = '', setup: str = '', returns: str = 'void', c_name: str = '', basis: str = '', parts: str = '', notes: str = '', manager=None):
        self.name = name
        self.family = family
        self.title = title
        self.intent = intent
        self.role = role
        self.action = action
        self.setup = setup
        self.returns = returns
        self.c_name = c_name
        self.basis = basis
        self.parts = parts
        self.notes = notes
