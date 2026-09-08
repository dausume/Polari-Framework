"""
@cross-cutting
@module casting.sprue_basis
@tags @xc:bindings

cast-4: sprues and gating as OBJECTS — a reusable strategy, and the
strategy APPLIED to one mold with the generated geometry + the
removability verdict recorded.

  SprueStrategyDefinition   HOW to gate (style, vents, taper, neck
                            ratio, removal mode) — reusable across
                            molds; the neck ratio is THE removability
                            knob (Dustin's "easy to remove", made
                            numeric: neck cross-section as a fraction
                            of the LOCAL part section, thresholds
                            0.25 brittle / 0.40 ductile — named
                            priors, confirmable).
  SprueSetInstance          the strategy applied to one mold: which
                            -eq rows were generated, where and WHY
                            (placements carry evidence), and the
                            worst-wins removability score.

Parity note: the same generated solids serve both parities — they
are SUBTRACTED from the mold body (channels in a negative) and
UNIONED onto the master (attached sprues on a positive); cast-3's
derived parity decides which artifact gets printed.

@consumers polariServer.defClassList, casting.custom.sprue_geometry
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-4)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/sprue/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.sprue._shared import GATE_STYLES, NECK_RATIO_LIMITS, REMOVAL_MODES, VENT_PLACEMENTS  # noqa: F401
from casting.objects.sprue.SprueStrategyDefinition import SprueStrategyDefinition  # noqa: F401
from casting.objects.sprue.SprueSetInstance import SprueSetInstance  # noqa: F401
