"""
@module casting.objects.interventions.FillInterventionDefinition

Row class FillInterventionDefinition of the casting module — one class per file (design §7), split
from interventions_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from casting.objects.interventions._shared import INTERVENTION_KINDS

class FillInterventionDefinition(treeObject):
    """One available intervention knob — kind, default magnitude,
    where it applies. Evaluation is evaluate_intervention; a row is
    a capability, never an auto-applied action."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 kind: str = 'pressure-positive',
                 # kPa for pressures; Δ°C for heat/chill.
                 default_magnitude: float = 0.0,
                 applied_at: str = 'sprue',
                 is_prior: bool = True, notes: str = '',
                 provenance_id: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.kind = (kind if kind in INTERVENTION_KINDS
                     else 'pressure-positive')
        self.default_magnitude = default_magnitude
        self.applied_at = applied_at
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
