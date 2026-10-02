"""
@module firmwarefaults.firmwarefaults_basis

The INDEX of the firmware-fault rows (FIRMWARE_SCENARIO_PLAN.md §1; D-sc-1 ruled 2026-10-02: its own module). Classes
live one-per-file under objects/<family>/; this file re-exports them and holds the class lists the server registers.
"""
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault, BASE_FIELDS, LAYERS  # noqa: F401
from firmwarefaults.objects.firmwarefaults.ConcurrencyPrimitive import ConcurrencyPrimitive  # noqa: F401
from firmwarefaults.objects.firmwarefaults.Assumption import Assumption  # noqa: F401
from firmwarefaults.objects.firmwarefaults.Technique import Technique  # noqa: F401
from firmwarefaults.objects.firmwarefaults.Scenario import Scenario  # noqa: F401
from firmwarefaults.objects.firmwarefaults.ScenarioStep import ScenarioStep  # noqa: F401
from firmwarefaults.objects.firmwarefaults.ScenarioRun import ScenarioRun  # noqa: F401
from firmwarefaults.objects.firmwarefaults.ScenarioTraceCycle import ScenarioTraceCycle  # noqa: F401
from firmwarefaults.objects.concurrency import (TornReadFault, DoubleGiveFault, LostWakeupFault, PriorityInversionFault,  # noqa: F401
                                                DeadlockFault, LivelockFault, StarvationFault)
from firmwarefaults.objects.physical import (UartBitErrorFault, DoubleEdgeFault, MetastableInputFault, BrownoutMidWriteFault,  # noqa: F401
                                             BitFlipFault, ClockSkewFault)
from firmwarefaults.objects.space_safety import StackOverflowFault, BufferOverrunFault, MissedDeadlineFault  # noqa: F401

#: the fault KIND classes by family (the selftest asserts 7 + 6 + 3 = 16)
FAULT_KINDS = {
    'concurrency': [TornReadFault, DoubleGiveFault, LostWakeupFault, PriorityInversionFault, DeadlockFault, LivelockFault, StarvationFault],
    'physical-trigger': [UartBitErrorFault, DoubleEdgeFault, MetastableInputFault, BrownoutMidWriteFault, BitFlipFault, ClockSkewFault],
    'space-safety': [StackOverflowFault, BufferOverrunFault, MissedDeadlineFault],
}
FAULT_KIND_CLASSES = [c for fam in FAULT_KINDS.values() for c in fam]
FAULT_CLASS_NAMES = [c.__name__ for c in FAULT_KIND_CLASSES]

#: every row class of the module, in registration order
FIRMWAREFAULTS_CLASSES = [FirmwareFault] + FAULT_KIND_CLASSES + [ConcurrencyPrimitive, Assumption, Technique, Scenario, ScenarioStep,
                                                                 ScenarioRun, ScenarioTraceCycle]
