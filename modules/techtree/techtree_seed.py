"""
@cross-cutting
@module techtree.techtree_seed

The Open Source Economic Baseline as THREE DOMAIN TREES (tt-8,
Dustin 2026-07-18 — 'we need a larger containment'):

  electronics       — 'Electronics / Microelectronics': the original
                      tt-5 tree (wax → printing → BLCNC/PVD →
                      microfab), theory wired to the modules that
                      already exist.
  raw-supply-chain  — 'Raw Supply Chain': SHELLS ONLY for
                      aquaponics/household nutrition, agroforestry,
                      biomining, and carbon management — the
                      containers for that work, not the work.
  os-economy-politics — 'Open Source Economy & Politics': SHELLS
                      for judicial systems, policy tracking,
                      business-logic models, and micro-business
                      tailoring (businesses as small as technology
                      allows).

Reaching the end of ALL THREE trees, combined, is the OSEB —
baseline_report rolls them up (every tree is is_baseline=True; the
electronics tree stays is_active as the default view).

Seeded PolariModule rows mark genuinely-present module directories
as installed (the theory done-test reads that) and self-declare
their primary tech-node placement. Refs like 'blcnc' / 'ospvd' /
'agroforestry' / 'microbusiness' point at modules that DO NOT exist
yet — honest gaps naming exactly what to build.

The tt-5 single-tree seed ('oseb') is RETIRED: retire_legacy_trees
removes its rows from the DB + object tree at boot (idempotent,
no-op once gone) and remaps stale PolariModule.tech_node_ref hints.

@consumers
  - polariServer seed loop (idempotent-by-name) + boot retirement
  - techtree.selftest_techtree (seed-coherence suite)
"""

import json as _json

TREE_ELECTRONICS = 'electronics'
TREE_SUPPLY = 'raw-supply-chain'
TREE_ECONOMY = 'os-economy-politics'
TREE_MATERIALS = 'materials-science'  # mtt-1
TREE_SIMULATION = 'simulation-methods'  # smt-1


def _node(tree, short, title, deps=(), description='', cross=(),
          data_deps=()):
    """cross: ((other_tree, other_short, relation), ...) — tt-9
    cross-tree references, shown as zoom-to chips, never edges.
    data_deps: DigitizedDataset names the technology needs to be
    quantitatively complete (mtt-2) — missing/provisional ones surface
    as derived data gaps."""
    return {'name': f'{tree}/{short}', 'tree_name': tree,
            'title': title, 'description': description,
            'depends_on_json': _json.dumps(
                [f'{tree}/{d}' for d in deps]),
            'layout_hints_json': '{}',
            'cross_refs_json': _json.dumps([
                {'tree': ct, 'node': f'{ct}/{cn}', 'relation': rel}
                for ct, cn, rel in cross]),
            'data_dependencies_json': _json.dumps(list(data_deps)),
            'notes': ''}


def _theory(tree, short, ref):
    return {'name': f'{tree}/{short}:theory:{ref}',
            'tech_node': f'{tree}/{short}', 'tree_name': tree,
            'segment_kind': 'theory', 'ref_name': ref, 'notes': ''}


def _module(name, tree, tech_short, summary):
    """One genuinely-present framework module directory, installed
    in this image, self-declaring its primary tech-node placement."""
    return {'name': name, 'version': '', 'source_kind': 'file',
            'source_ref': name, 'status': 'installed',
            'manifest_json': _json.dumps({'summary': summary}),
            'bundle_json': '', 'data_only': False,
            'tech_node_ref': f'{tree}/{tech_short}'}


SEED_TECH_TREE_DEFINITIONS = [
    {'name': TREE_ELECTRONICS,
     'title': 'Electronics / Microelectronics',
     'owner': 'polari',
     'description': 'Wax materials → printing/extrusion → laser CNC '
                    '+ PVD → theoretical chip → combined microfab '
                    'device: the open path to microelectronics.',
     'is_active': True, 'is_baseline': True, 'notes': ''},
    {'name': TREE_SUPPLY,
     'title': 'Raw Supply Chain',
     'owner': 'polari',
     'description': 'Where the raw inputs come from: aquaponics / '
                    'household nutrition, agroforestry, biomining, '
                    'carbon management. Shells for that work — the '
                    'containers, filled as the work happens.',
     'is_active': False, 'is_baseline': True, 'notes': ''},
    {'name': TREE_ECONOMY,
     'title': 'Open Source Economy & Politics',
     'owner': 'polari',
     'description': 'Judicial issues, policies passed, business '
                    'logic for the particular kinds of businesses '
                    'needed, and technology tailored so businesses '
                    'can be as small as possible.',
     'is_active': False, 'is_baseline': True, 'notes': ''},
    {'name': TREE_MATERIALS,
     'title': 'Materials Science',
     'owner': 'polari',
     'description': 'The material bodies we manufacture and simulate. '
                    'Two representation sub-domains — STATISTICAL '
                    '(distribution/amorphous/reactive: the pspp+gsp '
                    'engine) and DISCRETE (precise lattice/particle: '
                    'the msci/ssp engine) — plus the ENCAPSULATION '
                    'bridge (discrete particle -> safe statistical '
                    'carrier). See MATERIALS_TECH_TREE_PLAN.md.',
     'is_active': False, 'is_baseline': True, 'notes': ''},
    {'name': TREE_SIMULATION,
     'title': 'Simulation Methods',
     'owner': 'polari',
     'description': 'The cross-cutting engine layer that serves every '
                    'other tree: SimSpace + runner, multi-scale '
                    'composition/coupling, resource-aware stepping, '
                    'distributed + cross-instance compute, the gRPC '
                    'bridge, hardware-sim digital twins, the no-code '
                    'execution engine, and schema stabilization. '
                    'Cross-refs INTO materials/electronics/hardware — '
                    'the methods, not the domain science.',
     'is_active': False, 'is_baseline': True, 'notes': ''},
]

