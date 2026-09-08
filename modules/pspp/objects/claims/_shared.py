"""@module pspp.objects.claims._shared — what the claims row classes share (constants, seeds, helpers); split from claims_basis.py (sap-2c)."""
import json
from pspp.evidence_methods_basis import validate_evidence_method

def canonical_subject(material_name):
    """The pre-pspp-2 canonical subject key for a material identity."""
    return f'{material_name}#as-defined'
def validate_claim(row):
    """Evidence-bearing verdict for one claim row (or dict-like) —
    checks the evidence method against the vocabulary and that the
    method's required provenance is not silently absent."""
    get = (row.get if isinstance(row, dict)
           else lambda k, d='': getattr(row, k, d))
    method = get('evidence_method', 'unknown')
    verdict = validate_evidence_method(method)
    if not verdict['ok']:
        return verdict
    problems = []
    if not get('subject_state_key', ''):
        problems.append("subject_state_key is empty — a claim must name "
                        "its state ('<material>#<state>')")
    if method != 'unknown' and not (get('provenance_id', '')
                                    or get('source_execution_id', '')):
        problems.append(f'evidence method {method!r} requires provenance '
                        '(provenance_id or source_execution_id) — see '
                        'its EvidenceMethod.required_provenance')
    if problems:
        return {'ok': False, 'refusal': '; '.join(problems),
                'suggestion': 'fill the named fields on the claim row'}
    return {'ok': True, 'evidenceMethod': method}
def claim_summary(row):
    """The page-facing view of one claim row."""
    def loads(attr, fallback):
        try:
            return json.loads(getattr(row, attr, '') or fallback)
        except Exception:
            return json.loads(fallback)
    return {
        'name': getattr(row, 'name', ''),
        'subject': getattr(row, 'subject_state_key', ''),
        'property': getattr(row, 'property_meaning_name',
                            getattr(row, 'descriptor_name', '')),
        'scaleLevel': getattr(row, 'scale_level', 0),
        'value': getattr(row, 'value', None),
        'valueDetail': loads('value_json', 'null'),
        'units': getattr(row, 'units', ''),
        'evidenceMethod': getattr(row, 'evidence_method', 'unknown'),
        'assumptions': loads('assumptions_json', '[]'),
        'validity': loads('validity_json', '{}'),
        'confidence': loads('confidence_json', 'null'),
        'sourceExecution': getattr(row, 'source_execution_id', ''),
    }
def claims_for_subject(manager, subject_state_key,
                       table='PropertyClaim'):
    """All claims on one state, as summaries — the one lookup the
    detail views (and later gates) read claims through."""
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    rows = rows.values() if isinstance(rows, dict) else rows
    return [claim_summary(r) for r in rows
            if getattr(r, 'subject_state_key', '') == subject_state_key]
