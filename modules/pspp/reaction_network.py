"""
@module pspp.reaction_network

The reaction network as DATA (Ch.8.2-8.6 review, Findings 3/5/7):
Polari is not a "geopolymer simulator" — it is a generic
reactive-material engine, and the geopolymer chemistry is one LIBRARY
of species and graph-rewrite rules within it. Swapping the library,
not redesigning the simulator, is how sol-gels / cement hydration /
oxidation arrive later.

- ChemicalSpecies rows — the inventory reaction rules consume and
  produce (Q-species are DYNAMIC RESOURCES here, not static labels).
- ReactionRule rows — graph-rewrite templates (reactants → products +
  topology change), each carrying its hypothesis status: Ch.7's
  lesson is that mechanisms are COMPETING HYPOTHESES (seven-step
  mechanism vs Loewenstein-conflicting Al-O-Al condensation), so
  rules register their standing and rivals instead of being hardcoded
  truth. NO rule carries kinetics until a cited calibration is loaded
  (invariant I5) — rate queries refuse.
- REACTION_STAGES — the reusable common pipeline (Finding 7):
  activation → dissolution → ortho-sialate generation → branch
  selection → framework growth. Na and K systems share the stages;
  only branching condensation and framework selection differ, which
  is exactly why rules are per-family DATA.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp-8 reaction-progress engines (rules feed the network)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: The reusable common stages (Finding 7). Rules name one.
REACTION_STAGES = (
    'activation', 'dissolution', 'ortho-sialate-generation',
    'branch-selection', 'framework-growth', 'phase-evolution',
)

HYPOTHESIS_STATUSES = (
    'book-supported',       # mechanism shown with structures/data
    'mechanistic-proposal',  # historical/proposed mechanism (Ch.7)
    'contested',            # named conflict (e.g. Loewenstein)
)

#: Fig 8.21 (p.184): TRANSPORT selects the pathway — surface sites see
#: ions AND oligo-siloxonates; interlayer interiors admit only small
#: ions (even Q0 ortho-siloxonate is too big to penetrate). A rule may
#: therefore be site-constrained; '' = no constraint.
SITE_CONSTRAINTS = ('', 'surface-only', 'interior-only')


class ChemicalSpecies(treeObject):
    """One species/motif the reaction network trades in."""

    @treeObjectInit
    def __init__(
        self,
        # Kebab-case key ('hydroxide-ion', 'siloxonate-q2').
        name: str = '',
        display_name: str = '',
        formula: str = '',
        charge: int = 0,
        # 'ion' | 'molecule' | 'motif' (Q-species are motifs over an
        # underlying network — never complete structures) |
        # 'framework' (crystalline/amorphous product families).
        species_kind: str = 'molecule',
        # Q-state for silicate motifs (-1 = not applicable).
        qn: int = -1,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.formula = formula
        self.charge = charge
        self.species_kind = species_kind
        self.qn = qn
        self.provenance_id = provenance_id
        self.notes = notes


class ReactionRule(treeObject):
    """One graph-rewrite template: reactants → products + topology
    change. Kinetics-free until a cited calibration exists."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # JSON lists of ChemicalSpecies names.
        reactants_json: str = '[]',
        products_json: str = '[]',
        # What happens to the network topology, as prose the rewrite
        # engine will later formalize ('break one Si-O bridge; create
        # silanol + NBO; associate charge-compensating cation').
        topology_change: str = '',
        # One of REACTION_STAGES.
        stage: str = '',
        # One of HYPOTHESIS_STATUSES + the rivals it competes with.
        hypothesis_status: str = 'mechanistic-proposal',
        competing_with_json: str = '[]',
        # One of SITE_CONSTRAINTS — where transport permits this rule
        # (Fig 8.21 two-phase selection; '' = anywhere).
        site_constraint: str = '',
        # 'Na' | 'K' | '' (both): §8.5 routes are Na, §8.6 their K
        # analogues — a rule never fires in a mix whose alkali it
        # does not name ('' rules fire in both).
        cation_family: str = '',
        # JSON list of ThresholdReactionWindow names (condition-gate
        # role) that must not grade 'failure' for this rule to fire —
        # pathway thresholds as DATA (e.g. the p.188 MR<1.20 Q0
        # gate). Enforced by pspp.network_stepping.
        condition_windows_json: str = '[]',
        # 'none' until a calibration row is loaded (invariant I5).
        kinetics_status: str = 'none',
        kinetics_ref: str = '',
        material_family: str = 'general',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.reactants_json = reactants_json
        self.products_json = products_json
        self.topology_change = topology_change
        self.stage = stage
        self.hypothesis_status = hypothesis_status
        self.competing_with_json = competing_with_json
        self.site_constraint = site_constraint
        self.cation_family = cation_family
        self.condition_windows_json = condition_windows_json
        self.kinetics_status = kinetics_status
        self.kinetics_ref = kinetics_ref
        self.material_family = material_family
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