_E = TREE_ELECTRONICS
_S = TREE_SUPPLY
_P = TREE_ECONOMY
_M = TREE_MATERIALS
_SM = TREE_SIMULATION

#: Electronics / Microelectronics — the original tt-5 nodes (the
#: household-nutrition node moved to the Raw Supply Chain tree).
SEED_TECH_NODES = [
    _node(_E, 'wax-materials', 'Wax materials',
          description='Bio/synthetic wax basis + supply routes.',
          cross=((_S, 'wax-supply', 'supplied-by'),)),
    _node(_E, '3d-printing', '3D printing + extrusion',
          deps=('wax-materials',),
          description='Pellet-fed auger-screw wax printing '
                      '(waxprint wp-1..8).',
          cross=((_S, 'wax-supply', 'supplied-by'),)),
    _node(_E, 'filament-formulation', 'Filament formulation',
          deps=('wax-materials',),
          description='Formulation searches over the materials '
                      'basis.'),
    _node(_E, 'carbon-nanotubes', 'Carbon nanotubes',
          deps=('cnt-co-reduction',),
          description='CNT family in the materials basis. Usable '
                      'CNTs need the CO-reduction production route; '
                      'the supply streams (raw, p-doped, n-doped) '
                      'are tracked in the Raw Supply Chain tree.'),
    _node(_E, 'cnt-co-reduction',
          'CNT production via CO reduction',
          description='Carbon-nanotube PRODUCTION as its own '
                      'technology: carbon monoxide reduction route '
                      '(disproportionation → CNT growth). Shell — '
                      'production sim not built yet.',
          cross=((_S, 'cnt-supply', 'produces'),)),
    _node(_E, 'battery-semiconductors',
          'Solid-state battery + semiconductors',
          deps=('carbon-nanotubes', 'ceramics-composites',
                'silicon-refinement'),
          description='Electrodevice stack over the materials '
                      'basis.',
          cross=((_S, 'cnt-supply-p-doped', 'consumes'),
                 (_S, 'cnt-supply-n-doped', 'consumes'),
                 (_S, 'silicon-supply-semiconductor-grade',
                  'consumes'))),
    _node(_E, 'silicon-refinement', 'Silicon refinement grade-scale',
          description='Making the different grades of silicon — '
                      'down the grade-scale from raw/metallurgical '
                      'to PV-grade to semiconductor-grade. The '
                      'grade supply streams live in the Raw Supply '
                      'Chain tree. Shell — refinement sim not '
                      'built yet.',
          cross=((_S, 'silicon-supply-pv-grade', 'produces'),
                 (_S, 'silicon-supply-semiconductor-grade',
                  'produces'))),
    _node(_E, 'bombastic-laser-cnc', 'Bombastic Laser CNC',
          deps=('wax-materials', 'lasis',
                'precision-laser-apparatus', 'open-source-hardware'),
          description='Laser melt/ablate wax voxels (BLCNC_PLAN). '
                      'The REAL device requires the Precision Laser '
                      'Apparatus.',
          cross=((_S, 'wax-nanocomposite-supply', 'supplied-by'),)),
    _node(_E, 'lasis', 'LASiS nanoparticle synthesis',
          deps=('precision-laser-apparatus',),
          description='Laser Ablation Synthesis in Solution — the '
                      'key nanoparticle-making technology (msci-20 '
                      'family). Its output stream is the '
                      'nanoparticle SUPPLY tracked in the Raw '
                      'Supply Chain tree.',
          cross=((_S, 'nanoparticle-supply', 'produces'),)),
    _node(_E, 'precision-laser-apparatus',
          'Precision Laser Apparatus',
          deps=('expandable-dielectrics',),
          description='Modulatable precision laser optics (ETL '
                      'focal control) — required by BOTH the real '
                      'BLCNC and LASiS. Built on dielectrics that '
                      'can be modified to expand/contract.'),
    _node(_E, 'expandable-dielectrics',
          'Tunable expansion dielectrics',
          description='Dielectric materials modifiable to '
                      'expand/contract — the actuation basis for '
                      'the Precision Laser Apparatus.'),
    _node(_E, 'vacuum-pump', 'Open-source vacuum pump',
          description='Prerequisite for the PVD chamber (and the '
                      'BLCNC near-vacuum melt extraction). See '
                      'OSPVD_ROADMAP.md.'),
    _node(_E, 'piezoelectrics', 'Piezoelectric sputter materials',
          description='Materials that can act as piezoelectronics '
                      '— enable the sputter the PVD deposition '
                      'needs. See OSPVD_ROADMAP.md.'),
    _node(_E, 'ceramics-composites', 'Ceramics + composites',
          description='Ceramics/geopolymer families in the '
                      'materials basis.'),
    _node(_E, 'electromagnetic-systems', 'Electromagnetic systems',
          deps=('ceramics-composites',),
          description='Ferrite/magnetics + electromagnetic '
                      'hardware.'),
    _node(_E, 'open-source-hardware', 'Open-source hardware',
          description='MCU+FPGA stack, safety MCU, hwsim digital '
                      'twins.'),
    _node(_E, 'computational-methods', 'Computational methods',
          description='The Polari framework itself: FEM/DFT/MD/meso '
                      'engines, no-code, simulation composition.'),
    _node(_E, 'os-pvd', 'Open-Source PVD',
          deps=('vacuum-pump', 'piezoelectrics'),
          description='PVD physics: make the wax, deposit '
                      'sol-gel/CNT into laser-cut wax masks. Its '
                      'OWN roadmap (OSPVD_ROADMAP.md): vacuum pump '
                      'and piezo sputter materials are '
                      'prerequisites.',
          cross=((_S, 'sol-gel-supply', 'supplied-by'),)),
    _node(_E, 'blcnc-p1-ideal-melt-voxel',
          'P1 Ideal melt-voxel proof',
          deps=('bombastic-laser-cnc', '3d-printing'),
          description='Prove melt-voxel physics under MOST IDEAL '
                      'conditions; gates = Single Melt Action '
                      'Metrics (leakage≈0).'),
    _node(_E, 'blcnc-p2-theoretical-chip', 'P2 Theoretical chip',
          deps=('blcnc-p1-ideal-melt-voxel', 'os-pvd'),
          description='PVD + verified melt-voxel cycle → smallest '
                      'possible device; prove microchips possible '
                      'by calculation.'),
    _node(_E, 'blcnc-p31-stochastic-materials',
          'P3.1 Stochastic materials priors',
          deps=('os-pvd',),
          description='Guess stochastic nanocomposite definitions '
                      'from existing PVD/CVD knowledge.'),
    _node(_E, 'blcnc-p3-feasible-production',
          'P3 Feasible production',
          deps=('os-pvd', 'blcnc-p2-theoretical-chip',
                'blcnc-p31-stochastic-materials'),
          description='What nanocomposites are actually producible '
                      '+ their stochastic materials (locked by '
                      'OS-PVD).'),
    _node(_E, 'blcnc-p4-hardware', 'P4 BLCNC hardware',
          deps=('bombastic-laser-cnc', 'open-source-hardware'),
          description='Laser fleet + ETL + gantry + FPGA + safety '
                      'in the hwsim twin; aluminum heat-calibration '
                      'voxels.'),
    _node(_E, 'blcnc-p5-microfab-device',
          'P5 Combined microfab device',
          deps=('blcnc-p3-feasible-production', 'blcnc-p4-hardware'),
          description='The all-in-one BLCNC+PVD microfab device.'),
    # ---- Raw Supply Chain (SHELLS: containers, not the work) -----
    _node(_S, 'aquaponics', 'Aquaponics / Household nutrition',
          description='Self-watering pots, FEM hydraulics, '
                      'vermicompost, plant growth, harvest→meal '
                      'nutrients, tanks.'),
    _node(_S, 'agroforestry', 'Agroforestry',
          description='Tree/crop system layer over the plant '
                      'morphology model. Shell — module not built '
                      'yet.'),
    _node(_S, 'biomining', 'Biomining / Bioextraction',
          description='Bacteria/algae extraction → product '
                      'variants.'),
    _node(_S, 'carbon-management', 'Carbon management',
          description='Photobioreactor decarbonization + the '
                      'unifying carbon/materials/food ledger.'),
    _node(_S, 'nanoparticle-supply', 'Nanoparticle supply',
          description='The supply stream of nanoparticles as a RAW '
                      'MATERIAL (volumes, sources, feedstocks) — '
                      'produced by LASiS in the Electronics tree. '
                      'Shell — supply module not built yet.',
          cross=((_E, 'lasis', 'produced-by'),)),
    _node(_S, 'cnt-supply', 'Carbon nanotube supply',
          description='Raw CNT supply stream — produced by the '
                      'CO-reduction route in the Electronics tree. '
                      'Shell.',
          cross=((_E, 'cnt-co-reduction', 'produced-by'),)),
    _node(_S, 'cnt-supply-p-doped', 'p-doped CNT supply',
          deps=('cnt-supply',),
          description='p-doped CNTs as their own raw-material '
                      'stream (semiconductor substrate). Shell.',
          cross=((_E, 'battery-semiconductors', 'consumed-by'),)),
    _node(_S, 'cnt-supply-n-doped', 'n-doped CNT supply',
          deps=('cnt-supply',),
          description='n-doped CNTs as their own raw-material '
                      'stream (semiconductor substrate). Shell.',
          cross=((_E, 'battery-semiconductors', 'consumed-by'),)),
    _node(_S, 'silicon-supply', 'Raw silicon supply',
          description='Raw / metallurgical-grade silicon as the '
                      'base of the grade-scale. Shell.'),
    _node(_S, 'silicon-supply-pv-grade', 'PV-grade silicon supply',
          deps=('silicon-supply',),
          description='PV-grade silicon — first stop down the '
                      'grade-scale (refined by the Electronics '
                      'tree\'s silicon-refinement tech). Shell.',
          cross=((_E, 'silicon-refinement', 'produced-by'),)),
    _node(_S, 'silicon-supply-semiconductor-grade',
          'Semiconductor-grade silicon supply',
          deps=('silicon-supply-pv-grade',),
          description='Semiconductor-grade silicon — the far end '
                      'of the grade-scale. Shell.',
          cross=((_E, 'silicon-refinement', 'produced-by'),
                 (_E, 'battery-semiconductors', 'consumed-by'))),
    _node(_S, 'sol-gel-supply', 'Sol-gel supply',
          description='Sol-gel precursors/coatings as a critical '
                      'raw material (the OS-PVD deposition feed). '
                      'Shell.',
          cross=((_E, 'os-pvd', 'supplies'),)),
    _node(_S, 'geopolymer-composite-supply',
          'Geopolymer composite supply',
          description='Geopolymer composites as a critical raw '
                      'material (msci ceramics/geopolymer family '
                      'carries the theory). Shell.'),
    _node(_S, 'wax-supply', 'Wax supply',
          description='Wax as a critical raw material — bio + '
                      'synthetic source routes (waxsupply module).',
          cross=((_E, 'wax-materials', 'supplies'),
                 (_E, '3d-printing', 'supplies'))),
    _node(_S, 'wax-nanocomposite-supply',
          'Wax nanocomposite layer supply',
          deps=('wax-supply', 'nanoparticle-supply'),
          description='Wax + nanoparticle composite LAYERS as their '
                      'own raw-material stream (the 7 msci recipes; '
                      'recipe 7 = the BLCNC sim target). Shell for '
                      'the supply side.',
          cross=((_E, 'bombastic-laser-cnc', 'supplies'),)),
    # ---- Open Source Economy & Politics (SHELLS) -----------------
    _node(_P, 'judicial-systems', 'Judicial systems',
          description='Addressing judicial issues: court cases as '
                      'no-code rows, democratic proofs, term '
                      'competition.'),
    _node(_P, 'policy-tracking', 'Policy tracking',
          description='Policies passed: legislation tracking, cost '
                      'of living evidence, accountability '
                      'scorecards.'),
    _node(_P, 'business-logic-models', 'Business-logic models',
          description='Business logic for the particular kinds of '
                      'businesses the baseline needs (scale ladder: '
                      'one-person → unit-economy).',
          cross=((_E, '3d-printing', 'applies-to'),)),
    _node(_P, 'micro-business-tailoring', 'Micro-business tailoring',
          deps=('business-logic-models',),
          description='Efficiency + technology tailored so each '
                      'business can be AS SMALL AS POSSIBLE. Shell '
                      '— module not built yet.'),
]

