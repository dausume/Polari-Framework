"""
@cross-cutting
@module mathshapes.tower_basis
@tags @xc:bindings, @xc:render-3d

The aquaponic TOWER (shape-2 context): a vertical stack of self-watering
pots sharing a reservoir + water path — the structure shape-4 predicts
growth inside. One treeObject (auto-CRUDE + persisted).

  AquaponicTowerDefinition   n tiers of a per-tier pot MathShapeDefinition
                             (a math-defined pot from pot_shape_from_
                             definition), the vertical spacing between
                             tiers, and the shared reservoir at the base.
                             tower_analysis sums grow volume per tier,
                             the footprint, and the top→bottom water path.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - mathshapes.custom.tower_analysis / tower_api
@see /MATH_SHAPES_PLAN.md (PHASE shape-2 / shape-4)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/tower/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mathshapes.objects.tower.AquaponicTowerDefinition import AquaponicTowerDefinition  # noqa: F401