_NET_PROVENANCE = ('pspp-4 reaction-network schema (Ch.5 photographed '
                   'mechanism + Ch.8.2-8.6 review 2026-07-18)')

SEED_CHEMICAL_SPECIES = [
    {'name': 'water', 'formula': 'H2O', 'species_kind': 'molecule'},
    {'name': 'hydroxide-ion', 'formula': 'OH-', 'charge': -1,
     'species_kind': 'ion'},
    {'name': 'sodium-ion', 'formula': 'Na+', 'charge': 1,
     'species_kind': 'ion'},
    {'name': 'potassium-ion', 'formula': 'K+', 'charge': 1,
     'species_kind': 'ion'},
    {'name': 'silanol-group', 'formula': 'Si-OH',
     'species_kind': 'motif',
     'notes': 'Terminal silanol on a siloxonate network.'},
    {'name': 'aluminol-group', 'formula': 'Al-OH',
     'species_kind': 'motif'},
    {'name': 'siloxane-bridge', 'formula': 'Si-O-Si',
     'species_kind': 'motif'},
    {'name': 'sialate-bridge', 'formula': 'Si-O-Al',
     'species_kind': 'motif'},
    {'name': 'nbo-terminal', 'formula': 'Si-O(-)',
     'charge': -1, 'species_kind': 'motif',
     'notes': 'Non-bridging oxygen (Si-ONa/Si-OK after charge '
              'compensation) — p.90 §5.4.1.'},
] + [
    {'name': f'siloxonate-q{n}', 'formula': f'Q{n}',
     'species_kind': 'motif', 'qn': n,
     'notes': 'Q-species are structural MOTIFS over the network, '
              'dynamic resources the rules consume/produce — never '
              'complete structures.'}
    for n in range(5)
] + [
    {'name': 'metakaolin-layer', 'formula': 'Al2O3·2SiO2',
     'species_kind': 'framework',
     'notes': 'MK-750 layered aluminosilicate reactant particle '
              '(pp.183-184): attack starts at edges/faces (Phase 1); '
              'interlayers swell to admit only small ions (Phase 2).'},
    {'name': 'ortho-sialate', 'formula': '(OH)3-Si-O-Al(OH)3(Na+)',
     'species_kind': 'motif',
     'notes': 'The ortho-sialate molecule — product of steps 1-5 '
              '(pp.186-187; step detail is Ch.6 Fig 6.6, not yet '
              'photographed).'},
    {'name': 'di-siloxonate', 'formula': 'Q1 dimer',
     'species_kind': 'motif', 'qn': 1,
     'notes': 'Q1 di-siloxonate from the waterglass — a Phase-1 '
              '(surface) reactant only; too big to penetrate '
              'interlayers (p.184).'},
    {'name': 'ortho-sialate-disiloxo-cycle',
     'species_kind': 'motif',
     'notes': 'Cyclic ortho-sialate-disiloxo intermediate (reaction '
              '6, p.186; molecule types No.4/No.5 of Fig 6.6).'},
    {'name': 'cyclo-tri-sialate', 'species_kind': 'motif',
     'notes': 'Cyclo-tri-sialate intermediate (reaction 7, p.187).'},
    {'name': 'ortho-sialate-siloxo-linear', 'species_kind': 'motif',
     'notes': 'Linear ortho-sialate-siloxo (No.2, North & Swaddle '
              '2000; step 6a, p.188-189).'},
    {'name': 'quadratic-di-sialate', 'species_kind': 'motif',
     'notes': 'Quadratic di-sialate from two ortho-sialates '
              '(step 6b, p.189).'},
    {'name': 'branched-quadratic-di-sialate-siloxo',
     'species_kind': 'motif',
     'notes': 'Branched quadratic di-(sialate-siloxo) — the COMMON '
              'product both 6a and 6b converge on (similar to the '
              'oligo-siloxane hexamer No.6d, Felmy et al. 2001 / '
              'Fig 5.13); polycondenses to phillipsite (p.189).'},
    {'name': 'sodium-hydroxide', 'formula': 'NaOH',
     'species_kind': 'molecule',
     'notes': 'Liberated by both condensation pathways and reacts '
              'again (pp.186-187) — the alkali is regenerated, not '
              'consumed.'},
    {'name': 'potassium-hydroxide', 'formula': 'KOH',
     'species_kind': 'molecule',
     'notes': 'The K-route regenerated alkali (pp.195-196).'},
    {'name': 'cyclo-di-sialate-siloxo', 'species_kind': 'motif',
     'notes': 'Cyclic hexagonal di-(sialate-siloxo) intermediate of '
              'the K leucite route (p.196, reaction 6).'},
] + [
    # Competing framework families (Finding 4) — products COEXIST;
    # a cured material is phase fractions, never one framework.
    # pp.185-187 pin the first two concretely: nepheline NaAlSiO4
    # (Si:Al=1) + albite NaAlSi3O8 (Si:Al=3) coexist ~50/50 in
    # MK-750 Na-PSS (bulk NaAlSi2O6, Si:Al=2), nano-scale solid
    # solution; XRD-visible only after heat treatment >500 C.
    {'name': f'framework-{f}', 'display_name': f.capitalize(),
     'species_kind': 'framework',
     'notes': 'Competing framework family (pp.185-190).'}
    for f in ('amorphous-gel', 'nepheline', 'phillipsite', 'albite',
              'leucite', 'kalsilite')
] + [
    {'name': 'framework-kaliophilite', 'display_name': 'Kaliophilite',
     'formula': 'KAlSiO4', 'species_kind': 'framework',
     'notes': 'K-PS X-ray relative (US 4,472,199, p.191): anhydrous '
              'feldspathoid Kn(-Si-O-Al-O-)n.wH2O, w in [0,1] — NOT '
              'a zeolite. TGA discriminator: <=5% water loss to '
              '325C (feldspathoidic, thermal-shock resistant) vs '
              '21-29% between 100-500C for (Na,K)-PSS (zeolitic '
              'water, must dehydroxylate <=400C before high-T use). '
              'Brittle but hard, 5 Mohs. Patent also names analcime/'
              'gismondine/gmelinite/phillipsite relatives for the '
              'non-PSS polysilicate+KOH route.'},
]