SEED_TECH_SEGMENT_ASSIGNMENTS = [
    # ---- Electronics / Microelectronics --------------------------
    _theory(_E, 'wax-materials', 'materialsScience'),
    _theory(_E, 'wax-materials', 'waxsupply'),
    _theory(_E, '3d-printing', 'Wax-3D-Printing'),
    _theory(_E, 'filament-formulation', 'materialsScience'),
    _theory(_E, 'carbon-nanotubes', 'materialsScience'),
    _theory(_E, 'cnt-co-reduction', 'cntproduction'),
    _theory(_E, 'battery-semiconductors', 'electrodevice'),
    _theory(_E, 'battery-semiconductors', 'materialsScience'),
    _theory(_E, 'silicon-refinement', 'siliconrefinement'),
    _theory(_E, 'bombastic-laser-cnc', 'blcnc'),
    _theory(_E, 'lasis', 'materialsScience'),
    _theory(_E, 'lasis', 'blcnc'),
    _theory(_E, 'precision-laser-apparatus', 'precisionlaser'),
    _theory(_E, 'expandable-dielectrics', 'materialsScience'),
    _theory(_E, 'vacuum-pump', 'vacuumpump'),
    _theory(_E, 'piezoelectrics', 'materialsScience'),
    _theory(_E, 'ceramics-composites', 'materialsScience'),
    _theory(_E, 'electromagnetic-systems', 'materialsScience'),
    _theory(_E, 'electromagnetic-systems', 'electrodevice'),
    _theory(_E, 'open-source-hardware', 'hwdigital'),
    _theory(_E, 'open-source-hardware', 'hwfpga'),
    _theory(_E, 'open-source-hardware', 'grpcbridge'),
    _theory(_E, 'computational-methods', 'simulations'),
    _theory(_E, 'computational-methods', 'matrices'),
    _theory(_E, 'computational-methods', 'polariNoCode'),
    _theory(_E, 'os-pvd', 'ospvd'),
    _theory(_E, 'blcnc-p1-ideal-melt-voxel', 'blcnc'),
    _theory(_E, 'blcnc-p1-ideal-melt-voxel', 'Wax-3D-Printing'),
    _theory(_E, 'blcnc-p2-theoretical-chip', 'ospvd'),
    _theory(_E, 'blcnc-p2-theoretical-chip', 'blcnc'),
    _theory(_E, 'blcnc-p31-stochastic-materials', 'materialsScience'),
    _theory(_E, 'blcnc-p31-stochastic-materials', 'blcnc'),
    _theory(_E, 'blcnc-p3-feasible-production', 'blcnc'),
    _theory(_E, 'blcnc-p4-hardware', 'grpcbridge'),
    _theory(_E, 'blcnc-p4-hardware', 'hwfpga'),
    _theory(_E, 'blcnc-p4-hardware', 'blcnc'),
    _theory(_E, 'blcnc-p5-microfab-device', 'blcnc'),
    # ---- Raw Supply Chain (what exists counts; shells stay gaps) -
    _theory(_S, 'aquaponics', 'aquaponics'),
    _theory(_S, 'aquaponics', 'nutrition'),
    _theory(_S, 'aquaponics', 'tanks'),
    _theory(_S, 'aquaponics', 'plant_morphology'),
    _theory(_S, 'agroforestry', 'plant_morphology'),
    _theory(_S, 'agroforestry', 'agroforestry'),
    _theory(_S, 'biomining', 'biomining'),
    _theory(_S, 'carbon-management', 'microalgae'),
    _theory(_S, 'carbon-management', 'supplychain'),
    _theory(_S, 'nanoparticle-supply', 'nanoparticlesupply'),
    _theory(_S, 'cnt-supply', 'cntsupply'),
    _theory(_S, 'cnt-supply-p-doped', 'cntsupply'),
    _theory(_S, 'cnt-supply-n-doped', 'cntsupply'),
    _theory(_S, 'silicon-supply', 'siliconsupply'),
    _theory(_S, 'silicon-supply-pv-grade', 'siliconsupply'),
    _theory(_S, 'silicon-supply-semiconductor-grade',
            'siliconsupply'),
    _theory(_S, 'sol-gel-supply', 'solgelsupply'),
    _theory(_S, 'geopolymer-composite-supply', 'materialsScience'),
    _theory(_S, 'geopolymer-composite-supply', 'geopolymersupply'),
    _theory(_S, 'wax-supply', 'waxsupply'),
    _theory(_S, 'wax-nanocomposite-supply', 'materialsScience'),
    _theory(_S, 'wax-nanocomposite-supply', 'waxnanosupply'),
    # ---- Open Source Economy & Politics --------------------------
    _theory(_P, 'judicial-systems', 'polariNoCode'),
    _theory(_P, 'judicial-systems', 'scorecard'),
    _theory(_P, 'policy-tracking', 'scorecard'),
    _theory(_P, 'policy-tracking', 'dmvdata'),
    _theory(_P, 'business-logic-models', 'techtree'),
    _theory(_P, 'micro-business-tailoring', 'microbusiness'),
]

