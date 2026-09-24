"""
@module tensortree.objects.tensortree.TensorDiscoveryPolicy

Row class TensorDiscoveryPolicy of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorDiscoveryPolicy(treeObject):
    """THE SCORE IS CONFIGURATION, not a scientific constant (plan §F3): weights and the evidence map of the ranking a selection's candidate mappings get AFTER the hard filters (dims ⊆ selection, units, validity domain). Invalid mappings are never rescued by a score."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        w_evidence: float = 0.3,
        w_dims: float = 0.25,
        w_validity: float = 0.25,
        w_context: float = 0.1,
        w_uncertainty: float = 0.1,
        evidence_map_json: str = '{"measured": 1.0, "validated": 0.85, "implemented": 0.65, "analytical": 0.4, "proposed": 0.2, "none": 0.1}',
        is_default: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.w_evidence = w_evidence
        self.w_dims = w_dims
        self.w_validity = w_validity
        self.w_context = w_context
        self.w_uncertainty = w_uncertainty
        self.evidence_map_json = evidence_map_json
        self.is_default = is_default
        self.notes = notes
