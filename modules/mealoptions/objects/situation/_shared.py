"""@module mealoptions.objects.situation._shared — what the situation row classes share (constants, seeds, helpers); split from situation_basis.py (sap-2c)."""

_PROV = 'mlg-1'
COLD_CHAIN_CITATION = ('USDA FSIS "Keeping Bag Lunches Safe": perishables must not '
                       'sit above 40 °F for more than 2 hours; an insulated bag with '
                       'frozen gel packs (or a frozen juice box) keeps food cold '
                       'until lunch — transcribed prior')
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
