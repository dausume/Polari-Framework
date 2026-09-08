"""
@module grpcbridge.hwsim_basis

hwsim-1 (HARDWARE_SIMULATION_PLAN.md): the first hardware-family
object — one row per physical/simulated rig, the digital twin the
Renode firmware streams into. Deliberately scalar-heavy (numbers +
one short status string) so the C-struct twin on a bare-metal MCU is
trivial; richer classes come with grpc-4's HardwareSignalDefinition.

The row IS the device to everything above the seam: telemetry frames
update it, and updating it over REST commands the device (grpc-j2's
proven Commands loop).

@consumers
  - polariServer (registration + seed)
  - grpcbridge.custom.c_twin (generated <class>_packets.h for firmware)
  - the sim-rig / renode-rig Polari Hardware Bridges
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/hwsim/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.objects.hwsim._shared import SEED_SIM_RIGS  # noqa: F401
from grpcbridge.objects.hwsim.SimRigState import SimRigState  # noqa: F401
