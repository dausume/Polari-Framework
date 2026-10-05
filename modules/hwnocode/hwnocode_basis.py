"""
@module hwnocode.hwnocode_basis

The INDEX of the hardware no-code rows (HARDWARE_NOCODE_PLAN.md §2c). Classes live one-per-file under objects/hwnocode/; this file
re-exports them and holds the class list the server registers. NODE_KIND_CLASSES are the canvas node kinds (D-hn-2): their
`statePalette` rides GET /stateSpaceClasses so the ONE canvas's palette learns them as data.
"""
from hwnocode.objects.hwnocode import (HardwareSolution, HardwareNodePlacement, HardwareSubgraph, HardwareInterface, CAtom,  # noqa: F401
                                       SimRigTempSample, SimRigTempDerived, Runtime)

#: every row class of the module, in registration order
HWNOCODE_CLASSES = [HardwareSolution, HardwareNodePlacement, HardwareSubgraph, HardwareInterface, CAtom, SimRigTempSample,
                    SimRigTempDerived, Runtime]
#: the canvas node kinds (palette data via /stateSpaceClasses)
NODE_KIND_CLASSES = [HardwareSubgraph, HardwareInterface, CAtom]
