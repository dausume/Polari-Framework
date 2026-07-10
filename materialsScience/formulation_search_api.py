"""
@module materialsScience.formulation_search_api

HTTP surface for FormulationSearchDefinition rows (PeersAPI pattern —
self-registering falcon routes; separate module so ScaleExecutionAPI
stays at size):

  POST /api/msci/formulation-searches/{name}/run
       {"continueAfterWinner"?, "attemptTag"?, "knobOverrides"?} →
       run_formulation_search (persists run + top-N candidate rows,
       returns the full report; report['run'] names the row).
  GET  /api/msci/formulation-searches/{name}/runs
       the persisted runs + their candidate rows.
  POST /api/msci/formulation-runs/{run_name}/promote/{candidate_name}
       the EXPLICIT winner→MaterialScaleDefinition L1 promotion knob.

The legacy stateless endpoints (POST /api/msci/composites/search and
/refine on ScaleExecutionAPI) remain for quick queries; this is the
object-coherent surface a page or msim stage drives.
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.formulation_search_runner import (
    promote_winner_to_scale_definition, run_formulation_search,
)


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


class FormulationSearchAPI(treeObject):
    """Formulation-search object endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/formulation-searches/{name}/run', self,
                suffix='run')
            polServer.falconServer.add_route(
                '/api/msci/formulation-searches/{name}/runs', self,
                suffix='runs')
            polServer.falconServer.add_route(
                '/api/msci/formulation-runs/{run_name}/promote/'
                '{candidate_name}', self, suffix='promote')

    def on_post_run(self, request, response, name):
        try:
            body = json.load(request.bounded_stream)
        except Exception:
            body = {}
        # xsim-2: search runs are mutating sims — single-writer gated
        # (tied children pass through on the ambient run context).
        from simulationLocks.gate import gate_refusal_media, simulation_gate
        with simulation_gate(self.manager, 'search', name,
                             submitted_by='formulation_search_api'
                             ) as slot:
            if not slot['ok']:
                response.status = '423 Locked'
                response.media = {'ok': False,
                                  **gate_refusal_media(slot)}
                return
            result = run_formulation_search(
                self.manager, name,
                continue_after_winner=body.get('continueAfterWinner'),
                attempt_tag=str(body.get('attemptTag', '') or ''),
                knob_overrides=body.get('knobOverrides') or None)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_runs(self, request, response, name):
        runs = [r for r in _rows(self.manager, 'FormulationSearchRun')
                if getattr(r, 'search_ref', '') == name]
        cands = _rows(self.manager, 'FormulationCandidateResult')

        def _run_payload(run):
            run_name = getattr(run, 'name', '')
            return {
                'name': run_name,
                'mode': getattr(run, 'mode', ''),
                'status': getattr(run, 'status', ''),
                'outcome': getattr(run, 'outcome', ''),
                'evaluated': getattr(run, 'evaluated', 0),
                'sweepCapped': getattr(run, 'sweep_capped', False),
                'winnersCount': getattr(run, 'winners_count', 0),
                'sourcingPolicy': getattr(run, 'sourcing_policy', ''),
                'startedAt': getattr(run, 'started_at', ''),
                'finishedAt': getattr(run, 'finished_at', ''),
                'error': getattr(run, 'error', ''),
                'fidelitySummary': _loads(
                    getattr(run, 'fidelity_summary_json', '{}')),
                'gapAnalysis': _loads(
                    getattr(run, 'gap_analysis_json', '[]')),
                'trajectory': _loads(
                    getattr(run, 'trajectory_json', '[]')),
                'excludedBySourcing': _loads(
                    getattr(run, 'excluded_by_sourcing_json', '[]')),
                'predictableProperties': _loads(
                    getattr(run, 'predictable_properties_json', '[]')),
                'assumptions': _loads(
                    getattr(run, 'assumptions_json', '[]')),
                'candidates': sorted(
                    (_cand_payload(c) for c in cands
                     if getattr(c, 'run_ref', '') == run_name),
                    key=lambda c: c['rank']),
            }

        response.media = {'success': True,
                          'data': [_run_payload(r) for r in runs]}

    def on_post_promote(self, request, response, run_name,
                        candidate_name):
        result = promote_winner_to_scale_definition(
            self.manager, run_name, candidate_name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result


def _loads(blob):
    try:
        return json.loads(blob or 'null')
    except (TypeError, ValueError):
        return None


def _cand_payload(cand):
    return {
        'name': getattr(cand, 'name', ''),
        'rank': getattr(cand, 'rank', 0),
        'components': _loads(getattr(cand, 'components_json', '[]')),
        'predicted': _loads(
            getattr(cand, 'predicted_properties_json', '{}')),
        'score': getattr(cand, 'score', 0.0),
        'meetsTargets': getattr(cand, 'meets_targets', False),
        'violations': _loads(getattr(cand, 'violations_json', '[]')),
        'unpredicted': _loads(getattr(cand, 'unpredicted_json', '[]')),
        'thermalVerdict': _loads(
            getattr(cand, 'thermal_verdict_json', '{}')),
        'fidelity': _loads(getattr(cand, 'fidelity_json', '{}')),
        'isWinner': getattr(cand, 'is_winner', False),
        'promotedScaleDef': getattr(cand, 'promoted_scale_def', ''),
    }
