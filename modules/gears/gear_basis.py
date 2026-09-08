"""
@module gears.gear_basis

gr-1 (GEARS_PLAN §2, §3): GEAR TRAINS AS DATA. A gear train is a
GRAPH of rotating bodies: SHAFT NODES carry one angular speed each,
MESH EDGES impose a speed ratio and a torque ratio between two
shafts. That is the mechanical twin of the reluctance network
(mag-3): shaft node ~ flux node, mesh ~ element, power conservation ~
flux conservation — so it rides the same rows-then-solve discipline
rather than a second invented one.

Every gear TYPE is a row (GearTypeDefinition), never a code branch:
its ratio law, its efficiency PRIOR BAND (literature, flagged, until
measured runs replace it), its axis relationship, its geometry
generator key, and how it would actually be MADE in our stack. Adding
a type = adding a row + (for 3D) a generator.

Honesty pinned here so it travels on every payload:
- quasi-static ONLY; inertia/acceleration/resonance are out of v1;
- efficiency numbers are priors until GearVerificationRun rows land;
- tooth stress is a SCREEN (gr-2), never a certification;
- backlash is a first-class column — cast (T0) parts have a lot of
  it, and a reduction train ACCUMULATES it.

@consumers gears.custom.gear_kinematics, gears.gear_api, polariServer
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/gear/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from gears.objects.gear._shared import AXIS_RELATIONS, PROFILE_FAMILIES, TOLERANCE_TIERS  # noqa: F401
from gears.objects.gear.GearTypeDefinition import GearTypeDefinition  # noqa: F401
from gears.objects.gear.GearDefinition import GearDefinition  # noqa: F401
from gears.objects.gear.ShaftNodeDefinition import ShaftNodeDefinition  # noqa: F401
from gears.objects.gear.GearMeshDefinition import GearMeshDefinition  # noqa: F401
from gears.objects.gear.GearTrainDefinition import GearTrainDefinition  # noqa: F401
from gears.objects.gear.GearVerificationRun import GearVerificationRun  # noqa: F401
