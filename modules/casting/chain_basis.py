"""
@cross-cutting
@module casting.chain_basis
@tags @xc:bindings

cast-3: the nesting chain as DATA. Two treeObjects:

  MoldNestingChain        the multi-tier chain identity. Carries NO
                          parity field on purpose — whether the wax
                          master is a positive or a negative is
                          DERIVED from the stages (chain_analysis),
                          never stored, never hand-set. The handoff's
                          first correctness property.
  CastingStageDefinition  one stage: what shapes it (mold material),
                          what goes in (cast material), how it goes
                          in (fill method), what it cures/fires at,
                          whether the mold is DISPOSABLE (Dustin
                          2026-08-05: sacrificing the geopolymer
                          mold in the firing is allowed — a finding,
                          not a blocker), and how the previous form
                          leaves.

Stages link by (chain_ref, sequence) exactly like composition's
RoutingOperation rides RoutingDefinition — same spine idiom, no
parallel chain model.

@consumers polariServer.defClassList, casting.custom.chain_analysis,
casting.chain_seed
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-3)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/chain/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.chain._shared import FILL_METHODS, STAGE_KINDS  # noqa: F401
from casting.objects.chain.MoldNestingChain import MoldNestingChain  # noqa: F401
from casting.objects.chain.CastingStageDefinition import CastingStageDefinition  # noqa: F401
