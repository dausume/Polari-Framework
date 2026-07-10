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

from objectTreeDecorators import treeObject, treeObjectInit


class LedMatrix4x4State(treeObject):
    """State of one small LED grid. pixels bit(row*width+col) lights
    the LED at (row, col); low width*height bits are meaningful."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Bitmask of lit LEDs (bit 0 = top-left, row-major).
        pixels: int = 0,
        # THE PROFILE KNOB: 'fpga' | 'mcu' (see module docstring).
        driver: str = 'mcu',
        width: int = 4,
        height: int = 4,
        manager=None,
    ):
        self.name = name
        self.pixels = pixels
        self.driver = driver
        self.width = width
        self.height = height


SEED_LED_MATRICES = [
    {'name': 'renode-led-grid', 'pixels': 0, 'driver': 'mcu',
     'width': 4, 'height': 4},
]
