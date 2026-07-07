"""
@module materialsScience.formulation_stage

The `formulationSearch` stage kind — the executor that lets a
MultiScaleSimulationDefinition stage drive a FormulationSearchDefinition
instead of SimulationRun stepping. The msim stage machinery stays
untouched: parse_stages already keeps unknown kinds, and this module
reshapes the formulation report into the EXACT contract
multi_scale_search.run_stage_search returns, so the existing
msim-stage-search frontend renders a wax derivation with zero changes.

Stage shape (stages_json entry):
    {"key": "formulation-screening", "kind": "formulationSearch",
     "intent": "search",
     "formulationSearchRef": "<FormulationSearchDefinition name>",
     "gate": {"solutionRef"?: "<SolutionDefinition name>",
              "failReason": "..."},
     "derive": {"params": {"<target>": "<derived key>"}}}

Gate: with a solutionRef the verdict runs through the SAME no-code
SolutionExecutionEngine contract evaluate_stage_gate uses — flattened
context in (`candidate.<prop>`, `thermal.<key>`, `run.<field>`),
outcome/reason/derived values out — authored in the existing no-code
editor. Without one, the honest default: complete when the run's
outcome is 'met' or 'first-winner' (the reason says so explicitly).
"""

import json
from typing import Any, Dict

from materialsScience.formulation_search_runner import (
    run_formulation_search,
)


def _flatten_candidate(candidate: Dict, run_info: Dict) -> Dict[str, Any]:
    """The formulation analogue of flatten_stage_results: dotted keys a
    no-code gate (or a derive map) reads. `candidate.<prop>` carries
    predicted properties; `thermal.<key>` the window verdict; `run.<k>`
    the run-level outcome facts; components as loading percentages."""
    flat: Dict[str, Any] = {}
    for prop, value in (candidate.get('predicted') or {}).items():
        flat[f'candidate.{prop}'] = value
    flat['candidate.score'] = candidate.get('score')
    flat['candidate.meets'] = candidate.get('meets')
    flat['candidate.componentCount'] = len(
        candidate.get('components') or [])
    for comp in candidate.get('components') or []:
        flat[f"loading.{comp.get('materialId', '?')}"] = comp.get(
            'weightPercent')
    thermal = candidate.get('thermal') or {}
    for key in ('ok', 'windowC', 'process', 'refusal'):
        if key in thermal:
            flat[f'thermal.{key}'] = thermal[key]
    for key in ('outcome', 'batches', 'evaluated'):
        if key in run_info:
            flat[f'run.{key}'] = run_info[key]
    return flat


