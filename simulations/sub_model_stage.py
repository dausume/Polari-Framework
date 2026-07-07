"""
@module simulations.sub_model_stage

The `subModel` stage kind — RECURSIVE multi-scale composition: a stage
of one MultiScaleSimulationDefinition that runs ANOTHER msim as a
nested component ("MultiScale Models incorporating abstracted
multiscale model components").

Stage shape:
    {"key": "formulation-screening", "kind": "subModel",
     "intent": "search", "msimRef": "wax-derivation",
     "gate": {"failReason"?: ...},
     "derive": {"params": {"derived.winnerScore":
                           "sub.formulation-screening.candidate.score"}}}

v1 SEMANTICS (honest, minimal-but-real recursion): executing the stage
walks the CHILD msim's stages in order —
  - child engineModel / formulationSearch / subModel stages EXECUTE
    directly (they are complete server-side one-shot/one-batch
    executors); each stage's derived values accumulate into the child
    context that later child stages' stageDerived bindings read;
  - child runToCompletion / coStep stages are GATE-CHECKED only over
    their newest existing run: those kinds advance through interactive
    per-timestep stepping, and auto-driving them inside one HTTP call
    would be a new headless run engine — out of scope, so an incomplete
    stepping stage stops the walk with an honest report naming it and
    a suggestion linking the child's own page. NO silent skipping.

Cycle guard: the visited set (including the parent) travels down the
recursion; a revisit refuses naming the full path. Depth cap
MAX_SUB_MODEL_DEPTH keeps pathological chains honest.

The report reshapes into the stage-search contract: one attempt per
child stage (candidate = {stage, kind, complete} readable pairs),
derivedValues namespaced `sub.<childStageKey>.<key>`.
"""

from typing import Any, Dict, List, Optional, Set

from simulations.multi_scale_stages import (
    evaluate_gate_over_fields, parse_stages,
)

MAX_SUB_MODEL_DEPTH = 8


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _find_msim(manager, name):
    return next((r for r in _rows(
        manager, 'MultiScaleSimulationDefinition')
        if getattr(r, 'name', '') == name), None)


def _empty_report(error: Optional[str]) -> Dict:
    return {'achieved': False, 'winner': None, 'winners': [],
            'searchComplete': True, 'exhausted': False,
            'totalCandidates': 0, 'attempted': 0, 'advancedThisCall': 0,
            'attempts': [], 'backend': 'subModel', 'warnings': [],
            'parallelHint': None, 'workerSplit': None, 'error': error}


