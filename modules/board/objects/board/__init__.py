"""
@module board.objects.board

The board-arc rows (plan BOARD_PROGRAMMING_PLAN.md §2, §7a, §8a).
"""
from board.objects.board.BoardDefinition import BoardDefinition  # noqa: F401
from board.objects.board.BoardInstance import BoardInstance  # noqa: F401
from board.objects.board.FirmwareBuild import FirmwareBuild  # noqa: F401
from board.objects.board.ProgrammerKind import ProgrammerKind  # noqa: F401
from board.objects.board.AdapterDefinition import AdapterDefinition  # noqa: F401
from board.objects.board.DatasheetFact import DatasheetFact  # noqa: F401
from board.objects.board.Datasheet import Datasheet  # noqa: F401
from board.objects.board.BoardSimCost import BoardSimCost  # noqa: F401
from board.objects.board.Road import Road  # noqa: F401
from board.objects.board.FirmwareVariant import FirmwareVariant  # noqa: F401
from board.objects.board.InstallPlan import InstallPlan  # noqa: F401
from board.objects.board.InstallRecord import InstallRecord  # noqa: F401
from board.objects.board.UnoAnalogState import UnoAnalogState  # noqa: F401
# brd-bo: THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b)
from board.objects.board.SocDefinition import SocDefinition  # noqa: F401
from board.objects.board.SocPin import SocPin  # noqa: F401
from board.objects.board.BoardHardware import BoardHardware  # noqa: F401
from board.objects.board.BoardNet import BoardNet  # noqa: F401
from board.objects.board.Connector import Connector  # noqa: F401
from board.objects.board.ConnectorPin import ConnectorPin  # noqa: F401
from board.objects.board.BoardPin import BoardPin  # noqa: F401
from board.objects.board.RuntimeProfile import RuntimeProfile  # noqa: F401
from board.objects.board.BoardConflict import BoardConflict  # noqa: F401
from board.objects.board.BoardView import BoardView  # noqa: F401
# ucd-0a: THE HARDWARE CHAIN (UNO_CORE_DEMO_PLAN.md §5f/§5g) — Board → Pin → SoC Pin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField
from board.objects.board.Peripheral import Peripheral  # noqa: F401
from board.objects.board.PeripheralSignal import PeripheralSignal  # noqa: F401
from board.objects.board.PinFunction import PinFunction  # noqa: F401
from board.objects.board.SignalRoute import SignalRoute  # noqa: F401
from board.objects.board.Register import Register  # noqa: F401
from board.objects.board.RegisterField import RegisterField  # noqa: F401
from board.objects.board.RegisterSetting import RegisterSetting  # noqa: F401
from board.objects.board.RegisterFieldSetting import RegisterFieldSetting  # noqa: F401
from board.objects.board.BoardPinNet import BoardPinNet  # noqa: F401
# ucd-0b2a: address space as rows (UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9)
from board.objects.board.AddressSpace import AddressSpace  # noqa: F401
from board.objects.board.RegisterAddressMapping import RegisterAddressMapping  # noqa: F401
from board.objects.board.RegisterBlock import RegisterBlock  # noqa: F401
from board.objects.board.MemoryRegion import MemoryRegion  # noqa: F401
# ucd-0e1: THE WIRE CONTRACT of the button-clock demo — the third and fourth wire classes (brd-fi's pattern)
from board.objects.board.ButtonClockState import ButtonClockState  # noqa: F401
from board.objects.board.ButtonClockEvent import ButtonClockEvent  # noqa: F401
