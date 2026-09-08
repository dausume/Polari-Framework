"""
@module hwfpga.objects.fpga.RegisterDefinition

Row class RegisterDefinition of the hwfpga module — one class per file (design §7), split
from fpga_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RegisterDefinition(treeObject):
    """One register — one knob. access: 'const' (hardwired identity,
    e.g. Device ID), 'ro' (logic-driven, MCU reads), 'rw' (MCU/Polari
    write, logic obeys)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        map_name: str = '',
        offset: int = 0,
        register: str = '',
        access: str = 'rw',
        reset_value: int = 0,
        # KNOB: how many of this register's low bits drive physical
        # output pins (0 = none). The generator emits a
        # `<register>_pins` output port wired to them — LEDs, relays,
        # enables… all data-driven, no generator edits per device.
        pins_out: int = 0,
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.map_name = map_name
        self.offset = offset
        self.register = register
        self.access = access
        self.reset_value = reset_value
        self.pins_out = pins_out
        self.description = description
