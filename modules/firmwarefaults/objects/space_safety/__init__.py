"""
@module firmwarefaults.objects.space_safety

FirmwareFault kinds of family space-safety (FIRMWARE_SCENARIO_PLAN.md §1), one class per file.
"""
from firmwarefaults.objects.space_safety.StackOverflowFault import StackOverflowFault  # noqa: F401
from firmwarefaults.objects.space_safety.BufferOverrunFault import BufferOverrunFault  # noqa: F401
from firmwarefaults.objects.space_safety.MissedDeadlineFault import MissedDeadlineFault  # noqa: F401
