"""
@module hwmap.objects.hwmap

The hardware-map rows: a device's snapshot, its ports, its slots
(controllers with capacity), and the passthrough verdict per port.
"""
from hwmap.objects.hwmap.HardwareMapSnapshot import HardwareMapSnapshot  # noqa: F401
from hwmap.objects.hwmap.HardwarePort import HardwarePort  # noqa: F401
from hwmap.objects.hwmap.HardwareSlot import HardwareSlot  # noqa: F401
from hwmap.objects.hwmap.PassthroughCandidate import PassthroughCandidate  # noqa: F401
