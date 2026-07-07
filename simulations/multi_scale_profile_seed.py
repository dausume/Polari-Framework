"""
@module simulations.multi_scale_profile_seed

Seed data for the two MultiScaleSimulationProfile families:

  - 'pendulum-in-wind' — the 1st multi-scale test case, retrofit as the
    proof the profile abstraction generalizes (its shape was previously
    inlined as JSON literals in multi_scale_seed.py).
  - 'materials-science' — the 2nd test case's family: the 5 scale
    levels (imported from materialsScience.materials_basis so the
    taxonomy has ONE home), the staged-fidelity ladder
    (rules-of-mixtures screening -> FEM verification -> DFT evidence,
    engine keys from materialsScience.scale_execution.ENGINE_REGISTRY),
    and the formulation-search stage shapes the wax-derivation msim
    instantiates.

Same registration pattern as the other sim seeds: polariServer wires
SEED_MSIM_PROFILES into _seedSimulations' seed_pairs.
"""

import json

from materialsScience.materials_basis import SCALE_LEVELS
from materialsScience.scale_execution import ENGINE_REGISTRY

# Sanity anchors: the ladder below must only name registered engines.
_FEM_HOMOG = 'fem.effective-conductivity'
_FEM_CONDUCTION = 'fem.conduction'
_DFT_ENERGY = 'dft.molecular-energy'
assert {_FEM_HOMOG, _FEM_CONDUCTION, _DFT_ENERGY} <= set(ENGINE_REGISTRY), (
    'profile seed names engines missing from ENGINE_REGISTRY'
)

_MSCI_UNITS = {
    'experimental': 'mm-m', 'continuum': 'µm-mm', 'mesoscale': 'nm-µm',
    'atomistic': 'Å-nm', 'quantum': 'Å',
}