#: tt-6 worked examples on the electronics 3d-printing node — REAL
#: rows, HONEST state: sim-proven printer, unevidenced business
#: model + policy. Their gaps name exactly what makes them real.
SEED_REAL_ARTIFACTS = [{
    'name': 'waxprinter-v1',
    'cad_ref': 'waxprint device parts (wp-1..8)',
    'hardware_design_ref': 'two-zone melt + safety interlock design',
    'proven': False,
    'evidence_json': '[]',
    'commercial_route_json': '{}',
    'self_manufacture_route_json': _json.dumps({
        'guide': 'waxprint module: pellet-fed auger-screw design, '
                 'movement patterns, print-recipe optimizer',
        'status': 'sim-proven only — no physical build yet'}),
    'notes': 'Real segment completes when a physical printer is '
             'proven and the commercial route is documented.',
}]

SEED_BUSINESS_MODELS = [{
    'name': 'one-person-printfarm',
    'scale': 'one-person',
    'policies_json': _json.dumps([
        'print-to-order from the open recipe catalog',
        'source pellets via the waxsupply routes']),
    'unit_economics_json': '{}',
    'self_sustaining': False,
    'evidence_json': '[]',
    'notes': 'First rung of the scale ladder for 3D printing.',
}]

SEED_POLICY_DEFINITIONS = [{
    'name': 'open-hardware-procurement',
    'policy': 'public procurement preference for open-hardware '
              'devices with documented self-manufacture routes',
    'effect': 'increase',
    'target_business_model': 'one-person-printfarm',
    'evidence_json': '[]',
    'notes': 'Needs outcome evidence before the politics segment '
             'counts it done.',
}]

