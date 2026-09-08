"""
@module hwfpga.objects.led.LedMatrix4x4State

Row class LedMatrix4x4State of the hwfpga module — one class per file (design §7), split
from led_basis.py (sap-2c). The class docstring below is the explanation.
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
