"""
@module materialsScience.wax_multiscale_seed

Seed: the 'wax-multiscale' MultiScaleSimulationDefinition — the
materials-science multiscale model assembled PURELY FROM CONFIGURATION
nesting abstracted components (Dustin's directive, end to end):

    stage 1  subModel      -> the whole 'wax-derivation' msim runs as a
                              nested component (recursive composition)
    stage 2  engineModel   -> 'wax-thermal-continuum' (FEM numerical
                              homogenization, inputs OBJECT-BOUND to
                              live rows), intent calibrate, derives the
                              effective conductivity onward
    stage 3  engineModel   -> 'paraffin-quantum-energy' (DFT molecular
                              SCF via the local->worker ladder), intent
                              validate — quantum-level evidence

A NEW msim row (seeds are idempotent-by-name: editing wax-derivation's
seed would not reach existing volumes, and that msim stays exactly as
Dustin tested it).

@consumers
  - polariServer._seedSimulations (seed pair)
  - the msim page at /multi-scale-sim/wax-multiscale
"""

import json

MSIM_WAX_MULTISCALE = 'wax-multiscale'

SEED_WAX_MULTISCALE_MSIMS = [{
    'name': MSIM_WAX_MULTISCALE,
    'profile_ref': 'materials-science',
    'description': (
        'The materials-science multiscale model as PURE CONFIGURATION '
        'nesting abstracted components: the whole wax-derivation '
        'multi-scale simulation runs as a nested sub-model, its '
        'winner feeds a configured FEM homogenization model (inputs '
        'bound to live material rows), and a configured DFT model '
        'attaches quantum-level evidence — three scales, zero new '
        'code, every piece an object you can open and re-configure.'
    ),
    'member_simulation_refs_json': '[]',
    'coupling_refs_json': '[]',
    'primary_simulation_ref': '',
    'stages_json': json.dumps([
        {
            'key': 'formulation-screening',
            'label': 'Derive the formulation (nested wax-derivation)',
            'kind': 'subModel',
            'intent': 'search',
            'msimRef': 'wax-derivation',
            'gate': {
                'failReason': 'The nested wax-derivation has not '
                              'achieved a winning formulation yet — '
                              'open its page to see exactly which '
                              'stage blocks and why.',
            },
            'derive': {
                'params': {
                    'derived.winnerScore':
                        'sub.formulation-screening.candidate.score',
                    'derived.processingWindowC':
                        'sub.formulation-screening.thermal.windowC',
                },
            },
        },
        {
            'key': 'continuum-verify',
            'label': 'Verify the continuum scale (FEM homogenization)',
            'kind': 'engineModel',
            'intent': 'calibrate',
            'modelRef': 'wax-thermal-continuum',
            'gate': {
                'failReason': 'The FEM homogenization refused (missing '
                              'inputs or engine unavailable) or fell '
                              'outside the Voigt/Reuss bounds.',
            },
            'derive': {
                'params': {
                    'derived.effectiveK': 'model.effectiveK',
                },
            },
        },
        {
            'key': 'quantum-evidence',
            'label': 'Attach quantum-level evidence (DFT)',
            'kind': 'engineModel',
            'intent': 'validate',
            'modelRef': 'paraffin-quantum-energy',
            'gate': {
                'failReason': 'No reachable DFT layer (local pyscf or '
                              'the msci-engines worker) — capability '
                              'suggestions name the knob.',
            },
        },
    ]),
    'panels_json': json.dumps([
        {
            'kind': 'explainer',
            'stageKey': 'formulation-screening',
            'title': 'A multiscale model made of multiscale components',
            'body': (
                'This composition writes NO new physics: stage 1 runs '
                'the entire wax-derivation multi-scale simulation as a '
                'nested sub-model (open it from the stage chip); stage '
                '2 executes a configured FEM homogenization whose '
                'material conductivities are BOUND to live material '
                'rows — edit the row, the model reads the new value; '
                'stage 3 executes a configured DFT calculation for '
                'quantum-level evidence through the local-or-worker '
                'ladder. Every stage is an object: the nested msim, '
                'the two model definitions, and their template catalog '
                'are all open-and-edit configuration.'
            ),
            'showSearchSpace': False,
            'showGate': True,
            'showDerive': True,
            'showConditionMap': False,
            'showMeltLine': False,
        },
    ]),
    'display_ref': '',
    'compare_run_policy_json': '{}',
    'enabled': True,
}]
