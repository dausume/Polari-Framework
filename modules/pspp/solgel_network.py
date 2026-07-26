"""
@module pspp.solgel_network

mtt-2 sg-1/sg-2 (MTT2_SOLGEL_SINTERING_PLAN Part A): the SOL-GEL
chemistry library — the third swap-the-library proof (after wax and
CMC) that pspp is a generic reactive-material engine. Sol-gel is
geopolymer's sibling: hydrolysis/condensation are graph-rewrite rules
and Q^n speciation is the SAME motif ledger (siloxonate-q0..q4 rows
are reused, not duplicated).

- SOLGEL_CHEMICAL_SPECIES — alkoxide precursors (generic Si(OR)4 the
  rules trade in + TEOS/TMOS concrete members; Al/Ti/Zr alkoxides as
  species-only rows, rules pending), alcohols, the Si(OH)4 monomer.
- SOLGEL_REACTION_RULES — hydrolysis + the two condensation families
  (water/alcohol) + growth rules whose GATES encode the catalysis
  fork: acid -> weakly-branched/linear (low Q4, spinnable), base ->
  dense colloidal particles (high Q4). Kinetics-free (invariant I5).
- SOLGEL_THRESHOLD_WINDOWS — the pH route gates + the R-ratio
  (H2O:alkoxide) gate as ThresholdReactionWindow rows. The gate
  machinery needed NO schema change: condition gates already key on
  an arbitrary descriptor, pH is just a new one (data, not code).
- solgel_inventory — the starting species pool of one mix from its
  stoichiometry (R ratio), rule-application units.

Provenance honesty: seeded from general sol-gel literature (Brinker &
Scherer, "Sol-Gel Science", 1990; Iler, "The Chemistry of Silica",
1979) WITHOUT the books in hand — mechanisms and stoichiometry are
canonical, but every numeric boundary carries a coarse-boundary note
and the numeric curves live in pspp.solgel_process as points-empty
provisional datasets that REFUSE until real figures are digitized.

@consumers
  - polariServer.defClassList seeding (rows concatenate into the
    ChemicalSpecies / ReactionRule / ThresholdReactionWindow seeds)
  - pspp.network_stepping (rules passed explicitly or via live rows)
  - pspp.solgel_structure (inventory + route demos)
"""

import json

_SG_PROVENANCE = ('mtt-2 sg-1/2 sol-gel library seed 2026-07-26 — '
                  'general literature (Brinker & Scherer 1990; Iler '
                  '1979), books not in hand: mechanisms canonical, '
                  'numeric boundaries coarse (see window notes)')

_BS = 'Brinker & Scherer, Sol-Gel Science (1990)'

