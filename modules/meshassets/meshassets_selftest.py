"""
@module meshassets.meshassets_selftest

mesh-1 selftests. Hand-checked numbers:

  basil leaf organ  60 x 35 x 1.5 mm  (lamina)
  quat broadleaf    120 x 70 x 2.0 mm
    scales          0.5, 0.5, 0.75  -> fidelity 0.5/0.75 = 0.6667
                    => usable-with-distortion (the mesh is 33%
                    too thick for the blade once sized)
  quat grass blade  260 x 14 x 1.0 mm
    scales          0.2308, 2.5, 1.5 -> fidelity 0.0923
                    => wrong-shape (a strap blade is NOT a basil
                    leaf, and the number says so without anyone
                    eyeballing it)

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m
meshassets.meshassets_selftest
"""

import types

from meshassets.mesh_asset_seed import (
    SEED_MESH_ASSETS, SEED_MESH_SOURCES,
)
from meshassets.custom.mesh_fit import (
    candidates_for_organ, citation_manifest, citation_record,
    fit_asset_to_organ, license_gate, source_catalog,
)
from plant_morphology.morphology_seed import SEED_ORGAN_MODELS

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    return types.SimpleNamespace(objectTables={
        'MeshAssetSource': table(SEED_MESH_SOURCES),
        'MeshAssetReference': table(SEED_MESH_ASSETS),
        'OrganModel': table(SEED_ORGAN_MODELS),
        'OrganMeshChoice': {},
    })


mgr = _mgr()

print('== suite: compatibility is judged against OUR licence ==')
cat = source_catalog(mgr)
by_src = {s['name']: s for s in cat['sources']}
check('7 sources catalogued, each with a quoted licence statement',
      cat['count'] == 7
      and all(s['license']['statement'] for s in cat['sources']),
      extra=str(cat['count']))
check('the verdict names OUR licence (GPL-3.0) and where it was '
      'verified from — a relation, not a property',
      cat['projectLicense'] == 'GPL-3.0-or-later'
      and 'LICENSE' in by_src['polyhaven']['license']
      ['projectLicenseVerifiedFrom'])
check('CC0 is compatible with NO obligations attached',
      by_src['polyhaven']['license']['compatible']
      and not by_src['polyhaven']['license']['attributionRequired']
      and not by_src['polyhaven']['license']['shareAlike'])
check('CC-BY-SA-4.0 IS compatible — Creative Commons declared it '
      'ONE-WAY into GPLv3, and we are GPLv3 (the correction: '
      'copyleft is not a problem for a copyleft project)',
      by_src['polygear']['license']['compatible']
      and by_src['polygear']['license']['relation']
      == 'one-way-into-gplv3'
      and by_src['polygear']['license']['shareAlike'])
check('LGPL-2.1 IS compatible — its section 3 relicenses to GPL '
      '"v2 or any later", which reaches ours',
      by_src['mcad-involute-gears']['license']['compatible']
      and 'section 3' in by_src['mcad-involute-gears']['license']
      ['why'])
check('public-domain pd-gears is compatible with nothing to '
      'satisfy',
      by_src['pd-gears']['license']['compatible']
      and not by_src['pd-gears']['license']['attributionRequired'])
check('PlantMap3D stays INCOMPATIBLE — no licence means default '
      'copyright, and OUR licence cannot invent permission the '
      'author never gave',
      not by_src['plantmap3d']['license']['compatible']
      and 'cannot create permission'
      in by_src['plantmap3d']['license']['why'])
check('GPL-2.0-only is named as the one genuinely blocking '
      'copyleft case, so it is not confused with the compatible '
      'ones',
      license_gate(types.SimpleNamespace(
          name='x', license_spdx='GPL-2.0-only'))['compatible']
      is False)
check('an UNREVIEWED spdx is incompatible BY CONSTRUCTION',
      license_gate(types.SimpleNamespace(
          name='x', license_spdx='WTFPL-9000'))['relation']
      == 'unreviewed')
check('the verdict disclaims being legal advice and points at the '
      'quote + link as the authority',
      'not legal advice'
      in by_src['polygear']['license']['disclaimer'])
