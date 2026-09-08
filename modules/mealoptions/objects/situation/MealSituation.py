"""
@module mealoptions.objects.situation.MealSituation

Row class MealSituation of the mealoptions module — one class per file (design §7), split
from situation_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealSituation(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', eaten_at: str = 'home',
                 reheat_available: bool = True, needs_container: str = '',
                 needs_cold_pack: bool = False, cold_pack_count: int = 0,
                 cold_hours_required: float = 0.0, pack_minutes: float = 0.0,
                 pack_when: str = 'morning',   # night-before | morning
                 citation: str = '', is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.eaten_at = eaten_at
        self.reheat_available = reheat_available
        self.needs_container = needs_container
        self.needs_cold_pack = needs_cold_pack
        self.cold_pack_count = cold_pack_count
        self.cold_hours_required = cold_hours_required
        self.pack_minutes = pack_minutes
        self.pack_when = pack_when
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
