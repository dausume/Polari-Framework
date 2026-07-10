"""
@module materialsScience.l2_l3_models_seed

msci-26 seed models: the first L2 (mesoscale) and L3 (atomistic)
studies, each chosen because it CLOSES an assumption a live L1 model
currently states or answers a standing microstructure question.

@consumers
  - polariServer (registration next to the FEM/DFT model seeds)
  - materialsScience.selftest_standard_materials
"""

import json

SEED_MD_MODELS = [
    {
        'name': 'lj-reference-fluid',
        'display_name': 'LJ reference fluid (validation rung)',
        'description': (
            'The canonical LJ melt at rho*=0.8, T*=1.0 — keeps the '
            'integrator/thermostat honest forever: measured T, '
            'cohesion U*/N, and virial pressure land ON this row '
            'every execution, comparable against the literature '
            'state point.'
        ),
        'physics_ref': 'md-lj-melt',
        'system_json': json.dumps({'nParticles': 256}),
        'thermodynamic_state_json': json.dumps({'density': 0.8,
                                                'temperature': 1.0}),
        'integration_json': json.dumps({'steps': 3000,
                                        'equilibration': 1000,
                                        'dt': 0.005,
                                        'thermostat': 'langevin',
                                        'seed': 1234}),
        'notes': 'Reduced units — the validation model, not a '
                 'material claim.',
        'enabled': True,
    },
    {
        'name': 'paraffin-bead-spring-melt',
        'display_name': 'Paraffin melt — Kremer-Grest bead-spring '
                        '(L3)',
        'description': (
            'Coarse-grained paraffin melt: chainLength 10 at ~3 CH2 '
            'per bead maps a C30-class wax alkane; melt density '
            '0.85, T*=1.0. Yields chain conformation (Rg, '
            'end-to-end, bond length) for the printable-wax story.'
        ),
        'physics_ref': 'md-bead-spring-melt',
        'system_json': json.dumps({'chainLength': 10, 'nChains': 20}),
        'thermodynamic_state_json': json.dumps({'density': 0.85,
                                                'temperature': 1.0}),
        'integration_json': json.dumps({'steps': 3000,
                                        'equilibration': 1000,
                                        'dt': 0.004, 'seed': 1234}),
        'notes': 'Bead-to-monomer mapping ~3 CH2/bead (stated, not '
                 'derived); full TraPPE/GAFF alkane MD is the named '
                 'force-field gap.',
        'enabled': True,
    },
]

SEED_MESO_MODELS = [
    {
        'name': 'cnt-percolation-threshold',
        'display_name': 'CNT rod-network percolation threshold (L2)',
        'description': (
            'DERIVES the percolation threshold the L1 CNT '
            'conductivity models assume (0.005 literature). '
            'aspectRatio 100 — real CNTs run ~1000, beyond the '
            "engine's finite-size-validated range; vf_c scales as "
            '1/aspect, so the derived value is an UPPER bound for '
            'real tubes.'
        ),
        'physics_ref': 'meso-rod-percolation',
        'system_json': json.dumps({'aspectRatio': 100, 'nRods': 400}),
        'sampling_json': json.dumps({'trials': 8, 'iterations': 9,
                                     'seed': 1234}),
        'integration_json': '{}',
        'notes': 'Feeds cnt-wax-percolation-derived-vfc (the closing '
                 'move): assumed 0.005 vs derived — the comparison '
                 'IS the evidence.',
        'enabled': True,
    },
    {
        'name': 'ferrite-chaining-in-wax',
        'display_name': 'Ferrite particle chaining in wax melt (L2)',
        'description': (
            'Do magnetite particles chain under a field in a wax '
            'melt? couplingLambda 12 from the documented arithmetic '
            'below; vf 0.12 (the validated regime).'
        ),
        'physics_ref': 'meso-dipolar-chaining',
        'system_json': json.dumps({'couplingLambda': 12.0,
                                   'volumeFraction': 0.12,
                                   'nParticles': 150}),
        'sampling_json': '{}',
        'integration_json': json.dumps({'steps': 6000, 'dt': 0.002,
                                        'seed': 1234}),
        'notes': 'lambda = mu0*m^2/(4*pi*d^3*kT): magnetite Ms '
                 '4.8e5 A/m, d = 20 nm -> m = Ms*pi*d^3/6 = '
                 '2.01e-18 A*m^2 -> lambda ~= 12 at 300 K [prov: '
                 'standard ferrofluid estimate; ~10 nm particles '
                 'give lambda ~1.5 and do NOT chain — size is the '
                 'knob]. Real ferrite is polydisperse; treat '
                 'thresholds as indicative.',
        'enabled': True,
    },
]

