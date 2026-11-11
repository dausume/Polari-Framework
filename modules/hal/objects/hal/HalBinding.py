"""
@module hal.objects.hal.HalBinding

HalBinding — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalBinding(treeObject):
    """One HalOperation on one SoC pin, resolved to ONE register write or read (hal-0). Derived on every read, never typed in.

    What it is: the exact register, field, bit and value an operation touches on this chip, the access mechanism chosen for it,
    and where each fact came from. An operation may need several bindings in order (the ESP32-C3's GPIO output = route the
    matrix, select the pad function, then set the enable bit); `part` numbers them and `purpose` says why each is there.
    Related concepts: HalOperation, HalAccessMechanism, Register / RegisterField (board), HalCodeUnit (what it becomes).
    How it is derived: hal.custom.generate from board's cited register tables (DS40002061B for the ATmega328P, TRM v1.4 for
    the ESP32-C3) and avr-libc's register snapshot; `status` resolved | unsupported | undetermined with `why`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', unit: str = '', soc: str = '', operation: str = '', pin: str = '', part: int = 0, purpose: str = '', register: str = '', field: str = '', bit_lo: int = 0, bit_hi: int = 0, value: str = '', access: str = '', address: str = '', space: str = '', mechanism: str = '', c_text: str = '', cite: str = '', status: str = '', why: str = '', notes: str = '', manager=None):
        self.name = name
        self.unit = unit
        self.soc = soc
        self.operation = operation
        self.pin = pin
        self.part = part
        self.purpose = purpose
        self.register = register
        self.field = field
        self.bit_lo = bit_lo
        self.bit_hi = bit_hi
        self.value = value
        self.access = access
        self.address = address
        self.space = space
        self.mechanism = mechanism
        self.c_text = c_text
        self.cite = cite
        self.status = status
        self.why = why
        self.notes = notes
