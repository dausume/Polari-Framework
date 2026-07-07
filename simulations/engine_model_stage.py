"""
@module simulations.engine_model_stage

The `engineModel` stage kind — a multi-scale stage that executes a
configured FEM/DFT model definition (materialsScience.model_execution)
as a ONE-SHOT solve, plus the STAGE-CONTEXT builder every
context-consuming stage kind shares.

Stage shape (stages_json entry):
    {"key": "continuum-verify", "kind": "engineModel",
     "intent": "calibrate",            # product-bearing → derive allowed
     "modelRef": "wax-thermal-continuum",
     "gate": {"solutionRef"?: ..., "failReason"?: ...},
     "derive": {"params": {"derived.effectiveK": "model.effectiveK"}}}

The executor reshapes into the EXACT run_stage_search report contract
(single attempt; candidate = the resolved inputs with provenance
readable as `key = value`; derivedValues = `model.<outputKey>` +
`input.<param>`), so the existing Search-for-a-solution UI renders it
unchanged — the formulationSearch precedent.

STAGE CONTEXT (v1, honest): nothing server-side persists "stage X
derived Y", so `build_stage_context` RE-EVALUATES the prior stages'
existing gates over their newest persisted artifacts at call time —
cheap, stateless, and the provenance in every execution report names
what was read. Keys are namespaced `"<stageKey>.<derivedKey>"` plus a
`"<stageKey>.__complete"` flag so refusals can say WHY a key is absent.
"""

from typing import Any, Dict

from simulations.multi_scale_stages import (
    evaluate_gate_over_fields, evaluate_stage_gate, parse_stages,
)


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _newest(rows, key=lambda r: getattr(r, 'name', '')):
    return max(rows, key=key, default=None)


def build_stage_context(manager, msim, upto_stage_key: str
                        ) -> Dict[str, Any]:
    """Flattened derived values of every stage BEFORE `upto_stage_key`
    (exclusive), namespaced `<stageKey>.<key>`, with
    `<stageKey>.__complete` flags. Incomplete stages contribute only
    their flag."""
    context: Dict[str, Any] = {}
    for stage in parse_stages(msim):
        key = stage.get('key', '')
        if key == upto_stage_key:
            break
        verdict = stage_verdict(manager, msim, stage)
        context[f'{key}.__complete'] = bool(verdict.get('complete'))
        if verdict.get('complete'):
            for dk, dv in (verdict.get('derivedValues') or {}).items():
                context[f'{key}.{dk}'] = dv
    return context


def stage_verdict(manager, msim, stage) -> Dict[str, Any]:
    """A prior stage's gate verdict over its newest persisted artifact
    — the same evaluators the gate endpoint uses, so the context can
    never disagree with what the page shows."""
    kind = stage.get('kind')
    if kind == 'formulationSearch':
        from materialsScience.formulation_stage import (
            evaluate_formulation_gate,
        )
        search_ref = stage.get('formulationSearchRef') or ''
        run = _newest([r for r in _rows(manager, 'FormulationSearchRun')
                       if getattr(r, 'search_ref', '') == search_ref])
        if run is None:
            return {'complete': False}
        return evaluate_formulation_gate(manager, stage, run)
    if kind == 'engineModel':
        from materialsScience.model_execution import find_model
        model, _ = find_model(manager, stage.get('modelRef', ''))
        if model is None:
            return {'complete': False}
        return evaluate_engine_model_gate(manager, stage, model)
    if kind == 'subModel':
        from simulations.sub_model_stage import evaluate_sub_model_gate
        return evaluate_sub_model_gate(manager, stage)
    # runToCompletion / coStep: newest run of the stage's own sim.
    sim_ref = (stage.get('simulationRef')
               or stage.get('primarySimulationRef') or '')
    runs = [r for r in _rows(manager, 'SimulationRun')
            if getattr(r, 'simulation_ref', '') == sim_ref]
    run = _newest(runs, key=lambda r: (
        getattr(r, 'last_recorded_step', 0) or 0,
        getattr(r, 'name', '')))
    if run is None:
        return {'complete': False}
    return evaluate_stage_gate(manager, stage, run)


# ---------------------------------------------------------------------
# The engineModel executor + gate.
# ---------------------------------------------------------------------

def _flatten_model_report(report: Dict) -> Dict[str, Any]:
    """`model.<outputKey>` for every result key + `input.<param>`
    echoes — the derive/gate namespace."""
    flat: Dict[str, Any] = {}
    for k, v in (report.get('result') or {}).items():
        flat[f'model.{k}'] = v
    for k, v in (report.get('inputs') or {}).items():
        flat[f'input.{k}'] = v
    flat['model.__engine'] = report.get('engine', '')
    return flat


