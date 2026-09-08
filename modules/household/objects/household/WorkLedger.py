"""
@module household.objects.household.WorkLedger

Row class WorkLedger of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WorkLedger(treeObject):
    """What actually happened — minutes of work by person and type."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '', person_name: str = '',
                 workload_type: str = '', minutes: float = 0.0, event_name: str = '',
                 date: str = '', source: str = 'event-done',
                 is_prior: bool = False, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.person_name = person_name
        self.workload_type = workload_type
        self.minutes = minutes
        self.event_name = event_name
        self.date = date
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
