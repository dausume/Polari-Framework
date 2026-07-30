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

from meshassets.mesh_asset_basis import (
    COMPATIBILITY, PROJECT_LICENSE_SPDX,
    PROJECT_LICENSE_VERIFIED_FROM,
)

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
    """Judge this source's licence AGAINST OUR OWN (GPL-3.0).

    Compatibility is a RELATION, not a property: being GPLv3 is
    exactly what makes CC BY-SA 4.0 and LGPL-2.1 assets usable
    here. An unlisted SPDX is unusable by construction — a licence
    nobody has reasoned about is not one to rely on."""
    spdx = getattr(source, 'license_spdx', 'NONE') or 'NONE'
    rel = COMPATIBILITY.get(spdx)
    unknown = rel is None
    if unknown:
        rel = {'compatible': False, 'relation': 'unreviewed',
               'attribution_required': False, 'share_alike': False,
               'why': f'"{spdx}" is not in the reviewed '
                      f'compatibility table — read the actual terms '
                      f'and add it before relying on this asset.'}
    return {
        'source': getattr(source, 'name', ''),
        'licenseSpdx': spdx,
        'licenseUrl': getattr(source, 'license_url', ''),
        'projectLicense': PROJECT_LICENSE_SPDX,
        'projectLicenseVerifiedFrom': PROJECT_LICENSE_VERIFIED_FROM,
        'relation': rel['relation'],
        'compatible': rel['compatible'],
        # Kept under the old key names so every caller and stored
        # payload keeps working: for a GPLv3 project these now mean
        # what they say rather than being a conservatism.
        'maySimulate': rel['compatible'],
        'mayRedistribute': rel['compatible'],
        'attributionRequired': rel['attribution_required'],
        'shareAlike': rel['share_alike'],
        'why': rel['why'],
        'verificationMethod': getattr(source, 'verification_method',
                                      'not-checked'),
        'verifiedAt': getattr(source, 'verified_at', ''),
        'statement': getattr(source, 'license_statement', ''),
        'note': (rel['why'] if not rel['compatible'] else
                 'compatible with our GPL-3.0 licence; the '
                 'share-alike/attribution obligations below travel '
                 'with anything we ship'
                 if rel['share_alike'] else
                 'compatible; attribution travels with anything we '
                 'ship' if rel['attribution_required'] else
                 'compatible with no obligations attached'),
        'disclaimer': 'licence RECORD-KEEPING, not legal advice — '
                      'the quoted statement and the link are the '
                      'authority, this verdict is our reading of '
                      'them',
    }


def citation_record(manager, asset_name):
    """THE CITATION, as data (Dustin: "assets have clear citations
    tracked as data").

    TASL — Title, Author, Source, Licence — is what CC asks for and
    what any downstream credits file needs. Where a licence requires
    attribution and a field is missing, this reports the GAP rather
    than quietly substituting the site name for a person: an
    incomplete credit that LOOKS complete is the failure mode worth
    designing against."""
    asset = _named(manager, 'MeshAssetReference', asset_name)
    if asset is None:
        return _refuse(f'no MeshAssetReference named '
                       f'"{asset_name}"')
    source = _named(manager, 'MeshAssetSource',
                    getattr(asset, 'source_ref', ''))
    if source is None:
        return _refuse(
            f'asset "{asset_name}" names an unknown source — an '
            f'asset without a licence finding cannot be cited')
    gate = license_gate(source)
    title = getattr(asset, 'display_name', '') or asset_name
    author = getattr(source, 'author', '')
    src_url = (getattr(asset, 'asset_url', '')
               or getattr(source, 'url', ''))

    gaps = []
    if gate['attributionRequired']:
        if not author:
            gaps.append('author missing, and this licence REQUIRES '
                        'attribution — find the credited creator '
                        'before shipping this asset')
        if not src_url:
            gaps.append('source URL missing')
        if not gate['licenseUrl']:
            gaps.append('licence URL missing — a credit should link '
                        'the terms, not just name them')

    line = (f'"{title}"'
            + (f' by {author}' if author else ' (author UNKNOWN)')
            + (f' — {src_url}' if src_url else '')
            + f' — {gate["licenseSpdx"]}'
            + (f' ({gate["licenseUrl"]})' if gate['licenseUrl']
               else ''))
    return {
        'ok': True, 'asset': asset_name,
        'title': title, 'author': author or None,
        'sourceUrl': src_url or None,
        'licenseSpdx': gate['licenseSpdx'],
        'licenseUrl': gate['licenseUrl'] or None,
        'attributionRequired': gate['attributionRequired'],
        'shareAlike': gate['shareAlike'],
        'compatible': gate['compatible'],
        'citationLine': line,
        'complete': not gaps,
        'gaps': gaps,
        'modificationNote': 'if we scale or edit the mesh, say so '
                            'in the credit — CC licences ask that '
                            'adaptations be indicated, and an '
                            'OrganMeshChoice IS an adaptation '
                            '(it records the per-axis scaling)',
        'note': 'this record is what travels into a credits file, '
                'an exported scene, or a release — cite from the '
                'ROW so the credit cannot drift from the asset',
    }


def citation_manifest(manager):
    """Every catalogued asset's citation in one list — the thing a
    release or an exported scene ships. Assets whose licence is
    incompatible are listed too, flagged, so the manifest doubles
    as the do-not-ship list."""
    entries, incomplete, blocked = [], [], []
    for asset in _rows(manager, 'MeshAssetReference'):
        rec = citation_record(manager, getattr(asset, 'name', ''))
        if not rec.get('ok'):
            continue
        entries.append(rec)
        if not rec['compatible']:
            blocked.append(rec['asset'])
        elif not rec['complete']:
            incomplete.append(rec['asset'])
    entries.sort(key=lambda r: r['asset'])
    return {
        'ok': True, 'projectLicense': PROJECT_LICENSE_SPDX,
        'citations': entries, 'count': len(entries),
        'incompleteCitations': incomplete,
        'blockedAssets': blocked,
        'note': 'ship this list with the build. Entries under '
                '"blockedAssets" are catalogued but NOT usable — '
                'they stay visible so the reason is on record '
                'rather than rediscovered.',
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
    if not gate['compatible']:
        return _refuse(
            f'asset "{asset_name}" is licence-gated against our '
            f'{gate["projectLicense"]} project: {gate["why"]}',
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
    out.sort(key=lambda r: (not r['license']['compatible'],
                            r['name']))
    usable = [r for r in out if r['license']['compatible']]
    return {
        'ok': True, 'sources': out, 'count': len(out),
        'usableCount': len(usable),
        'projectLicense': PROJECT_LICENSE_SPDX,
        'note': 'compatibility is judged AGAINST OUR OWN LICENCE '
                f'({PROJECT_LICENSE_SPDX}) — being GPLv3 is what '
                'makes the copyleft assets usable here. Licences '
                'were read from the publisher\'s own words on the '
                'date in each row and the quote is kept. An '
                'incompatible source stays IN this list on purpose: '
                'a written-down negative finding does not have to '
                'be re-discovered every few months.',
    }
