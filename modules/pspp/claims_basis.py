"""
@module pspp.claims_basis

Claims, not values (plan invariant I4): every predicted/looked-up
quantity is a CLAIM — value + evidence method + assumptions + validity
+ source — attached to a material-state subject. "38 GPa" is never
stored bare.

Subjects key by the state convention '<material>#<state>'
('metakaolin-geopolymer#7-day-cure'). Until pspp-2 lands MaterialState
rows, the canonical subject is '<material>#as-defined' — the same key
the canonical-state backfill will mint, so pspp-1 claims migrate for
free (plan invariant I1).

Claims are ANNOTATIONS on a state, never DAG edges (invariant I2) —
an OBSERVATIONAL engine run attaches claims; only TRANSFORMATIVE
executions (pspp-4) create states.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.dataset_interpolation (returns claim-shaped evidence payloads)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/claims/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.evidence_methods_basis import validate_evidence_method

from pspp.objects.claims._shared import canonical_subject, claim_summary, claims_for_subject, validate_claim  # noqa: F401
from pspp.objects.claims.PropertyClaim import PropertyClaim  # noqa: F401
from pspp.objects.claims.StructureClaim import StructureClaim  # noqa: F401
from pspp.objects.claims.ValidationClaim import ValidationClaim  # noqa: F401
