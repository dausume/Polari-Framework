"""
@module hwfpga.fpga_basis

hwsim-3 (HARDWARE_SIMULATION_PLAN.md): the FPGA register map as DATA
— Dustin's directive made concrete: "polari has access to as many
knobs as possible … so that we can later make no-code states that can
allow no-code programming for these different components."

Every register of the Hardware Runtime map (hardware-architecture:
0x0000 Device ID … Commands/Config) is an OBJECT ROW. The Verilog
register block, the firmware C defines, and the Renode attachment are
all GENERATED from these rows — editing a row (a knob today, a
no-code state later) reprograms the component at every layer.

@consumers
  - hwfpga.custom.fpga_verilog (the generators)
  - hwfpga.fpga_api (the knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/fpga/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from hwfpga.objects.fpga._shared import SEED_FPGA_STATES, SEED_REGISTERS, SEED_REGISTER_MAPS  # noqa: F401
from hwfpga.objects.fpga.RegisterMapDefinition import RegisterMapDefinition  # noqa: F401
from hwfpga.objects.fpga.RegisterDefinition import RegisterDefinition  # noqa: F401
from hwfpga.objects.fpga.FpgaRegisterState import FpgaRegisterState  # noqa: F401
