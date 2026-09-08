"""
@module nutrition.objects.logistics.MealLogistics

Row class MealLogistics of the nutrition module — one class per file (design §7), split
from logistics_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealLogistics(treeObject):
    """A MealEntry's situation (no MealEntry schema change)."""

    @treeObjectInit
    def __init__(self, name: str = '', entry_name: str = '', person_name: str = '',
                 situation_name: str = 'at-home', container_tool_name: str = '',
                 cold_pack_count: int = 0, pack_when: str = '',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.entry_name = entry_name
        self.person_name = person_name
        self.situation_name = situation_name
        self.container_tool_name = container_tool_name
        self.cold_pack_count = cold_pack_count
        self.pack_when = pack_when
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
