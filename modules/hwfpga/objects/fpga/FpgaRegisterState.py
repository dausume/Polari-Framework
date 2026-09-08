"""
@module hwfpga.objects.fpga.FpgaRegisterState

Row class FpgaRegisterState of the hwfpga module — one class per file (design §7), split
from fpga_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FpgaRegisterState(treeObject):
    """Digital twin of one rig's FPGA registers — the telemetry class
    the firmware streams after reading the (verilated) silicon, and
    the command surface: writing commands/config/mode_mux here reaches
    the FPGA through the bridge -> firmware -> bus write."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_id: int = 0,
        version: int = 0,
        status: int = 0,
        faults: int = 0,
        commands: int = 0,
        config: int = 0,
        # THE MUX KNOB: selects which input source feeds STATUS[15:8]
        # (0 = sim counter, 1 = hardware pin stub) — a multiplexer's
        # select bits, exposed as a Polari field.
        mode_mux: int = 0,
        manager=None,
    ):
        self.name = name
        self.device_id = device_id
        self.version = version
        self.status = status
        self.faults = faults
        self.commands = commands
        self.config = config
        self.mode_mux = mode_mux
