"""
@cross-cutting
@module simulations.multi_scale_stages
@tags @xc:bindings

Multi-scale progression stages — the no-code stage/gate model on
MultiScaleSimulationDefinition.stages_json.

A stage is either:
  * runToCompletion — a precondition space that must run and PROVE
    something before later stages unlock (e.g. the material simulation
    finding temp/pressure where the substance condenses into a solid
    ball and analyzing the ball size), or
  * coStep — live coupled stepping (the wind+pendulum mode).

A runToCompletion stage's GATE is a no-code SolutionDefinition evaluated
over the stage run's results. Deliberate reuse: the gate executes through
the SAME SolutionExecutionEngine flow as the initial-conditions validator
(simulation_runner.validate_initial_conditions) — flattened
`<class>.<field>` context in, outcome/reason/derived values out — so
gates are authored in the existing no-code editor with a contract users
already know. `derive` then maps the gate's outputs (e.g. proven
ball_mass/ball_radius) onto later stages' parameters/ICs.

Gate solution contract (terminal context):
  * outcome — 'valid' | 'complete' | 'pass' → gate passes (any other
    value, or absent → not yet complete)
  * reason  — human-readable explanation (surfaced verbatim in the
    stage stepper; write it for a non-specialist)
  * derivedValues — optional dict of named outputs; when absent, the
    whole final context serves as the output namespace for `derive`.

@consumers
  - simulations.simulation_api (stage-gate endpoint)
  - frontend multi-scale page (stage stepper)
@see /OVERLAP_MAP.md
"""

from typing import Any, Dict, List, Optional

from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine
from polariNoCode.stepping import StepConfig
from simulations.simulation_runner import (
    _extract_final_context,
    _load_solution_data,
    _parse_json,
)

GATE_PASS_OUTCOMES = ('valid', 'complete', 'pass')


def parse_stages(msim_def) -> List[Dict[str, Any]]:
    """The definition's stages list ([] when unset/malformed). An empty
    list means a single implicit coStep stage over the primary sim."""
    raw = getattr(msim_def, 'stages_json', '') or '[]'
    parsed = _parse_json(raw, [])
    if not isinstance(parsed, list):
        return []
    return [s for s in parsed if isinstance(s, dict) and s.get('key')]


def find_stage(msim_def, stage_key: str) -> Optional[Dict[str, Any]]:
    for s in parse_stages(msim_def):
        if s.get('key') == stage_key:
            return s
    return None


def evaluate_stage_gate(manager, stage: Dict[str, Any], run) -> Dict[str, Any]:
    """Run a stage's gate solution against the stage run's current
    results and return a structured verdict:

        { complete, hasGate, reason, derivedValues, error }

    No gate declared → complete as soon as the run has any recorded
    step (a stage with nothing to prove just has to have run).
    """
    gate = stage.get('gate') or {}
    gate_ref = gate.get('solutionRef') or ''
    last_step = int(getattr(run, 'last_recorded_step', 0) or 0)
    if not gate_ref:
        # THE "defined AND achieved" rule: a stage that later stages
        # derive from (it has a `derive` map) is a FIRST-PRINCIPLES
        # stage — its valid-solution condition must be DEFINED (a gate
        # solution authored) and ACHIEVED (that gate passing on a real
        # run) before downstream initial conditions are legitimate.
        # Merely having run is not enough.
        if stage.get('derive'):
            return {
                'complete': False,
                'hasGate': False,
                'reason': ('This stage feeds later stages\' initial '
                           'conditions, but its valid-solution condition '
                           '(gate) is not defined yet. Author a gate '
                           'solution in the no-code editor first.'),
                'derivedValues': None,
                'error': None,
            }
        return {
            'complete': last_step > 0,
            'hasGate': False,
            'reason': '' if last_step > 0 else 'Stage has not run yet.',
            'derivedValues': None,
            'error': None,
        }

    sdata = _load_solution_data(manager, gate_ref)
    if sdata is None:
        return {
            'complete': False, 'hasGate': True, 'reason': '',
            'derivedValues': None,
            'error': f"gate solution '{gate_ref}' not found",
        }

    flat = flatten_stage_results(manager, stage, run)
    engine = SolutionExecutionEngine(manager=manager)
    try:
        trace = engine.execute(
            solution_data=sdata,
            input_params={},
            config=StepConfig(mode='step', record_context=True),
            target_runtime='python_backend',
            instance_fields=flat,
        )
    except Exception as exc:
        return {
            'complete': False, 'hasGate': True, 'reason': '',
            'derivedValues': None,
            'error': f'{type(exc).__name__}: {exc}',
        }
    if trace.status != 'completed':
        err = getattr(trace, 'error_summary', None) or 'engine error'
        return {
            'complete': False, 'hasGate': True, 'reason': '',
            'derivedValues': None, 'error': str(err),
        }

    final = _extract_final_context(trace)
    outcome = (str(final.get('outcome') or '')).strip().lower()
    complete = outcome in GATE_PASS_OUTCOMES
    derived = final.get('derivedValues')
    if not isinstance(derived, dict):
        # Whole final context doubles as the output namespace, so simple
        # gates don't need an explicit derivedValues mapping node.
        derived = {k: v for k, v in final.items()
                   if k not in ('outcome', 'reason')}
    return {
        'complete': complete,
        'hasGate': True,
        'reason': str(final.get('reason') or '').strip(),
        'derivedValues': derived,
        'error': None,
    }