for _row in SEED_CHEMICAL_SPECIES:
    _row.setdefault('provenance_id', _NET_PROVENANCE)

#: The two rules the photographed pages actually support — topology
#: templates ONLY, kinetics_status='none' (rate queries refuse).
SEED_REACTION_RULES = [
    {
        'name': 'siloxane-hydrolysis',
        'display_name': 'Siloxane bridge hydrolysis',
        'reactants_json': json.dumps(
            ['siloxane-bridge', 'hydroxide-ion']),
        'products_json': json.dumps(['silanol-group', 'nbo-terminal']),
        'topology_change': 'Break one Si-O connection of a Si-O-Si '
                           'bridge; create a silanol termination and '
                           'a non-bridging oxygen; associate a '
                           'charge-compensating alkali cation.',
        'stage': 'dissolution',
        'hypothesis_status': 'book-supported',
        'material_family': 'general',
        'source_reference': 'Davidovits Ch.5 §5.3.1 p.84 (depolymer- '
                            'ization equation) + §5.4.1 p.90 '
                            '(alkaline attack at inter-helix bonds)',
    },
    {
        'name': 'sialate-condensation',
        'display_name': 'Sialate condensation',
        'reactants_json': json.dumps(
            ['silanol-group', 'aluminol-group']),
        'products_json': json.dumps(['sialate-bridge', 'water']),
        'topology_change': 'Condense Si-OH + Al-OH into a Si-O-Al '
                           'bridge, releasing water.',
        'stage': 'framework-growth',
        'hypothesis_status': 'mechanistic-proposal',
        'competing_with_json': json.dumps(['al-o-al-condensation']),
        'material_family': 'geopolymer',
        'source_reference': 'Ch.7/8 mechanism discussion (relayed '
                            '2026-07-18; chapter pages pending). '
                            'Registered as a PROPOSAL: Ch.7 notes the '
                            'Al-O-Al variant conflicts with '
                            "Loewenstein's avoidance principle.",
    },
    # ---- pp.184-187: the MK-750 two-phase mechanism as rules ----
    {
        'name': 'ortho-sialate-formation',
        'display_name': 'Ortho-sialate formation (steps 1-5)',
        'reactants_json': json.dumps(
            ['metakaolin-layer', 'sodium-ion', 'hydroxide-ion']),
        'products_json': json.dumps(['ortho-sialate']),
        'topology_change': 'Steps 1-5 (pp.181-182): alkalination '
                           'forms the tetravalent-Al side group '
                           'O3-Si-O-Al-(OH)3(-)Na+ — via the Al(V) '
                           'alumoxyl (-Al=O) route (§8.3.1) or '
                           'Al-O-Al cleavage + hydroxylation '
                           '(§8.3.2); steps 2-4 cleave the '
                           'poly(siloxo) layer and isolate the '
                           'ortho-sialate; step 5 reacts the basic '
                           'siloxo Si-O(-) with Na+/K+ to the '
                           'Si-ONa/Si-OK terminal. Same steps for Na '
                           'and K (K+ bigger -> slightly different '
                           'kinetics; MK-750 poly(siloxo) backbone '
                           'stays practically intact).',
        'stage': 'ortho-sialate-generation',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits pp.181-182 (§8.3-8.3.2, '
                            'reactions 1 and 5) + pp.184-187 (both '
                            'phases branch after these steps)',
    },
    # ---- pp.194-196: the K analogues — same stages, different
    # frameworks (the generality proof for rules-as-data) ----
    {
        'name': 'kalsilite-pathway-condensation',
        'display_name': 'K step 6: three ortho-sialates → '
                        'cyclo-tri-sialate',
        'reactants_json': json.dumps(
            ['ortho-sialate', 'ortho-sialate', 'ortho-sialate']),
        'products_json': json.dumps(
            ['cyclo-tri-sialate', 'potassium-hydroxide']),
        'topology_change': 'Condensation between THREE ortho-sialate '
                           'molecules (Si-OK + OH-Al) creates the '
                           'hexagonal cyclo-tri-sialate; KOH '
                           'liberated, reacts again.',
        'stage': 'branch-selection',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.195 §8.6.1 reaction (6) — '
                            'K analogue of the Na nepheline route '
                            '(same stages, different framework)',
    },
    {
        'name': 'kalsilite-framework-polycondensation',
        'display_name': 'Polycondensation to kalsilite',
        'reactants_json': json.dumps(['cyclo-tri-sialate']),
        'products_json': json.dumps(['framework-kalsilite']),
        'topology_change': 'Polycondensation into the K-poly(sialate) '
                           'kalsilite framework (KAlSiO4, Si:Al=1).',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.195 §8.6.1',
    },
    {
        'name': 'leucite-pathway-condensation',
        'display_name': 'K step 6: Q0 + two ortho-sialates → '
                        'cyclo-di-sialate-siloxo',
        'reactants_json': json.dumps(
            ['siloxonate-q0', 'ortho-sialate', 'ortho-sialate']),
        'products_json': json.dumps(
            ['cyclo-di-sialate-siloxo', 'potassium-hydroxide']),
        'topology_change': 'Ortho-siloxonate Q0 condenses with two '
                           'ortho-sialates (Si-OK, Si-OH, OH-Al) into '
                           'the cyclic hexagonal di-(sialate-siloxo); '
                           'KOH liberated. Q0 again requires mild '
                           'depolymerization of Q1/Q2 at MR < 1.20 — '
                           'the SAME threshold as the Na phillipsite '
                           'route (p.196).',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits pp.195-196 §8.6.2 — K '
                            'analogue of the Na phillipsite route',
    },
    {
        'name': 'leucite-framework-polycondensation',
        'display_name': 'Polycondensation to leucite',
        'reactants_json': json.dumps(['cyclo-di-sialate-siloxo']),
        'products_json': json.dumps(['framework-leucite']),
        'topology_change': 'Polycondensation into the K-poly(sialate-'
                           'siloxo) leucite framework (KAlSi2O6, '
                           'Si:Al=2). Kriven route to pure leucite '
                           'CERAMIC: crush geopolymer '
                           'K2O.Al2O3.4SiO2.7.5H2O, die-press, '
                           'sinter 1200C/12h (~3um leucite grains in '
                           'amorphous matrix), anneal 1400C/5h '
                           '(p.196).',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.196 §8.6.2 (Kriven et al. '
                            '2003/2005)',
    },
    {
        'name': 'albite-pathway-condensation',
        'display_name': 'Phase 1: ortho-sialate + di-siloxonate '
                        'condensation (reaction 6)',
        'reactants_json': json.dumps(
            ['ortho-sialate', 'di-siloxonate']),
        'products_json': json.dumps(
            ['ortho-sialate-disiloxo-cycle', 'sodium-hydroxide']),
        'topology_change': 'Condensation of reactive Si-ONa, Si-OH, '
                           'OH-Al groups builds the cyclic '
                           'ortho-sialate-disiloxo structure; NaOH '
                           'is liberated and reacts again.',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.186 §8.5.1 reaction (6): '
                            'outer faces/edges; needs waterglass '
                            'siloxonates, so SURFACE ONLY (Fig 8.21)',
    },
    {
        'name': 'albite-framework-polycondensation',
        'display_name': 'Step 7: polycondensation to albite',
        'reactants_json': json.dumps(['ortho-sialate-disiloxo-cycle']),
        'products_json': json.dumps(['framework-albite']),
        'topology_change': 'Further polycondensation into the '
                           'Na-poly(sialate-disiloxo) albite '
                           'framework (NaAlSi3O8, Si:Al=3) with the '
                           'feldspar crankshaft chain structure.',
        'stage': 'framework-growth',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.186 §8.5.1 step 7',
    },
    {
        'name': 'nepheline-pathway-condensation',
        'display_name': 'Phase 2: ortho-sialate self-condensation '
                        '(reaction 7)',
        'reactants_json': json.dumps(
            ['ortho-sialate', 'ortho-sialate']),
        'products_json': json.dumps(
            ['cyclo-tri-sialate', 'sodium-hydroxide']),
        'topology_change': 'Interstitial monophase reaction with '
                           'MK-750 alone: Si-ONa + OH-Al condense to '
                           'the cyclo-tri-sialate structure; NaOH '
                           'liberated, reacts again.',
        'stage': 'branch-selection',
        'site_constraint': 'interior-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.187 §8.5.2 reaction (7): '
                            'interlayers admit ONLY Na+/K+/OH- — '
                            'even Q0 is too big (Fig 8.21, p.184)',
    },
    # ---- pp.188-189: the phillipsite (Si:Al=2) route via Q0 ----
    {
        'name': 'mild-oligo-depolymerization',
        'display_name': 'Mild depolymerization Q1/Q2 → Q0',
        'reactants_json': json.dumps(
            ['siloxonate-q2', 'siloxonate-q1']),
        'products_json': json.dumps(['siloxonate-q0']),
        'topology_change': 'Mild depolymerization of Na-oligo-'
                           'siloxonates frees monomeric '
                           'ortho-siloxonate Q0.',
        'stage': 'dissolution',
        'hypothesis_status': 'book-supported',
        'condition_windows_json': json.dumps(
            ['na-silicate:mr-q0-depolymerization']),
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.188 §8.5.3 — CONDITION: '
                            'only when the Na-silicate solution has '
                            'MR < 1.20 (gated by the '
                            "ThresholdReactionWindow row "
                            "'na-silicate:mr-q0-depolymerization')",
    },
    {
        'name': 'phillipsite-6a-linear-formation',
        'display_name': 'Step 6a: Q0 + ortho-sialate → linear '
                        'sialate-siloxo',
        'reactants_json': json.dumps(
            ['ortho-sialate', 'siloxonate-q0']),
        'products_json': json.dumps(['ortho-sialate-siloxo-linear']),
        'topology_change': 'Condense one ortho-siloxonate Q0 with '
                           'one ortho-sialate (Si-ONa + OH-Al '
                           'reactive groups) into the linear '
                           'ortho-sialate-siloxo structure (No.2).',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'competing_with_json': json.dumps(
            ['phillipsite-6b-disialate-condensation']),
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits pp.188-189 step 6a (North & '
                            'Swaddle 2000)',
    },
    {
        'name': 'phillipsite-6a-quadratic-condensation',
        'display_name': 'Step 6a cont.: two linears → branched '
                        'quadratic',
        'reactants_json': json.dumps(
            ['ortho-sialate-siloxo-linear',
             'ortho-sialate-siloxo-linear']),
        'products_json': json.dumps(
            ['branched-quadratic-di-sialate-siloxo',
             'sodium-hydroxide']),
        'topology_change': 'Two linear ortho-sialate-siloxo '
                           'molecules condense into the branched '
                           'quadratic di-(sialate-siloxo); NaOH '
                           'liberated, reacts again.',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.189 reaction (6a)',
    },
    {
        'name': 'phillipsite-6b-disialate-condensation',
        'display_name': 'Step 6b: two ortho-sialates → quadratic '
                        'di-sialate, then + 2 Q0',
        'reactants_json': json.dumps(
            ['ortho-sialate', 'ortho-sialate']),
        'products_json': json.dumps(
            ['quadratic-di-sialate', 'sodium-hydroxide']),
        'topology_change': 'Two ortho-sialate molecules condense '
                           '(Si-ONa + OH-Al) into the quadratic '
                           'di-sialate, which then condenses with '
                           'two ortho-siloxonates Q0 into the SAME '
                           'branched quadratic as 6a.',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'competing_with_json': json.dumps(
            ['phillipsite-6a-linear-formation']),
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.189 reaction (6b) — 6a and '
                            '6b are ALTERNATIVE PATHS converging on '
                            'one intermediate',
    },
    {
        'name': 'phillipsite-6b-siloxo-addition',
        'display_name': 'Step 6b cont.: quadratic di-sialate + 2 Q0',
        'reactants_json': json.dumps(
            ['quadratic-di-sialate', 'siloxonate-q0']),
        'products_json': json.dumps(
            ['branched-quadratic-di-sialate-siloxo',
             'sodium-hydroxide']),
        'topology_change': 'The quadratic di-sialate condenses with '
                           'ortho-siloxonates Q0 into the branched '
                           'quadratic di-(sialate-siloxo).',
        'stage': 'branch-selection',
        'site_constraint': 'surface-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.189 (6b continuation)',
    },
    {
        'name': 'phillipsite-framework-polycondensation',
        'display_name': 'Step 7: polycondensation to phillipsite',
        'reactants_json': json.dumps(
            ['branched-quadratic-di-sialate-siloxo']),
        'products_json': json.dumps(['framework-phillipsite']),
        'topology_change': 'Polycondensation into the Na-poly'
                           '(sialate-siloxo) phillipsite framework '
                           '(NaAlSi2O6, Si:Al=2) — the IDEAL Na-PSS '
                           'structure; zeolitic (micro-porosity + '
                           'higher zeolitic water). NOTE p.185: the '
                           'heat-treated Zoulgami sample crystallized '
                           'to nepheline+albite 50/50 instead — '
                           'framework selection is genuinely '
                           'competitive.',
        'stage': 'framework-growth',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.189 step 7 + p.185 §8.5',
    },
    {
        'name': 'nepheline-framework-polycondensation',
        'display_name': 'Polycondensation to nepheline',
        'reactants_json': json.dumps(['cyclo-tri-sialate']),
        'products_json': json.dumps(['framework-nepheline']),
        'topology_change': 'Further polycondensation into the '
                           'Na-poly(sialate) nepheline framework '
                           '(NaAlSiO4, Si:Al=1).',
        'stage': 'framework-growth',
        'site_constraint': 'interior-only',
        'hypothesis_status': 'book-supported',
        'material_family': 'geopolymer',
        'source_reference': 'Davidovits p.187 §8.5.2',
    },
]

#: §8.5 = the Na routes, §8.6 = their K analogues; unfamilied rules
#: fire in both (ortho-sialate formation is 'same steps for Na and K',
#: pp.181-182; mild depolymerization spans both — p.196 pins the K
#: route to the SAME MR<1.20 threshold as the Na phillipsite route).
_RULE_CATION_FAMILIES = {
    'albite-pathway-condensation': 'Na',
    'albite-framework-polycondensation': 'Na',
    'nepheline-pathway-condensation': 'Na',
    'nepheline-framework-polycondensation': 'Na',
    'phillipsite-6a-linear-formation': 'Na',
    'phillipsite-6a-quadratic-condensation': 'Na',
    'phillipsite-6b-disialate-condensation': 'Na',
    'phillipsite-6b-siloxo-addition': 'Na',
    'phillipsite-framework-polycondensation': 'Na',
    'kalsilite-pathway-condensation': 'K',
    'kalsilite-framework-polycondensation': 'K',
    'leucite-pathway-condensation': 'K',
    'leucite-framework-polycondensation': 'K',
}

for _row in SEED_REACTION_RULES:
    _row.setdefault('provenance_id', _NET_PROVENANCE)
    _row.setdefault('cation_family',
                    _RULE_CATION_FAMILIES.get(_row['name'], ''))


def _species_names(seed_or_rows):
    names = set()
    for r in seed_or_rows:
        get = (r.get if isinstance(r, dict)
               else lambda k, d='': getattr(r, k, d))
        names.add(get('name', ''))
    return names


def validate_rule(rule, species_rows=None):
    """A rule may only trade in species the inventory knows; stage
    must be a named common stage; hypothesis status must be declared."""
    get = (rule.get if isinstance(rule, dict)
           else lambda k, d='': getattr(rule, k, d))
    known = _species_names(species_rows if species_rows is not None
                           else SEED_CHEMICAL_SPECIES)

    def loads(key):
        raw = get(key, '[]') or '[]'
        try:
            return raw if isinstance(raw, list) else json.loads(raw)
        except Exception:
            return []
    unknown = [s for s in loads('reactants_json') + loads('products_json')
               if s not in known]
    if unknown:
        return {'ok': False,
                'refusal': f'rule {get("name", "?")!r} names unknown '
                           f'species {unknown}',
                'suggestion': 'add ChemicalSpecies rows first — rules '
                              'may only trade in the inventory'}
    if get('stage', '') not in REACTION_STAGES:
        return {'ok': False,
                'refusal': f'unknown stage {get("stage", "")!r}',
                'suggestion': f'use one of {list(REACTION_STAGES)}'}
    if get('hypothesis_status', '') not in HYPOTHESIS_STATUSES:
        return {'ok': False,
                'refusal': 'hypothesis_status must be declared',
                'suggestion': f'one of {list(HYPOTHESIS_STATUSES)} — '
                              'mechanisms are competing hypotheses, '
                              'never hardcoded truth'}
    if get('site_constraint', '') not in SITE_CONSTRAINTS:
        return {'ok': False,
                'refusal': f'unknown site_constraint '
                           f'{get("site_constraint", "")!r}',
                'suggestion': f'one of {list(SITE_CONSTRAINTS)} '
                              '(Fig 8.21 transport selection)'}
    return {'ok': True, 'name': get('name', '')}


def rule_rate(rule, conditions=None):
    """Rate queries REFUSE until a cited calibration exists — the
    topology template ships before the kinetics (invariant I5)."""
    get = (rule.get if isinstance(rule, dict)
           else lambda k, d='': getattr(rule, k, d))
    if get('kinetics_status', 'none') == 'none':
        return {'ok': False,
                'refusal': f'rule {get("name", "?")!r} has no '
                           'calibrated kinetics',
                'suggestion': 'load a cited rate law (set '
                              'kinetics_status + kinetics_ref on the '
                              'rule) — the source pages photographed '
                              'so far provide the topology change '
                              'only, not rate constants'}
    return {'ok': False,
            'refusal': 'calibrated kinetics execution not yet '
                       'implemented (pspp-8)',
            'suggestion': 'pspp-8 ReactionProgressModel consumes '
                          'calibrated rules'}
