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
from board.objects.board.Datasheet import Datasheet  # noqa: F401
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
from board.objects.board.ChipLadderEntry import ChipLadderEntry  # noqa: F401   # chp-0: the chips-and-levels ladder
from board.objects.board.Bench import Bench  # noqa: F401   # bench-0: the boards and breadboards on one bench
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
from board.objects.board.RegisterAccessKind import RegisterAccessKind  # noqa: F401  (rm-2a: the access vocabulary as rows)
from board.objects.board.BoardPinNet import BoardPinNet  # noqa: F401
# ucd-0b2a: address space as rows (UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9) — AddressSpace, RegisterAddressMapping,
# RegisterBlock, MemoryRegion; materialized beside the hardware chain, atmega328p only (Phase 2 for the C3)
from board.objects.board.AddressSpace import AddressSpace  # noqa: F401
from board.objects.board.RegisterAddressMapping import RegisterAddressMapping  # noqa: F401
from board.objects.board.RegisterBlock import RegisterBlock  # noqa: F401
from board.objects.board.MemoryRegion import MemoryRegion  # noqa: F401
# ucd-0e1: THE WIRE CONTRACT of the button-clock demo — the third and fourth wire classes (brd-fi's pattern: a
# telemetry+command state class and a telemetry-only event class, both generated through the same c_twin codegen)
from board.objects.board.ButtonClockState import ButtonClockState  # noqa: F401
from board.objects.board.ButtonClockEvent import ButtonClockEvent  # noqa: F401
from board.objects.board.LightState import LightState  # noqa: F401
from board.objects.board.LightStateV2 import LightStateV2  # noqa: F401   # fgm-6a
from board.objects.board.LightCommand import LightCommand  # noqa: F401   # fgm-6a
# fgm-2: the UNO hardware truth (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7 slice 1')
from board.objects.board.PackageDefinition import PackageDefinition  # noqa: F401
from board.objects.board.PackageContact import PackageContact  # noqa: F401
from board.objects.board.UsbInterfaceDefinition import UsbInterfaceDefinition  # noqa: F401
from board.objects.board.BoardComponent import BoardComponent  # noqa: F401
from board.objects.board.ElectricalCharacteristic import ElectricalCharacteristic  # noqa: F401
from board.objects.board.PinGroupBudget import PinGroupBudget  # noqa: F401
from board.objects.board.PinLifecycleConstraint import PinLifecycleConstraint  # noqa: F401
# hsp-0: enclosures and exposure maps (HARDWARE_SYSTEM_PINS_PLAN.md L1-L3) — kinds catalogue (tentative), instances, one row per pin crossing
from board.objects.board.EnclosureKind import EnclosureKind  # noqa: F401
from board.objects.board.HardwareEnclosure import HardwareEnclosure  # noqa: F401
from board.objects.board.EnclosureContact import EnclosureContact  # noqa: F401
# hsp-1: Hardware System, links, signal paths (HARDWARE_SYSTEM_PINS_PLAN.md L6/L7)
from board.objects.board.HardwareSystem import HardwareSystem  # noqa: F401
from board.objects.board.SystemLink import SystemLink  # noqa: F401
from board.objects.board.SignalPath import SignalPath  # noqa: F401
from board.objects.board.ConfigurationEvent import ConfigurationEvent  # noqa: F401
from board.objects.board.TwinSession import TwinSession  # noqa: F401   # sim-1: a running simulated board with a live control port
from board.objects.board.BenchInteraction import BenchInteraction  # noqa: F401   # sim-3: one thing a person did on the sim bench
from board.objects.board.SimInstallConfirmation import SimInstallConfirmation  # noqa: F401   # ins-1: a person's tick that the sim does what the firmware says
from board.objects.board.BoardFoothold import BoardFoothold  # noqa: F401   # bob-0: footholds of a Board on the Bench
from board.objects.board.BenchConnection import BenchConnection  # noqa: F401   # bob-2: a wire / jumper / mating between two footholds
from board.objects.board.FirmwareStateObject import FirmwareStateObject  # noqa: F401   # fst-0: a firmware's state objects, derived
from board.objects.board.FirmwareStateField import FirmwareStateField  # noqa: F401   # fst-0: their fields (readers / writers / direction)

#: every row class of the module, in registration order (the selftest asserts the count)
BOARD_CLASSES = [BoardDefinition, BoardInstance, FirmwareBuild, ProgrammerKind, AdapterDefinition, DatasheetFact, BoardSimCost, Road,
                 FirmwareVariant, InstallPlan, InstallRecord, UnoAnalogState,   # brd-fi: the installer rows + the second class
                 SocDefinition, SocPin, BoardHardware, BoardNet, Connector, ConnectorPin, BoardPin, RuntimeProfile,
                 BoardConflict, BoardView,   # brd-bo: the board object's layers + its views and conflicts
                 TargetCompatibilityRule,   # fs-2a: task-kind <-> pin-role compatibility, cited
                 KitPart,   # fs-2d: the kit parts register (cited to the kit's own book)
                 ChipLadderEntry,   # chp-0: the chips-and-levels ladder (RISC-V sample apart from the convenience boards)
                 Bench,   # bench-0: the bench (its breadboard selection list = electrodevice BoardModel kind breadboard since D-bob-3)
                 Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting, RegisterFieldSetting,
                 BoardPinNet,   # ucd-0a: the hardware chain (nine)
                 RegisterAccessKind,   # rm-2a: what each RegisterField.access word means (read / write effect, UVM / SVD names)
                 AddressSpace, RegisterAddressMapping, RegisterBlock, MemoryRegion,   # ucd-0b2a: address space as rows (four)
                 ButtonClockState, ButtonClockEvent,   # ucd-0e1: the third and fourth wire classes
                 LightState,   # ucd-light: the light test's one wire struct
                 LightStateV2, LightCommand,   # fgm-6a: the same struct with command confirmation + the backend's command ledger
                 Datasheet,   # ucd-doc: datasheets as documents — one row per cited document, kinded (soc/board/programming/combined/other)
                 PackageDefinition, PackageContact, UsbInterfaceDefinition, BoardComponent,   # fgm-2: package + USB-interface axes, chips as rows
                 ElectricalCharacteristic, PinGroupBudget, PinLifecycleConstraint,   # fgm-2: numbers per pad class, group budgets, lifecycle
                 EnclosureKind, HardwareEnclosure, EnclosureContact,   # hsp-0: enclosure kinds (tentative), enclosures, exposure maps
                 HardwareSystem, SystemLink, SignalPath,   # hsp-1: Hardware System, links, signal paths
                 ConfigurationEvent,   # pv-4: real-world configuration changes (observed, never seeded)
                 TwinSession,   # sim-1: twin sessions (observed, never seeded)
                 BenchInteraction,   # sim-3: what a person did on the sim bench (observed, never seeded)
                 SimInstallConfirmation,   # ins-1: the confirmed-sim gate's tick (a person's record, never seeded)
                 FirmwareStateObject, FirmwareStateField,
                 BoardFoothold,   # bob-0
                 BenchConnection]   # bob-2: connections between footholds of any two Boards on a Bench (observed, never seeded); bob-0: footholds (derived on read for datasheet / geometry boards; stored by a PCB ingest)   # fst-0: a firmware's state objects + fields (derived on read, never seeded)
