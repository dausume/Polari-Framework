"""
@module grpcbridge.objects.bridges

Where a bridge IS, one class per file (hsp-3a, HARDWARE_SYSTEM_PINS_PLAN.md §7): BridgePath (the hop chain chip pins -> converter -> connector -> host port ->
userspace) and PolariBridgeInstance (the bridge as a row: the hardware it is bound to + the Polari node it binds to).
"""
from grpcbridge.objects.bridges.BridgePath import BridgePath  # noqa: F401
from grpcbridge.objects.bridges.PolariBridgeInstance import PolariBridgeInstance  # noqa: F401
