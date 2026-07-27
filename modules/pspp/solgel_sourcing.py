"""
@module pspp.solgel_sourcing

mtt-2 sg-community: PRECURSOR SOURCING as first-class data — the layer
that turns a sol-gel chemistry route into a question a community can
answer: "can we make this from common materials, and if not, what is
the common-material analog?"

Per Dustin (2026-07-26): model EVERY route, common or not — the
industrial/lab routes are reference points whose precursors we map to
common-material SUBSTITUTES. Accessibility is therefore a recorded
PROPERTY of each precursor and route, never a gate that hides a route.

- PrecursorSource — one way to obtain a ChemicalSpecies, with its
  accessibility tier, the common inputs it is derivable from, the lab
  reagent it substitutes for, and a citation. This is the object the
  substitution map is built from.
- COMMUNITY_ROUTES — named sol-gel routes (water-glass+citric-acid,
  citrus-catalyzed TEOS, rice-husk bio-silica, Stoeber lab reference…)
  each declaring its precursors; route accessibility = the LEAST
  accessible precursor (a route is only as community-ready as its
  hardest input).
- route_report — runs the chemistry through the existing engine to a
  gel AND attaches the sourcing/accessibility/substitution picture,
  with honest caveats (numbers refuse; the water-glass morphology
  fork is unvalidated vs the alkoxide picture until digitized).

Honesty: accessibility tiers + derivations are QUALITATIVE cited
claims (textbook-level: water glass from sand + alkali, silica from
rice-husk ash). Numeric performance (gel time, yield, morphology) is
NOT asserted — the reference datasets in solgel_process refuse until
the photographed figures are digitized.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/solgel/sources, /solgel/community-routes)
  - pspp.selftest_solgel_sourcing
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: Ordered least- to most-demanding. A route's tier is its worst
#: precursor's tier; 'derived' resolves to the tier of its own inputs
#: (a derived precursor is as accessible as what it is made from).
ACCESSIBILITY_TIERS = (
    'household',          # lemon juice, vinegar, sand, wood ash, lye
    'common-industrial',  # water glass, mineral acid, ammonia — cheap
                          # commodities, widely sold, not household
    'mined-nonlocal',     # olivine, bauxite, zircon — a specific
                          # geology, mined + shipped; NOT locally
                          # producible (olivine is mantle rock —
                          # theoretically deep-sourced)
    'lab-reagent',        # TEOS/TMOS, metal alkoxides — specialty
)
_TIER_RANK = {t: i for i, t in enumerate(ACCESSIBILITY_TIERS)}

_SRC_PROVENANCE = ('mtt-2 sg-community precursor-sourcing seed '
                   '2026-07-26 — qualitative cited claims; numeric '
                   'performance refuses until figures digitized')


class PrecursorSource(treeObject):
    """One sourcing option for a species: how accessible it is and
    what common materials it can be made from."""

    @treeObjectInit
    def __init__(
        self,
        # Unique kebab-case key ('water-glass-from-sand-alkali').
        name: str = '',
        display_name: str = '',
        # The ChemicalSpecies.name this sources.
        species_ref: str = '',
        # One of ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'lab-reagent',
        # JSON list of common inputs this is derivable from (each a
        # {material, tier, note}) — empty = obtained directly.
        common_inputs_json: str = '[]',
        # Prose: how the derivation is done (community-scale).
        derivation: str = '',
        # JSON list of species/reagent names this can SUBSTITUTE FOR
        # (e.g. citric-acid substitutes-for a mineral-acid catalyst) —
        # the substitution map.
        substitutes_for_json: str = '[]',
        # 'community-proven' | 'literature' | 'proposed' — the standing
        # of the accessibility CLAIM (never the numeric performance).
        claim_status: str = 'literature',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.species_ref = species_ref
        self.accessibility_tier = accessibility_tier
        self.common_inputs_json = common_inputs_json
        self.derivation = derivation
        self.substitutes_for_json = substitutes_for_json
        self.claim_status = claim_status
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


CLAIM_STATUSES = ('community-proven', 'literature', 'proposed')

SEED_PRECURSOR_SOURCES = [
    # -- household-tier commons --
    {'name': 'citric-acid-from-citrus-juice',
     'display_name': 'Citric acid from citrus juice',
     'species_ref': 'citric-acid', 'accessibility_tier': 'household',
     'common_inputs_json': json.dumps([
         {'material': 'lemon/citrus juice', 'tier': 'household',
          'note': '60-70% of soluble solids are organic acids, '
                  'predominantly citric'}]),
     'derivation': 'Press citrus fruit; the juice is directly usable '
                   'as the acidifier/catalyst. No purification needed '
                   'for gelation — the juice acids do the work.',
     'substitutes_for_json': json.dumps(
         ['hydrochloric-acid', 'nitric-acid', 'acetic-acid',
          'mineral-acid-catalyst']),
     'claim_status': 'literature',
     'source_reference': 'Synthesis of silica-based solids by sol-gel '
                         'using lemon bio-waste (Sustainable Chemistry '
                         '2021, doi:10.3390/suschem2040037); lemon '
                         'juice replaces the acetic-acid catalyst.'},
    {'name': 'silica-from-rice-husk-ash',
     'display_name': 'Silica from rice-husk ash',
     'species_ref': 'sodium-silicate', 'accessibility_tier': 'household',
     'common_inputs_json': json.dumps([
         {'material': 'rice husk', 'tier': 'household',
          'note': 'agricultural waste, ~15-20% silica'},
         {'material': 'wood ash / lye (KOH/NaOH)', 'tier': 'household',
          'note': 'alkali to dissolve the ash silica into a silicate '
                  'solution'}]),
     'derivation': 'Burn rice husk to a white ash (controlled, to keep '
                   'silica amorphous), then dissolve the ash silica in '
                   'hot alkali to make a sodium/potassium silicate '
                   'solution — a home-brewed water glass.',
     'substitutes_for_json': json.dumps(['teos', 'tmos',
                                         'silicon-alkoxide']),
     'claim_status': 'literature',
     'source_reference': 'Rice-husk-ash silica extraction is standard '
                         'green-silica literature (e.g. mesoporous '
                         'silica from rice husk); alkali-dissolution '
                         'route. Numbers refuse until a specific '
                         'figure is digitized.'},
    {'name': 'silica-from-waste-glass',
     'display_name': 'Silica from waste glass / slag',
     'species_ref': 'sodium-silicate', 'accessibility_tier': 'household',
     'common_inputs_json': json.dumps([
         {'material': 'crushed waste glass or geothermal slag',
          'tier': 'household', 'note': 'discarded silicate solids'},
         {'material': 'alkali (NaOH)', 'tier': 'common-industrial'}]),
     'derivation': 'Alkali-digest crushed glass or slag to a silicate '
                   'solution — turns a waste stream into the silica '
                   'source (dual-purpose: waste reduction).',
     'substitutes_for_json': json.dumps(['teos', 'tmos']),
     'claim_status': 'literature',
     'source_reference': 'Silica gel from glass waste (IOP Conf. '
                         'Ser. Mater. Sci. Eng. 509:012028); '
                         'citric-acid-assisted nano-silica from Dieng '
                         'geothermal slag (2024).'},
    # -- common-industrial commodities --
    {'name': 'water-glass-commodity',
     'display_name': 'Sodium silicate (commodity water glass)',
     'species_ref': 'sodium-silicate',
     'accessibility_tier': 'common-industrial',
     'common_inputs_json': json.dumps([
         {'material': 'quartz sand + soda ash', 'tier': 'household',
          'note': 'fused industrially; also sold ready-made cheaply'}]),
     'derivation': 'Buy commodity water glass, or fuse sand with soda '
                   'ash. The workhorse alkoxide-free silica source.',
     'substitutes_for_json': json.dumps(['teos', 'tmos',
                                         'silicon-alkoxide']),
     'claim_status': 'community-proven',
     'source_reference': 'Iler, The Chemistry of Silica (1979); '
                         'sodium-silicate sol-gel is the classic '
                         'low-cost route.'},
    {'name': 'mineral-acid-catalyst',
     'display_name': 'Mineral acid (HCl / HNO3)',
     'species_ref': '',
     'accessibility_tier': 'common-industrial',
     'common_inputs_json': json.dumps([]),
     'derivation': 'The conventional lab/industrial acid catalyst — '
                   'the reference that citrus juice substitutes for.',
     'substitutes_for_json': json.dumps([]),
     'claim_status': 'literature',
     'notes': 'Reference precursor: modeled so the citrus substitute '
              'has something explicit to replace.',
     'source_reference': 'Brinker & Scherer, Sol-Gel Science (1990).'},
    # -- lab-reagent reference (the routes we map AWAY from) --
    {'name': 'teos-reagent',
     'display_name': 'TEOS (lab reagent)',
     'species_ref': 'teos', 'accessibility_tier': 'lab-reagent',
     'common_inputs_json': json.dumps([]),
     'derivation': 'Purchased specialty alkoxide — the industrial '
                   'precursor. Its community analog is water glass '
                   '(see silica-from-* sources).',
     'substitutes_for_json': json.dumps([]),
     'claim_status': 'literature',
     'notes': 'Reference precursor. The whole point of the community '
              'layer is to route AROUND this.',
     'source_reference': 'Brinker & Scherer, Sol-Gel Science (1990).'},
]

for _row in SEED_PRECURSOR_SOURCES:
    _row.setdefault('provenance_id', _SRC_PROVENANCE)
    _row.setdefault('notes', '')


#: Named routes. si_source/catalyst reference PrecursorSource.species_ref
#: values; `sources` names the specific PrecursorSource rows used.
#: `alkoxide_free` marks the genuinely-industrial-free routes.
#: morphology_note keeps the water-glass-vs-alkoxide caveat explicit.
COMMUNITY_ROUTES = {
    'waterglass-citrus': {
        'display_name': 'Water glass + citrus juice (alkoxide-free)',
        'si_source': 'sodium-silicate',
        'catalyst': 'citric-acid',
        'sources': ['water-glass-commodity',
                    'citric-acid-from-citrus-juice'],
        'alkoxide_free': True,
        'chemistry': 'waterglass',
        'product': 'silica gel',
        'story': 'The headline community route: acidify commodity '
                 'water glass with citrus juice — no alkoxide, no '
                 'mineral acid.',
        'morphology_note': 'Sodium-silicate gels do NOT follow the '
                           'alkoxide acid=open/base=dense fork: the '
                           'literature reports acidic water-glass gels '
                           'as SMALLER, denser particle networks and '
                           'basic as larger aggregates (Gels 2024; '
                           'JMRT 2020). The morphology fork here is '
                           'UNVALIDATED against the alkoxide gates and '
                           'refuses a winner until digitized.',
        'source_reference': 'Iler (1979); lemon bio-waste sol-gel '
                            '(Sustainable Chemistry 2021); acid-'
                            'initiated sodium silicate (Gels 2024).'},
    'ricehusk-citrus': {
        'display_name': 'Rice-husk silica + citrus juice',
        'si_source': 'sodium-silicate',
        'catalyst': 'citric-acid',
        'sources': ['silica-from-rice-husk-ash',
                    'citric-acid-from-citrus-juice'],
        'alkoxide_free': True,
        'chemistry': 'waterglass',
        'product': 'silica gel',
        'story': 'Fully waste-derived: silica from rice-husk ash, '
                 'acid from citrus. Both inputs are household-tier '
                 'agricultural streams.',
        'morphology_note': 'Water-glass morphology does NOT follow the '
                           'alkoxide acid=open/base=dense fork '
                           '(acidic water-glass gels are denser, '
                           'smaller-particle networks; Gels 2024) — '
                           'UNVALIDATED here, a winner is refused '
                           'until digitized.',
        'source_reference': 'Rice-husk-ash silica literature + lemon '
                            'bio-waste sol-gel (Sustainable Chemistry '
                            '2021).'},
    'teos-citrus': {
        'display_name': 'TEOS + citric acid (green catalyst reference)',
        'si_source': 'silicon-alkoxide',
        'catalyst': 'citric-acid',
        'sources': ['teos-reagent', 'citric-acid-from-citrus-juice'],
        'alkoxide_free': False,
        'chemistry': 'alkoxide',
        'product': 'mesoporous silica',
        'story': 'Reference route: keeps the lab alkoxide but swaps '
                 'the acid for citric — citric acid is both catalyst '
                 'and pore-former. Maps the alkoxide fork onto a '
                 'common catalyst.',
        'morphology_note': 'Alkoxide chemistry: the acid=polymeric / '
                           'base=colloidal fork applies (see '
                           'solgel_route_demo).',
        'source_reference': 'Low-cost mesoporous silica, citric-acid '
                            'template (Mater. Lett., '
                            'doi:10.1016/j.matlet.2011.xx).'},
    'teos-ammonia-lab': {
        'display_name': 'TEOS + ammonia (Stoeber, lab reference)',
        'si_source': 'silicon-alkoxide',
        'catalyst': 'ammonia',
        'sources': ['teos-reagent'],
        'alkoxide_free': False,
        'chemistry': 'alkoxide',
        'product': 'colloidal silica particles',
        'story': 'The full lab reference (Stoeber, base-catalyzed) — '
                 'modeled so its precursors map to common substitutes '
                 '(water glass for TEOS; a common base for ammonia).',
        'morphology_note': 'Alkoxide base route: dense Q4-rich '
                           'colloidal particles (solgel_route_demo '
                           'route=base).',
        'source_reference': 'Stoeber, Fink & Bohn (1968).'},
}


def _tier_rank(tier):
    return _TIER_RANK.get(tier, len(ACCESSIBILITY_TIERS))


def _source_index(sources=None):
    rows = sources if sources is not None else SEED_PRECURSOR_SOURCES
    index = {}
    for r in rows:
        get = (r.get if isinstance(r, dict)
               else lambda k, d='': getattr(r, k, d))
        index[get('name', '')] = {
            'name': get('name', ''),
            'displayName': get('display_name', ''),
            'speciesRef': get('species_ref', ''),
            'tier': get('accessibility_tier', 'lab-reagent'),
            'commonInputs': _loads(get('common_inputs_json', '[]')),
            'derivation': get('derivation', ''),
            'substitutesFor': _loads(get('substitutes_for_json', '[]')),
            'claimStatus': get('claim_status', 'literature'),
            'source': get('source_reference', ''),
        }
    return index


def _loads(raw):
    try:
        return raw if isinstance(raw, list) else json.loads(raw or '[]')
    except Exception:
        return []


def substitution_map(sources=None):
    """{reference reagent -> [common substitutes]} — the answer to
    'what common material replaces this lab input?'. Built from every
    PrecursorSource's substitutes_for list."""
    index = _source_index(sources)
    mapping = {}
    for src in index.values():
        for target in src['substitutesFor']:
            mapping.setdefault(target, [])
            mapping[target].append({
                'source': src['name'], 'tier': src['tier'],
                'claimStatus': src['claimStatus']})
    return mapping


