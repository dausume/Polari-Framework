"""
@cross-cutting
@module simulations.simulation_intents
@tags @xc:bindings

Simulation INTENTS — "what is this simulation for?" as machine-readable
data. Declared first (on SimulationDefinition.intent for a space's own
purpose, and per stage for its role in a composition), an intent:

  * gives the authoring wizard a short, concrete required-definitions
    CHECKLIST instead of an open-ended editor (the normal-people rule),
  * declares what the simulation PRODUCES, and
  * constrains where it can legally plug into a multi-scale composition
    (validate_composition enforces the coherence rules with plain-
    language reasons — never silent misbehavior).

The intents are mostly VARIATIONS of existing machinery, not separate
engines: Search/Feasibility/Optimize/Calibrate are the one solution-
search orchestrator with different candidate generators and selection
rules; Validate is the gate engine pointed at invariants; Compare is the
scenario-comparison overlay.

@consumers
  - simulations.simulation_api (GET /intents, POST validate-composition)
  - frontend Phase-5 wizard + Configure rail
@see /OVERLAP_MAP.md
"""

from typing import Any, Dict, List

from simulations.simulation_runner import _parse_json
from simulations.multi_scale_stages import parse_stages

# Product-bearing intents may be `derive` sources (they end with a
# solution artifact later stages can build initial conditions from).
PRODUCT_BEARING = ('search', 'feasibility', 'optimize', 'calibrate')
# Continuous intents step live and expose sampleable trajectories/fields.
CONTINUOUS = ('observe',)

INTENTS: Dict[str, Dict[str, Any]] = {
    'observe': {
        'label': 'Observe',
        'question': 'See what happens.',
        'requires': ['spaces & states', 'step solutions',
                     'initial conditions', 'a scene to watch it in'],
        'produces': 'trajectories / fields over time',
        'plugPoints': 'co-steps live in a composition; its fields are '
                      'sampleable sources for couplings',
    },
    'search': {
        'label': 'Solution search',
        'question': 'Find conditions where something is possible.',
        'requires': ['everything Observe needs',
                     'a candidate space (parameters + ranges)',
                     'a valid-solution condition (gate solution)'],
        'produces': 'one achieved solution + its derived properties',
        'plugPoints': 'first-principles stage; `derive` feeds downstream '
                      'initial conditions',
    },
    'feasibility': {
        'label': 'Feasibility map',
        'question': 'Map the whole envelope where a condition holds.',
        'requires': ['everything Search needs (the search keeps going '
                     'instead of stopping at the first valid solution)'],
        'produces': 'a validity region + its boundary',
        'plugPoints': 'constrains downstream choice interfaces (choices '
                      'outside the envelope are disabled with reason + data)',
    },
    'optimize': {
        'label': 'Optimize toward a target',
        'question': 'Get as close as possible to a goal.',
        'requires': ['everything Search needs',
                     'an objective / score equation',
                     'a stopping budget or tolerance'],
        'produces': 'best-found solution + its score history',
        'plugPoints': "Search's slot; re-enterable to keep improving",
    },
    'calibrate': {
        'label': 'Calibrate to data',
        'question': 'Tune the model until it matches measured data.',
        'requires': ['a reference dataset binding',
                     'the tunable parameter set',
                     'a fit objective (mismatch measure)'],
        'produces': 'calibrated parameters',
        'plugPoints': 'upstream of everything — writes back into the '
                      "space's own definition",
    },
    'validate': {
        'label': 'Validate lawful behavior',
        'question': 'Prove the model obeys what it must (conservation, '
                    'convergence, reference results).',
        'requires': ['invariant / expectation definitions with tolerances'],
        'produces': 'pass/fail + drift metrics',
        'plugPoints': 'a trust gate on a space; compositions may require '
                      'passing validations before couplings are trusted',
    },
    'sensitivity': {
        'label': 'Sensitivity / robustness',
        'question': 'Which inputs matter, and how fragile is the outcome?',
        'requires': ['a parameter perturbation spec', 'output metrics'],
        'produces': 'sensitivity rankings / tolerance bands',
        'plugPoints': 'guides coupling fidelity and resolution choices — '
                      'the evidence node consolidation needs',
    },
    'compare': {
        'label': 'Scenario comparison',
        'question': 'What differs between A and B?',
        'requires': ['variant parameter/IC bundles', 'contrast metrics'],
        'produces': 'time-aligned trajectories + deltas',
        'plugPoints': 'an ANALYSIS OVERLAY only — causally independent '
                      'runs; never a member of the causal chain',
    },
}

VALID_INTENTS = tuple(INTENTS.keys())


def intents_catalog() -> Dict[str, Any]:
    """The taxonomy for the wizard UI, plus the rule groups."""
    return {
        'intents': INTENTS,
        'productBearing': list(PRODUCT_BEARING),
        'continuous': list(CONTINUOUS),
    }