SOLGEL_CHEMICAL_SPECIES = [
    {'name': 'silicon-alkoxide', 'display_name': 'Silicon alkoxide',
     'formula': 'Si(OR)4', 'species_kind': 'molecule', 'qn': 0,
     'notes': 'Generic tetraalkoxysilane the sol-gel rules trade in '
              '(TEOS/TMOS are concrete members). Unreacted alkoxide '
              'Si is Q0 in 29Si NMR — qn=0 so unreacted precursor '
              'honestly enters the Q ledger.'},
    {'name': 'teos', 'display_name': 'TEOS',
     'formula': 'Si(OC2H5)4', 'species_kind': 'molecule', 'qn': 0,
     'notes': 'Tetraethyl orthosilicate — the workhorse precursor. '
              'Concrete member of silicon-alkoxide; rules trade in '
              'the generic, inventories note the concrete one.'},
    {'name': 'tmos', 'display_name': 'TMOS',
     'formula': 'Si(OCH3)4', 'species_kind': 'molecule', 'qn': 0,
     'notes': 'Tetramethyl orthosilicate — hydrolyzes faster than '
              'TEOS (methoxide leaving group); kinetics refuse until '
              'calibrated (I5).'},
    {'name': 'silicic-acid', 'display_name': 'Silicic acid',
     'formula': 'Si(OH)4', 'species_kind': 'molecule', 'qn': 0,
     'notes': 'The fully hydrolyzed monomer — Q0 in 29Si NMR. '
              'Distinct from the silanol-group MOTIF (a terminal '
              'Si-OH on an existing network).'},
    {'name': 'alkanol', 'display_name': 'Alcohol (ROH)',
     'formula': 'R-OH', 'species_kind': 'molecule',
     'notes': 'Generic alcohol — hydrolysis/alcohol-condensation '
              'byproduct AND the usual cosolvent (ethanol for TEOS, '
              'methanol for TMOS).'},
    {'name': 'ethanol', 'display_name': 'Ethanol',
     'formula': 'C2H5OH', 'species_kind': 'molecule',
     'notes': 'Concrete member of alkanol (TEOS systems).'},
    {'name': 'methanol', 'display_name': 'Methanol',
     'formula': 'CH3OH', 'species_kind': 'molecule',
     'notes': 'Concrete member of alkanol (TMOS systems).'},
    {'name': 'aluminum-alkoxide', 'display_name': 'Aluminum alkoxide',
     'formula': 'Al(OR)3', 'species_kind': 'molecule',
     'notes': 'RULES PENDING — Al alkoxides hydrolyze far faster '
              'than Si alkoxides; practical routes moderate them '
              '(chelating ligands, e.g. acetylacetone). Recorded as '
              'inventory so the gap is honest data.'},
    {'name': 'titanium-alkoxide', 'display_name': 'Titanium alkoxide',
     'formula': 'Ti(OR)4', 'species_kind': 'molecule',
     'notes': 'RULES PENDING — same fast-hydrolysis caveat as '
              'aluminum-alkoxide.'},
    {'name': 'zirconium-alkoxide', 'display_name': 'Zirconium alkoxide',
     'formula': 'Zr(OR)4', 'species_kind': 'molecule',
     'notes': 'RULES PENDING — same fast-hydrolysis caveat as '
              'aluminum-alkoxide.'},
    {'name': 'framework-silica-polymeric-gel',
     'display_name': 'Silica gel (polymeric)',
     'species_kind': 'framework',
     'notes': 'Acid-route product family: weakly-branched/linear '
              'chains percolating into an OPEN low-Q4 gel — the '
              'spinnable regime.'},
    {'name': 'framework-silica-colloidal-gel',
     'display_name': 'Silica gel (colloidal)',
     'species_kind': 'framework',
     'notes': 'Base-route product family: dense highly-condensed '
              '(high Q4) colloidal particles aggregating into a '
              'particulate gel (Stoeber synthesis lives here).'},
]

for _row in SOLGEL_CHEMICAL_SPECIES:
    _row.setdefault('provenance_id', _SG_PROVENANCE)

