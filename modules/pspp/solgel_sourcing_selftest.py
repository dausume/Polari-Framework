"""
Self-test for mtt-2 sg-community: precursor sourcing, the substitution
map, route accessibility rollups, and the alkoxide-free water-glass +
citrus chemistry reaching a gel through the shared engine.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.solgel_sourcing_selftest
"""

import sys

from pspp.reaction_network_basis import SEED_CHEMICAL_SPECIES
from pspp.custom.solgel_network import (
    SOLGEL_CHEMICAL_SPECIES, SOLGEL_REACTION_RULES, waterglass_inventory,
)
from pspp.solgel_sourcing_basis import (
    ACCESSIBILITY_TIERS, COMMUNITY_ROUTES, SEED_PRECURSOR_SOURCES,
    route_accessibility, route_report, substitution_map,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_alkoxide_free_chemistry():
    print('[sg-community: the water-glass gelation species + rule]')
    names = {s['name'] for s in SOLGEL_CHEMICAL_SPECIES}
    check('water-glass precursors present',
          {'sodium-silicate', 'citric-acid', 'dissolved-salt'} <= names)
    rule = next((r for r in SOLGEL_REACTION_RULES
                 if r['name'] == 'silicate-acid-gelation'), None)
    check('acid-gelation rule exists, kinetics-free',
          rule is not None and rule.get('kinetics_status', 'none')
          == 'none')
    inv = waterglass_inventory(acid_equiv=1.0, amount=100.0)
    check('water-glass inventory ok, alkoxide-free',
          inv['ok'] and 'silicon-alkoxide' not in inv['inventory']
          and inv['inventory']['sodium-silicate'] == 100.0)
    check('acid is a consumed reactant here (not a bare pH condition)',
          inv['inventory']['citric-acid'] == 100.0
          and any('consumed reactant' in a.lower()
                  for a in inv['assumptions']))
    check('non-positive acid refuses',
          waterglass_inventory(acid_equiv=0)['ok'] is False)


def test_sourcing_rows():
    print('[sg-community: precursor sourcing rows]')
    tiers = {s['accessibility_tier'] for s in SEED_PRECURSOR_SOURCES}
    check('every tier is a known tier',
          tiers <= set(ACCESSIBILITY_TIERS))
    check('household commons include citrus acid + rice-husk silica',
          {'citric-acid-from-citrus-juice', 'silica-from-rice-husk-ash'}
          <= {s['name'] for s in SEED_PRECURSOR_SOURCES})
    citrus = next(s for s in SEED_PRECURSOR_SOURCES
                  if s['name'] == 'citric-acid-from-citrus-juice')
    check('citrus juice is household tier + cites the lemon paper',
          citrus['accessibility_tier'] == 'household'
          and 'lemon' in citrus['source_reference'].lower())
    check('every source carries a citation',
          all(s.get('source_reference')
              for s in SEED_PRECURSOR_SOURCES))
    check('source names are unique',
          len({s['name'] for s in SEED_PRECURSOR_SOURCES})
          == len(SEED_PRECURSOR_SOURCES))


def test_substitution_map():
    print('[sg-community: the substitution map]')
    subs = substitution_map()
    check('a common substitute exists for TEOS (water glass / '
          'rice husk)',
          'teos' in subs
          and any(s['source'] in ('water-glass-commodity',
                                  'silica-from-rice-husk-ash')
                  for s in subs['teos']))
    check('citrus juice substitutes for a mineral-acid catalyst',
          'mineral-acid-catalyst' in subs
          and any(s['source'] == 'citric-acid-from-citrus-juice'
                  for s in subs['mineral-acid-catalyst']))
    check('every substitute carries its accessibility tier',
          all('tier' in s for lst in subs.values() for s in lst))


def test_route_accessibility():
    print('[sg-community: route accessibility rollups]')
    wg = route_accessibility('waterglass-citrus')
    check('water-glass+citrus is alkoxide-free',
          wg['ok'] and wg['alkoxideFree'] is True)
    check('its tier is at worst common-industrial (no lab reagent)',
          wg['accessibilityTier'] in ('household', 'common-industrial'))
    teos = route_accessibility('teos-citrus')
    check('TEOS route is lab-reagent tier (its hardest input)',
          teos['accessibilityTier'] == 'lab-reagent'
          and teos['alkoxideFree'] is False)
    check('the TEOS route surfaces a common substitute for its '
          'alkoxide',
          'silicon-alkoxide' in teos['availableSubstitutions'])
    check('worst-precursor is named as the limiter',
          teos['limitedBy'] is not None
          and teos['limitedBy']['tier'] == 'lab-reagent')
    check('unknown route refuses',
          route_accessibility('nope')['ok'] is False)


def test_route_report():
    print('[sg-community: full route report]')
    wg = route_report('waterglass-citrus')
    check('water-glass route runs chemistry to silicic acid',
          wg['ok']
          and wg['chemistry']['ok']
          and wg['chemistry']['liberatedSilicicAcid'] > 0)
    check('report refuses to assert the morphology fork for water '
          'glass',
          'UNVALIDATED' in wg['morphologyNote']
          and any('morphology winner refused' in a
                  for a in wg['assumptions']))
    teos = route_report('teos-citrus')
    check('alkoxide route points at the fork demo instead of '
          'reasserting it',
          teos['ok'] and 'chemistryPointer' in teos)
    check('accessibility travels on the report',
          wg['accessibility']['ok']
          and 'precursors' in wg['accessibility'])
    check('reference routes are modeled too (lab Stoeber present)',
          'teos-ammonia-lab' in COMMUNITY_ROUTES
          and route_report('teos-ammonia-lab', run_chemistry=False)[
              'ok'])


def test_no_seed_collisions():
    print('[idempotent-by-name safety]')
    sg = {s['name'] for s in SOLGEL_CHEMICAL_SPECIES}
    check('sol-gel species (incl. new water-glass rows) unique vs '
          'existing inventory',
          not (sg & {s['name'] for s in SEED_CHEMICAL_SPECIES}))


def main():
    test_alkoxide_free_chemistry()
    test_sourcing_rows()
    test_substitution_map()
    test_route_accessibility()
    test_route_report()
    test_no_seed_collisions()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
