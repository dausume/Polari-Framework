"""
@module pspp.objects.scale_transfers.ScaleTransferDefinition

Row class ScaleTransferDefinition of the pspp module — one class per file (design §7), split
from scale_transfers_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScaleTransferDefinition(treeObject):
    """One cross-scale information transfer between material states."""

    @treeObjectInit
    def __init__(
        self,
        # Unique: '<source_state>@L<a>-><target_state>@L<b>[-variant]'.
        name: str = '',
        source_state_key: str = '',
        source_scale: int = 0,
        target_state_key: str = '',
        target_scale: int = 0,
        # HOW: a registered engine key ('fem.effective-conductivity'),
        # a model ref ('model:wax-thermal-continuum'), or an
        # EvidenceMethod identifier for non-engine transfers
        # ('rules-of-mixtures') — validate_transfer names the options.
        transfer_method: str = '',
        # What the transfer moves (descriptor/property names, JSON).
        transported_json: str = '[]',
        assumptions_json: str = '[]',
        validity_json: str = '{}',
        uncertainty_json: str = '',
        # 'declared' | 'executed' | 'validated'
        status: str = 'declared',
        validation_evidence_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_state_key = source_state_key
        self.source_scale = source_scale
        self.target_state_key = target_state_key
        self.target_scale = target_scale
        self.transfer_method = transfer_method
        self.transported_json = transported_json
        self.assumptions_json = assumptions_json
        self.validity_json = validity_json
        self.uncertainty_json = uncertainty_json
        self.status = status
        self.validation_evidence_json = validation_evidence_json
        self.provenance_id = provenance_id
        self.notes = notes
