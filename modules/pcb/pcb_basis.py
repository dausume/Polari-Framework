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
from pcb.objects.pcb.KiCadArtifact import KiCadArtifact  # noqa: F401
from pcb.objects.pcb.KiCadCoverage import KiCadCoverage  # noqa: F401
from pcb.objects.pcb.SchematicSymbol import SchematicSymbol  # noqa: F401
from pcb.objects.pcb.SchematicNet import SchematicNet  # noqa: F401
from pcb.objects.pcb.NetEndpoint import NetEndpoint  # noqa: F401
from pcb.objects.pcb.PcbPad import PcbPad  # noqa: F401
from pcb.objects.pcb.NetGeometry import NetGeometry  # noqa: F401
from pcb.objects.pcb.PcbZone import PcbZone  # noqa: F401
from pcb.objects.pcb.PcbNetClass import PcbNetClass  # noqa: F401
from pcb.objects.pcb.PcbDesignRule import PcbDesignRule  # noqa: F401
from pcb.objects.pcb.PcbLayerGraphics import PcbLayerGraphics  # noqa: F401
from pcb.objects.pcb.SpiceRun import SpiceRun  # noqa: F401
from pcb.objects.pcb.SpiceVector import SpiceVector  # noqa: F401
from pcb.objects.pcb.PartPowerInput import PartPowerInput  # noqa: F401
from pcb.objects.pcb.PartThermalModel import PartThermalModel  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
PCB_CLASSES = [Part, Symbol, Footprint, LandPattern, Schematic, SchematicSheet, PcbBoard, Placement, Route, DrcResult,
              FabricationExport, FabRuleSet, FabRule, KiCadArtifact, KiCadCoverage, SchematicSymbol,   # kxc-1
              SchematicNet, NetEndpoint,   # kxc-2: the schematic's own electrical graph
              PcbPad, NetGeometry, PcbZone, PcbNetClass, PcbDesignRule, PcbLayerGraphics,   # kxc-4: the PCB complete
              SpiceRun, SpiceVector,   # kxc-3b: simulation runs kept
              PartPowerInput, PartThermalModel]   # bob-3g: powers a person gives + datasheet thermal models