def run_engine_model_stage(manager, msim_name: str, stage: Dict,
                           body: Dict, msim=None) -> Dict:
    """Execute the stage's model definition and reshape into the
    stage-search report contract (see module docstring)."""
    model_ref = stage.get('modelRef') or ''
    empty = {'achieved': False, 'winner': None, 'winners': [],
             'searchComplete': True, 'exhausted': False,
             'totalCandidates': 1, 'attempted': 0,
             'advancedThisCall': 0, 'attempts': [],
             'backend': 'engineModel', 'warnings': [],
             'parallelHint': None, 'workerSplit': None, 'error': None}
    if not model_ref:
        return {**empty,
                'error': f'Stage "{stage.get("key")}" declares no '
                         'modelRef.'}
    if msim is None:
        msim = next((r for r in _rows(
            manager, 'MultiScaleSimulationDefinition')
            if getattr(r, 'name', '') == msim_name), None)
    stage_context = dict(body.get('stageContext') or {})
    if msim is not None:
        stage_context.update(
            build_stage_context(manager, msim, stage.get('key', '')))

    from materialsScience.model_execution import execute_model
    report = execute_model(manager, model_ref,
                           stage_context=stage_context or None)

    candidate = {}
    for param, prov in (report.get('resolved') or {}).items():
        candidate[param] = prov.get('value')
    candidate['model'] = model_ref
    flat = _flatten_model_report(report)

    if not report.get('ok'):
        reason_bits = [report.get('error', 'engine refused')]
        for refusal in report.get('refusals', []) or []:
            reason_bits.append(refusal.get('error', ''))
        attempt = {'run': model_ref, 'candidate': candidate,
                   'stepped': 0, 'complete': False,
                   'reason': '; '.join(b for b in reason_bits if b),
                   'derivedValues': flat, 'error': report.get('error')}
        return {**empty, 'attempted': 1, 'advancedThisCall': 1,
                'exhausted': True, 'attempts': [attempt],
                'engineModel': {k: report.get(k) for k in
                                ('model', 'template', 'engine',
                                 'missing', 'refusals', 'suggestions',
                                 'suggestion', 'findings')
                                if k in report},
                'failReason': (stage.get('gate') or {}).get('failReason'),
                'error': None}

    # Gate: optional no-code solution over the flattened outputs; the
    # honest default is "the solve succeeded".
    gate_ref = (stage.get('gate') or {}).get('solutionRef') or ''
    if gate_ref:
        verdict = evaluate_gate_over_fields(manager, stage, flat)
        complete = bool(verdict.get('complete'))
        reason = verdict.get('reason') or verdict.get('error') or ''
        derived = verdict.get('derivedValues') or flat
    else:
        complete = True
        reason = ('engine solve succeeded (no gate solution configured '
                  '— the default accepts a successful solve)')
        derived = flat
    attempt = {'run': model_ref, 'candidate': candidate, 'stepped': 1,
               'complete': complete, 'reason': reason,
               'derivedValues': derived, 'error': None}
    result = {**empty,
              'achieved': complete,
              'winner': attempt if complete else None,
              'winners': [attempt] if complete else [],
              'attempted': 1, 'advancedThisCall': 1,
              'exhausted': not complete,
              'attempts': [attempt],
              'engineModel': {
                  'model': model_ref,
                  'template': report.get('template', ''),
                  'engine': report.get('engine', ''),
                  'result': report.get('result', {}),
                  'resolved': report.get('resolved', {}),
                  'executedAt': report.get('executedAt', ''),
              }}
    if not complete and (stage.get('gate') or {}).get('failReason'):
        result['failReason'] = stage['gate']['failReason']
    return result


def evaluate_engine_model_gate(manager, stage: Dict, model_row
                               ) -> Dict:
    """Gate verdict over the model row's PERSISTED last result — same
    contract as evaluate_stage_gate. Never executed → honest refusal
    pointing at the stage's run button."""
    import json as _json
    executed_at = getattr(model_row, 'last_executed_at', '') or ''
    if not executed_at:
        return {'complete': False, 'hasGate': False,
                'reason': f"model '{getattr(model_row, 'name', '')}' "
                          'has never executed — run this stage (or '
                          'POST /api/msci/models/{name}/execute) first.',
                'derivedValues': None, 'error': None}
    try:
        result = _json.loads(
            getattr(model_row, 'last_result_json', '') or '{}')
    except (TypeError, ValueError):
        result = {}
    flat = _flatten_model_report({'result': result, 'inputs': {},
                                  'engine': ''})
    gate_ref = (stage.get('gate') or {}).get('solutionRef') or ''
    if gate_ref:
        return evaluate_gate_over_fields(manager, stage, flat)
    return {'complete': True, 'hasGate': False,
            'reason': f'last execution at {executed_at} succeeded (no '
                      'gate solution configured — the default accepts '
                      'a persisted successful solve)',
            'derivedValues': flat, 'error': None}
