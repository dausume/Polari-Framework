"""
@module pspp.evidence_methods_basis

The ONE evidence vocabulary (plan invariant I4 + ChatGPT convergence:
"use one shared EvidenceMethod object everywhere") — how a value came
to be known, as editable rows. Claims (pspp.claims_basis) and scale rows
(materialsScience MaterialScaleDefinition.derivation_method) both name
identifiers from THIS vocabulary; the seed is a superset of the legacy
DERIVATION_METHODS tuple so existing rows validate unchanged.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.claims_basis (validate_claim checks evidence_method against this)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/evidence_methods/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.materials_basis import DERIVATION_METHODS

from pspp.objects.evidence_methods._shared import EVIDENCE_METHOD_VOCAB, SEED_EVIDENCE_METHODS, evidence_identifiers, legacy_methods_covered, validate_evidence_method  # noqa: F401
from pspp.objects.evidence_methods.EvidenceMethod import EvidenceMethod  # noqa: F401