#: Sol-gel rules — material_family 'sol-gel', cation_family '' (no
#: alkali routes here), kinetics_status 'none' (rate queries refuse).
#: The catalysis fork lives in the GATES, not in code.
SOLGEL_REACTION_RULES = [
    {
        'name': 'alkoxide-hydrolysis',
        'display_name': 'Alkoxide hydrolysis',
        'reactants_json': json.dumps(['silicon-alkoxide', 'water']),
        'products_json': json.dumps(['silicic-acid', 'alkanol']),
        'topology_change': 'Net template for the four stepwise Si-OR '
                           'hydrolyses: Si-OR + H2O -> Si-OH + ROH. '
                           'Acid: protonated-alkoxide mechanism, '
                           'hydrolysis fast vs condensation; base: '
                           'OH- nucleophilic attack, condensation '
                           'fast. The RATE asymmetry is the catalysis '
                           'story — refused until calibrated (I5).',
        'stage': 'activation',
        'hypothesis_status': 'book-supported',
        'source_reference': f'{_BS} Ch.3 (hydrolysis); stoichiometry '
                            'canonical',
    },
    {
        'name': 'silicic-dimerization',
        'display_name': 'Water condensation: dimerization',
        'reactants_json': json.dumps(['silicic-acid', 'silicic-acid']),
        'products_json': json.dumps(
            ['siloxonate-q1', 'siloxonate-q1', 'water']),
        'topology_change': 'Two Si-OH condense to the first Si-O-Si '
                           'bridge: both monomers become chain-end Q1 '
                           'sites; water released (water '
                           'condensation).',
        'stage': 'branch-selection',
        'hypothesis_status': 'book-supported',
        'source_reference': f'{_BS} Ch.3 (water condensation); Q '
                            'bookkeeping is definitional',
    },
    {
        'name': 'alcohol-condensation',
        'display_name': 'Alcohol condensation',
        'reactants_json': json.dumps(
            ['silicic-acid', 'silicon-alkoxide']),
        'products_json': json.dumps(
            ['siloxonate-q1', 'siloxonate-q1', 'alkanol']),
        'topology_change': 'Si-OH + Si-OR -> Si-O-Si + ROH: an '
                           'unhydrolyzed alkoxide condenses directly '
                           'with a silanol — the water-starved (low '
                           'R) growth channel.',
        'stage': 'branch-selection',
        'hypothesis_status': 'book-supported',
        'condition_windows_json': json.dumps(
            ['sol-gel:r-alcohol-condensation']),
        'source_reference': f'{_BS} Ch.3 (alcohol condensation); '
                            'gated below the full-hydrolysis '
                            'stoichiometry R=4',
    },
    {
        'name': 'chain-extension-condensation',
        'display_name': 'Chain extension (monomer to chain end)',
        'reactants_json': json.dumps(
            ['siloxonate-q1', 'silicic-acid']),
        'products_json': json.dumps(
            ['siloxonate-q2', 'siloxonate-q1', 'water']),
        'topology_change': 'A monomer condenses onto a chain end: the '
                           'old end becomes an interior Q2, the '
                           'monomer the new Q1 end — linear growth, '
                           'open in both routes.',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'source_reference': f'{_BS} Ch.3; Q bookkeeping definitional',
    },
    {
        'name': 'end-crosslinking-condensation',
        'display_name': 'Cluster-cluster end joining',
        'reactants_json': json.dumps(
            ['siloxonate-q1', 'siloxonate-q1']),
        'products_json': json.dumps(
            ['siloxonate-q2', 'siloxonate-q2', 'water']),
        'topology_change': 'Two chain/cluster ends condense: both Q1 '
                           'ends become interior Q2 sites — '
                           'cluster-cluster aggregation, open in '
                           'both routes.',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'source_reference': f'{_BS} Ch.3 (cluster-cluster growth)',
    },
    {
        'name': 'site-addition-condensation',
        'display_name': 'Monomer-cluster site addition',
        'reactants_json': json.dumps(
            ['siloxonate-q2', 'silicic-acid']),
        'products_json': json.dumps(
            ['siloxonate-q3', 'siloxonate-q1', 'water']),
        'topology_change': 'A monomer adds onto an interior Q2 site, '
                           'branching it to Q3 — monomer-cluster '
                           '(Eden-like) growth: base conditions '
                           'favor addition at the most condensed '
                           'sites, densifying particles.',
        'stage': 'framework-growth',
        'hypothesis_status': 'mechanistic-proposal',
        'condition_windows_json': json.dumps(
            ['sol-gel:ph-particulate-route']),
        'source_reference': f'{_BS} Ch.3 growth models '
                            '(monomer-cluster vs cluster-cluster) — '
                            'model-level picture, not a measured '
                            'elementary step',
    },
    {
        'name': 'crosslink-condensation',
        'display_name': 'Interior crosslinking Q2 -> Q3',
        'reactants_json': json.dumps(
            ['siloxonate-q2', 'siloxonate-q2']),
        'products_json': json.dumps(
            ['siloxonate-q3', 'siloxonate-q3', 'water']),
        'topology_change': 'Two interior Q2 sites condense into a '
                           'crosslink — both branch to Q3. Gated to '
                           'the base/particulate route: acid gels '
                           'stay weakly branched.',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'condition_windows_json': json.dumps(
            ['sol-gel:ph-particulate-route']),
        'source_reference': f'{_BS} Ch.3; COARSE fork — acid gels '
                            'show reduced (not zero) Q3/Q4; refine '
                            'when NMR curves are digitized',
    },
    {
        'name': 'network-completion-condensation',
        'display_name': 'Network completion Q3 -> Q4',
        'reactants_json': json.dumps(
            ['siloxonate-q3', 'siloxonate-q3']),
        'products_json': json.dumps(
            ['siloxonate-q4', 'siloxonate-q4', 'water']),
        'topology_change': 'Two Q3 sites condense to fully '
                           'cross-linked Q4 framework sites — the '
                           'dense-particle interior. Same '
                           'base-route gate as crosslinking.',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'condition_windows_json': json.dumps(
            ['sol-gel:ph-particulate-route']),
        'source_reference': f'{_BS} Ch.3; same coarse-fork caveat as '
                            'crosslink-condensation',
    },
    {
        'name': 'polymeric-gel-percolation',
        'display_name': 'Percolation to polymeric gel',
        'reactants_json': json.dumps(
            ['siloxonate-q2', 'siloxonate-q2']),
        'products_json': json.dumps(
            ['framework-silica-polymeric-gel']),
        'topology_change': 'Weakly-branched chains span the volume — '
                           'the acid-route gel point. Cluster-cluster '
                           'aggregation of low-Q4 chains into an OPEN '
                           'network (spinnable regime upstream of '
                           'this point).',
        'stage': 'framework-growth',
        'hypothesis_status': 'mechanistic-proposal',
        'condition_windows_json': json.dumps(
            ['sol-gel:ph-polymeric-route']),
        'competing_with_json': json.dumps(
            ['colloidal-gel-percolation']),
        'source_reference': f'{_BS} Ch.3 growth models — the '
                            'polymeric-vs-colloidal fork is the '
                            'central sol-gel domain fact',
    },
    {
        'name': 'colloidal-gel-percolation',
        'display_name': 'Percolation to colloidal gel',
        'reactants_json': json.dumps(
            ['siloxonate-q4', 'siloxonate-q4']),
        'products_json': json.dumps(
            ['framework-silica-colloidal-gel']),
        'topology_change': 'Dense (Q4-rich) colloidal particles '
                           'aggregate into a particulate gel — the '
                           'base-route gel point (Stoeber particles '
                           'live on this branch).',
        'stage': 'framework-growth',
        'hypothesis_status': 'mechanistic-proposal',
        'condition_windows_json': json.dumps(
            ['sol-gel:ph-particulate-route']),
        'competing_with_json': json.dumps(
            ['polymeric-gel-percolation']),
        'source_reference': f'{_BS} Ch.3 growth models; Stoeber 1968 '
                            '(ammoniacal TEOS, ~pH 11)',
    },
]

