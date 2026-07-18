"""
@cross-cutting
@module techtree.techtree_seed

The Open Source Economic Baseline tree (tt-5, TECH_TREE_TOPOLOGY_PLAN
B5): the 13-domain OSEB slice as TechNode rows — theory segments
wired to the modules that ALREADY EXIST in this framework (the
theory baseline is substantially built), real/business/politics left
as honest gaps for tt-6+. The BLCNC/PVD worked example
(BLCNC_PVD_ROADMAP P1..P5 + OS-PVD) is seeded as connected nodes so
dependencies, transient designation, and per-segment completion get
exercised by real content: as each phase's sim modules land, its
theory segment fills and the node's completion rises.

Seeded PolariModule rows below mark the module directories genuinely
present in this image as installed (that is what the theory
done-test reads) and self-declare their primary tech-node placement
(tech_node_ref, tt-1). Refs like 'blcnc' / 'ospvd' point at modules
that DO NOT exist yet — those assignments stay undone and their gaps
name exactly what to build (knobs-and-suggestions).

@consumers
  - polariServer seed loop (idempotent-by-name)
  - techtree.selftest_techtree (seed-coherence suite)
"""

import json as _json

TREE = 'oseb'


def _node(short, title, deps=(), description=''):
    return {'name': f'{TREE}/{short}', 'tree_name': TREE,
            'title': title, 'description': description,
            'depends_on_json': _json.dumps(
                [f'{TREE}/{d}' for d in deps]),
            'layout_hints_json': '{}', 'notes': ''}


def _theory(short, ref):
    return {'name': f'{TREE}/{short}:theory:{ref}',
            'tech_node': f'{TREE}/{short}', 'tree_name': TREE,
            'segment_kind': 'theory', 'ref_name': ref, 'notes': ''}


def _module(name, tech_short, summary):
    """One genuinely-present framework module directory, installed
    in this image, self-declaring its primary tech-node placement."""
    return {'name': name, 'version': '', 'source_kind': 'file',
            'source_ref': name, 'status': 'installed',
            'manifest_json': _json.dumps({'summary': summary}),
            'bundle_json': '', 'data_only': False,
            'tech_node_ref': f'{TREE}/{tech_short}'}


SEED_TECH_TREE_DEFINITIONS = [{
    'name': TREE, 'owner': 'polari',
    'description': 'The Open Source Economic Baseline: the full set '
                   'of technologies needed for an open, '
                   'self-sufficient unit economy. Complete tree = '
                   'baseline achieved — the end goal of the whole '
                   'Polari project.',
    'is_active': True, 'is_baseline': True, 'notes': '',
}]