def flatten_stage_results(manager, stage: Dict[str, Any], run) -> Dict[str, Any]:
    """The gate's evaluation context — same flattening convention as the
    IC validator, but over the stage run's LATEST rows:

      * `<ClassName>.<field>` for every participating class's most
        recent persisted row
      * `params.<key>` from the stage sim's parameters_json
      * `run.last_recorded_step`, `run.status`, `participating_classes`
    """
    sim_ref = stage.get('simulationRef') or getattr(run, 'simulation_ref', '')
    sim_def = _find_by_name(manager, 'SimulationDefinition', sim_ref)
    flat: Dict[str, Any] = {}
    participating: List[str] = []
    if sim_def is not None:
        participating = [
            c for c in _parse_json(
                getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]', []
            ) if isinstance(c, str)
        ]
        params = _parse_json(getattr(sim_def, 'parameters_json', '{}') or '{}', {})
        if isinstance(params, dict):
            for k, v in params.items():
                flat[f'params.{k}'] = v

    run_name = getattr(run, 'name', '')
    skip = {'manager', 'branch', 'inTree', 'polariId'}
    for cls_name in participating:
        latest, latest_step = None, -1
        for inst in (manager.objectTables.get(cls_name, {}) or {}).values():
            if getattr(inst, 'simulation_run_ref', '') != run_name:
                continue
            try:
                step_val = int(getattr(inst, 'step', -1) or -1)
            except (TypeError, ValueError):
                continue
            if step_val > latest_step:
                latest, latest_step = inst, step_val
        if latest is None:
            continue
        for k, v in vars(latest).items():
            if k.startswith('_') or k in skip:
                continue
            flat[f'{cls_name}.{k}'] = v

    flat['run.last_recorded_step'] = int(getattr(run, 'last_recorded_step', 0) or 0)
    flat['run.status'] = getattr(run, 'status', '')
    flat['participating_classes'] = participating
    return flat


def apply_derive(stage: Dict[str, Any], derived_values: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a stage's `derive` map against the gate's outputs into
    concrete override bundles for later stages:

        derive: {"params": {"<sim>.<param>": "<output key>"},
                 "fields": {"<sim>.<Class>.<field>": "<output key>"}}
        →       {"params": {"<sim>": {"<param>": value}},
                 "fields": {"<sim>": {"<Class>": {"<field>": value}}}}

    Output keys missing from derived_values are skipped (the gate simply
    didn't produce them — the page shows what was and wasn't derived).
    """
    derive = stage.get('derive') or {}
    derived_values = derived_values or {}
    out: Dict[str, Any] = {'params': {}, 'fields': {}}

    for target, source_key in (derive.get('params') or {}).items():
        if source_key not in derived_values or '.' not in str(target):
            continue
        sim, param = str(target).split('.', 1)
        out['params'].setdefault(sim, {})[param] = derived_values[source_key]

    for target, source_key in (derive.get('fields') or {}).items():
        parts = str(target).split('.')
        if source_key not in derived_values or len(parts) != 3:
            continue
        sim, cls, field = parts
        out['fields'].setdefault(sim, {}).setdefault(cls, {})[field] = \
            derived_values[source_key]
    return out


def _find_by_name(manager, class_name: str, name: str):
    if not name:
        return None
    for inst in (manager.objectTables.get(class_name, {}) or {}).values():
        if getattr(inst, 'name', '') == name:
            return inst
    return None
