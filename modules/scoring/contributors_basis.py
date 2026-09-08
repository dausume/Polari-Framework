"""
@cross-cutting
@module scoring.contributors_basis
@tags @xc:bindings

Contributor — WHO contributes (scr-5). Dustin 2026-07-08: "individuals
contributing data and we should be able to track individuals and orgs
(or allow them to stay anonymous under pseudonames) for research
contributions … hold groups accountable for research statements,
lobbies for their own scorecard assertions".

A Contributor row is an identity handle: an individual, organization,
lobby, or institution. Pseudonymity is a KNOB on the row — a
pseudonymous contributor is still one accountable track record, just
not a legal identity. Assertions (asserted_by), validity votes
(voter), evidence (submitted_by) and ingested values (contributed_by)
all key to contributor names, so a contributor's record — how many of
their assertions survived validity review, what they ingested — is
computable, which is exactly what holds lobbies accountable for their
own scorecard assertions.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (GET /api/scoring/contributors/{name}/record)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/contributors/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.contributors._shared import CONTRIBUTOR_KINDS, SEED_CONTRIBUTORS, _rows, contributor_record  # noqa: F401
from scoring.objects.contributors.Contributor import Contributor  # noqa: F401
