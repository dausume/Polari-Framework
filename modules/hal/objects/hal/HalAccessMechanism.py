"""
@module hal.objects.hal.HalAccessMechanism

HalAccessMechanism — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalAccessMechanism(treeObject):
    """HOW a register is reached and changed — the tracked data that decides how HAL code is generated (hal-0, plan §4a).

    What it is: one way a chip lets software touch a register bit or field: AVR's bit-addressable low I/O space (one sbi/cbi
    instruction), a read-modify-write on an ordinary address, a write-1-to-set / write-1-to-clear alias register, writing the
    input register to toggle, a write-1-to-clear status flag, a signal routing matrix that must be set first. `selects_when`
    says in words which facts select it, `templates_json` the C it writes per action, `isr_safe` whether that C is one
    indivisible write (False = the generator wraps it in the SoC's atomic guard). `implemented` False = documented for a chip
    family the generator does not reach yet (bit-band, atomic alias windows).
    Related concepts: HalBinding.mechanism, RegisterAccessKind (the field's access word it reads), Register (space, address).
    How it is derived: seeded (hal.custom.mechanisms), each with the datasheet / manual place it comes from in `cite`. The
    generator chooses it from the binding's own register facts; a person never picks it.
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'access', meaning: str = '', selects_when: str = '', templates_json: str = '{}', isr_safe: bool = False, chips: str = '', cite: str = '', implemented: bool = True, notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.kind = kind
        self.meaning = meaning
        self.selects_when = selects_when
        self.templates_json = templates_json
        self.isr_safe = isr_safe
        self.chips = chips
        self.cite = cite
        self.implemented = implemented
        self.notes = notes
