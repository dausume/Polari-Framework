"""
@module hwfpga.led_basis

The 4x4 LED demo object (hwsim LED phase): "send this object instance
to the hardware and it lights up." One row per LED grid; updating
`pixels` over REST rides the Commands stream to the firmware.

THE PROFILE KNOB is the `driver` field:
  'fpga' — firmware writes the FPGA's LED_MATRIX register and reads
           the pixels BACK FROM THE SILICON (pins follow, hwsim-3);
  'mcu'  — firmware drives the grid itself from RAM, no FPGA in the
           path at all (works on rigs with no FPGA attached).
Switching profile = updating one field on the object — no rebuild,
no redeploy, the same firmware serves both.

@consumers
  - polariServer (registration + seed)
  - the renode-rig bridge (msg_type 3) + renode_twin firmware
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/led/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from hwfpga.objects.led._shared import SEED_LED_MATRICES  # noqa: F401
from hwfpga.objects.led.LedMatrix4x4State import LedMatrix4x4State  # noqa: F401