SEED_TECH_SEGMENT_ASSIGNMENTS += [
    {'name': f'{_E}/3d-printing:real:waxprinter-v1',
     'tech_node': f'{_E}/3d-printing', 'tree_name': _E,
     'segment_kind': 'real', 'ref_name': 'waxprinter-v1',
     'notes': ''},
    {'name': f'{_E}/3d-printing:business:one-person-printfarm',
     'tech_node': f'{_E}/3d-printing', 'tree_name': _E,
     'segment_kind': 'business', 'ref_name': 'one-person-printfarm',
     'notes': ''},
    {'name': f'{_E}/3d-printing:politics:'
             'open-hardware-procurement',
     'tech_node': f'{_E}/3d-printing', 'tree_name': _E,
     'segment_kind': 'politics',
     'ref_name': 'open-hardware-procurement', 'notes': ''},
]

#: Framework module directories genuinely present in this image —
#: the theory substrate the done-test reads. tech_node_ref is the
#: module's PRIMARY placement hint (modules like materialsScience
#: serve several nodes via assignments). Name kept from tt-5 —
#: polariServer imports it.
SEED_OSEB_POLARI_MODULES = [
    _module('materialsScience', _E, 'wax-materials',
            'Materials basis: identities, scale levels, formulation '
            'searches, FEM/DFT/MD/meso engines, nanoparticle + CNT '
            '+ ceramics families.'),
    _module('waxsupply', _E, 'wax-materials',
            'Bio wax sources + supply routes.'),
    _module('electrodevice', _E, 'battery-semiconductors',
            'Electronic devices: circuits, breadboards, '
            'semiconductor stack.'),
    _module('hwdigital', _E, 'open-source-hardware',
            'Digital hardware: iCE40 bitstream generation.'),
    _module('hwfpga', _E, 'open-source-hardware',
            'FPGA register maps as data + generated artifacts.'),
    _module('grpcbridge', _E, 'open-source-hardware',
            'Hardware bridges + hwsim digital twins.'),
    _module('simulations', _E, 'computational-methods',
            'Simulation definitions, runners, multi-scale '
            'compositions.'),
    _module('matrices', _E, 'computational-methods',
            'Matrix/equation definitions + executors.'),
    _module('mathshapes', _E, 'computational-methods',
            'Math-defined shapes: quadric/primitive/CSG, algorithmic '
            'modification, CAD import (the auger-shape variant '
            'substrate).'),
    _module('polariNoCode', _E, 'computational-methods',
            'No-code solution graphs + execution engine (incl. '
            'judicial CourtCase compilation).'),
    _module('aquaponics', _S, 'aquaponics',
            'Self-watering pots, FEM hydraulics, vermicompost, '
            'plant growth.'),
    _module('nutrition', _S, 'aquaponics',
            'Harvest→meal nutrients, household demand.'),
    _module('tanks', _S, 'aquaponics',
            'Freshwater/saltwater tank systems.'),
    _module('plant_morphology', _S, 'aquaponics',
            'Organ/root confinement plant model.'),
    _module('biomining', _S, 'biomining',
            'Bacteria/algae extraction → product variants.'),
    _module('microalgae', _S, 'carbon-management',
            'Photobioreactor decarbonization route.'),
    _module('supplychain', _S, 'carbon-management',
            'Unifying carbon/materials/food supply ledger.'),
    _module('dmvdata', _P, 'policy-tracking',
            'DMV cost-of-living source catalog + trust stack.'),
    _module('techtree', _P, 'business-logic-models',
            'Tech trees, business-model/policy definitions, '
            'completion rollups.'),
]

