"""@module collab.objects.avatar._shared — what the avatar row classes share (constants, seeds, helpers); split from avatar_basis.py (sap-2c)."""

AVATAR_RIGS = ('head-hands', 'head-only')
AVATAR_LICENCES = ('unstated', 'CC0', 'CC-BY', 'GPLv3-compatible',
                   'project-owned')
_USABLE_LICENCES = ('CC0', 'CC-BY', 'GPLv3-compatible', 'project-owned')
def usable(licence, attribution=''):
    """May this avatar be shown to other participants? Refuses an
    unstated licence, and refuses CC-BY that names nobody — an
    attribution licence with no attribution is unfulfilled, not
    merely untidy."""
    if licence not in _USABLE_LICENCES:
        return {'ok': False,
                'reason': f'licence {licence!r} is not usable here '
                          '(unstated licence = all rights reserved; '
                          'silence is not permission)'}
    if licence == 'CC-BY' and not (attribution or '').strip():
        return {'ok': False,
                'reason': 'CC-BY requires an attribution string, and '
                          'this row carries none — the licence is '
                          'unfulfilled until it does'}
    return {'ok': True, 'reason': ''}
SEED_AVATARS = [
    {'name': 'avatar-primitive-slate', 'display_name': 'Slate',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#6a7fd6', 'is_default': True,
     'notes': 'Default: a head and two hands drawn from primitives. '
              'No asset file, so nothing to licence-gate and nothing '
              'to download before a meeting works.'},
    {'name': 'avatar-primitive-moss', 'display_name': 'Moss',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#4f9d69', 'is_default': False,
     'notes': 'Second primitive so a room of two is legible at a '
              'glance without anyone configuring anything.'},
    {'name': 'avatar-primitive-ember', 'display_name': 'Ember',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#c9704a', 'is_default': False,
     'notes': 'Third primitive.'},
]