def run_sub_model_stage(manager, msim_name: str, stage: Dict,
                        body: Dict, visited: Optional[Set[str]] = None,
                        depth: int = 0) -> Dict:
    """Run the child msim's stages (see module docstring) and reshape
    into the stage-search contract."""
    child_name = stage.get('msimRef') or ''
    if not child_name:
        return _empty_report(
            f'Stage "{stage.get("key")}" declares no msimRef.')
    visited = set(visited or ())
    visited.add(msim_name)
    if child_name in visited:
        path = ' -> '.join(sorted(visited)) + f' -> {child_name}'
        return _empty_report(
            f'sub-model cycle refused: {path} — a multiscale model '
            'cannot (transitively) contain itself.')
    if depth >= MAX_SUB_MODEL_DEPTH:
        return _empty_report(
            f'sub-model depth cap ({MAX_SUB_MODEL_DEPTH}) reached at '
            f'"{child_name}" — flatten the composition.')
    child = _find_msim(manager, child_name)
    if child is None:
        return _empty_report(
            f'sub-model msim "{child_name}" not found.')
    visited.add(child_name)

    from simulations.engine_model_stage import run_engine_model_stage
    child_context: Dict[str, Any] = {}
    attempts: List[Dict] = []
    child_stages: List[Dict] = []
    blocked_at = None

    for child_stage in parse_stages(child):
        ckey = child_stage.get('key', '')
        ckind = child_stage.get('kind', '')
        entry: Dict[str, Any] = {'stage': ckey, 'kind': ckind}
        if ckind == 'engineModel':
            sub_report = run_engine_model_stage(
                manager, child_name, child_stage,
                {'stageContext': child_context}, msim=child)
            complete = bool(sub_report.get('achieved'))
            reason = ((sub_report.get('winner') or {}).get('reason')
                      if complete else
                      ((sub_report.get('attempts') or [{}])[0]
                       .get('reason') or sub_report.get('error')
                       or 'not achieved'))
            derived = ((sub_report.get('winner') or {})
                       .get('derivedValues') or {})
        elif ckind == 'formulationSearch':
            from materialsScience.formulation_stage import (
                run_formulation_stage,
            )
            child_body = {'attemptTag':
                          f"sub-{msim_name}-{body.get('attemptTag', '')}"
                          .rstrip('-'),
                          'continueAfterWinner':
                          body.get('continueAfterWinner')}
            sub_report = run_formulation_stage(
                manager, child_name, child_stage, child_body)
            complete = bool(sub_report.get('achieved'))
            winner = sub_report.get('winner') or {}
            best = (sub_report.get('attempts') or [{}])[0]
            reason = (winner.get('reason') if complete
                      else best.get('reason')
                      or sub_report.get('error') or 'not achieved')
            derived = (winner.get('derivedValues')
                       or best.get('derivedValues') or {})
        elif ckind == 'subModel':
            sub_report = run_sub_model_stage(
                manager, child_name, child_stage, body,
                visited=visited, depth=depth + 1)
            complete = bool(sub_report.get('achieved'))
            reason = (sub_report.get('error')
                      or ('nested sub-model complete' if complete
                          else 'nested sub-model incomplete'))
            derived = ((sub_report.get('winner') or {})
                       .get('derivedValues') or {})
        else:
            # runToCompletion / coStep: gate-check only (honest v1 —
            # stepping sims own their run lifecycle).
            from simulations.engine_model_stage import stage_verdict
            verdict = stage_verdict(manager, child, child_stage)
            complete = bool(verdict.get('complete'))
            reason = (verdict.get('reason')
                      or ('stage gate complete' if complete else
                          'stage has not completed'))
            if not complete:
                reason = (f"child stage '{ckey}' ({ckind}) is not "
                          f'complete: {reason} — drive it on the '
                          f"child's own page (/multi-scale-sim/"
                          f'{child_name}); stepping stages are not '
                          'auto-run by a sub-model (honest v1).')
            derived = verdict.get('derivedValues') or {}

        entry['complete'] = complete
        entry['reason'] = reason
        child_stages.append(entry)
        attempts.append({
            'run': f'{child_name}:{ckey}',
            'candidate': {'stage': ckey, 'kind': ckind,
                          'complete': complete},
            'stepped': 1 if complete else 0,
            'complete': complete,
            'reason': reason,
            'derivedValues': {f'sub.{ckey}.{k}': v
                              for k, v in (derived or {}).items()},
            'error': None,
        })
        if complete:
            for k, v in (derived or {}).items():
                child_context[f'{ckey}.{k}'] = v
            child_context[f'{ckey}.__complete'] = True
        else:
            child_context[f'{ckey}.__complete'] = False
            blocked_at = ckey
            break

    achieved = blocked_at is None and bool(child_stages)
    merged: Dict[str, Any] = {}
    for a in attempts:
        merged.update(a['derivedValues'])

    # Optional no-code gate over the merged child context.
    gate_ref = (stage.get('gate') or {}).get('solutionRef') or ''
    if gate_ref and achieved:
        verdict = evaluate_gate_over_fields(manager, stage, merged)
        achieved = bool(verdict.get('complete'))

    winner = {'run': child_name,
              'candidate': {'subModel': child_name,
                            'stages': len(child_stages)},
              'stepped': len(child_stages), 'complete': achieved,
              'reason': (f'all {len(child_stages)} child stage(s) '
                         'complete' if achieved else
                         f"blocked at '{blocked_at}'"),
              'derivedValues': merged, 'error': None}
    report = _empty_report(None)
    report.update({
        'achieved': achieved,
        'winner': winner if achieved else None,
        'winners': [winner] if achieved else [],
        'totalCandidates': len(child_stages),
        'attempted': len(attempts),
        'advancedThisCall': len(attempts),
        'exhausted': not achieved,
        'attempts': attempts,
        'subModel': {'child': child_name, 'depth': depth,
                     'childStages': child_stages,
                     'blockedAt': blocked_at},
    })
    if not achieved and (stage.get('gate') or {}).get('failReason'):
        report['failReason'] = stage['gate']['failReason']
    return report


def evaluate_sub_model_gate(manager, stage: Dict, run_row=None) -> Dict:
    """Read-only gate: re-check the child's stage gates without
    executing anything. Same verdict contract as evaluate_stage_gate."""
    child_name = stage.get('msimRef') or ''
    child = _find_msim(manager, child_name)
    if child is None:
        return {'complete': False, 'hasGate': False, 'reason': '',
                'derivedValues': None,
                'error': f'sub-model msim "{child_name}" not found'}
    from simulations.engine_model_stage import stage_verdict
    merged: Dict[str, Any] = {}
    for child_stage in parse_stages(child):
        verdict = stage_verdict(manager, child, child_stage)
        ckey = child_stage.get('key', '')
        if not verdict.get('complete'):
            return {'complete': False, 'hasGate': False,
                    'reason': f"child stage '{ckey}' is not complete: "
                              f"{verdict.get('reason', '')}",
                    'derivedValues': None, 'error': None}
        for k, v in (verdict.get('derivedValues') or {}).items():
            merged[f'sub.{ckey}.{k}'] = v
    gate_ref = (stage.get('gate') or {}).get('solutionRef') or ''
    if gate_ref:
        return evaluate_gate_over_fields(manager, stage, merged)
    return {'complete': True, 'hasGate': False,
            'reason': f'every stage of "{child_name}" is complete',
            'derivedValues': merged, 'error': None}