#: The 13 Open-Source-Economy-Notes domains (B5) + the OS-PVD node
#: and the five BLCNC/PVD roadmap phases (the worked example).
SEED_TECH_NODES = [
    _node('wax-materials', 'Wax materials',
          description='Bio/synthetic wax basis + supply routes.'),
    _node('3d-printing', '3D printing + extrusion',
          deps=('wax-materials',),
          description='Pellet-fed auger-screw wax printing '
                      '(waxprint wp-1..8).'),
    _node('filament-formulation', 'Filament formulation',
          deps=('wax-materials',),
          description='Formulation searches over the materials '
                      'basis.'),
    _node('carbon-nanotubes', 'Carbon nanotubes',
          description='CNT family in the materials basis.'),
    _node('battery-semiconductors',
          'Solid-state battery + semiconductors',
          deps=('carbon-nanotubes', 'ceramics-composites'),
          description='Electrodevice stack over the materials '
                      'basis.'),
    _node('bombastic-laser-cnc', 'Bombastic Laser CNC',
          deps=('wax-materials', 'nanoparticles',
                'open-source-hardware'),
          description='Laser melt/ablate wax voxels + LASiS '
                      'nanoparticle synthesis (BLCNC_PLAN).'),
    _node('nanoparticles', 'Nanoparticles',
          description='LASiS nanoparticle family (msci-20).'),
    _node('ceramics-composites', 'Ceramics + composites',
          description='Ceramics/geopolymer families in the '
                      'materials basis.'),
    _node('electromagnetic-systems', 'Electromagnetic systems',
          deps=('ceramics-composites',),
          description='Ferrite/magnetics + electromagnetic '
                      'hardware.'),
    _node('open-source-hardware', 'Open-source hardware',
          description='MCU+FPGA stack, safety MCU, hwsim digital '
                      'twins.'),
    _node('computational-methods', 'Computational methods',
          description='The Polari framework itself: FEM/DFT/MD/meso '
                      'engines, no-code, simulation composition.'),
    _node('household-nutrition',
          'Household nutrition / agroforestry',
          deps=('computational-methods',),
          description='Aquaponics towers, nutrition ledger, tanks, '
                      'plant morphology.'),
    # ---- The BLCNC/PVD worked example (BLCNC_PVD_ROADMAP) --------
    _node('os-pvd', 'Open-Source PVD',
          description='PVD physics: make the wax, deposit '
                      'sol-gel/CNT into laser-cut wax masks.'),
    _node('blcnc-p1-ideal-melt-voxel', 'P1 Ideal melt-voxel proof',
          deps=('bombastic-laser-cnc', '3d-printing'),
          description='Prove melt-voxel physics under MOST IDEAL '
                      'conditions; gates = Single Melt Action '
                      'Metrics (leakage≈0).'),
    _node('blcnc-p2-theoretical-chip', 'P2 Theoretical chip',
          deps=('blcnc-p1-ideal-melt-voxel', 'os-pvd'),
          description='PVD + verified melt-voxel cycle → smallest '
                      'possible device; prove microchips possible '
                      'by calculation.'),
    _node('blcnc-p31-stochastic-materials',
          'P3.1 Stochastic materials priors',
          deps=('os-pvd',),
          description='Guess stochastic nanocomposite definitions '
                      'from existing PVD/CVD knowledge.'),
    _node('blcnc-p3-feasible-production', 'P3 Feasible production',
          deps=('os-pvd', 'blcnc-p2-theoretical-chip',
                'blcnc-p31-stochastic-materials'),
          description='What nanocomposites are actually producible '
                      '+ their stochastic materials (locked by '
                      'OS-PVD).'),
    _node('blcnc-p4-hardware', 'P4 BLCNC hardware',
          deps=('bombastic-laser-cnc', 'open-source-hardware'),
          description='Laser fleet + ETL + gantry + FPGA + safety '
                      'in the hwsim twin; aluminum heat-calibration '
                      'voxels.'),
    _node('blcnc-p5-microfab-device', 'P5 Combined microfab device',
          deps=('blcnc-p3-feasible-production', 'blcnc-p4-hardware'),
          description='The all-in-one BLCNC+PVD microfab device.'),
]

#: Theory assignments. Refs matching an installed PolariModule (or
#: an enabled ModuleAssignment) test done; refs to not-yet-built
#: modules ('blcnc', 'ospvd') stay honest gaps naming the build.
SEED_TECH_SEGMENT_ASSIGNMENTS = [
    _theory('wax-materials', 'materialsScience'),
    _theory('wax-materials', 'waxsupply'),
    _theory('3d-printing', 'Wax-3D-Printing'),
    _theory('filament-formulation', 'materialsScience'),
    _theory('carbon-nanotubes', 'materialsScience'),
    _theory('battery-semiconductors', 'electrodevice'),
    _theory('battery-semiconductors', 'materialsScience'),
    _theory('bombastic-laser-cnc', 'blcnc'),
    _theory('nanoparticles', 'materialsScience'),
    _theory('ceramics-composites', 'materialsScience'),
    _theory('electromagnetic-systems', 'materialsScience'),
    _theory('electromagnetic-systems', 'electrodevice'),
    _theory('open-source-hardware', 'hwdigital'),
    _theory('open-source-hardware', 'hwfpga'),
    _theory('open-source-hardware', 'grpcbridge'),
    _theory('computational-methods', 'simulations'),
    _theory('computational-methods', 'matrices'),
    _theory('computational-methods', 'polariNoCode'),
    _theory('household-nutrition', 'aquaponics'),
    _theory('household-nutrition', 'nutrition'),
    _theory('household-nutrition', 'tanks'),
    _theory('household-nutrition', 'plant_morphology'),
    # BLCNC/PVD slice: existing substrate counts, future sims gap.
    _theory('os-pvd', 'ospvd'),
    _theory('blcnc-p1-ideal-melt-voxel', 'blcnc'),
    _theory('blcnc-p1-ideal-melt-voxel', 'Wax-3D-Printing'),
    _theory('blcnc-p2-theoretical-chip', 'ospvd'),
    _theory('blcnc-p2-theoretical-chip', 'blcnc'),
    _theory('blcnc-p31-stochastic-materials', 'materialsScience'),
    _theory('blcnc-p31-stochastic-materials', 'blcnc'),
    _theory('blcnc-p3-feasible-production', 'blcnc'),
    _theory('blcnc-p4-hardware', 'grpcbridge'),
    _theory('blcnc-p4-hardware', 'hwfpga'),
    _theory('blcnc-p4-hardware', 'blcnc'),
    _theory('blcnc-p5-microfab-device', 'blcnc'),
]