def route_accessibility(route_name, routes=None, sources=None):
    """A route's accessibility rollup: the LEAST accessible precursor
    sets the tier, with each precursor's sourcing options and any
    common substitute for the hard ones."""
    routes = routes if routes is not None else COMMUNITY_ROUTES
    route = routes.get(route_name)
    if route is None:
        return {'ok': False,
                'refusal': f'unknown route {route_name!r}',
                'suggestion': f'available: {sorted(routes)}'}
    index = _source_index(sources)
    subs = substitution_map(sources)
    used = []
    worst_rank = -1
    worst_tier = 'household'
    for src_name in route['sources']:
        src = index.get(src_name)
        if src is None:
            used.append({'source': src_name, 'tier': 'unknown',
                         'note': 'PrecursorSource row missing'})
            worst_rank = len(ACCESSIBILITY_TIERS)
            worst_tier = 'unknown'
            continue
        rank = _tier_rank(src['tier'])
        if rank > worst_rank:
            worst_rank, worst_tier = rank, src['tier']
        used.append({
            'source': src['name'], 'speciesRef': src['speciesRef'],
            'tier': src['tier'], 'derivation': src['derivation'],
            'commonInputs': src['commonInputs'],
            'claimStatus': src['claimStatus']})
    # The precursor SPECIES the route needs, and whether a common
    # substitute exists for any lab-tier one.
    substitutions = {}
    for species in (route['si_source'], route['catalyst']):
        if species in subs:
            substitutions[species] = subs[species]
    return {
        'ok': True, 'route': route_name,
        'displayName': route['display_name'],
        'alkoxideFree': route['alkoxide_free'],
        'accessibilityTier': worst_tier,
        'limitedBy': (max(used, key=lambda u: _tier_rank(u['tier']))
                      if used else None),
        'precursors': used,
        'availableSubstitutions': substitutions,
        'claim': 'accessibility is a QUALITATIVE cited claim; numeric '
                 'performance (gel time, yield, morphology) is NOT '
                 'asserted here',
        'source': route.get('source_reference', ''),
    }


