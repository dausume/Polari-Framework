"""
@module meshassets.selftest_meshassets

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
meshassets.selftest_meshassets
"""

import types

from meshassets.mesh_asset_seed import (
    SEED_MESH_ASSETS, SEED_MESH_SOURCES,
)
from meshassets.mesh_fit import (
    candidates_for_organ, fit_asset_to_organ, license_gate,
    source_catalog,
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

print('== suite: the licence GATE (the PlantMap3D lesson) ==')
cat = source_catalog(mgr)
by_src = {s['name']: s for s in cat['sources']}
check('7 sources catalogued, each with a quoted licence statement',
      cat['count'] == 7
      and all(s['license']['statement'] for s in cat['sources']),
      extra=str(cat['count']))
check('CC0 sources clear BOTH simulate and redistribute, with no '
      'attribution obligation',
      by_src['polyhaven']['license']['maySimulate']
      and by_src['polyhaven']['license']['mayRedistribute']
      and not by_src['polyhaven']['license']['attributionRequired'])
check('PlantMap3D is IN the catalog, graded unverified, and clears '
      'NOTHING — a written-down negative finding',
      by_src['plantmap3d']['license']['grade'] == 'unverified'
      and not by_src['plantmap3d']['license']['maySimulate']
      and not by_src['plantmap3d']['license']['mayRedistribute'])
check('copyleft (LGPL / CC-BY-SA) is reference-only: readable and '
      'runnable, NOT shippable without a human decision',
      by_src['mcad-involute-gears']['license']['grade']
      == 'reference-only'
      and by_src['polygear']['license']['grade'] == 'reference-only'
      and not by_src['polygear']['license']['mayRedistribute'])
check('public-domain pd-gears is unrestricted — the unencumbered '
      'algorithm reference for gr-3',
      by_src['pd-gears']['license']['grade'] == 'unrestricted')
check('an UNKNOWN spdx grades unverified BY CONSTRUCTION (a licence '
      'nobody graded is not one we may lean on)',
      license_gate(types.SimpleNamespace(
          name='x', license_spdx='WTFPL-9000'))['grade']
      == 'unverified')
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