#: msci-26 L2/L3 scale rows: 'partial' until first execution lands
#: results on the model rows.
SEED_L2_L3_SCALE_ROWS = [
    {'name': 'carbon-nanotube@L2', 'material_name': 'carbon-nanotube',
     'scale_level': 2, 'scale_category': 'mesoscale',
     'definition_class': 'MesoModelDefinition',
     'definition_ref': 'cnt-percolation-threshold',
     'status': 'partial', 'derivation_method': 'coarse-grained',
     'parameters_json': json.dumps({
         'aspectRatioModeled': 100,
         'realCntAspectNote': 'real tubes ~1000: derived vf_c is an '
                              'upper bound (scales ~1/aspect)'}),
     'provenance_id': 'msci-26',
     'notes': 'The L2 rung that derives what L1 assumes.'},
    {'name': 'wax-ferrite@L2', 'material_name': 'wax-ferrite',
     'scale_level': 2, 'scale_category': 'mesoscale',
     'definition_class': 'MesoModelDefinition',
     'definition_ref': 'ferrite-chaining-in-wax',
     'status': 'partial', 'derivation_method': 'coarse-grained',
     'derived_from_name': 'wax-ferrite@L0',
     'parameters_json': json.dumps({'couplingLambda': 12.0,
                                    'particleDiameter_nm': 20}),
     'provenance_id': 'msci-26',
     'notes': 'Microstructure behind the tuned-magnetics goal.'},
    {'name': 'paraffin-wax@L3', 'material_name': 'paraffin-wax',
     'scale_level': 3, 'scale_category': 'atomistic',
     'definition_class': 'MDModelDefinition',
     'definition_ref': 'paraffin-bead-spring-melt',
     'status': 'partial', 'derivation_method': 'coarse-grained',
     'derived_from_name': 'paraffin-wax@L0',
     'parameters_json': json.dumps({'beadsPerChain': 10,
                                    'ch2PerBead': 3}),
     'provenance_id': 'msci-26',
     'notes': 'Coarse-grained chain rung; force-field MD is the '
              'named gap above it.'},
]

#: The CLOSING MOVE (knobs-and-suggestions — never rewire silently):
#: a VARIANT of the msci-23 wax percolation model whose threshold is
#: an objectRef into the L2-derived result. The assumed-0.005
#: original stays; the comparison IS the evidence.
SEED_DERIVED_VFC_MODELS = [
    {
        'name': 'cnt-wax-percolation-derived-vfc',
        'display_name': 'CNT in wax — percolation with the L2-DERIVED '
                        'threshold',
        'description': (
            'Same physics as cnt-wax-percolation, but '
            'percolationThreshold binds to the LIVE result of the '
            'L2 rod-network study instead of the 0.005 literature '
            'assumption. Compare the two models side by side.'
        ),
        'physics_ref': 'percolation-conductivity',
        'domain_json': json.dumps({
            'inclusion': {
                'volumeFraction': 0.02,
                'percolationThreshold': {
                    'kind': 'objectRef',
                    'className': 'MesoModelDefinition',
                    'name': 'cnt-percolation-threshold',
                    'path': 'last_result_json.percolationThreshold'},
            }}),
        'materials_json': json.dumps({
            'matrix': {'electricalConductivity': 1e-13},
            'inclusion': {'electricalConductivity': 1e6}}),
        'boundary_conditions_json': '[]',
        'source_terms_json': '{}',
        'mesh_json': '{}',
        'solver_json': json.dumps({'transportExponent': 2.0}),
        'notes': 'Executes ONLY after the L2 study has run (the '
                 'objectRef refuses honestly on an empty result) — '
                 'the dependency is the point.',
        'enabled': True,
    },
]
