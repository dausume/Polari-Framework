"""
@module meshassets.mesh_fit

THE FIT: how close is a borrowed mesh to OUR vector-based organ
definition, and what does it take to get it there?

An OrganModel already states the organ as VECTORS — length, width,
thickness, a shape primitive and a count. A candidate mesh states
its own bounding box. Fitting is therefore not a mystery: scale the
asset per axis until its box matches the organ's, and then report
the thing that actually matters —

  SHAPE FIDELITY = min(per-axis scale) / max(per-axis scale)

1.0 means the mesh's PROPORTIONS already matched and it only needed
resizing: a genuine "close enough". 0.2 means we are squashing it
5:1 to make the numbers agree, which is not an approximation of the
organ, it is a different shape wearing the organ's dimensions. The
number says which, so nobody has to take "close enough" on trust.

This mirrors the mag-fv threshold shells: a user draws a shape, and
precision/recall MEASURE the compromise rather than the UI implying
there isn't one.

Gates, in order, because a good fit on an unusable asset is worse
than no answer:
  1. LICENCE — unverified grades refuse outright (PlantMap3D).
  2. APPROXIMATION VALIDITY — a source flagged approximation_valid
     False (gears) refuses to be offered as a stand-in at all: an
     approximate gear does not mesh.
  3. MEASUREMENT — an asset with no measured bbox refuses instead
     of inventing a size.

@consumers meshassets.mesh_asset_api, meshassets.selftest_meshassets
"""

import json

from meshassets.mesh_asset_basis import LICENSE_GRADE_BY_SPDX

#: Grades that may be used in a simulation at all.
SIMULATABLE_GRADES = ('simulate-only', 'simulate-and-attribute',
                      'unrestricted', 'reference-only')
#: Grades that may be SHIPPED inside something we hand to someone
#: else. Deliberately narrower than the above.
REDISTRIBUTABLE_GRADES = ('unrestricted', 'simulate-and-attribute')

#: Fidelity below this is reported as a poor stand-in. A judgement
#: threshold, exposed as a knob rather than buried in a comparison.
FIDELITY_GOOD = 0.75
FIDELITY_USABLE = 0.4


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except (TypeError, ValueError):
        return default


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def license_gate(source):
    """The licence finding, as a usable verdict. Unknown SPDX ->
    'unverified' BY CONSTRUCTION: a licence nobody has graded is
    not one we may lean on."""
    spdx = getattr(source, 'license_spdx', 'NONE') or 'NONE'
    grade = LICENSE_GRADE_BY_SPDX.get(spdx, 'unverified')
    attribution = grade == 'simulate-and-attribute'
    return {
        'source': getattr(source, 'name', ''),
        'licenseSpdx': spdx,
        'grade': grade,
        'maySimulate': grade in SIMULATABLE_GRADES,
        'mayRedistribute': grade in REDISTRIBUTABLE_GRADES,
        'attributionRequired': attribution,
        'verificationMethod': getattr(source, 'verification_method',
                                      'not-checked'),
        'verifiedAt': getattr(source, 'verified_at', ''),
        'statement': getattr(source, 'license_statement', ''),
        'note': ('no licence on record — default copyright applies, '
                 'so this asset may not be used at all; the fix is '
                 'to ASK the publisher, not to assume'
                 if grade == 'unverified' else
                 'copyleft: read it, run it locally, but shipping a '
                 'derivative carries obligations — a human decides '
                 'per case' if grade == 'reference-only' else
                 'attribution must travel with anything shipped'
                 if attribution else
                 'public-domain equivalent: use and redistribute '
                 'freely'),
    }


