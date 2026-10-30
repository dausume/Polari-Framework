"""
@module electrodevice.layout_basis

lay-0/lay-1 (PROTOTYPING_VIEWS_PLAN section 3, BREADBOARD_BUILD_PLAN section 6): THE BOARD FAMILY AS OBJECTS and the rows a build keeps.
  BoardModel       one kind of board, identity only (breadboard half / full / mini / BUD / the kit's, the UNO, protoboard + pcb reserved); D-bob-3 merged
                   board.BreadboardModel into it, and the facts only some boards have are rows naming the model:
  BreadboardLayout   the strips and rails of a breadboard (the sold tie count the derived count must equal)
  BoardOutline       a vendor-STATED outline and whether the derived drawing fits it
  BoardRating        a vendor-rated contact limit (or that none is published)
  BenchBoard       one physical board on a bench, an instance of a model (the older BreadboardDefinition rows converge onto it by name)
  WireColorScheme  the wire colour convention (seeded from the pin view's palette; copy before editing); a wire can also carry its own colour
  LayoutEdit       a person's change to a derived build, kept BESIDE the derived value and re-checked by the netlist gate
The derived parts of a layout (placements, wires, build steps) are computed from the design every time (electrodevice.custom.layout_*) and never stored.

@consumers
  - electrodevice.breadboard_netlist_seed (board geometry + the hole grammar), electrodevice.custom.layout_core, electrodevice.layout_api
  - polariServer (registration + seed)
"""
from electrodevice.objects.layout._shared import (BENCH_DEFAULT, PITCH_MM, SCHEME_DEFAULT, SEED_BENCH_BOARDS, SEED_BOARD_MODELS,  # noqa: F401
                                                  SEED_BREADBOARD_LAYOUTS, SEED_BOARD_OUTLINES, SEED_BOARD_RATINGS, MODEL_ALIASES,
                                                  SEED_WIRE_COLOR_SCHEMES, WIRE_COLOURS, colour_name_of_hex, migrated_bench_boards)
from electrodevice.objects.layout.BoardModel import BoardModel  # noqa: F401
from electrodevice.objects.layout.BreadboardLayout import BreadboardLayout  # noqa: F401
from electrodevice.objects.layout.BoardOutline import BoardOutline  # noqa: F401
from electrodevice.objects.layout.BoardRating import BoardRating  # noqa: F401
from electrodevice.objects.layout.BenchBoard import BenchBoard  # noqa: F401
from electrodevice.objects.layout.WireColorScheme import WireColorScheme  # noqa: F401
from electrodevice.objects.layout.LayoutEdit import LayoutEdit  # noqa: F401
from electrodevice.objects.breadboard._shared import SEED_BREADBOARDS

#: converged by name from the older BreadboardDefinition seeds, then the bench's own boards
SEED_BENCH_BOARDS_ALL = migrated_bench_boards(SEED_BREADBOARDS) + [dict(b) for b in SEED_BENCH_BOARDS]
