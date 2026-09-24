"""
@module tensortree.objects.tensortree.TensorMapping

Row class TensorMapping of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorMapping(treeObject):
    """THE RELATIONSHIP between two tensor spaces (plan §14, §F2): one class, `kind` says which. It names the dims it operates on at both ends and carries validity, loss, uncertainty, TWO statuses and evidence. kind=scale over material scales is a PSPP ScaleTransferDefinition by reference; kind=scale|coupling is also a SimulationCouplingDefinition so the existing runner executes it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        kind: str = 'projection',
        source_node: str = '',
        source_dims_json: str = '[]',
        target_node: str = '',
        target_dims_json: str = '[]',
        expression_ref: str = '',
        coupling_ref: str = '',
        scale_transfer_ref: str = '',
        validity_json: str = '{}',
        units: str = '',
        conservation_json: str = '[]',
        loss_note: str = '',
        reconstruction_error: float = 0.0,
        error_method: str = '',
        uncertainty_json: str = '{}',
        mapping_status: str = 'proposed',
        evidence_level: str = 'none',
        evidence_ref: str = '',
        provenance: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.kind = kind  # projection | reconstruction | decomposition | aggregation | restriction | scale | basis-transform | coordinate-transform | operator | kernel | coupling
        self.source_node = source_node
        self.source_dims_json = source_dims_json  # the named dims consumed
        self.target_node = target_node
        self.target_dims_json = target_dims_json  # the named dims produced
        self.expression_ref = expression_ref  # TensorMathExpression.name or MatrixEquationDefinition.name
        self.coupling_ref = coupling_ref  # SimulationCouplingDefinition.name when executable
        self.scale_transfer_ref = scale_transfer_ref  # pspp ScaleTransferDefinition.name for material scales
        self.validity_json = validity_json  # domain where the mapping holds, per dim
        self.units = units
        self.conservation_json = conservation_json  # what must be conserved
        self.loss_note = loss_note  # what is lost (lossy / noninvertible)
        self.reconstruction_error = reconstruction_error  # ‖X − X̂‖ / ‖X‖ where applicable
        self.error_method = error_method
        self.uncertainty_json = uncertainty_json
        self.mapping_status = mapping_status  # proposed | implemented | validated
        self.evidence_level = evidence_level  # none | analytical | simulated | measured
        self.evidence_ref = evidence_ref
        self.provenance = provenance
        self.notes = notes