def route_report(route_name, run_chemistry=True, n_tetrahedra=60,
                 seed=1, routes=None, sources=None):
    """Full picture for one route: accessibility/sourcing + (optional)
    the chemistry run through the existing engine to a gel. Water-glass
    routes report reachability honestly WITHOUT asserting the
    unvalidated morphology fork; alkoxide routes defer to
    solgel_route_demo where the fork is the point."""
    access = route_accessibility(route_name, routes=routes,
                                 sources=sources)
    if not access['ok']:
        return access
    routes = routes if routes is not None else COMMUNITY_ROUTES
    route = routes[route_name]
    payload = {'ok': True, 'route': route_name,
               'story': route['story'],
               'product': route['product'],
               'accessibility': access,
               'morphologyNote': route['morphology_note'],
               'assumptions': []}
    if not run_chemistry:
        return payload
    if route['chemistry'] == 'waterglass':
        payload.update(_run_waterglass(route, n_tetrahedra, seed))
    else:
        payload['chemistryPointer'] = (
            'alkoxide route — GET /api/pspp/solgel/routes?route='
            + ('base' if route['catalyst'] == 'ammonia' else 'acid')
            + ' runs the fork demo through the same engine')
    return payload


def _run_waterglass(route, n_tetrahedra, seed):
    """Reach silicic acid from water glass, condense to a gel, and
    report reachable frameworks — but flag the morphology as
    calibration-pending (the alkoxide fork does not transfer)."""
    from pspp.network_stepping import reachable_frameworks, step_once
    from pspp.solgel_network import waterglass_inventory
    from pspp.solgel_structure import (
        _combined_rules, _combined_species, _combined_windows,
    )
    start = waterglass_inventory(acid_equiv=1.0, amount=100.0)
    if not start.get('ok'):
        return {'chemistry': start}
    # Acidify: liberate silicic acid (ungated — the acid IS what sets
    # pH). Then the shared condensation rules can carry it to a gel.
    gelled = step_once(
        dict(start['inventory']), 'silicate-acid-gelation',
        rules=_combined_rules(), windows=_combined_windows(),
        conditions={'pH': 5.0}, cation=None, times=100)
    if not gelled.get('ok'):
        return {'chemistry': gelled}
    reach = reachable_frameworks(
        gelled['inventory'], rules=_combined_rules(),
        conditions={'pH': 5.0}, windows=_combined_windows(),
        species=_combined_species(), cation=None)
    return {
        'chemistry': {
            'ok': True,
            'liberatedSilicicAcid': gelled['produced'].get(
                'silicic-acid'),
            'reachableFrameworks': [
                f['framework'] for f in reach['reachableFrameworks']],
            'note': 'water glass -> silicic acid -> condensation to a '
                    'silica gel via the SHARED rules; the specific '
                    'morphology (dense-acidic vs aggregated-basic) is '
                    'the water-glass fork, UNVALIDATED here — see '
                    'morphologyNote',
        },
        'assumptions': [
            'alkoxide-free: no TEOS/TMOS in this route',
            'the acid is a consumed reactant (neutralizes alkali), '
            'not a bare pH condition',
            'morphology winner refused: digitize the sodium-silicate '
            'gel-time/morphology-vs-pH figure to calibrate',
        ],
    }
