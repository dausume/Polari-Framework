"""
@cross-cutting
@module casting.casting_basis
@tags @xc:bindings

cast-1 (WAX_MOLD_NESTING_PLAN): the mold as a first-class object — a
NEGATIVE derived from a part's math definition, never hand-built.

One treeObject (auto-CRUDE + persisted — object-coherence):

  MoldDefinition   names a part shape and the declared allowances; the
                   mold geometry itself (stock block, shrink-scaled
                   part, mold body = stock DIFFERENCE part) is DERIVED
                   by casting.custom.mold_geometry.derive_mold as mathshapes
                   rows. The inversion is algebra the existing CSG
                   executor already evaluates: body field =
                   max(F_stock, −F_part). Hand-editing a derived row is
                   not an error state that sticks — re-derivation
                   overwrites it and REPORTS the drift (the parity
                   handoff's "compute and refuse" posture: the cavity
                   is not an opinion).

Shrink allowance is a DECLARED parameter (pattern-maker's shrink: the
cavity is oversized so the cast part lands on-size after
solidification shrink), default 0 — an honest "not yet modelled"
rather than a baked constant. Chain parity / thermal ordering live in
cast-3; sprues in cast-4.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - casting.custom.mold_geometry (derivation), casting.casting_seed
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-1)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/casting/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.casting._shared import FEEDSTOCK_PRIORITIES, MAKE_ROUTES, MASTER_MATERIAL_KINDS, PART_SOURCES, REMOVAL_ROUTES  # noqa: F401
from casting.objects.casting.CastingMaterialThermalProfile import CastingMaterialThermalProfile  # noqa: F401
from casting.objects.casting.MasterFeedstockDefinition import MasterFeedstockDefinition  # noqa: F401
from casting.objects.casting.MoldDefinition import MoldDefinition  # noqa: F401
