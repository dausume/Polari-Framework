"""
@module pspp.objects.claims.PropertyClaim

Row class PropertyClaim of the pspp module — one class per file (design §7), split
from claims_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
