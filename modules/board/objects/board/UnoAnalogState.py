"""
@module board.objects.board.UnoAnalogState

UnoAnalogState — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class UnoAnalogState(treeObject):
    """What it is: The live state of an UNO running the uno-adc-sweep variant (brd-fi): the raw 10-bit ADC counts of
    A0, A1, A2 (AVcc reference: count = mV·1024/5000), uptime and a status word. The SECOND class an UNO speaks — its
    per-class C header is generated exactly as SimRigState's is (c_twin target=avr), which is the point.
    Related concepts: grpcbridge `SimRigState` (the first class), `FirmwareVariant` uno-adc-sweep.
    """

    @treeObjectInit
    def __init__(self, name: str = '', uptime_ms: int = 0, a0: int = 0, a1: int = 0, a2: int = 0, status: str = '',
                 manager=None):
        self.name = name  # the Push match key (RIG_NAME of the firmware)
        self.uptime_ms = uptime_ms
        self.a0 = a0
        self.a1 = a1
        self.a2 = a2
        self.status = status  # boot | ok
