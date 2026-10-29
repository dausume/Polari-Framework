"""
@module grpcbridge.bridges_basis

hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7): where a bridge is, as DATA - BridgePath + PolariBridgeInstance (classes under objects/bridges/) and their seeds
(the UNO's and the Elecrow S3's paths on the home bench; the UNO's bridge bound to polari-pol). The logic (validation, the node URL rule) is
grpcbridge.custom.bridge_paths.

@consumers
  - grpcbridge.bridges_api (the doors)
  - polariApiServer (defClassList + the seed list)
"""
from grpcbridge.objects.bridges import BridgePath, PolariBridgeInstance  # noqa: F401
from grpcbridge.custom.bridge_paths import SEED_BRIDGE_PATHS, SEED_POLARI_BRIDGES  # noqa: F401

BRIDGES_CLASSES = [BridgePath, PolariBridgeInstance]
