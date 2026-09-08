"""
@module household.objects.household.DurationObservation

Row class DurationObservation of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DurationObservation(treeObject):
    """The refinement loop's facts: how long a step / a meal took."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 kind: str = 'prep-step',   # prep-step | final-prep | eating | packing | cleanup
                 method_name: str = '', skill_name: str = '', entry_name: str = '',
                 slot: str = '', observed_min: float = 0.0, date: str = '',
                 source: str = 'logged', is_prior: bool = False,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.person_name = person_name
        self.kind = kind
        self.method_name = method_name
        self.skill_name = skill_name
        self.entry_name = entry_name
        self.slot = slot
        self.observed_min = observed_min
        self.date = date
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