def run_formulation_stage(manager, msim_name: str, stage: Dict,
                          body: Dict) -> Dict:
    """Execute the stage's FormulationSearchDefinition and reshape the
    report into the run_stage_search contract (see module docstring)."""
    search_ref = stage.get('formulationSearchRef') or ''
    if not search_ref:
        return {'achieved': False, 'winner': None, 'winners': [],
                'searchComplete': True, 'exhausted': False,
                'totalCandidates': 0, 'attempted': 0,
                'advancedThisCall': 0, 'attempts': [],
                'backend': 'formulation', 'warnings': [],
                'error': f'Stage "{stage.get("key")}" declares no '
                         'formulationSearchRef.'}
    report = run_formulation_search(
        manager, search_ref,
        continue_after_winner=body.get('continueAfterWinner'),
        attempt_tag=str(body.get('attemptTag') or ''),
        knob_overrides=body.get('knobOverrides') or None)
    if not report.get('ok'):
        return {'achieved': False, 'winner': None, 'winners': [],
                'searchComplete': True, 'exhausted': False,
                'totalCandidates': 0, 'attempted': 0,
                'advancedThisCall': 0, 'attempts': [],
                'backend': 'formulation', 'warnings': [],
                'error': report.get('error', 'formulation search failed')}

    run_info = {'outcome': report.get('outcome', ''),
                'batches': report.get('batches', 0),
                'evaluated': report.get('evaluated', 0),
                'run': report.get('run', '')}
    # Additive display names for the candidate summaries the existing
    # stage-search UI prints as flat `key = value` pairs.
    from materialsScience.composite_search import load_legacy_seed_data
    try:
        names = {a['id']: a['name']
                 for a in load_legacy_seed_data()['additives']}
    except Exception:
        names = {}
    # Candidates in report order (refine: the single best + trajectory;
    # grid: the ranked list).
    ranked = (report.get('ranked')
              or ([report['best']] if report.get('best') else []))
    winners = report.get('winners')
    if winners is None:
        winners = [c for c in ranked if c.get('meets')]

    def _entry(cand):
        # Flat, human-readable candidate (the stage-search UI renders
        # `key = value` pairs): additive loadings by NAME + the score.
        candidate = {}
        for comp in cand.get('components') or []:
            label = names.get(comp.get('materialId'),
                              comp.get('materialId', '?'))
            candidate[f'{label} wt%'] = comp.get('weightPercent')
        score = cand.get('score')
        candidate['score'] = (round(float(score), 4)
                              if isinstance(score, (int, float)) else score)
        return {
            'run': report.get('run', ''),
            'candidate': candidate,
            'stepped': 0,
            'complete': bool(cand.get('meets')),
            'reason': ('meets all predictable targets'
                       if cand.get('meets') else
                       '; '.join(_violation_texts(cand)) or
                       'does not meet the targets'),
            'derivedValues': _flatten_candidate(cand, run_info),
            'femVerify': (cand.get('femVerify') or {}).get('status'),
            'error': None,
        }

    attempts = [_entry(c) for c in ranked]
    winner_entries = [_entry(c) for c in winners]
    achieved = bool(winner_entries)
    result = {
        'achieved': achieved,
        'winner': winner_entries[0] if winner_entries else None,
        'winners': winner_entries,
        'searchComplete': True,
        'exhausted': not achieved,
        'totalCandidates': int(report.get('evaluated', len(attempts))
                               or len(attempts)),
        'attempted': len(attempts),
        'advancedThisCall': len(attempts),
        'attempts': attempts,
        'backend': 'formulation',
        'warnings': [],
        'parallelHint': None,
        'workerSplit': None,
        'error': None,
        # Formulation extras the panel can surface without breaking the
        # base contract:
        'formulation': {
            'run': report.get('run', ''),
            'outcome': report.get('outcome', ''),
            'gapAnalysis': report.get('gapAnalysis', []),
            'trajectory': report.get('trajectory', []),
            'fidelity': report.get('fidelity', {}),
            'dftEvidenceSuggestions': report.get(
                'dftEvidenceSuggestions', []),
            'excludedBySourcingPolicy': report.get(
                'excludedBySourcingPolicy', []),
            'persistedCandidates': report.get('persistedCandidates', 0),
        },
    }
    if not achieved and stage.get('gate', {}).get('failReason'):
        result['failReason'] = stage['gate']['failReason']
    return result


def _violation_texts(cand):
    out = []
    for v in cand.get('violations') or []:
        if isinstance(v, dict):
            out.append(v.get('detail') or v.get('type')
                       or json.dumps(v)[:80])
        else:
            out.append(str(v)[:80])
    return out


def evaluate_formulation_gate(manager, stage: Dict, run_row) -> Dict:
    """Gate verdict for a formulationSearch stage over a persisted
    FormulationSearchRun row. Same contract as evaluate_stage_gate:
    {complete, hasGate, reason, derivedValues, error}."""
    run_name = getattr(run_row, 'name', '')
    outcome = getattr(run_row, 'outcome', '')
    # Rebuild the flattened context from the run's best persisted
    # candidate (rank 1).
    table = (manager.objectTables or {}).get(
        'FormulationCandidateResult', {}) or {}
    cands = [c for c in
             (table.values() if isinstance(table, dict) else table)
             if getattr(c, 'run_ref', '') == run_name]
    best = min(cands, key=lambda c: getattr(c, 'rank', 1 << 30),
               default=None)
    candidate = {}
    if best is not None:
        candidate = {
            'predicted': _loads(getattr(
                best, 'predicted_properties_json', '{}'), {}),
            'score': getattr(best, 'score', 0.0),
            'meets': getattr(best, 'meets_targets', False),
            'components': _loads(getattr(best, 'components_json', '[]'),
                                 []),
            'thermal': _loads(getattr(best, 'thermal_verdict_json', '{}'),
                              {}),
        }
    flat = _flatten_candidate(candidate, {
        'outcome': outcome,
        'evaluated': getattr(run_row, 'evaluated', 0),
    })

    solution_ref = (stage.get('gate') or {}).get('solutionRef') or ''
    if solution_ref:
        # The SAME no-code engine seam evaluate_stage_gate uses.
        from simulations.multi_scale_stages import (
            evaluate_gate_over_fields,
        )
        return evaluate_gate_over_fields(manager, stage, flat)
    complete = outcome in ('met', 'first-winner')
    return {
        'complete': complete,
        'hasGate': False,
        'reason': (f"run '{run_name}' outcome '{outcome}' "
                   + ('meets the targets'
                      if complete else
                      'does not meet the targets (no gate solution '
                      'configured — the default checks outcome in '
                      "('met', 'first-winner'))")),
        'derivedValues': flat,
        'error': None,
    }


def _loads(blob, default):
    try:
        parsed = json.loads(blob or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (TypeError, ValueError):
        return default
