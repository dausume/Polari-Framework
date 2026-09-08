"""
@module household.objects.household.PersonSkill

Row class PersonSkill of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PersonSkill(treeObject):
    """A person's level + speed factor for ONE skill (refined)."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', skill_name: str = '',
                 level: str = 'novice',
                 # PRIOR from SKILL_FACTORS by level; refined from observations.
                 speed_factor: float = 1.3, fidelity: str = 'estimate',
                 observation_count: int = 0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.skill_name = skill_name
        self.level = level
        self.speed_factor = speed_factor
        self.fidelity = fidelity
        self.observation_count = observation_count
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