for _row in SOLGEL_REACTION_RULES:
    _row.setdefault('provenance_id', _SG_PROVENANCE)
    _row.setdefault('material_family', 'sol-gel')
    _row.setdefault('cation_family', '')

#: The catalysis fork + R gate as DATA. Gate semantics (see
#: pspp.threshold_windows): grade 'failure' = pathway CLOSED.
_COARSE_PH_NOTE = ('COARSE boundary at neutral pH — the real '
                   'crossover is gradual (silica IEP ~pH 2, '
                   'condensation-rate maximum ~pH 7-8). Refine when '
                   'the gel-time/NMR figures are digitized '
                   '(pspp.solgel_process datasets).')

SOLGEL_THRESHOLD_WINDOWS = [
    {
        'name': 'sol-gel:ph-polymeric-route',
        'material_family': 'sol-gel',
        'descriptor': 'pH',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 7.0, 'grade': 'ideal',
             'note': 'Below neutral: hydrolysis outruns condensation '
                     '— weakly-branched/linear cluster-cluster '
                     'growth dominates; the polymeric route is '
                     'OPEN.'},
            {'lo': 7.0, 'hi': None, 'grade': 'failure',
             'note': 'Above neutral: fast OH--catalyzed condensation '
                     'plus dissolution/reprecipitation ripening '
                     'favors dense particles — the polymeric route '
                     'is CLOSED.'},
        ]),
        'behavior_note': _COARSE_PH_NOTE,
        'source_reference': f'{_BS} Ch.3; Iler 1979',
    },
    {
        'name': 'sol-gel:ph-particulate-route',
        'material_family': 'sol-gel',
        'descriptor': 'pH',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 7.0, 'grade': 'failure',
             'note': 'Below neutral the particulate/monomer-cluster '
                     'route is CLOSED — growth stays '
                     'weakly-branched.'},
            {'lo': 7.0, 'hi': None, 'grade': 'ideal',
             'note': 'Above neutral: monomer-cluster growth onto '
                     'condensed sites -> dense high-Q4 colloidal '
                     'particles (Stoeber synthesis ~pH 11).'},
        ]),
        'behavior_note': _COARSE_PH_NOTE,
        'source_reference': f'{_BS} Ch.3; Stoeber 1968',
    },
    {
        'name': 'sol-gel:r-alcohol-condensation',
        'material_family': 'sol-gel',
        'descriptor': 'R',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 4.0, 'grade': 'ideal',
             'note': 'Below the full-hydrolysis stoichiometry R=4, '
                     'unhydrolyzed Si-OR persists — alcohol '
                     'condensation is a real growth channel.'},
            {'lo': 4.0, 'hi': None, 'grade': 'failure',
             'note': 'At/above R=4 every OR is nominally '
                     'hydrolyzable — alcohol condensation closed. '
                     'Coarse stoichiometric boundary (transient '
                     'Si-OR still exists in reality).'},
        ]),
        'behavior_note': 'R = mol H2O / mol Si(OR)4. Stoichiometric '
                         'full hydrolysis needs R=4; net conversion '
                         'to SiO2 needs only R=2 because '
                         'condensation reclaims water.',
        'source_reference': f'{_BS} Ch.3 (stoichiometry canonical)',
    },
    {
        # The sg-4 grader window: spinnable vs bulk-gelling mixes.
        'name': 'sol-gel-spinnable:R:banded',
        'material_family': 'sol-gel-spinnable',
        'descriptor': 'R',
        'window_role': 'quality',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 1.0, 'grade': 'marginal',
             'note': 'Below the reported spinnable window — too '
                     'little water for enough hydrolysis-driven '
                     'chain growth.'},
            {'lo': 1.0, 'hi': 2.0, 'grade': 'ideal',
             'note': 'Reported spinnable-sol window: acid-catalyzed, '
                     'R ~ 1-2 -> linear chains, drawable fibers.'},
            {'lo': 2.0, 'hi': 4.0, 'grade': 'marginal',
             'note': 'Hydrolysis toward completion — spinnability '
                     'degrades toward bulk gelation.'},
            {'lo': 4.0, 'hi': None, 'grade': 'failure',
             'note': 'Fully hydrolyzed systems gel in bulk — not '
                     'spinnable.'},
        ]),
        'behavior_note': 'Approximate literature boundaries (Sakka '
                         'spinnable silica sols: acid, low R) — '
                         'pending page-level citation + digitized '
                         'viscosity data.',
        'source_reference': f'Sakka via {_BS} Ch.3 — approximate; '
                            'page citation pending',
    },
]

