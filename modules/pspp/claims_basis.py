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

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.evidence_methods_basis import validate_evidence_method


class PropertyClaim(treeObject):
    """One claimed property value for one material state at one scale."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<subject>:<property>@L<level>[-variant]'.
        name: str = '',
        # '<material>#<state>' ('beeswax#as-defined').
        subject_state_key: str = '',
        # MaterialPropertyMeaning.name the value means.
        property_meaning_name: str = '',
        scale_level: int = 0,
        value: float = 0.0,
        # Non-scalar values (distributions, tensors, Q-splits) — JSON;
        # when set, `value` is a representative scalar or 0.
        value_json: str = '',
        units: str = '',
        # EvidenceMethod identifier (pspp.evidence_methods_basis vocabulary).
        evidence_method: str = 'unknown',
        # JSON list of assumption strings ('isotropic', 'no cracks').
        assumptions_json: str = '[]',
        # JSON dict of validity bounds ({'temperatureC': [20, 80]}).
        validity_json: str = '{}',
        # The engine run / process execution that produced this ('' =
        # entered by hand, which required_provenance then covers).
        source_execution_id: str = '',
        # Optional interval/distribution/variance (JSON '' = none —
        # provenance without pretend statistics).
        confidence_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_state_key = subject_state_key
        self.property_meaning_name = property_meaning_name
        self.scale_level = scale_level
        self.value = value
        self.value_json = value_json
        self.units = units
        self.evidence_method = evidence_method
        self.assumptions_json = assumptions_json
        self.validity_json = validity_json
        self.source_execution_id = source_execution_id
        self.confidence_json = confidence_json
        self.provenance_id = provenance_id
        self.notes = notes


class StructureClaim(treeObject):
    """One claimed STRUCTURE descriptor (porosity, phase fraction,
    Q-distribution…) for one state at one scale — same evidence payload
    as PropertyClaim, different subject vocabulary (descriptors, which
    pspp-3's structure layer owns)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject_state_key: str = '',
        # Descriptor key ('totalPorosity', 'qDistribution').
        descriptor_name: str = '',
        scale_level: int = 0,
        value: float = 0.0,
        value_json: str = '',
        units: str = '',
        evidence_method: str = 'unknown',
        assumptions_json: str = '[]',
        validity_json: str = '{}',
        source_execution_id: str = '',
        confidence_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_state_key = subject_state_key
        self.descriptor_name = descriptor_name
        self.scale_level = scale_level
        self.value = value
        self.value_json = value_json
        self.units = units
        self.evidence_method = evidence_method
        self.assumptions_json = assumptions_json
        self.validity_json = validity_json
        self.source_execution_id = source_execution_id
        self.confidence_json = confidence_json
        self.provenance_id = provenance_id
        self.notes = notes


class ValidationClaim(treeObject):
    """A validation statement ABOUT other claims/states ('the L1
    elastic claim matched the 7-day compression test within 8%') —
    the evidence that upgrades a claim's standing."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject_state_key: str = '',
        # The claim row this validates ('' = validates the state
        # itself, e.g. 'phase identity confirmed by XRD').
        validated_claim_name: str = '',
        # 'confirmed' | 'contradicted' | 'inconclusive'
        verdict: str = 'inconclusive',
        statement: str = '',
        evidence_method: str = 'measured',
        assumptions_json: str = '[]',
        source_execution_id: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_state_key = subject_state_key
        self.validated_claim_name = validated_claim_name
        self.verdict = verdict
        self.statement = statement
        self.evidence_method = evidence_method
        self.assumptions_json = assumptions_json
        self.source_execution_id = source_execution_id
        self.provenance_id = provenance_id
        self.notes = notes


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