def fit_asset_to_organ(manager, organ_name, asset_name):
    """Scale one asset onto one OrganModel's vector dimensions and
    MEASURE the compromise."""
    organ = _named(manager, 'OrganModel', organ_name)
    if organ is None:
        return _refuse(
            f'no OrganModel named "{organ_name}" — is the '
            f'plant_morphology module enabled?',
            {'knob': 'POLARI_MODULES',
             'action': 'enable plant_morphology (it owns the '
                       'vector organ definitions)'})
    asset = _named(manager, 'MeshAssetReference', asset_name)
    if asset is None:
        return _refuse(f'no MeshAssetReference named '
                       f'"{asset_name}"')
    source = _named(manager, 'MeshAssetSource',
                    getattr(asset, 'source_ref', ''))
    if source is None:
        return _refuse(
            f'asset "{asset_name}" names an unknown source '
            f'"{getattr(asset, "source_ref", "")}" — an asset '
            f'without a licence finding is unusable by definition')

    gate = license_gate(source)
    if not gate['maySimulate']:
        return _refuse(
            f'asset "{asset_name}" is licence-gated: '
            f'{gate["note"]}',
            {'evidence': gate['statement'],
             'knob': 'MeshAssetSource.license_spdx',
             'action': 'obtain an explicit licence from the '
                       'publisher, then re-verify the row'})
    if not getattr(source, 'approximation_valid', True):
        return _refuse(
            f'source "{gate["source"]}" is flagged '
            f'approximation-INVALID: a gear (or any exactly-'
            f'specified part) either meshes or does not — a '
            f'"close enough" one is a broken part, not a stand-in',
            {'evidence': 'module, tooth count and pressure angle '
                         'must MATCH between mating gears',
             'knob': 'GearDefinition',
             'action': 'generate the geometry from our own rows '
                       '(GEARS_PLAN gr-3); this asset is an '
                       'algorithm reference only'})

    bbox = _loads(asset, 'bbox_mm_json', [])
    if not (isinstance(bbox, list) and len(bbox) == 3
            and all(isinstance(v, (int, float)) and v > 0
                    for v in bbox)):
        return _refuse(
            f'asset "{asset_name}" has no measured bounding box — '
            f'an unmeasured stand-in is a guess wearing a mesh',
            {'knob': 'MeshAssetReference.bbox_mm_json',
             'action': 'download the asset, measure [length, '
                       'width, thickness] in mm, and record it'})

    target = [float(getattr(organ, 'length_mm', 0.0)),
              float(getattr(organ, 'width_mm', 0.0)),
              float(getattr(organ, 'thickness_mm', 0.0))]
    if any(v <= 0 for v in target):
        return _refuse(
            f'organ "{organ_name}" has a non-positive dimension '
            f'{target} — nothing to fit against')

    scales = [t / b for t, b in zip(target, bbox)]
    fidelity = min(scales) / max(scales)
    axis_names = ('length', 'width', 'thickness')
    worst = max(range(3), key=lambda i: abs(
        scales[i] - sum(scales) / 3.0))

    if fidelity >= FIDELITY_GOOD:
        verdict = 'good-stand-in'
        reading = ('proportions already agree — this is a genuine '
                   '"close enough": it only needs resizing')
    elif fidelity >= FIDELITY_USABLE:
        verdict = 'usable-with-distortion'
        reading = (f'usable, but it is being distorted: the '
                   f'{axis_names[worst]} axis scales '
                   f'{round(max(scales) / min(scales), 2)}x '
                   f'differently from the others')
    else:
        verdict = 'wrong-shape'
        reading = (f'NOT an approximation of this organ: matching '
                   f'the numbers takes a '
                   f'{round(max(scales) / min(scales), 2)}x '
                   f'non-uniform squash, which makes it a different '
                   f'shape wearing the organ\'s dimensions')

    return {
        'ok': True,
        'organ': organ_name,
        'organType': getattr(organ, 'organ', ''),
        'shapePrimitive': getattr(organ, 'shape_primitive', ''),
        'asset': asset_name,
        'assetSubject': getattr(asset, 'subject', ''),
        'targetMm': {'length': target[0], 'width': target[1],
                     'thickness': target[2]},
        'assetBboxMm': {'length': bbox[0], 'width': bbox[1],
                        'thickness': bbox[2]},
        'scale': {'length': round(scales[0], 6),
                  'width': round(scales[1], 6),
                  'thickness': round(scales[2], 6)},
        'uniformScaleSuggestion': round(
            sum(scales) / 3.0, 6),
        'shapeFidelity': round(fidelity, 4),
        'verdict': verdict,
        'reading': reading,
        'subjectMatches': (getattr(asset, 'subject', '')
                           == getattr(organ, 'organ', '')),
        'license': gate,
        'morphologyNote': getattr(asset, 'morphology_note', ''),
        'honesty': 'shape fidelity measures PROPORTION agreement '
                   'from bounding boxes only — it does not judge '
                   'silhouette, venation or curvature. A high score '
                   'means "not obviously the wrong shape", never '
                   '"botanically right".',
    }


def candidates_for_organ(manager, organ_name, min_fidelity=0.0):
    """PICK AND CHOOSE: every catalogued asset ranked against one
    organ, best fit first, with the unusable ones listed separately
    WITH their reason — a candidate that silently vanishes teaches
    nobody why."""
    organ = _named(manager, 'OrganModel', organ_name)
    if organ is None:
        return _refuse(f'no OrganModel named "{organ_name}"')
    ranked, rejected = [], []
    for asset in _rows(manager, 'MeshAssetReference'):
        aname = getattr(asset, 'name', '')
        fit = fit_asset_to_organ(manager, organ_name, aname)
        if not fit.get('ok'):
            rejected.append({'asset': aname,
                             'reason': fit['refusal']})
            continue
        if fit['shapeFidelity'] < min_fidelity:
            rejected.append({
                'asset': aname,
                'reason': f'shape fidelity '
                          f'{fit["shapeFidelity"]} below the '
                          f'requested floor {min_fidelity}'})
            continue
        ranked.append(fit)
    # Same-subject candidates first (a leaf asset for a leaf organ),
    # then by fidelity: a well-proportioned FLOWER is still the
    # wrong thing to stand in for a leaf.
    ranked.sort(key=lambda f: (not f['subjectMatches'],
                               -f['shapeFidelity']))
    return {
        'ok': True, 'organ': organ_name,
        'organType': getattr(organ, 'organ', ''),
        'candidates': ranked, 'count': len(ranked),
        'rejected': rejected,
        'note': 'ranked by SUBJECT match first, then shape '
                'fidelity — a well-proportioned flower is still '
                'the wrong stand-in for a leaf. Choosing is a '
                'human act: record it as an OrganMeshChoice with '
                'who accepted it and why.',
    }


def source_catalog(manager):
    """Every publisher with its licence verdict — the thing to read
    BEFORE downloading anything."""
    out = []
    for s in _rows(manager, 'MeshAssetSource'):
        gate = license_gate(s)
        out.append({
            'name': getattr(s, 'name', ''),
            'displayName': getattr(s, 'display_name', ''),
            'url': getattr(s, 'url', ''),
            'formats': _loads(s, 'formats_json', []),
            'approximationValid': getattr(s, 'approximation_valid',
                                          True),
            'license': gate,
            'notes': getattr(s, 'notes', ''),
        })
    out.sort(key=lambda r: (not r['license']['mayRedistribute'],
                            r['name']))
    usable = [r for r in out if r['license']['maySimulate']]
    return {
        'ok': True, 'sources': out, 'count': len(out),
        'usableCount': len(usable),
        'note': 'licences were read from the publisher\'s own words '
                'on the date in each row, and the quote is kept. A '
                'source graded "unverified" is IN this list on '
                'purpose: a written-down negative finding does not '
                'have to be re-discovered every few months.',
    }
