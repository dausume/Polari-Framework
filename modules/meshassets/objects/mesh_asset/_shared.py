"""@module meshassets.objects.mesh_asset._shared — what the mesh_asset row classes share (constants, seeds, helpers); split from mesh_asset_basis.py (sap-2c)."""

PROJECT_LICENSE_SPDX = 'GPL-3.0-or-later'
PROJECT_LICENSE_VERIFIED_FROM = (
    './LICENSE (suite root) and polari-rf-node/polari-framework/'
    'LICENSE — GNU GPL v3 full text, read 2026-07-30')
COMPATIBILITY = {
    'CC0-1.0': {
        'compatible': True, 'relation': 'public-domain',
        'attribution_required': False, 'share_alike': False,
        'why': 'CC0 waives rights worldwide — nothing to satisfy. '
               'Credit is appreciated by the publishers and we give '
               'it anyway, but it is courtesy, not obligation.'},
    'public-domain': {
        'compatible': True, 'relation': 'public-domain',
        'attribution_required': False, 'share_alike': False,
        'why': 'No rights reserved; no obligations attach.'},
    'MIT': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Permissive and GPL-compatible; the copyright notice '
               'and licence text must be preserved in what we '
               'ship.'},
    'BSD-3-Clause': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Permissive and GPL-compatible; notice preserved.'},
    'Apache-2.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'GPLv3-compatible specifically (NOT GPLv2 — the '
               'patent-termination clause is why). We are v3, so '
               'this is fine.'},
    'CC-BY-4.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Attribution only. The credit must travel with the '
               'asset wherever it goes.'},
    'CC-BY-3.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Attribution only.'},
    'CC-BY-SA-4.0': {
        'compatible': True, 'relation': 'one-way-into-gplv3',
        'attribution_required': True, 'share_alike': True,
        'why': 'Creative Commons declared CC BY-SA 4.0 ONE-WAY '
               'compatible with GPLv3 (2015): BY-SA material may be '
               'adapted and released under GPLv3. ONE-WAY means we '
               'can bring it in and cannot push the result back '
               'out as BY-SA — which suits us, since we are GPLv3 '
               'already.'},
    'LGPL-2.1': {
        'compatible': True, 'relation': 'relicensable-to-gpl',
        'attribution_required': True, 'share_alike': True,
        'why': 'LGPL-2.1 section 3 lets a recipient apply the '
               'ordinary GPL "version 2 or any later version" to a '
               'copy — so it reaches GPLv3 and sits comfortably in '
               'a GPLv3 project.'},
    'GPL-3.0': {
        'compatible': True, 'relation': 'same-licence',
        'attribution_required': True, 'share_alike': True,
        'why': 'Identical terms to ours.'},
    'GPL-2.0-only': {
        'compatible': False, 'relation': 'incompatible',
        'attribution_required': True, 'share_alike': True,
        'why': 'GPLv2 WITHOUT "or later" cannot be combined with '
               'GPLv3 — the one genuinely blocking copyleft case, '
               'named so it is not confused with the compatible '
               'ones above.'},
    'NONE': {
        'compatible': False, 'relation': 'no-licence',
        'attribution_required': False, 'share_alike': False,
        'why': 'No licence means default copyright: no rights are '
               'granted to us. Our own licence cannot create '
               'permission the author never gave. Ask them.'},
    'NOASSERTION': {
        'compatible': False, 'relation': 'no-licence',
        'attribution_required': False, 'share_alike': False,
        'why': 'The host could not identify a licence — treat as '
               'unlicensed until a human reads the actual terms.'},
}
VERIFICATION_METHODS = ('api', 'file', 'header', 'site-terms',
                        'not-checked')
ASSET_SUBJECTS = ('leaf', 'stem', 'branch', 'root-visible', 'fruit',
                  'flower', 'tuber', 'whole-plant',
                  'gear', 'hardware', 'other')
