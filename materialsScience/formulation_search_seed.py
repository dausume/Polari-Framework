"""
@module materialsScience.formulation_search_seed

Seed: the 'wax-derivation-screening' FormulationSearchDefinition — the
MVW (minimum-viable-wax filament) derivation as a configurable OBJECT
(previously only reachable as POST /api/msci/composites/refine knobs).
The wax-derivation msim's formulationSearch stage points here.

Base properties are MANUALLY-ENTERED PRIORS (the worksheet at suite
root, MISSING_MATERIALS_DATA.md Priority 2, tracks replacing them with
measured values); the same set the msci-10/11 live verifications used.
They are echoed into every run's assumptions — nothing is invented
silently.

The FEM verify rung ships with matrixK/inclusionK for the components
with literature-order conductivities already used by the msci-4
homogenization seeds (beeswax matrix 0.25 W/mK, carnauba 0.30); grog
(clay, ~1.0 literature-order) included. Additives without a k refuse
honestly per candidate — the refusal names the exact knob to fill.
"""

import json

SEED_FORMULATION_SEARCHES = [{
    'name': 'wax-derivation-screening',
    'display_name': 'MVW wax derivation (screening + refine)',
    'description': (
        'Derive a 3D-printable fossil-free wax formulation toward the '
        'minimum-viable-wax filament targets: batch-incremental '
        'refinement over the seeded additive pool, thermal-window gated '
        'for printing (no component may smoke inside the melt window), '
        'FEM homogenization verifying the shortlist, DFT evidence '
        'suggested for winners. Base properties are worksheet priors '
        '(MISSING_MATERIALS_DATA.md), not measurements.'
    ),
    'target_profile_id': 'profile-min-viable-wax-filament',
    'targets_json': '[]',
    'base_material_name': 'beeswax',
    'base_properties_json': json.dumps({
        'ShrinkageRate': 3.0,
        'ShoreHardness': 10.0,
        'LayerAdhesionStrength': 0.15,
        'FlexuralModulus': 40.0,
    }),
    'additive_pool_json': '[]',
    'sourcing_policy': 'fossil-free-local',
    'mode': 'refine',
    'knobs_json': json.dumps({
        'loadingStep': 2.5,
        'perAdditiveCap': 20.0,
        'maxTotalLoad': 30.0,
        'maxBatches': 40,
    }),
    'process': '3d-print',
    'thermal_knobs_json': '{}',
    'fidelity_stages_json': json.dumps({
        'screening': {'engine': 'rules-of-mixtures'},
        'verify': {
            'engine': 'fem.effective-conductivity',
            'shortlistN': 5,
            'property': 'thermalConductivity',
            # Literature-order values, same provenance as the msci-4
            # homogenization seeds; wt% treated as vol% (flagged on
            # every verified result).
            'matrixK': 0.25,
            'inclusionK': {
                'Carnauba Wax': 0.30,
                'Grog (1 um)': 1.0,
                'Pine Rosin': 0.15,
            },
            'refine': 5,
        },
        'evidence': {
            'engine': 'dft.molecular-energy',
            'onWinnersOnly': True,
            'autoRun': False,
        },
    }),
    'results_keep_top_n': 25,
    'enabled': True,
}]
