"""
@module board.board_basis

The INDEX of the board-arc rows (plan BOARD_PROGRAMMING_PLAN.md §2, §7a, §8a): classes live one-per-file under
objects/board/; this file re-exports them (brd-bo: + the board object's ten) and holds the class list the server registers.
"""
from board.objects.board.BoardDefinition import BoardDefinition  # noqa: F401
from board.objects.board.BoardInstance import BoardInstance  # noqa: F401
from board.objects.board.FirmwareBuild import FirmwareBuild  # noqa: F401
from board.objects.board.ProgrammerKind import ProgrammerKind  # noqa: F401
from board.objects.board.AdapterDefinition import AdapterDefinition  # noqa: F401
from board.objects.board.DatasheetFact import DatasheetFact  # noqa: F401
from board.objects.board.BoardSimCost import BoardSimCost  # noqa: F401
from board.objects.board.Road import Road  # noqa: F401
from board.objects.board.FirmwareVariant import FirmwareVariant  # noqa: F401
from board.objects.board.InstallPlan import InstallPlan  # noqa: F401
from board.objects.board.InstallRecord import InstallRecord  # noqa: F401
from board.objects.board.UnoAnalogState import UnoAnalogState  # noqa: F401
# brd-bo: THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b) — the layers beside the Identity row (BoardDefinition)
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
# fs-2a: the compatibility table between a firmware task's target kind and a board's pin roles/capabilities
from board.objects.board.TargetCompatibilityRule import TargetCompatibilityRule  # noqa: F401
# fs-2d: the kit parts register (his ask: "these are all the parts in our kit ... reference for how we make our sample firmwares")
from board.objects.board.KitPart import KitPart  # noqa: F401
# ucd-0a: THE HARDWARE CHAIN (UNO_CORE_DEMO_PLAN.md §5f/§5g), materialized + cited: Board → Pin → SoC Pin → PinFunction →
# PeripheralSignal → Peripheral → Register → RegisterField, both ways; SignalRoute / RegisterSetting / RegisterFieldSetting filled by
# ucd-0b (the claims), BoardPinNet by ucd-0c (the circuit)
from board.objects.board.Peripheral import Peripheral  # noqa: F401
from board.objects.board.PeripheralSignal import PeripheralSignal  # noqa: F401
from board.objects.board.PinFunction import PinFunction  # noqa: F401
from board.objects.board.SignalRoute import SignalRoute  # noqa: F401
from board.objects.board.Register import Register  # noqa: F401
from board.objects.board.RegisterField import RegisterField  # noqa: F401
from board.objects.board.RegisterSetting import RegisterSetting  # noqa: F401
from board.objects.board.RegisterFieldSetting import RegisterFieldSetting  # noqa: F401
from board.objects.board.BoardPinNet import BoardPinNet  # noqa: F401
# ucd-0b2a: address space as rows (UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9) — AddressSpace, RegisterAddressMapping,
# RegisterBlock, MemoryRegion; materialized beside the hardware chain, atmega328p only (Phase 2 for the C3)
from board.objects.board.AddressSpace import AddressSpace  # noqa: F401
from board.objects.board.RegisterAddressMapping import RegisterAddressMapping  # noqa: F401
from board.objects.board.RegisterBlock import RegisterBlock  # noqa: F401
from board.objects.board.MemoryRegion import MemoryRegion  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
BOARD_CLASSES = [BoardDefinition, BoardInstance, FirmwareBuild, ProgrammerKind, AdapterDefinition, DatasheetFact, BoardSimCost, Road,
                 FirmwareVariant, InstallPlan, InstallRecord, UnoAnalogState,   # brd-fi: the installer rows + the second class
                 SocDefinition, SocPin, BoardHardware, BoardNet, Connector, ConnectorPin, BoardPin, RuntimeProfile,
                 BoardConflict, BoardView,   # brd-bo: the board object's layers + its views and conflicts
                 TargetCompatibilityRule,   # fs-2a: task-kind <-> pin-role compatibility, cited
                 KitPart,   # fs-2d: the kit parts register (cited to the kit's own book)
                 Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting, RegisterFieldSetting,
                 BoardPinNet,   # ucd-0a: the hardware chain (nine)
                 AddressSpace, RegisterAddressMapping, RegisterBlock, MemoryRegion]   # ucd-0b2a: address space as rows (four)
