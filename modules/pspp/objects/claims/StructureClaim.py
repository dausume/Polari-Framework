"""
@module pspp.objects.claims.StructureClaim

Row class StructureClaim of the pspp module — one class per file (design §7), split
from claims_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
