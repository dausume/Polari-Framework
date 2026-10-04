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

#: every row class of the module, in registration order (the selftest asserts the count)
BOARD_CLASSES = [BoardDefinition, BoardInstance, FirmwareBuild, ProgrammerKind, AdapterDefinition, DatasheetFact, BoardSimCost, Road,
                 FirmwareVariant, InstallPlan, InstallRecord, UnoAnalogState,   # brd-fi: the installer rows + the second class
                 SocDefinition, SocPin, BoardHardware, BoardNet, Connector, ConnectorPin, BoardPin, RuntimeProfile,
                 BoardConflict, BoardView]   # brd-bo: the board object's layers + its views and conflicts