def validate_composition(manager, msim) -> List[Dict[str, str]]:
    """Check a MultiScaleSimulationDefinition against the coherence
    rules. Returns findings [{level: 'error'|'warning', message}] —
    empty when coherent. Every message is written for a non-specialist.
    """
    findings: List[Dict[str, str]] = []

    def err(msg):
        findings.append({'level': 'error', 'message': msg})

    def warn(msg):
        findings.append({'level': 'warning', 'message': msg})

    sim_intents: Dict[str, str] = {}
    for r in (manager.objectTables.get('SimulationDefinition', {}) or {}).values():
        sim_intents[getattr(r, 'name', '')] = (
            getattr(r, 'intent', '') or 'observe')

    members = _parse_json(
        getattr(msim, 'member_simulation_refs_json', '') or '[]', [])
    members = [m for m in members if isinstance(m, str)]
    for m in members:
        if m not in sim_intents:
            err(f'Member simulation "{m}" does not exist.')

    stages = parse_stages(msim)
    for stage in stages:
        key = stage.get('key', '?')
        stage_intent = stage.get('intent') or (
            'observe' if stage.get('kind') == 'coStep' else 'search')
        if stage_intent not in VALID_INTENTS:
            err(f'Stage "{key}": unknown intent "{stage_intent}". '
                f'Valid intents: {", ".join(VALID_INTENTS)}.')
            continue

        if stage_intent == 'compare':
            err(f'Stage "{key}": scenario comparison can never be a stage '
                f'— comparison runs are causally independent. Use the '
                f'composition\'s scenario-comparison policy instead.')

        sim_ref = (stage.get('simulationRef')
                   or stage.get('primarySimulationRef') or '')
        if sim_ref and sim_ref not in sim_intents:
            err(f'Stage "{key}" references simulation "{sim_ref}", which '
                f'does not exist.')

        # Rule: derive sources must be product-bearing.
        if stage.get('derive') and stage_intent not in PRODUCT_BEARING:
            err(f'Stage "{key}" feeds later stages\' initial conditions '
                f'(it has a derive map), but its intent '
                f'"{stage_intent}" does not produce a solution. Use a '
                f'product-bearing intent: '
                f'{", ".join(PRODUCT_BEARING)}.')

        # Rule: search-family intents need a candidate space (or at
        # least a gate for a single-shot search).
        if stage_intent in ('search', 'feasibility', 'optimize'):
            if not (stage.get('search') or {}).get('candidates') \
                    and not (stage.get('gate') or {}).get('solutionRef'):
                err(f'Stage "{key}" has intent "{stage_intent}" but '
                    f'defines neither candidates to try (search.candidates) '
                    f'nor a valid-solution condition (gate). Define at '
                    f'least the gate.')

        # Rule: co-stepping needs a continuous simulation.
        if stage.get('kind') == 'coStep':
            sim_intent = sim_intents.get(sim_ref, 'observe')
            if sim_intent not in CONTINUOUS:
                warn(f'Stage "{key}" co-steps "{sim_ref}", whose own '
                     f'intent is "{sim_intent}" — co-stepping expects a '
                     f'continuous (Observe) simulation. This may still '
                     f'work, but check that it is what you mean.')

        # Rule: the stage's role must be plausible for the sim's own
        # declared purpose (permissive: warn, don't block).
        if sim_ref:
            sim_intent = sim_intents.get(sim_ref, 'observe')
            if (stage_intent in PRODUCT_BEARING
                    and sim_intent not in PRODUCT_BEARING + CONTINUOUS):
                warn(f'Stage "{key}" uses "{sim_ref}" as a '
                     f'{stage_intent} subject, but that simulation '
                     f'declares intent "{sim_intent}". Confirm it '
                     f'defines what {stage_intent} needs.')

    # Rule: couplings must exist and reference member sims.
    couplings = _parse_json(
        getattr(msim, 'coupling_refs_json', '') or '[]', [])
    coupling_rows = {
        getattr(c, 'name', ''): c
        for c in (manager.objectTables.get(
            'SimulationCouplingDefinition', {}) or {}).values()
    }
    for cname in couplings:
        if not isinstance(cname, str):
            continue
        row = coupling_rows.get(cname)
        if row is None:
            err(f'Coupling "{cname}" does not exist.')
            continue
        for side, ref in (('source', getattr(row, 'source_simulation_ref', '')),
                          ('target', getattr(row, 'target_simulation_ref', ''))):
            if ref and members and ref not in members:
                warn(f'Coupling "{cname}"\'s {side} simulation "{ref}" is '
                     f'not a member of this composition — add it to the '
                     f'members list so its runs and scenes are managed here.')

    return findings
