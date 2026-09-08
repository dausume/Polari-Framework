"""
Selftest for foodstate fsp-1 — the common-base-ingredients database:
roster identities resolved FROM the vendored FDC file, composition
claims with full citation provenance, coverage honesty (contract
gaps NAMED, never filled).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m foodstate.food_materials_selftest
"""

import json
import sys
import types

from foodstate.custom.food_composition import (
    CONTRACT_GAPS, build_composition_claim_seeds, ingredient_report,
    vendor_food_index,
)
from foodstate.food_materials_basis import (
    ROSTER, ROSTER_CATEGORIES, FoodMaterial,
    build_food_material_seeds,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(materials, claims):
    tables = {'FoodMaterial': {}, 'PropertyClaim': {}}
    mgr = types.SimpleNamespace(objectTables=tables, db=None)
    for seed in materials:
        row = types.SimpleNamespace(**seed)
        tables['FoodMaterial'][id(row)] = row
    for seed in claims:
        row = types.SimpleNamespace(**seed)
        tables['PropertyClaim'][id(row)] = row
    return mgr


def main():
    index = vendor_food_index()
    materials = build_food_material_seeds(index)
    claims = build_composition_claim_seeds()

    check('roster: 49 vendored foods, every one categorized, every '
          'category from the vocabulary, rows construct',
          len(ROSTER) == 49 and len(materials) == 49
          and all(m['roster_category'] in ROSTER_CATEGORIES
                  for m in materials)
          and all(hasattr(FoodMaterial(**{**m, 'manager': None}),
                          'fdc_id') for m in materials))
    check('identity from the FILE, not memory: every roster row '
          'resolved a nonzero fdc_id + dataset + description from '
          'the vendor index',
          all(m['fdc_id'] > 0 and m['fdc_dataset']
              and m['fdc_description'] for m in materials))
    check('roster covers every vendored slug and nothing else '
          '(roster ⊆ vendor ∧ vendor ⊆ roster)',
          set(ROSTER) == set(index))

    check('claims: ~949 vendored values, each a PropertyClaim on '
          "'<slug>#as-defined', per-100g, evidence 'literature'",
          len(claims) == 949
          and all(c['subject_state_key'].endswith('#as-defined')
                  and c['evidence_method'] == 'literature'
                  for c in claims))
    check('every claim provenance carries the FDC citation (CC0), '
          'the pinned fdc_id AND the vendor sha256 — never a bare '
          'number',
          all('fdc_id' in c['provenance_id']
              and 'CC0' in c['provenance_id']
              and 'sha256' in c['provenance_id'] for c in claims))
    check('vendor derivation notes ride the affected claims as '
          'assumptions verbatim (omega-3 sum, unit conversions, '
          'energy fallbacks)',
          any('vendor derivation' in a
              for c in claims
              for a in json.loads(c['assumptions_json'])
              if c['property_meaning_name'] == 'omega-3')
          and any('Atwater' in a
                  for c in claims
                  for a in json.loads(c['assumptions_json'])
                  if c['property_meaning_name'] == 'calories'))
    tomato_ca = [c for c in claims
                 if c['name'] == 'tomato-raw#as-defined:calcium@L0']
    check('spot value verbatim from the vendor file: tomato-raw '
          'calcium 9.963 mg per 100 g (fdc_id 1750354)',
          len(tomato_ca) == 1
          and abs(tomato_ca[0]['value'] - 9.963) < 1e-9
          and tomato_ca[0]['units'] == 'mg'
          and '1750354' in tomato_ca[0]['provenance_id'])
    check('honest absences preserved: salt-iodized has NO calories '
          'claim fabricated beyond the vendor rows',
          not any(c['subject_state_key'] == 'salt-iodized#as-defined'
                  and c['property_meaning_name'] == 'calories'
                  and c['value'] > 0 for c in claims))

    mgr = _mgr(materials, claims)
    rep = ingredient_report(mgr)
    check('food-ingredients/1: 49 ingredients, category rollup, '
          'source cited, the D4 contract gaps NAMED on the report',
          rep['ok'] and rep['count'] == 49
          and sum(rep['byCategory'].values()) == 49
          and 'CC0' in rep['source']
          and 'organic-acid' in rep['gapNote'])
    check('every ingredient entry lists its quantities and its '
          'contract gaps (starch split + organic-acid species '
          'among them) — gaps named, never filled',
          all(e['claimCount'] > 0
              and 'organic-acids per species '
                  '(citric|malic|acetic|lactic)' in e['contractGaps']
              for e in rep['ingredients']))

    one = ingredient_report(mgr, slug='tomato-raw')
    check('single-ingredient report: identity + full claims with '
          'provenance + gap note',
          one['ok'] and one['fdcId'] == 1750354
          and any(c['quantity'] == 'calcium'
                  and 'fdc_id 1750354' in c['provenance']
                  for c in one['claims'])
          and 'never filled' in one['gapNote'])
    bad = ingredient_report(mgr, slug='dragonfruit')
    check('unknown ingredient refuses naming the roster size',
          not bad['ok'] and '49' in bad['error'])

    passed = sum(1 for _l, okc in _results if okc)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