SEED_MSIM_PROFILES = [
    {
        'name': 'pendulum-in-wind',
        'display_name': 'Pendulum in Wind (precondition-proof family)',
        'description': (
            'Multi-scale simulations whose macro dynamics only run after '
            'a micro-conditions space PROVES a physical precondition and '
            'derives the macro initial conditions from the proof (the '
            'condensed-ball pendulum is the reference member).'
        ),
        'scale_levels_json': json.dumps([
            {'key': 'micro-conditions', 'label': 'Material micro-conditions '
             '(condensation space)', 'units': 'K, Pa', 'order': 0},
            {'key': 'macro-dynamics', 'label': 'Macroscopic dynamics '
             '(pendulum + wind field)', 'units': 'm, s, N', 'order': 1},
        ]),
        'stage_templates_json': json.dumps([
            {'key': 'precondition-search', 'label':
             'Prove the precondition by searching conditions',
             'kind': 'runToCompletion', 'intent': 'search',
             'required': True,
             'slots': {'simulationRef': 'the space that proves the '
                       'precondition', 'gate': 'no-code pass/fail over the '
                       'space results', 'derive': 'gate outputs -> the next '
                       "stage's initial conditions"}},
            {'key': 'live-coupled', 'label':
             'Run the macro dynamics live against coupled sources',
             # 'observe' per the msim intents taxonomy: a coStep stage
             # watches coupled spaces evolve, it is not product-bearing.
             'kind': 'coStep', 'intent': 'observe', 'required': True,
             'slots': {'primarySimulationRef': 'the driven space',
                       'couplingRefs': 'the sample->inject bindings'}},
        ]),
        'fidelity_ladder_json': json.dumps([
            {'rung': 1, 'level': 'micro-conditions',
             'engines': ['no-code matrix equations (analytic cooling + '
                         'melt line)'],
             'costClass': 'cheap', 'purpose': 'screening'},
        ]),
        'panel_roster_json': json.dumps([
            {'kind': 'selector', 'slot': 'choose the subject substance',
             'required': True},
            {'kind': 'ic', 'slot': 'initial conditions from the choice',
             'required': True},
            {'kind': 'explainer', 'slot': "the stage's narrative + live "
             'config facts', 'required': True},
            {'kind': 'graph', 'slot': 'per-stage data over time',
             'required': True},
            {'kind': 'scene', 'slot': 'the spaces themselves',
             'required': True},
        ]),
        'coupling_shapes_json': json.dumps([
            {'from': 'micro-conditions', 'to': 'macro-dynamics',
             'mechanism': 'derive',
             'notes': "the proof gate's outputs become the macro stage's "
                      'initial conditions'},
            {'from': 'environment', 'to': 'macro-dynamics',
             'mechanism': 'coupling',
             'notes': 'live sample->inject while co-stepping (wind force)'},
        ]),
        'default_search_policy_json': json.dumps({
            'stopPolicy': 'firstValid',
        }),
        'enabled': True,
    },
    {
        'name': 'materials-science',
        'display_name': 'Materials Science (staged-fidelity formulation family)',
        'description': (
            'Multi-scale material simulations over the 5-level resolution '
            'ladder (experimental -> continuum -> mesoscale -> atomistic '
            '-> quantum). Formulation searches screen cheaply with rules '
            'of mixtures, verify shortlists with FEM homogenization, and '
            'attach DFT evidence to winners only — every rung an explicit '
            'knob, every refusal evidence-bearing.'
        ),
        # ONE home for the level taxonomy: materials_basis.SCALE_LEVELS.
        'scale_levels_json': json.dumps([
            {'key': label, 'label': label.capitalize(),
             'units': _MSCI_UNITS.get(label, ''), 'order': level}
            for level, label in sorted(SCALE_LEVELS.items())
        ]),
        'stage_templates_json': json.dumps([
            {'key': 'formulation-screening', 'label':
             'Screen candidate formulations against property targets',
             # Optional since msci-19: a member may screen DIRECTLY
             # (this template) or by NESTING a derivation msim (the
             # sub-derivation template below) — conformance v1 has no
             # recursive descent, so either shape satisfies the family.
             'kind': 'formulationSearch', 'intent': 'search',
             'required': False,
             'slots': {'formulationSearchRef': 'the FormulationSearchDefinition '
                       'carrying targets + knobs + sourcing policy',
                       'gate': 'optional no-code verdict over the winner',
                       'derive': 'winner components/properties -> later '
                       'stages'}},
            {'key': 'evidence-attachment', 'label':
             "Attach scale evidence to the winners' scale definitions",
             # 'validate' per the intents taxonomy. Optional: a member
             # may instead surface evidence via the search run's DFT
             # suggestions (conformance reports the note honestly).
             'kind': 'runToCompletion', 'intent': 'validate',
             'required': False,
             'slots': {'gate': 'scale-presence check over the winner '
                       'components'}},
            # msci-16/19: the abstracted-component stage shapes.
            {'key': 'sub-derivation', 'label':
             'Run a whole derivation msim as a nested component',
             'kind': 'subModel', 'intent': 'search', 'required': False,
             'slots': {'msimRef': 'the nested '
                       'MultiScaleSimulationDefinition',
                       'derive': "the child's derived values -> later "
                       'stages'}},
            {'key': 'continuum-verification', 'label':
             'One-shot FEM solve over a configured model definition',
             'kind': 'engineModel', 'intent': 'calibrate',
             'required': False,
             'slots': {'modelRef': 'the FEMModelDefinition',
                       'derive': 'model outputs -> later stages'}},
            {'key': 'quantum-evidence', 'label':
             'One-shot DFT calculation over a configured model '
             'definition',
             'kind': 'engineModel', 'intent': 'validate',
             'required': False,
             'slots': {'modelRef': 'the DFTModelDefinition'}},
        ]),
        'fidelity_ladder_json': json.dumps([
            # 'templates' names the EngineModelTemplate catalog rows
            # that implement each rung (msci-15) — the ladder is now
            # template-referencing, not just engine-key-referencing.
            {'rung': 1, 'level': 'experimental',
             'engines': ['rules-of-mixtures'], 'templates': [],
             'costClass': 'cheap', 'purpose': 'screening'},
            {'rung': 2, 'level': 'continuum',
             'engines': [_FEM_HOMOG, _FEM_CONDUCTION],
             'templates': ['fem-effective-conductivity',
                           'fem-steady-conduction'],
             'costClass': 'moderate', 'purpose': 'verification'},
            {'rung': 3, 'level': 'quantum',
             'engines': [_DFT_ENERGY],
             'templates': ['dft-molecular-energy', 'dft-bulk-structure',
                           'dft-total-energy'],
             'costClass': 'expensive', 'purpose': 'evidence'},
        ]),
        'panel_roster_json': json.dumps([
            {'kind': 'formulationSearch', 'slot': 'configure/run the search, '
             'winners + trajectory (optional: a nested derivation '
             'carries its own)', 'required': False},
            {'kind': 'explainer', 'slot': 'the staged-fidelity story',
             'required': True},
            {'kind': 'graph', 'slot': 'refinement trajectory over batches',
             'required': False},
            {'kind': 'display', 'slot': 'the materials-basis browser',
             'required': False},
        ]),
        'coupling_shapes_json': json.dumps([
            {'from': 'experimental', 'to': 'continuum',
             'mechanism': 'derive',
             'notes': 'winner formulations promote to level-1 '
                      'MaterialScaleDefinition rows with lineage'},
        ]),
        'default_search_policy_json': json.dumps({
            'stopPolicy': 'exhaustive',
            'sourcingPolicy': 'fossil-free-local',
        }),
        'enabled': True,
    },
]


def upgrade_profile_rows(manager):
    """Config-knob upgrade for UNTOUCHED profile rows (the msim-row
    upgrade's sibling): profiles are reference data — when a live row's
    description still matches its seed verbatim (the admin hasn't made
    it theirs), refresh the config blobs so template/ladder additions
    reach existing volumes. A customized description = hands off."""
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'MultiScaleSimulationProfile', {}) or {}
    rows_by_name = {getattr(r, 'name', None): r for r in (
        table.values() if isinstance(table, dict) else table)}
    blob_fields = ('scale_levels_json', 'stage_templates_json',
                   'fidelity_ladder_json', 'panel_roster_json',
                   'coupling_shapes_json', 'default_search_policy_json')
    for seed in SEED_MSIM_PROFILES:
        row = rows_by_name.get(seed.get('name'))
        if row is None:
            continue
        if (getattr(row, 'description', '') or '') != seed['description']:
            print(f'[SeedSimulations] profile "{seed.get("name")}" '
                  'description customized; upgrade skipped', flush=True)
            continue
        changed = [f for f in blob_fields
                   if (getattr(row, f, '') or '') != seed.get(f, '')]
        if not changed:
            continue
        for f in changed:
            setattr(row, f, seed.get(f, ''))
        try:
            manager.db.saveInstanceInDB(row)
            print(f'[SeedSimulations] Upgraded profile '
                  f'"{seed.get("name")}": {", ".join(changed)}',
                  flush=True)
        except Exception as e:
            print(f'[SeedSimulations] profile "{seed.get("name")}" '
                  f'upgrade save failed: {e}', flush=True)