# ---------------------------------------------------------------------
# mtt-1 (MATERIALS_TECH_TREE_PLAN): the Materials Science tree. Three
# sub-domain hub nodes + the 9 core manufacturing materials + the
# encapsulation bridge. Materials OWN identity/simulation here and
# cross-ref (never edge) to the electronics tree (what consumes them),
# the supply tree (feedstock), keeping the engine boundary as the
# statistical/discrete cut. Data-only — no engine code.
# ---------------------------------------------------------------------

SEED_TECH_NODES += [
    # -- sub-domain hubs (the engine boundary, as membership deps) ----
    _node(_M, 'statistical', 'Statistical materials (pspp)',
          description='Identity is a DISTRIBUTION over motifs/phases '
                      '— amorphous, reactive, formulated. Engine: '
                      'pspp datasets/rules/windows/state-DAG/progress/'
                      'grader + gsp Q-groups/sampler/Debye halo.'),
    _node(_M, 'discrete', 'Discrete materials (crystal / particle)',
          description='Identity is a PRECISE structure or particle — '
                      'lattice, stoichiometric crystal, sized '
                      'nanoparticle. Engine: msci/ssp '
                      'CrystalStructureDefinition, lattice scenes, '
                      'phonons/elastic, pymatgen symmetry/XRD, '
                      'MD/meso.'),
    _node(_M, 'encapsulation',
          'Encapsulation (discrete -> safe statistical carrier)',
          deps=('discrete', 'statistical'),
          description='Refine a nanoparticle and lock it into a '
                      'wax/lipid composite carrier so it is safe to '
                      'transport/handle (no free-particle spill or '
                      'inhalation hazard). The transform EDGE '
                      'discrete->statistical; safety gating (release '
                      'windows, spill scenarios) is first-class here '
                      '(reuses pspp windows + ExposureScenario).',
          cross=((_E, 'lasis', 'consumes-output-of'),
                 (_S, 'nanoparticle-supply', 'consumes'))),
    # -- the 9 core manufacturing materials ---------------------------
    _node(_M, 'wax', 'Wax', deps=('statistical',),
          description='Bio/synthetic wax as a formulated material — '
                      'wax states + feedstock routes (Wax-3D-Printing '
                      'carries the print process in the electronics '
                      'tree).',
          cross=((_E, 'wax-materials', 'consumed-by'),
                 (_S, 'wax-supply', 'supplied-by'))),
    _node(_M, 'sol-gel', 'Sol-gel', deps=('statistical',),
          description='Alkoxide hydrolysis/condensation to a silica '
                      'gel — BUILT (mtt-2 sg-1..5 + sg-community): '
                      'alkoxide species library + pH catalysis-fork '
                      'and R-ratio gates as ThresholdReactionWindow '
                      'data, sol->gel->xerogel/aerogel state route, '
                      'acid/base fork through the gsp sampler/halo. '
                      'PLUS a community layer: alkoxide-FREE water-'
                      'glass + citrus-juice route, rice-husk / waste-'
                      'glass silica sources, PrecursorSource '
                      'accessibility tiers + the lab->common '
                      'substitution map. Numeric curves + water-glass '
                      'morphology fork refuse pending digitized '
                      'figures.',
          cross=((_E, 'os-pvd', 'consumed-by'),
                 (_S, 'sol-gel-supply', 'supplied-by')),
          data_deps=('silica-solgel-gel-time-vs-ph',
                     'silica-solgel-q-speciation-vs-time',
                     'silica-xerogel-shrinkage-vs-temperature',
                     'sodium-silicate-gel-morphology-vs-ph',
                     'ricehusk-silica-extraction-yield',
                     'citrus-juice-acid-content')),
    _node(_M, 'geopolymer', 'Geopolymer', deps=('statistical',),
          description='Alkali-activated aluminosilicate — FULL pspp '
                      'stack + gsp groups/sampler/Debye halo built '
                      '(GEOPOLYMER_STRUCTURE_SAMPLING_PLAN). The '
                      'carbon-negative layer starts here.',
          cross=((_E, 'ceramics-composites', 'consumed-by'),
                 (_S, 'geopolymer-composite-supply', 'supplied-by'))),
    _node(_M, 'glass', 'Glass', deps=('statistical',),
          description='Silicate glass — the Maekawa alkali-silicate '
                      'Q-distribution curves are LIVE (pspp glass '
                      'mode). Refinement (fining/viscosity/'
                      'devitrification) = datasets + windows TODO; '
                      'crystallization risk hands off to discrete.',
          cross=((_M, 'silicon', 'shares-network-with'),)),
    _node(_M, 'ceramics', 'Ceramics', deps=('statistical',),
          description='Green body -> debind -> sinter. Sintering '
                      'engine BUILT (mtt-2 Part B): analytic Master '
                      'Sintering Curve — work-of-sintering integral Θ '
                      'over a firing schedule + mean-field grain '
                      'growth, writing grain/pore/relative-density '
                      'onto L2 structure rows. HONEST SPLIT: Θ is '
                      'pure math; ρ(Θ) and the grain kinetics are '
                      'CALIBRATION DATA and refuse until a real '
                      'densification master curve is digitized (see '
                      'data gaps). The fired crystalline phase is a '
                      'discrete crystal seed.',
          cross=((_E, 'ceramics-composites', 'consumed-by'),
                 (_S, 'geopolymer-composite-supply', 'related-to')),
          data_deps=('alumina-densification-master-curve',
                     'silica-xerogel-shrinkage-vs-temperature')),
    _node(_M, 'aluminum', 'Aluminum', deps=('discrete',),
          description='fcc metal — crystal seed + phonons/elastic '
                      'LIVE (ssp). BLCNC heat-calibration voxels use '
                      'it.',
          cross=((_E, 'blcnc-p4-hardware', 'consumed-by'),)),
    _node(_M, 'silicon', 'Silicon', deps=('discrete',),
          description='Diamond-cubic — crystal seed + XRD + phonons '
                      'LIVE (ssp). Refinement grades (metallurgical '
                      '-> PV -> semiconductor) + doping = TODO.',
          cross=((_E, 'silicon-refinement', 'refined-by'),
                 (_S, 'silicon-supply', 'supplied-by'))),
    _node(_M, 'carbon-nanotubes', 'Carbon nanotubes',
          deps=('discrete',),
          description='Rolled-graphene tubes — DISCRETE identity; '
                      'needs a chirality/tube structure builder (no '
                      'CrystalStructureDefinition analog yet). '
                      'Production route + supply live in the other '
                      'trees.',
          cross=((_E, 'carbon-nanotubes', 'consumed-by'),
                 (_S, 'cnt-supply', 'supplied-by'))),
    _node(_M, 'galvanized-bio-steel',
          'Galvanized bio-steel (stainless equivalent)',
          deps=('discrete',),
          description='The locally-manufacturable stainless STAND-IN '
                      '(bio_alloys_seed): plain-bio-steel + '
                      'bio-phosphate coat + bio-zinc hot-dip. Valid '
                      'for structural/atmospheric, NOT food-contact/'
                      'immersion/high-temp. TRUE stainless is an '
                      'honest gap — needs Cr, no bio-route.',
          cross=((_S, 'biomining', 'supplied-by'),)),
]

