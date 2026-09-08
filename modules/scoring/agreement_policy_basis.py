"""
@cross-cutting
@module scoring.agreement_policy_basis
@tags @xc:bindings

AgreementPolicy — the SETTINGS for group-agreement classification
(Dustin 2026-07-08: "allowing for settings to be made for what is
considered Consensus, what is considered majority definition, what is
considered split, etc."). Bands are rows, not code: edit the policy,
the classifications change.

Three band sets, each an ordered JSON list of {'label', 'max'} (a
value classifies into the FIRST band whose max it does not exceed):

  direction_bands_json — over the dominant-stance fraction (0.5-1.0):
      is the group split on a term being good or bad?
      Default (Dustin's): ≤0.5 divisive · ≤0.65 slight-majority ·
      ≤0.85 large-majority · ≤0.99 near-consensus · else consensus.
  weight_bands_json    — over the SPREAD of members' weight shares
      for a term (relative mean absolute deviation, 0 = identical
      weighting): do members agree how much the term MATTERS?
  similarity_bands_json — over cosine similarity (−1..1) between two
      groups' aggregate definitions ('min' bands: first band whose
      min the value meets): do groups agree on what good
      performance is?

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.group_aggregation
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/agreement_policy/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.agreement_policy._shared import SEED_AGREEMENT_POLICIES, classify_max, classify_min, policy_bands  # noqa: F401
from scoring.objects.agreement_policy.AgreementPolicy import AgreementPolicy  # noqa: F401