for _row in SOLGEL_THRESHOLD_WINDOWS:
    _row.setdefault('provenance_id', _SG_PROVENANCE)


def solgel_inventory(r_ratio, alkoxide='teos', amount=100.0):
    """The starting species pool of one alkoxide mix from its
    stoichiometry: `amount` units of Si(OR)4 + R x amount water.
    Rule-application units (Si basis) — never measured concentrations.
    The catalyst enters as the pH CONDITION, not a consumed species."""
    known = {'teos', 'tmos', 'silicon-alkoxide'}
    if alkoxide not in known:
        return {'ok': False,
                'refusal': f'unknown sol-gel precursor {alkoxide!r}',
                'suggestion': f'available: {sorted(known)} — Al/Ti/Zr '
                              'alkoxides are species-only rows so far '
                              '(rules pending: fast-hydrolysis '
                              'moderation needed)'}
    try:
        r = float(r_ratio)
    except (TypeError, ValueError):
        return {'ok': False, 'refusal': f'R ratio {r_ratio!r} is not '
                                        'a number',
                'suggestion': 'R = mol H2O per mol alkoxide'}
    if r <= 0:
        return {'ok': False,
                'refusal': f'R ratio {r} must be positive — without '
                           'water nothing hydrolyzes',
                'suggestion': 'R ~ 1-2 spinnable (acid), R = 4 full '
                              'hydrolysis, R >> 4 particulate/dilute'}
    inventory = {
        'silicon-alkoxide': float(amount),
        'water': float(amount) * r,
        'alkanol': None,  # cosolvent — present, honestly unquantified
    }
    return {
        'ok': True, 'R': r, 'alkoxide': alkoxide,
        'inventory': inventory,
        'assumptions': [
            'rule-application units on a Si basis — amounts are '
            'stoichiometric bookkeeping, never concentrations',
            f'concrete precursor {alkoxide!r} pooled under the '
            "generic 'silicon-alkoxide' the rules trade in",
            'alcohol cosolvent present unquantified (None); the '
            'catalyst is the pH condition, not a consumed species',
            'R sets the water pool: water = R x alkoxide',
        ],
        'evidence': 'stoichiometry of the declared mix (R ratio) — '
                    'no measurement involved',
    }