SEED_TECH_SEGMENT_ASSIGNMENTS += [
    # sub-domain hubs -> their engines
    _theory(_M, 'statistical', 'pspp'),
    _theory(_M, 'discrete', 'materialsScience'),
    _theory(_M, 'encapsulation', 'materialsScience'),
    _theory(_M, 'encapsulation', 'pspp'),
    # the 9 cores -> the modules carrying their theory today
    _theory(_M, 'wax', 'Wax-3D-Printing'),
    _theory(_M, 'wax', 'pspp'),
    _theory(_M, 'sol-gel', 'pspp'),
    _theory(_M, 'geopolymer', 'pspp'),
    _theory(_M, 'glass', 'pspp'),
    _theory(_M, 'glass', 'materialsScience'),
    _theory(_M, 'ceramics', 'pspp'),
    _theory(_M, 'ceramics', 'materialsScience'),
    _theory(_M, 'aluminum', 'materialsScience'),
    _theory(_M, 'silicon', 'materialsScience'),
    _theory(_M, 'carbon-nanotubes', 'materialsScience'),
    _theory(_M, 'galvanized-bio-steel', 'materialsScience'),
    _theory(_M, 'galvanized-bio-steel', 'biomining'),
]

SEED_OSEB_POLARI_MODULES += [
    _module('pspp', _M, 'statistical',
            'Processing-Structure-Properties-Performance: the generic '
            'reactive-material engine (datasets/rules/windows/'
            'state-DAG/progress/grader) + gsp geopolymer structure '
            'groups, ensemble sampler, and Debye halo validation.'),
]


# ---------------------------------------------------------------------
# smt-1 (MATERIALS_TECH_TREE_PLAN, sim-methods branch): the Simulation
# Methods tree — the cross-cutting engine layer. Nodes are METHODS
# (SimSpace/runner, multi-scale, resource-aware, distributed,
# cross-instance, gRPC, hardware-sim, no-code execution, schema
# stability); they cross-ref INTO the domain trees they serve. All
# theory carried by modules genuinely present today. Data-only.
# ---------------------------------------------------------------------

SEED_TECH_NODES += [
    _node(_SM, 'nocode-execution', 'No-code execution engine',
          description='SolutionDefinition graphs + the execution '
                      'engine every sim step ultimately runs on '
                      '(P1-P5 no-code foundations; parity across the '
                      'Python + TS engines).'),
    _node(_SM, 'sim-core', 'Simulation core (SimSpace + runner)',
          deps=('nocode-execution',),
          description='SimulationDefinition/Runner + SimSpace 2D/3D — '
                      'the reality-first vector/matrix sim substrate '
                      'materials and hardware both step on.',
          cross=((_E, 'computational-methods', 'detailed-by'),
                 (_M, 'statistical', 'runs'),
                 (_M, 'discrete', 'runs'))),
    _node(_SM, 'multi-scale', 'Multi-scale composition + coupling',
          deps=('sim-core',),
          description='MultiScaleSimulationDefinition, scale '
                      'transfers, SimulationCoupling (wind<->pendulum '
                      'verified) — L1-L5 resolutions composed into '
                      'one run.',
          cross=((_M, 'discrete', 'spans-scales-of'),)),
    _node(_SM, 'resource-aware', 'Resource-aware simulation',
          deps=('sim-core',),
          description='Per-step cost tracking, memory-drain warnings, '
                      'auto-suggested saving strategies, node '
                      'inventory + module-admission advisor '
                      '(resources module, res-1..4).'),
    _node(_SM, 'distributed-compute', 'Distributed compute',
          deps=('sim-core',),
          description='Dask parallel + twin instances + cross-instance '
                      'Dask — the same run spread across cores and '
                      'machines.'),
    _node(_SM, 'cross-instance-sim', 'Cross-instance simulation',
          deps=('distributed-compute',),
          description='xsim: reference ladder, fencing, module-scoped '
                      'backends — sims that span Polari instances '
                      '(xsim-1..6 + modsplit).'),
    _node(_SM, 'grpc-bridge', 'gRPC bridge + peer watch',
          deps=('cross-instance-sim',),
          description='gRPC parity + peer<->peer Watch — the wire '
                      'protocol under cross-instance runs '
                      '(grpc-1/2/j1/j2).'),
    _node(_SM, 'hardware-sim', 'Hardware simulation (digital twins)',
          deps=('sim-core',),
          description='hwsim: Renode/Verilator/ngspice stack, real '
                      'STM32F4 firmware driving the Polari loop — the '
                      'twin that stands in for physical hardware.',
          cross=((_E, 'open-source-hardware', 'twins'),
                 (_E, 'blcnc-p4-hardware', 'twins'))),
    _node(_SM, 'schema-stability', 'Schema stabilization',
          deps=('sim-core',),
          description='Per-class schema freeze + smooth OOPS recovery '
                      '(destabilize/widen/coerce/retry, never silent '
                      'loss) + simulation locks/leases — keeps '
                      'long/distributed runs persistable.'),
]

