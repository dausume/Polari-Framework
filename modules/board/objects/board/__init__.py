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
