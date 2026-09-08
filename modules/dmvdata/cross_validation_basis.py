"""
@module dmvdata.cross_validation_basis

Cross-validation of duplicated source data (Dustin 2026-07-16):
more users assert duplicate data as REAL by pulling the same source
on their own Polari instance and comparing — each comparison is a
RetrievalConfirmation row tying the validator's own independent
SourceRetrieval to the one being validated, with a computed
per-key/per-field comparison and group-or-individual attribution.
Confirmations by DISTINCT confirmers raise the sourcing-credibility
READING; contradictions lower it. Groups that PROVIDE data become
scoreable subjects through the standard engine (ScoreTerms + a
'data-provider-reliability' ScoreConcept whose weights are
mechanism-B votable).

Honesty stances baked in:
  * Credibility is a READING with evidence, never a truth
    declaration — the reading text says so.
  * Self-confirmation is refused (independence is the point).
  * Small samples are flagged (the scr-12a SMALL_SAMPLE idiom).
  * Verdict thresholds and the credibility prior are module
    constants — knobs, not hidden policy.

@consumers
  - dmvdata.cross_validation_selftest
  - scoring engine (via SEED_PROVIDER_TERMS / SEED_PROVIDER_CONCEPT
    + push_provider_scores)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cross_validation/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import threading
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from polariApiProfiler.schema_drift import verify_continuity
from scoring.survival_costs_basis import SMALL_SAMPLE

from dmvdata.objects.cross_validation._shared import CONTRADICTED_SHARE, CREDIBILITY_PRIOR, MISMATCH_DETAIL_CAP, SEED_PROVIDER_CONCEPT, SEED_PROVIDER_TERMS, VERDICT_WEIGHTS, _CONFIRMATION_LOCK, _PROVIDER_PROVENANCE, _confirmations_for_retrievals, _known_retrievals, _retrieval, _rows, compare_duplicate_data, provider_reliability, push_provider_scores, sourcing_credibility  # noqa: F401
from dmvdata.objects.cross_validation.RetrievalConfirmation import RetrievalConfirmation  # noqa: F401

from datetime import datetime, timezone
import json

def confirm_retrieval(manager, subject_retrieval_name,
                      confirming_retrieval_name, original_rows,
                      independent_rows, key_field, confirmed_by,
                      confirmed_by_group='', compared_at=None,
                      notes=''):
    """Record one cross-validation. Both retrieval rows must exist;
    the confirmer must be INDEPENDENT of the subject retrieval's
    origin (same person AND same group = self-confirmation,
    refused)."""
    subject = _retrieval(manager, subject_retrieval_name)
    if subject is None:
        return {'ok': False,
                'error': f'no SourceRetrieval named '
                         f"'{subject_retrieval_name}'",
                'knownRetrievals': _known_retrievals(manager)}
    confirming = _retrieval(manager, confirming_retrieval_name)
    if confirming is None:
        return {'ok': False,
                'error': f'no SourceRetrieval named '
                         f"'{confirming_retrieval_name}' — record "
                         f'the validator\'s own pull first '
                         f'(record_retrieval)',
                'knownRetrievals': _known_retrievals(manager)}
    if not confirmed_by:
        return {'ok': False,
                'error': 'confirmed_by must name the Contributor '
                         'doing the validation'}
    same_person = (confirmed_by
                   == getattr(subject, 'retrieved_by', ''))
    same_group = (confirmed_by_group
                  == getattr(subject, 'retrieved_by_group', ''))
    if same_person and same_group:
        return {'ok': False,
                'error': 'self-confirmation refused: the subject '
                         'retrieval was recorded by the same '
                         'person and group — cross-validation '
                         'requires an INDEPENDENT puller'}
    comparison = compare_duplicate_data(original_rows,
                                        independent_rows, key_field)
    stamp = compared_at or datetime.now(timezone.utc).isoformat()
    with _CONFIRMATION_LOCK:
        table = manager.objectTables.setdefault(
            'RetrievalConfirmation', {})
        taken = {getattr(r, 'name', '') for r in table.values()}
        base = (f'{subject_retrieval_name}--by-'
                f'{confirmed_by_group or confirmed_by}')
        row_name, suffix = base, 2
        while row_name in taken:
            row_name = f'{base}-{suffix}'
            suffix += 1
        row = RetrievalConfirmation(
            name=row_name,
            subject_retrieval_name=subject_retrieval_name,
            confirming_retrieval_name=confirming_retrieval_name,
            confirmed_by=confirmed_by,
            confirmed_by_group=confirmed_by_group,
            compared_at=stamp,
            rows_compared=comparison['rowsCompared'],
            matches=comparison['matches'],
            mismatches=comparison['mismatches'],
            mismatch_detail_json=json.dumps(
                comparison['mismatchDetail']),
            verdict=comparison['verdict'], notes=notes,
            manager=manager)
        if not any(existing is row for existing in table.values()):
            table[row_name] = row
    db = getattr(manager, 'db', None)
    persisted = True
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception as exc:
            persisted = False
            print(f'[CrossValidation] save FAILED for {row_name}: '
                  f'{exc}', flush=True)
    result = {'ok': True, 'confirmation': row_name,
              'comparison': comparison}
    if not persisted:
        result['persistWarning'] = ('the DB save FAILED — this '
                                    'confirmation exists in memory '
                                    'only')
    return result
