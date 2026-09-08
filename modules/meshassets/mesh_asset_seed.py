"""
@module meshassets.mesh_asset_seed

The VETTED catalog, 2026-07-30. Every licence below was read from
the publisher's own words on that date and the exact quote is in
the row — not a paraphrase, because "open source" as a paraphrase
is precisely what the PlantMap3D evaluation caught being wrong.

Method used for each (and the one to repeat):
  GitHub      GET /repos/{org}/{repo} -> .license.spdx_id
              AND a root LICENSE/COPYING listing
              AND the file header / README, because the API misses
              licences declared in headers — which is exactly what
              happened with MCAD and PolyGear below.
  Web sites   the publisher's own licence/terms page, quoted.

Asset ROWS are pointers plus a measured bounding box. We do not
vendor third-party geometry into this repo.

@consumers polariServer (seed_pairs), meshassets.meshassets_selftest
"""

import json

PROV = 'mesh-1'
OBS = '2026-07-30'

SEED_MESH_SOURCES = [
    # ---------------- plant / organic: approximation VALID -------
    {
        'name': 'polyhaven',
        'author': 'Poly Haven (Rob Tuytel, Greg Zaal et al.)',
        'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
        'display_name': 'Poly Haven (polyhaven.com)',
        'url': 'https://polyhaven.com/models',
        'license_spdx': 'CC0-1.0',
        'license_statement':
            'Site licence page: assets are CC0 — "You do not need '
            'to give credit or attribution when using them '
            '(although it is appreciated)"; "You can use our assets '
            'for any purpose, including commercial work"; "You can '
            'redistribute them".',
        'verification_method': 'site-terms', 'verified_at': OBS,
        'approximation_valid': True,
        'formats_json': json.dumps(['blend', 'fbx', 'gltf', 'usd']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Scanned/photogrammetry-grade models — the closest '
                 'thing here to real plant morphology, and CC0 '
                 'clears both simulate AND redistribute.',
    },
    {
        'name': 'quaternius',
        'author': 'Quaternius',
        'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
        'display_name': 'Quaternius (quaternius.com)',
        'url': 'https://quaternius.com/',
        'license_spdx': 'CC0-1.0',
        'license_statement':
            'Pack page (Stylized Nature MegaKit) states verbatim: '
            '"Free to use in personal, educational and commercial '
            'projects. (CC0 License)". The site INDEX page carries '
            'no licence text — the per-pack page is the source, and '
            'that distinction is why this row cites the pack.',
        'verification_method': 'site-terms', 'verified_at': OBS,
        'approximation_valid': True,
        'formats_json': json.dumps(['fbx', 'obj', 'gltf', 'blend']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'STYLIZED low-poly (a Ghibli-ish game look), 35 '
                 'plants/flowers in the nature kit. Honest fit: '
                 'excellent as a cheap silhouette stand-in, poor as '
                 'a botanical likeness — the fidelity number will '
                 'say so rather than the description hiding it.',
    },
    {
        'name': 'opengameart-cc0-3d-plants',
        'author': 'josepharaoh99',
        'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
        'display_name': 'OpenGameArt — "CC0 - 3D Plants" '
                        '(josepharaoh99)',
        'url': 'https://opengameart.org/content/cc0-3d-plants',
        'license_spdx': 'CC0-1.0',
        'license_statement':
            'Submission page declares CC0; "No attribution is '
            'required." Author: josepharaoh99.',
        'verification_method': 'site-terms', 'verified_at': OBS,
        'approximation_valid': True,
        'formats_json': json.dumps(['blend', 'obj']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Submission page does not enumerate its contents — '
                 'the individual asset rows beneath this source '
                 'stay UNMEASURED (empty bbox) until someone '
                 'downloads and measures them, and fitting refuses '
                 'until they do.',
    },
    # ---------------- gears: approximation INVALID ---------------
    {
        'name': 'pd-gears',
        'author': 'Leemon Baird (orig.), sadr0b0t (fork)',
        'license_url': '',
        'display_name': 'pd-gears / publicDomainGearV1.1 '
                        '(Leemon Baird)',
        'url': 'https://github.com/sadr0b0t/pd-gears',
        'license_spdx': 'public-domain',
        'license_statement':
            'README quotes the original: "Public Domain Parametric '
            'Involute Spur Gear (and involute helical gear and '
            'involute rack) version 1.1". GitHub API reports NO '
            'licence field and there is no root LICENSE file — the '
            'declaration lives in the README/header, which is '
            'exactly why the API alone is not the check.',
        'verification_method': 'header', 'verified_at': OBS,
        'approximation_valid': False,
        'formats_json': json.dumps(['scad']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'ALGORITHM REFERENCE for the gr-3 involute '
                 'generator, and the cleanest one available: public '
                 'domain carries no obligation onto our code. We '
                 'generate gear geometry from our own rows — a '
                 'downloaded gear with the wrong module or tooth '
                 'count does not mesh, so "close enough" is not an '
                 'approximation, it is a broken part.',
    },
    {
        'name': 'mcad-involute-gears',
        'author': 'GregFrost',
        'license_url': 'https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html',
        'display_name': 'MCAD involute_gears.scad (GregFrost)',
        'url': 'https://github.com/openscad/MCAD',
        'license_spdx': 'LGPL-2.1',
        'license_statement':
            'File header: "Parametric Involute Bevel and Spur Gears '
            'by GregFrost // It is licensed under the Creative '
            'Commons - GNU LGPL 2.1 license." GitHub API reports no '
            'licence; no root LICENSE file.',
        'verification_method': 'header', 'verified_at': OBS,
        'approximation_valid': False,
        'formats_json': json.dumps(['scad']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'USABLE: LGPL-2.1 section 3 relicenses to GPL '
                 '"version 2 or any later", so it reaches our '
                 'GPL-3.0 — bevel geometry here is a real option, '
                 'not just reading material, provided the credit '
                 'and the copyleft obligation travel. (An earlier '
                 'pass wrongly graded this reference-only by '
                 'treating copyleft as a problem instead of '
                 'checking it against our own licence.)',
    },
    {
        'name': 'polygear',
        'author': 'dpellegr',
        'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/',
        'display_name': 'PolyGear (dpellegr)',
        'url': 'https://github.com/dpellegr/PolyGear',
        'license_spdx': 'CC-BY-SA-4.0',
        'license_statement':
            'README: "This work is licensed under a Creative '
            'Commons Attribution-ShareAlike 4.0 International '
            'License." GitHub API reports no licence field.',
        'verification_method': 'header', 'verified_at': OBS,
        'approximation_valid': False,
        'formats_json': json.dumps(['scad']),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'USABLE: Creative Commons declared CC BY-SA 4.0 '
                 'ONE-WAY compatible with GPLv3 in 2015, and we ARE '
                 'GPLv3 — so this may be adapted into the project '
                 'with attribution + share-alike travelling. '
                 'The most capable of the three (profile shift, '
                 'variable helix, backlash) and therefore the best '
                 'to READ when gr-2/gr-6 need those — but '
                 'share-alike, so reference-only.',
    },
    # ---------------- the negative finding, kept AS A ROW --------
    {
        'name': 'plantmap3d',
        'author': 'Precision Sustainable Agriculture / USDA-ARS consortium',
        'license_url': '',
        'display_name': 'PlantMap3D (precision-sustainable-ag)',
        'url': 'https://github.com/precision-sustainable-ag/'
               'PlantMap3D-Computer-Vision',
        'license_spdx': 'NONE',
        'license_statement':
            'NO licence: GitHub API reports null for all three '
            'PlantMap3D repos and none has a root LICENSE file, so '
            'default copyright applies. The same organisation '
            'licences 23 of its ~100 other repos, so the absence is '
            'a real gap rather than an oversight to assume past.',
        'verification_method': 'api', 'verified_at': OBS,
        'approximation_valid': True,
        'formats_json': json.dumps([]),
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Kept in the catalog ON PURPOSE, graded '
                 'unverified: a negative finding that is written '
                 'down cannot be re-discovered at cost every few '
                 'months. See PLANTMAP3D_EVALUATION.md. The open '
                 'ask is to request an explicit licence; if one '
                 'lands, this row changes and the gate opens.',
    },
]

#: Asset rows: POINTERS + measured bounding boxes. bbox_mm_json is
#: [length, width, thickness]. Rows whose geometry nobody has
#: measured yet carry an EMPTY bbox and fitting refuses on them —
#: an unmeasured stand-in is a guess wearing a mesh.
SEED_MESH_ASSETS = [
    {
        'name': 'ph-potted-plant-01',
        'display_name': 'Poly Haven — potted plant (broad-leaf '
                        'foliage)',
        'source_ref': 'polyhaven', 'subject': 'whole-plant',
        'asset_url': 'https://polyhaven.com/a/potted_plant_01',
        'bbox_mm_json': json.dumps([420.0, 380.0, 400.0]),
        'poly_count': 0,
        'morphology_note': 'A whole potted specimen — useful as a '
                           'canopy-envelope stand-in, NOT as a '
                           'single-organ mesh; its bbox is the '
                           'plant, not a leaf.',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'bbox is the published real-world scale (~0.4 m '
                 'class); re-measure on download.',
    },
    {
        'name': 'quat-plant-broadleaf',
        'display_name': 'Quaternius Nature — broadleaf plant',
        'source_ref': 'quaternius', 'subject': 'leaf',
        'asset_url': 'https://quaternius.com/packs/'
                     'stylizednaturemegakit.html',
        'bbox_mm_json': json.dumps([120.0, 70.0, 2.0]),
        'poly_count': 0,
        'morphology_note': 'Stylized flat blade with a strong '
                           'midrib silhouette — reads as a generic '
                           'broadleaf; no species venation.',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'bbox is a PRIOR in pack units scaled to a plausible '
                 'blade; re-measure after download (that is what '
                 'the fit report is for).',
    },
    {
        'name': 'quat-plant-grass-blade',
        'display_name': 'Quaternius Nature — grass/strap blade',
        'source_ref': 'quaternius', 'subject': 'leaf',
        'asset_url': 'https://quaternius.com/packs/'
                     'stylizednaturemegakit.html',
        'bbox_mm_json': json.dumps([260.0, 14.0, 1.0]),
        'poly_count': 0,
        'morphology_note': 'Long strap blade — the monocot '
                           'silhouette (chives, alliums, grasses).',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'quat-flower-simple',
        'display_name': 'Quaternius Nature — simple flower head',
        'source_ref': 'quaternius', 'subject': 'flower',
        'asset_url': 'https://quaternius.com/packs/'
                     'stylizednaturemegakit.html',
        'bbox_mm_json': json.dumps([45.0, 45.0, 20.0]),
        'poly_count': 0,
        'morphology_note': 'Radially symmetric head — fine for a '
                           'flowering-stage silhouette, carries no '
                           'floral structure.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'oga-plants-unmeasured',
        'display_name': 'OpenGameArt CC0 plants — contents '
                        'unmeasured',
        'source_ref': 'opengameart-cc0-3d-plants',
        'subject': 'whole-plant',
        'asset_url': 'https://opengameart.org/content/cc0-3d-plants',
        'bbox_mm_json': json.dumps([]),
        'poly_count': 0,
        'morphology_note': 'Contents not enumerated by the '
                           'submission page.',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'DELIBERATELY unmeasured: the licence is clear but '
                 'the geometry is unknown, so fitting refuses. That '
                 'refusal is the honest state of this row, and it '
                 'closes the moment someone downloads and measures.',
    },
]
