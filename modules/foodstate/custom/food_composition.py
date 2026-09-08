"""
@module foodstate.custom.food_composition

fsp-1 — composition CLAIMS on the canonical states, built from the
vendored FDC subset (CC0, sha-pinned, values verbatim — see
modules/nutrition/custom/vendor/README.md). Every value lands as a pspp
PropertyClaim on '<slug>#as-defined' with evidence_method
'literature' and a provenance string carrying the FDC id, dataset,
nutrient number and the vendor sha — never a bare number
(claims-not-values, I4).

pspp's "claims are earned, never seeded" posture is respected in
spirit: these ARE earned — by citation to a pinned public-domain
measurement database; the vendor derivation notes (omega-3 sum,
unit conversions, energy fallbacks) ride each affected claim's
assumptions verbatim.

Coverage honesty: the vendor subset carries the nut-1 nutrient
vocabulary — it does NOT carry the fsp-0 contract's starch/sugars
split, organic-acid species, or structure quantities. The coverage
report NAMES those absences per ingredient (the D4 gap stays open
and visible), it never fills them.

@consumers
  - polariServer (PropertyClaim seed concat + FoodMaterial seeds)
  - foodstate.food_api (ingredients endpoints)
  - foodstate.food_materials_selftest
"""

import csv
import json
import os

_VENDOR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'nutrition',
                       'vendor', 'fdc_foundation_subset.csv')
_VENDOR_SHA = ('c0a9360747fc820fba2f14fd39e59c45e8eeeadf2a50a84dda'
               '77d82393808886')
_CITE = ('USDA FoodData Central (Foundation 2025-04-24 / SR Legacy '
         '2018-04), CC0; vendored fdc_foundation_subset.csv sha256 '
         + _VENDOR_SHA)

#: fsp-0 composition-contract quantities the vendor subset does NOT
#: carry — named per ingredient by the coverage report, never filled.
CONTRACT_GAPS = (
    'water (vendor subset carries no water rows — mass-balance '
    'transforms name this gap on every claim)',
    'starch (vs sugars split)', 'sugars (free)',
    'organic-acids per species (citric|malic|acetic|lactic)',
    'amino-acids per species', 'caffeine', 'capsaicinoids',
)


def _read_vendor():
    rows = []
    try:
        with open(os.path.abspath(_VENDOR), newline='',
                  encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                rows.append(row)
    except OSError:
        return None
    return rows


_VENDOR_ROWS = _read_vendor()


def vendor_food_index():
    """slug → {fdc_id, fdc_dataset, fdc_description} from the vendor
    file itself (identity is never typed from memory)."""
    index = {}
    for row in (_VENDOR_ROWS or []):
        index.setdefault(row['food_slug'], {
            'fdc_id': row['fdc_id'],
            'fdc_dataset': row['fdc_dataset'],
            'fdc_description': row['fdc_description'],
        })
    return index


def build_composition_claim_seeds():
    """PropertyClaim seed rows for every vendored (food, nutrient)
    value — per-100g edible, raw canonical state."""
    seeds = []
    for row in (_VENDOR_ROWS or []):
        slug = row['food_slug']
        nutrient = row['nutrient']
        assumptions = ['per 100 g edible portion',
                       'raw/as-purchased canonical state']
        if (row.get('derivation') or '').strip():
            assumptions.append('vendor derivation: '
                               + row['derivation'].strip())
        seeds.append({
            'name': f'{slug}#as-defined:{nutrient}@L0',
            'subject_state_key': f'{slug}#as-defined',
            'property_meaning_name': nutrient,
            'scale_level': 0,
            'value': float(row['amount_per_100g']),
            'value_json': '',
            'units': row['unit'],
            'evidence_method': 'literature',
            'assumptions_json': json.dumps(assumptions),
            'validity_json': json.dumps(
                {'basis': 'per-100g', 'state': 'as-defined'}),
            'source_execution_id': '',
            'confidence_json': '',
            'provenance_id': (f'{_CITE}; fdc_id {row["fdc_id"]} '
                              f'({row["fdc_dataset"]}), nutrient nbr '
                              f'{row["fdc_nutrient_nbr"]}'),
            'notes': '',
        })
    return seeds


def ingredient_report(manager, slug=None):
    """Roster + per-ingredient coverage: which quantities each
    ingredient HAS (claims on its canonical state) and which fsp-0
    contract quantities it lacks — honestly, by name."""
    tables = getattr(manager, 'objectTables', None) or {}
    claims_by_subject = {}
    for row in (tables.get('PropertyClaim') or {}).values():
        key = getattr(row, 'subject_state_key', '')
        claims_by_subject.setdefault(key, []).append(row)
    out = []
    for mat in sorted((tables.get('FoodMaterial') or {}).values(),
                      key=lambda r: getattr(r, 'name', '')):
        name = getattr(mat, 'name', '')
        if slug is not None and name != slug:
            continue
        claims = claims_by_subject.get(f'{name}#as-defined', [])
        entry = {
            'name': name,
            'displayName': getattr(mat, 'display_name', ''),
            'category': getattr(mat, 'roster_category', ''),
            'fdcId': getattr(mat, 'fdc_id', 0),
            'fdcDataset': getattr(mat, 'fdc_dataset', ''),
            'fdcDescription': getattr(mat, 'fdc_description', ''),
            'subject': f'{name}#as-defined',
            'quantities': sorted(
                getattr(c, 'property_meaning_name', '')
                for c in claims),
            'claimCount': len(claims),
            'contractGaps': list(CONTRACT_GAPS),
            'notes': getattr(mat, 'notes', ''),
        }
        if slug is not None:
            entry['claims'] = [{
                'quantity': getattr(c, 'property_meaning_name', ''),
                'value': getattr(c, 'value', 0.0),
                'units': getattr(c, 'units', ''),
                'evidenceMethod': getattr(c, 'evidence_method', ''),
                'assumptions': json.loads(
                    getattr(c, 'assumptions_json', '[]') or '[]'),
                'provenance': getattr(c, 'provenance_id', ''),
            } for c in sorted(claims, key=lambda c: getattr(
                c, 'property_meaning_name', ''))]
        out.append(entry)
    if slug is not None:
        if not out:
            known = sorted(getattr(r, 'name', '') for r in
                           (tables.get('FoodMaterial') or {}).values())
            return {'ok': False,
                    'error': f'no base ingredient "{slug}" — roster '
                             f'has {len(known)}: '
                             + ', '.join(known[:12]) + '…'}
        return {'ok': True, 'schema': 'food-ingredient/1', **out[0],
                'gapNote': ('contract gaps are NAMED, never filled — '
                            'vendoring or citing new data is the only '
                            'way a gap closes (D4)')}
    cats = {}
    for e in out:
        cats[e['category']] = cats.get(e['category'], 0) + 1
    return {'ok': True, 'schema': 'food-ingredients/1',
            'count': len(out), 'byCategory': cats,
            'ingredients': out,
            'source': _CITE,
            'gapNote': ('every ingredient carries the same NAMED '
                        'contract gaps (starch split, organic-acid '
                        'species, structure quantities) — the D4 '
                        'scope, open and visible')}
