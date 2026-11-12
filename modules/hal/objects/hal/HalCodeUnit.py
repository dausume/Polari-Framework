"""
@module hal.objects.hal.HalCodeUnit

HalCodeUnit — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalCodeUnit(treeObject):
    """The generated C for one HalOperation on one SoC pin: a macro, its bindings, and the digest of how it was made (hal-0).

    What it is: the smallest piece of finished HAL code, e.g. `#define HAL_GPIO_SET_HIGH_PB5() do { PORTB |= _BV(5); } while (0)`.
    `key` = soc:operation:pin identifies it everywhere (pages, links from a Bench Simulation). `steps_sha256` is the digest of
    its generation trace (HalGenerationStep rows), `code_sha256` of the text, so the same inputs give the same unit.
    Related concepts: HalBinding (its parts), HalGenerationStep (how), the generated header (where it lands).
    How it is derived: hal.custom.generate; never stored by hand.
    """

    @treeObjectInit
    def __init__(self, name: str = '', key: str = '', soc: str = '', operation: str = '', pin: str = '', board_pin: str = '', macro: str = '', c_text: str = '', c_text_init: str = '', includes: str = '', guarded: bool = False, status: str = '', why: str = '', steps_sha256: str = '', code_sha256: str = '', notes: str = '', manager=None):
        self.name = name
        self.key = key
        self.soc = soc
        self.operation = operation
        self.pin = pin
        self.board_pin = board_pin
        self.macro = macro
        self.c_text = c_text
        self.c_text_init = c_text_init
        self.includes = includes
        self.guarded = guarded
        self.status = status
        self.why = why
        self.steps_sha256 = steps_sha256
        self.code_sha256 = code_sha256
        self.notes = notes