check('every licence row records HOW it was verified and when',
      all(s['license']['verificationMethod'] != 'not-checked'
          and s['license']['verifiedAt']
          for s in cat['sources']))
check('the header/API split is captured: the three gear libraries '
      'were verified by HEADER because the GitHub API reported '
      'nothing',
      all(by_src[n]['license']['verificationMethod'] == 'header'
          for n in ('pd-gears', 'mcad-involute-gears', 'polygear')))

print('== suite: gears REFUSE to be approximated ==')
out = fit_asset_to_organ(mgr, 'sweet-basil-leaf-organ',
                         'quat-plant-broadleaf')
check('a plant asset fits fine (approximation is valid for organic '
      'parts)', out.get('ok'))
check('gear sources are flagged approximation-INVALID — "close '
      'enough" gears do not mesh',
      all(not by_src[n]['approximationValid']
          for n in ('pd-gears', 'mcad-involute-gears', 'polygear'))
      and by_src['quaternius']['approximationValid'])

print('== suite: the FIT against our vector organ definitions ==')
out = fit_asset_to_organ(mgr, 'sweet-basil-leaf-organ',
                         'quat-plant-broadleaf')
check('basil leaf (60x35x1.5) vs broadleaf mesh (120x70x2.0): '
      'scales 0.5 / 0.5 / 0.75 — hand-computed',
      abs(out['scale']['length'] - 0.5) < 1e-9
      and abs(out['scale']['width'] - 0.5) < 1e-9
      and abs(out['scale']['thickness'] - 0.75) < 1e-9,
      extra=str(out.get('scale')))
check('shape fidelity = 0.5/0.75 = 0.6667 -> usable WITH stated '
      'distortion, not a silent pass',
      abs(out['shapeFidelity'] - 0.6667) < 1e-3
      and out['verdict'] == 'usable-with-distortion'
      and 'distorted' in out['reading'],
      extra=str(out.get('shapeFidelity')))
check('the subject matches (a leaf asset for a leaf organ) and the '
      'payload says so', out['subjectMatches'] is True)
out = fit_asset_to_organ(mgr, 'sweet-basil-leaf-organ',
                         'quat-plant-grass-blade')
check('a STRAP blade against a basil leaf scores ~0.09 and is '
      'called WRONG-SHAPE — the metric catches what eyeballing a '
      'thumbnail would not',
      abs(out['shapeFidelity'] - 0.0923) < 1e-3
      and out['verdict'] == 'wrong-shape'
      and 'different shape wearing' in out['reading'],
      extra=str(out.get('shapeFidelity')))
check('fidelity is honestly scoped: proportions from bounding '
      'boxes, NOT silhouette/venation/curvature',
      'never' in out['honesty'] and 'venation' in out['honesty'])

print('== suite: pick and choose ==')
out = candidates_for_organ(mgr, 'sweet-basil-leaf-organ')
check('candidates ranked SUBJECT-first: leaf assets outrank a '
      'better-proportioned non-leaf',
      out['ok'] and out['candidates'][0]['assetSubject'] == 'leaf'
      and out['candidates'][0]['subjectMatches'] is True)
check('the best basil-leaf candidate is the broadleaf mesh',
      out['candidates'][0]['asset'] == 'quat-plant-broadleaf',
      extra=out['candidates'][0]['asset'])
rej = {r['asset']: r['reason'] for r in out['rejected']}
check('rejected candidates are LISTED WITH REASONS, never silently '
      'dropped', len(rej) >= 1)
check('the unmeasured OpenGameArt row refuses for the honest '
      'reason (no bbox), not for its licence — which is fine',
      'no measured bounding box' in rej.get('oga-plants-unmeasured',
                                            ''),
      extra=str(rej.get('oga-plants-unmeasured'))[:70])
out = candidates_for_organ(mgr, 'sweet-basil-leaf-organ',
                           min_fidelity=0.5)
check('a fidelity floor filters the wrong-shape candidates out AND '
      'says why they went',
      all(c['shapeFidelity'] >= 0.5 for c in out['candidates'])
      and any('below the requested floor' in r['reason']
              for r in out['rejected']))

