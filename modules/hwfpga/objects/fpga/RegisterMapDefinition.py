"""
@module hwfpga.objects.fpga.RegisterMapDefinition

Row class RegisterMapDefinition of the hwfpga module — one class per file (design §7), split
from fpga_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RegisterMapDefinition(treeObject):
    """One hardware register map (an FPGA block's programming model).
    Generation targets hang off THIS row; its registers are the
    RegisterDefinition rows naming it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Where the block sits on the MCU bus (external FSMC space on the
        # STM32F4 rig (0x70000000 is unmapped on the Renode model) —
        # where a real external FPGA would live.
        base_address: int = 0x70000000,
        # Bus the generated slave speaks. 'axi4lite' is what Renode's
        # IntegrationLibrary drives; SPI transport rides later boards.
        bus: str = 'axi4lite',
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.base_address = base_address
        self.bus = bus
        self.description = description
