"""
@module board.board_basis

The INDEX of the board-arc rows (plan BOARD_PROGRAMMING_PLAN.md §2, §7a, §8a): classes live one-per-file under
objects/board/; this file re-exports them and holds the class list the server registers.
"""
from board.objects.board.BoardDefinition import BoardDefinition  # noqa: F401
from board.objects.board.BoardInstance import BoardInstance  # noqa: F401
from board.objects.board.FirmwareBuild import FirmwareBuild  # noqa: F401
from board.objects.board.ProgrammerKind import ProgrammerKind  # noqa: F401
from board.objects.board.AdapterDefinition import AdapterDefinition  # noqa: F401
from board.objects.board.DatasheetFact import DatasheetFact  # noqa: F401
from board.objects.board.BoardSimCost import BoardSimCost  # noqa: F401
from board.objects.board.Road import Road  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
BOARD_CLASSES = [BoardDefinition, BoardInstance, FirmwareBuild, ProgrammerKind, AdapterDefinition, DatasheetFact, BoardSimCost, Road]
