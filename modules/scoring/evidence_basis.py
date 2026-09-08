"""
@cross-cutting
@module scoring.evidence_basis
@tags @xc:bindings

MediaEvidence + EvidencePolicy (scr-5, cited by scr-9..14) — proof is
DATA with a GRADE, and what a grade is worth is a SETTING.

MediaEvidence: one citable proof item (video, transcript, official
record, article…) with a quote/span, capture date, provenance and an
evidence_grade. Assertions, promises, rulings all cite these rows.

EvidencePolicy: the graded vocabulary as an editable row (the
AgreementPolicy idiom) — grade → weight, including the weight of
citing NOTHING ('unevidenced'), so how much proof matters is a policy
decision the user can see and change, never a constant buried in code.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.policy_scoring (assertion strength × evidence weight)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/evidence/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.evidence._shared import EVIDENCE_GRADES, EVIDENCE_KINDS, SEED_EVIDENCE_POLICIES, _policy, _rows, evidence_weight, grade_weights  # noqa: F401
from scoring.objects.evidence.MediaEvidence import MediaEvidence  # noqa: F401
from scoring.objects.evidence.EvidencePolicy import EvidencePolicy  # noqa: F401
