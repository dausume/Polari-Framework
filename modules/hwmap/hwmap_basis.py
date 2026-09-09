"""
@module hwmap.hwmap_basis

The INDEX of hwmap rows (design §7). No seeds: every row comes from a scan.
"""
from hwmap.objects.hwmap.HardwareMapSnapshot import HardwareMapSnapshot  # noqa: F401
from hwmap.objects.hwmap.HardwarePort import HardwarePort, PORT_KINDS  # noqa: F401
from hwmap.objects.hwmap.HardwareSlot import HardwareSlot, SLOT_KINDS  # noqa: F401
from hwmap.objects.hwmap.PassthroughCandidate import PassthroughCandidate, MAPPINGS  # noqa: F401

HWMAP_SEED_PAIRS = [('HardwareMapSnapshot', HardwareMapSnapshot, []), ('HardwarePort', HardwarePort, []),
                    ('HardwareSlot', HardwareSlot, []), ('PassthroughCandidate', PassthroughCandidate, [])]
HWMAP_CLASSES = [cls for _, cls, _ in HWMAP_SEED_PAIRS]
