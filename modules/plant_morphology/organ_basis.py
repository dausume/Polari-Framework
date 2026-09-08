"""
@cross-cutting
@module plant_morphology.organ_basis
@tags @xc:bindings, @xc:render-3d

3D stand-in / MOCK morphology models for plant organs + root systems —
parametric estimates, NOT photoreal meshes. Each organ is a shape
primitive with dimensions + count, giving a 3D bounding geometry and a
volume estimate the analysis reasons over (canopy envelope, root ball,
confinement). Own module + own data (separated cleanly from
aquaponics/nutrition), depends only on framework core.

Two treeObjects (auto-CRUDE + persisted — object-coherence):

  OrganModel       one organ TYPE of a plant (leaf / stem / branch /
                   root-visible / fruit / flower): a shape primitive
                   (ellipsoid, cylinder, cone, sphere, lamina) + its
                   dimensions + count + arrangement → a mock 3D form
                   and volume. The stand-in geometry until real meshes.
  RootSystemModel  the below-ground structure: spreading PATTERN,
                   natural spread radius + depth, root-ball density, and
                   the CONFINEMENT response knobs — can this plant be
                   dwarfed and kept in a pot indefinitely, and with what
                   root-prune cadence.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - plant_morphology.custom.morphology_analysis (geometry, root spread,
    confinement), SimSpace3D stand-in rendering later
@see /HOUSEHOLD_NUTRITION_PLAN.md, /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/organ/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from plant_morphology.objects.organ._shared import ARRANGEMENTS, ORGAN_TYPES, ROOT_PATTERNS, SHAPE_PRIMITIVES  # noqa: F401
from plant_morphology.objects.organ.OrganModel import OrganModel  # noqa: F401
from plant_morphology.objects.organ.RootSystemModel import RootSystemModel  # noqa: F401
