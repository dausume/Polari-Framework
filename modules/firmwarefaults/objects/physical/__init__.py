"""
@module firmwarefaults.objects.physical

FirmwareFault kinds of family physical-trigger (FIRMWARE_SCENARIO_PLAN.md §1), one class per file.
"""
from firmwarefaults.objects.physical.UartBitErrorFault import UartBitErrorFault  # noqa: F401
from firmwarefaults.objects.physical.DoubleEdgeFault import DoubleEdgeFault  # noqa: F401
from firmwarefaults.objects.physical.MetastableInputFault import MetastableInputFault  # noqa: F401
from firmwarefaults.objects.physical.BrownoutMidWriteFault import BrownoutMidWriteFault  # noqa: F401
from firmwarefaults.objects.physical.BitFlipFault import BitFlipFault  # noqa: F401
from firmwarefaults.objects.physical.ClockSkewFault import ClockSkewFault  # noqa: F401
