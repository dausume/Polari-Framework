"""
@module mealoptions.situation_basis

mlg-3 — the meal-SITUATION portability vocabulary (MEAL_LOGISTICS_PLAN
§2, D7/D8), moved here in mo-1 with its name unchanged:

  MealSituation   where a meal is eaten and what that needs
                  (lunchbox, cold packs, pack minutes, pack-when),
                  with the FSIS cold-chain citation on the rows that
                  need it.

The per-entry row (MealLogistics — names a person and an entry) and
the eating-time profile (MealTimeProfile — names a person) stay in
nutrition.logistics_basis.
"""

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'mlg-1'

COLD_CHAIN_CITATION = ('USDA FSIS "Keeping Bag Lunches Safe": perishables must not '
                       'sit above 40 °F for more than 2 hours; an insulated bag with '
                       'frozen gel packs (or a frozen juice box) keeps food cold '
                       'until lunch — transcribed prior')


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


SEED_MEAL_SITUATIONS = [
    {'name': 'at-home', 'display_name': 'At home', 'eaten_at': 'home', 'reheat_available': True,
     'needs_container': '', 'needs_cold_pack': False, 'cold_pack_count': 0,
     'cold_hours_required': 0.0, 'pack_minutes': 0.0, 'pack_when': 'morning', 'citation': ''},
    {'name': 'at-workplace-reheat', 'display_name': 'At the workplace (microwave available)',
     'eaten_at': 'workplace', 'reheat_available': True, 'needs_container': 'insulated-lunchbox',
     'needs_cold_pack': True, 'cold_pack_count': 1, 'cold_hours_required': 4.0,
     'pack_minutes': 5.0, 'pack_when': 'morning', 'citation': COLD_CHAIN_CITATION},
    {'name': 'at-workplace-cold', 'display_name': 'At the workplace (no reheating)',
     'eaten_at': 'workplace', 'reheat_available': False, 'needs_container': 'insulated-lunchbox',
     'needs_cold_pack': True, 'cold_pack_count': 2, 'cold_hours_required': 6.0,
     'pack_minutes': 6.0, 'pack_when': 'morning', 'citation': COLD_CHAIN_CITATION},
    {'name': 'packed-no-cooling', 'display_name': 'Packed, shelf-stable only',
     'eaten_at': 'away', 'reheat_available': False, 'needs_container': '',
     'needs_cold_pack': False, 'cold_pack_count': 0, 'cold_hours_required': 0.0,
     'pack_minutes': 3.0, 'pack_when': 'morning', 'citation': COLD_CHAIN_CITATION},
    {'name': 'travel', 'display_name': 'Travel day', 'eaten_at': 'away', 'reheat_available': False,
     'needs_container': 'insulated-lunchbox', 'needs_cold_pack': True, 'cold_pack_count': 2,
     'cold_hours_required': 8.0, 'pack_minutes': 8.0, 'pack_when': 'night-before',
     'citation': COLD_CHAIN_CITATION},
]
for _s in SEED_MEAL_SITUATIONS:
    _s.update({'is_prior': True, 'provenance_id': _PROV, 'notes': ''})