SEED_TECH_SEGMENT_ASSIGNMENTS += [
    _theory(_SM, 'nocode-execution', 'polariNoCode'),
    _theory(_SM, 'sim-core', 'simulations'),
    _theory(_SM, 'sim-core', 'matrices'),
    _theory(_SM, 'multi-scale', 'simulations'),
    _theory(_SM, 'resource-aware', 'resources'),
    _theory(_SM, 'resource-aware', 'simulations'),
    _theory(_SM, 'distributed-compute', 'simulations'),
    _theory(_SM, 'distributed-compute', 'grpcbridge'),
    _theory(_SM, 'cross-instance-sim', 'grpcbridge'),
    _theory(_SM, 'grpc-bridge', 'grpcbridge'),
    _theory(_SM, 'hardware-sim', 'grpcbridge'),
    _theory(_SM, 'schema-stability', 'simulations'),
]

SEED_OSEB_POLARI_MODULES += [
    _module('resources', _SM, 'resource-aware',
            'Node inventory, resource profiles, per-step measurement, '
            'module-admission advisor (res-1..4).'),
]


# ---------------------------------------------------------------------
# tt-5 single-tree retirement (the 'oseb' tree became three domain
# trees). Idempotent: no-op once the legacy rows are gone.
# ---------------------------------------------------------------------

LEGACY_TREE_NAMES = ('oseb',)

#: Old node names -> new homes, for remapping stale
#: PolariModule.tech_node_ref hints left by the tt-5 seed.
_LEGACY_NODE_REMAP = {
    'oseb/household-nutrition': f'{_S}/aquaponics',
    'oseb/nanoparticles': f'{_E}/lasis',
}


def _remap_legacy_node(old):
    if old in _LEGACY_NODE_REMAP:
        return _LEGACY_NODE_REMAP[old]
    for legacy in LEGACY_TREE_NAMES:
        prefix = f'{legacy}/'
        if old.startswith(prefix):
            return f'{TREE_ELECTRONICS}/{old[len(prefix):]}'
    return old


def backfill_cross_refs(manager):
    """tt-9 upgrade for rows seeded BEFORE cross_refs_json existed:
    stamp the seed's cross-refs onto existing TechNode rows whose
    field is still empty. Fills gaps only — a row somebody edited
    (non-empty field) is never overwritten. Idempotent."""
    seeded = {n['name']: n.get('cross_refs_json', '[]')
              for n in SEED_TECH_NODES
              if n.get('cross_refs_json', '[]') not in ('', '[]')}
    filled = 0
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'TechNode', {}) or {}
    for row in table.values():
        name = getattr(row, 'name', '')
        if name in seeded and getattr(
                row, 'cross_refs_json', '[]') in ('', '[]', None):
            row.cross_refs_json = seeded[name]
            filled += 1
            try:
                manager.db.saveInstanceInDB(row)
            except Exception:
                pass
    return {'filled': filled}


def retire_legacy_trees(manager):
    """Remove the retired single-tree rows from the object tree AND
    the DB, and remap stale tech_node_ref hints. Returns an honest
    count report; never raises."""
    removed = {}
    tables = getattr(manager, 'objectTables', None) or {}
    for legacy in LEGACY_TREE_NAMES:
        for class_name, column in (
                ('TechTreeDefinition', 'name'),
                ('TechNode', 'tree_name'),
                ('TechSegment', 'tree_name'),
                ('TechSegmentAssignment', 'tree_name'),
                ('TechDependencyEdge', 'tree_name')):
            table = tables.get(class_name, {}) or {}
            stale = [key for key, row in list(table.items())
                     if getattr(row, column, '') == legacy]
            for key in stale:
                table.pop(key, None)
            count = len(stale)
            try:
                deleted = manager.db.deleteRowsWhere(
                    class_name, column, legacy)
                if isinstance(deleted, int) and deleted > count:
                    count = deleted
            except Exception:
                pass
            if count:
                removed[f'{class_name}[{legacy}]'] = count
    remapped = 0
    for row in (tables.get('PolariModule', {}) or {}).values():
        old = getattr(row, 'tech_node_ref', '')
        new = _remap_legacy_node(old)
        if new != old:
            row.tech_node_ref = new
            remapped += 1
            try:
                manager.db.saveInstanceInDB(row)
            except Exception:
                pass
    if remapped:
        removed['PolariModule.tech_node_ref remapped'] = remapped
    return removed
