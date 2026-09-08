"""
@cross-cutting
@module scoring.media_accuracy_basis
@tags @xc:bindings

Media accountability (scr-15) — Dustin 2026-07-08: "media
accountability for accuracy to data". Outlets are subjects whose
FACTUAL CLAIMS are checked against the ingested data: the engine
already knows what the number actually was (same context + time
matching scores use), so accuracy is COMPUTED, not voted.

FactualClaim: one checkable statement an outlet published — the
statement text plus its checkable payload (term, subject, contexts,
claimed value) and the article evidence. Logged by contributors
(attributed, like everything else).

AccuracyPolicy: editable bands over relative error (the
AgreementPolicy idiom) — what counts as 'accurate' is a SETTING.

check_claim: measured value resolved through resolve_value_over_time
→ relative error → band, both numbers + the measured value's
provenance in the answer. No data = 'unverifiable', an honest refusal
naming what's missing.

outlet_accuracy: the contributor-record idiom for outlets — band
distribution, mean relative error, per-term breakdown. scr-16 reads
this as source quality.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api / scoring.group_bias_basis
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/media_accuracy/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy_basis import classify_max
from scoring.custom.scoring_engine import resolve_value_over_time

from scoring.objects.media_accuracy._shared import SEED_ACCURACY_POLICIES, SEED_FACTUAL_CLAIMS, SEED_MEDIA_OUTLETS, _by_name, _error_bands, _parse, _rows, check_claim, outlet_accuracy  # noqa: F401
from scoring.objects.media_accuracy.FactualClaim import FactualClaim  # noqa: F401
from scoring.objects.media_accuracy.AccuracyPolicy import AccuracyPolicy  # noqa: F401
