"""
@module pcb.pcb_basis

The INDEX of the PCB-arc rows (pcb-0, AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2, §7): classes live one-per-file under
objects/pcb/; this file re-exports them and holds the class list the server registers (the board module's board_basis.py
pattern). This module depends on `board` (the host/BoardDefinition a Part may name) and `electrodevice` (a Schematic's
nets, when a design also has a simulated circuit) — neither import is required at import time: both links are plain name
fields (board_definition, circuit_net-style references), resolved by name like the rest of the tree.
"""
from pcb.objects.pcb.Part import Part  # noqa: F401
from pcb.objects.pcb.Symbol import Symbol  # noqa: F401
from pcb.objects.pcb.Footprint import Footprint  # noqa: F401
from pcb.objects.pcb.LandPattern import LandPattern  # noqa: F401
from pcb.objects.pcb.Schematic import Schematic  # noqa: F401
from pcb.objects.pcb.SchematicSheet import SchematicSheet  # noqa: F401
from pcb.objects.pcb.PcbBoard import PcbBoard  # noqa: F401
from pcb.objects.pcb.Placement import Placement  # noqa: F401
from pcb.objects.pcb.Route import Route  # noqa: F401
from pcb.objects.pcb.DrcResult import DrcResult  # noqa: F401
from pcb.objects.pcb.FabricationExport import FabricationExport  # noqa: F401
from pcb.objects.pcb.FabRuleSet import FabRuleSet  # noqa: F401
from pcb.objects.pcb.FabRule import FabRule  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
PCB_CLASSES = [Part, Symbol, Footprint, LandPattern, Schematic, SchematicSheet, PcbBoard, Placement, Route, DrcResult,
              FabricationExport, FabRuleSet, FabRule]