#: tt-6 worked examples on the 3d-printing node — REAL rows, HONEST
#: state: the wax printer is designed + simulated but NOT physically
#: proven, the one-person print farm is defined but not evidenced
#: self-sustaining, the policy has no outcome evidence yet. Their
#: gaps are the point: they name exactly what makes them real.
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

#: Fill all four segments on the 3d-printing node so the quartered
#: rendering + per-segment gaps show on real content.
SEED_TECH_SEGMENT_ASSIGNMENTS += [
    {'name': f'{TREE}/3d-printing:real:waxprinter-v1',
     'tech_node': f'{TREE}/3d-printing', 'tree_name': TREE,
     'segment_kind': 'real', 'ref_name': 'waxprinter-v1',
     'notes': ''},
    {'name': f'{TREE}/3d-printing:business:one-person-printfarm',
     'tech_node': f'{TREE}/3d-printing', 'tree_name': TREE,
     'segment_kind': 'business', 'ref_name': 'one-person-printfarm',
     'notes': ''},
    {'name': f'{TREE}/3d-printing:politics:'
             'open-hardware-procurement',
     'tech_node': f'{TREE}/3d-printing', 'tree_name': TREE,
     'segment_kind': 'politics',
     'ref_name': 'open-hardware-procurement', 'notes': ''},
]

#: Framework module directories genuinely present in this image —
#: the theory substrate the done-test reads. tech_node_ref is the
#: module's PRIMARY placement hint (modules like materialsScience
#: serve several nodes via assignments).
SEED_OSEB_POLARI_MODULES = [
    _module('materialsScience', 'wax-materials',
            'Materials basis: identities, scale levels, formulation '
            'searches, FEM/DFT/MD/meso engines, nanoparticle + CNT '
            '+ ceramics families.'),
    _module('waxsupply', 'wax-materials',
            'Bio wax sources + supply routes.'),
    _module('electrodevice', 'battery-semiconductors',
            'Electronic devices: circuits, breadboards, '
            'semiconductor stack.'),
    _module('hwdigital', 'open-source-hardware',
            'Digital hardware: iCE40 bitstream generation.'),
    _module('hwfpga', 'open-source-hardware',
            'FPGA register maps as data + generated artifacts.'),
    _module('grpcbridge', 'open-source-hardware',
            'Hardware bridges + hwsim digital twins.'),
    _module('simulations', 'computational-methods',
            'Simulation definitions, runners, multi-scale '
            'compositions.'),
    _module('matrices', 'computational-methods',
            'Matrix/equation definitions + executors.'),
    _module('polariNoCode', 'computational-methods',
            'No-code solution graphs + execution engine.'),
    _module('aquaponics', 'household-nutrition',
            'Self-watering pots, FEM hydraulics, vermicompost, '
            'plant growth.'),
    _module('nutrition', 'household-nutrition',
            'Harvest→meal nutrients, household demand.'),
    _module('tanks', 'household-nutrition',
            'Freshwater/saltwater tank systems.'),
    _module('plant_morphology', 'household-nutrition',
            'Organ/root confinement plant model.'),
]