print('== suite: CITATIONS TRACKED AS DATA ==')
rec = citation_record(mgr, 'quat-plant-broadleaf')
check('a citation carries TASL — title, author, source, licence — '
      'plus a link to the terms',
      rec['ok'] and rec['title'] and rec['author'] == 'Quaternius'
      and rec['sourceUrl'] and rec['licenseSpdx'] == 'CC0-1.0'
      and rec['licenseUrl'],
      extra=str(rec.get('citationLine'))[:70])
check('the citation LINE is ready to paste into a credits file',
      'Quaternius' in rec['citationLine']
      and 'CC0-1.0' in rec['citationLine']
      and rec['complete'] is True)
check('adaptations must be declared — and an OrganMeshChoice IS an '
      'adaptation (it records the per-axis scaling)',
      'adaptation' in rec['modificationNote'])
rec = citation_record(mgr, 'oga-plants-unmeasured')
check('a CC0 asset needs no attribution, so a thin credit is still '
      'COMPLETE (obligations drive the gaps, not tidiness)',
      rec['complete'] is True
      and rec['attributionRequired'] is False)

mgr_gap = _mgr()
mgr_gap.objectTables['MeshAssetSource']['quaternius'].author = ''
mgr_gap.objectTables['MeshAssetSource']['quaternius'] \
    .license_spdx = 'CC-BY-4.0'
rec = citation_record(mgr_gap, 'quat-plant-broadleaf')
check('an attribution-REQUIRED licence with no author reports the '
      'GAP instead of quietly crediting the website',
      rec['complete'] is False
      and any('author missing' in g for g in rec['gaps'])
      and 'author UNKNOWN' in rec['citationLine'],
      extra=str(rec.get('gaps')))

man = citation_manifest(mgr)
check('the manifest covers every catalogued asset and names OUR '
      'licence', man['count'] == 5
      and man['projectLicense'] == 'GPL-3.0-or-later')
check('the manifest doubles as the DO-NOT-SHIP list: incompatible '
      'assets are listed, flagged, with the reason on record',
      isinstance(man['blockedAssets'], list)
      and 'do-not-ship' not in man['note']
      and 'NOT usable' in man['note'])
mgr_blocked = _mgr()
mgr_blocked.objectTables['MeshAssetReference'][
    'quat-plant-broadleaf'].source_ref = 'plantmap3d'
man = citation_manifest(mgr_blocked)
check('an asset under an unlicensed source lands in blockedAssets',
      'quat-plant-broadleaf' in man['blockedAssets'])

print('== suite: refusal ladder ==')
check('unknown organ refuses',
      not fit_asset_to_organ(mgr, 'nope',
                             'quat-plant-broadleaf').get('ok'))
check('unknown asset refuses',
      not fit_asset_to_organ(mgr, 'sweet-basil-leaf-organ',
                             'nope').get('ok'))
mgr2 = _mgr()
mgr2.objectTables['MeshAssetReference']['orphan'] = \
    types.SimpleNamespace(name='orphan', source_ref='ghost',
                          subject='leaf', bbox_mm_json='[1,1,1]')
out = fit_asset_to_organ(mgr2, 'sweet-basil-leaf-organ', 'orphan')
check('an asset with no licence FINDING behind it is unusable by '
      'definition',
      not out.get('ok') and 'unknown source' in out['refusal'])
mgr3 = _mgr()
mgr3.objectTables['MeshAssetReference']['quat-plant-broadleaf'] \
    .source_ref = 'plantmap3d'
out = fit_asset_to_organ(mgr3, 'sweet-basil-leaf-organ',
                         'quat-plant-broadleaf')
check('a well-fitting mesh under an UNVERIFIED licence still '
      'refuses — fit never overrides the gate, and the suggestion '
      'is to ASK rather than to assume',
      not out.get('ok')
      and 'licence-gated' in out['refusal']
      and 'publisher' in out['suggestion']['action'],
      extra=str(out.get('refusal'))[:80])

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
