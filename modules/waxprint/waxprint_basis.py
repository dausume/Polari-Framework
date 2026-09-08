"""
@cross-cutting
@module waxprint.waxprint_basis
@tags @xc:bindings, @xc:render-3d

The persisted objects of the wax 3D-printer ("magic 3D printer")
simulation — object coherence: the printer, the wax it eats, and the
conditions it prints under are all first-class tunable rows, each auto
CRUDE + persisted (like aquaponics/pot_basis).

  PrinterAssemblyDefinition   the pellet-fed auger-screw extruder as a
      MATH-SHAPED device — a screw inside a barrel with two independently
      controlled thermal zones (auger + hotend/spout) feeding a nozzle.
      Every length scales by one `assembly_scale` knob (Dustin: study
      size -> flow). Screw / chamber / nozzle / bed MATERIALS are refs
      into materialsScience so their thermal conductivity is an object,
      not a magic number.

  WaxFeedstockDefinition      the engineered all-natural wax, fed as
      pellets. Carries the COMPUTED material properties the melt physics
      consumes and — critically — the thermal SAFETY window (a natural
      wax degrades / volatilizes above a ceiling). Links to a
      materialsScience wax material and a waxsupply source.

  PrintConditionDefinition    one point in the condition vector we sweep:
      the two zone temperatures, screw RPM, nozzle size, ambient / bed
      temperature, the fan wind vector, speed and layer height. This is
      the object the optimizer iterates over across many trials.

Geometry is millimetres, temperatures Celsius (converted to SI in
melt_analysis). Priors are flagged in `notes`; nothing here is measured
until Dustin's rig pins it (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence) + seed_pairs
  - waxprint.custom.melt_analysis / bead_analysis / print_optimizer
  - waxprint.waxprint_api
@see /MVW_PRINT_SIM_PLAN.md, /WAX_PRINT_VOXEL_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/waxprint/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from waxprint.objects.waxprint._shared import CONVECTION_PRESETS, DEVICE_MATERIAL_ROLES  # noqa: F401
from waxprint.objects.waxprint.DeviceMaterialDefinition import DeviceMaterialDefinition  # noqa: F401
from waxprint.objects.waxprint.PrinterAssemblyDefinition import PrinterAssemblyDefinition  # noqa: F401
from waxprint.objects.waxprint.WaxFeedstockDefinition import WaxFeedstockDefinition  # noqa: F401
from waxprint.objects.waxprint.PrintConditionDefinition import PrintConditionDefinition  # noqa: F401
from waxprint.objects.waxprint.WaxReclaimBatch import WaxReclaimBatch  # noqa: F401
from waxprint.objects.waxprint.MoldLifecycleRecord import MoldLifecycleRecord  # noqa: F401
