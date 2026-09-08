"""
@cross-cutting
@module scoring.group_bias_basis
@tags @xc:bindings

Per-group bias analysis (scr-16) — Dustin 2026-07-08: "per group bias
analysis". Four independent reads per group, every label traveling
with its numbers, bands = editable BiasPolicy rows:

  stance skew      — the group's aggregate definition vs the
                     all-groups consensus, per term (opposed stances
                     and emphasis gaps named).
  one-sidedness    — supports-vs-harms fractions of the members'
                     assertions per target subject kind (a group that
                     only ever harms one kind of target is visible).
  vote alignment   — the confirmation-bias read: how often member
                     validity votes go the way the group's own stance
                     would prefer (self-serving) vs against it
                     (evidence-driven). Small samples flagged, never
                     over-read.
  source quality   — evidence grades + scr-15 outlet accuracy over
                     what the group's assertions actually cite.

Bias here is a READING of behavior against the group's own recorded
stances — evidence-bearing, recomputable, never a verdict on people.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (GET /api/scoring/groups/{name}/bias)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/group_bias/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy_basis import classify_max
from scoring.custom.group_aggregation import (
    aggregate_group, all_groups_consensus,
)
from scoring.media_accuracy_basis import outlet_accuracy

from scoring.objects.group_bias._shared import SEED_BIAS_POLICIES, SMALL_SAMPLE, _bias_bands, _by_name, _one_sidedness, _parse, _rows, _source_quality, _stance_skew, _vote_alignment, group_bias_report  # noqa: F401
from scoring.objects.group_bias.BiasPolicy import BiasPolicy  # noqa: F401
