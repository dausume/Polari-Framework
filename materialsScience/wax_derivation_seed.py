"""
@module materialsScience.wax_derivation_seed

Seed: the 'wax-derivation' MultiScaleSimulationDefinition — the MVW wax
derivation as a REAL multi-scale simulation on the msim page (the
object-coherence fix Dustin asked for: "I do not see any page for the
multi-scale simulations you were supposed to have used to derive the
waxes").

One product-bearing stage: 'formulation-screening', kind
`formulationSearch`, driving the seeded 'wax-derivation-screening'
FormulationSearchDefinition through the standard stage-search endpoint
(the executor in materialsScience.formulation_stage reshapes the report
into the stage-search contract, so the existing Search-for-a-solution
UI renders it unchanged). The staged-fidelity ladder (rules-of-mixtures
screening -> FEM shortlist verification -> DFT evidence suggestions)
lives on the search definition; the family's optional
'evidence-attachment' stage is deliberately NOT instantiated — evidence
arrives as suggestions on every run, and profile conformance reports
the unfilled optional slot as an honest note.

Family: profile_ref='materials-science' (multi_scale_profile_seed).
"""

import json

MSIM_WAX_DERIVATION = 'wax-derivation'
_SEARCH_REF = 'wax-derivation-screening'

SEED_WAX_DERIVATION_MSIMS = [{
    'name': MSIM_WAX_DERIVATION,
    'profile_ref': 'materials-science',
    'description': (
        'The MVW (minimum-viable-wax filament) derivation as a '
        'multi-scale simulation: screen fossil-free formulations toward '
        'the printable-wax targets with rules of mixtures under the '
        'thermal no-volatiles gate, FEM-verify the shortlist by '
        'numerical homogenization, and collect DFT-evidence suggestions '
        'for the winners. Configure every knob at the '
        f"'{_SEARCH_REF}' FormulationSearchDefinition."
    ),
    'member_simulation_refs_json': '[]',
    'coupling_refs_json': '[]',
    'primary_simulation_ref': '',
    'stages_json': json.dumps([
        {
            'key': 'formulation-screening',
            'label': 'Screen formulations (rules of mixtures + FEM '
                     'shortlist verify)',
            'kind': 'formulationSearch',
            'intent': 'search',
            'formulationSearchRef': _SEARCH_REF,
            'gate': {
                'failReason': 'No formulation met the wax-filament '
                              'targets within the additive pool, caps, '
                              'and sourcing policy. The gap analysis '
                              'names each unmet target and which '
                              'additives could still move it.',
            },
            # Winner facts for downstream consumers (e.g. the print sim
            # will read the derived processing window + score).
            'derive': {
                'params': {
                    'derived.winnerScore': 'candidate.score',
                    'derived.meetsTargets': 'candidate.meets',
                    'derived.processingWindowC': 'thermal.windowC',
                },
            },
        },
    ]),
    'panels_json': json.dumps([
        {
            'kind': 'explainer',
            'stageKey': 'formulation-screening',
            'title': 'How the wax derivation works',
            'body': (
                'The search steps batch-by-batch from the pure base wax '
                'toward the target profile, trying one loading move per '
                'batch and keeping the best scorer (steps halve when '
                'progress stalls, so it lands inside tight bands). '
                'Every candidate is scored by rules of mixtures over '
                'the quantified additive effects — properties without '
                'quantified effects are reported as unpredictable, '
                'never guessed. Printing candidates must also pass the '
                'thermal window gate: the blend must melt through '
                'without ANY component reaching its smoking point. '
                'The top shortlist is then verified by FEM numerical '
                'homogenization (a real unit-cell solve, refused '
                'honestly when inputs are missing), and quantum-level '
                'DFT evidence is SUGGESTED for winners — never run '
                'automatically. Fossil-derived additives are excluded '
                'by default (sourcing policy knob; they remain '
                'available as opt-in reference benchmarks).'
            ),
            'showSearchSpace': False,
            'showGate': True,
            'showDerive': True,
            'showConditionMap': False,
            'showMeltLine': False,
        },
        {
            'kind': 'formulationSearch',
            'stageKey': 'formulation-screening',
            'searchRef': _SEARCH_REF,
        },
    ]),
    'display_ref': '',
    'compare_run_policy_json': '{}',
    'enabled': True,
}]
