"""
@cross-cutting
@module waxprint.sim_api

HTTP for the wax-print simulation space (wp-5/wp-6): run one initial
condition, run a range of conditions, and evaluate whether the condition
gates are met for a run. Rows are created via the runner so a fresh run
renders in the wax-print-wall scene immediately.

Routes:
  POST /api/waxprint/sim/run            {assembly, feedstock, condition, ...}
  POST /api/waxprint/sim/run-range      {assembly, feedstock, conditions:[...]}
  GET  /api/waxprint/sim/evaluate?run=  (&target_voxel_xy_mm=&margin_tol_mm=)
  GET  /api/waxprint/sim/runs           (list wax-print runs)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from waxprint.custom import sim_runner
from waxprint.custom import sim_evaluation


def _run_rows(manager, run_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        'WaxPrintSimState', {}) or {}
    return [o for o in table.values()
            if getattr(o, 'simulation_run_ref', None) == run_name]


def _summary(rows):
    """Compact per-run summary for a range comparison."""
    rows = sorted(rows, key=lambda r: sim_evaluation._get(r, 'step'))
    if not rows:
        return {}
    g = sim_evaluation._get
    return {
        'steps': len(rows),
        'voxel_xy_first_mm': g(rows[0], 'voxel_xy_mm'),
        'voxel_xy_top_mm': g(rows[-1], 'voxel_xy_mm'),
        'worst_margin_mm': max(g(r, 'margin_mm') for r in rows),
        'thermally_safe': all(g(r, 'thermally_safe') >= 1 for r in rows),
        'printable': all(g(r, 'printable') >= 1 for r in rows),
    }


class WaxPrintSimAPI(treeObject):
    """Run + evaluate endpoints for the wax-print sim space."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/waxprint/sim'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/waxprint/sim/run', self, suffix='run')
            add('/api/waxprint/sim/run-range', self, suffix='run_range')
            add('/api/waxprint/sim/evaluate', self, suffix='evaluate')
            add('/api/waxprint/sim/runs', self, suffix='runs')

    def _body(self, request, response):
        try:
            return json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': f'bad JSON payload: {e}'}
            return None

    def _targets(self, src):
        t = {}
        if src.get('target_voxel_xy_mm') is not None:
            t['target_voxel_xy_mm'] = float(src['target_voxel_xy_mm'])
        if src.get('margin_tol_mm') is not None:
            t['margin_tol_mm'] = float(src['margin_tol_mm'])
        return t

    def on_post_run(self, request, response):
        body = self._body(request, response)
        if body is None:
            return
        a, f, c = (body.get('assembly'), body.get('feedstock'),
                   body.get('condition'))
        if not (a and f and c):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'assembly, feedstock, condition required'}
            return
        kwargs = {}
        for k in ('n_steps', 'max_height_mm', 'target_voxel_xy_mm',
                  'margin_tol_mm'):
            if body.get(k) is not None:
                kwargs[k] = float(body[k]) if 'mm' in k or k == 'target_' \
                    else int(body[k]) if k == 'n_steps' else body[k]
        out = sim_runner.persist_run(self.manager, a, f, c,
                                     run_name=body.get('run_name'), **kwargs)
        if not out.get('ok'):
            response.status = '404 Not Found'
            response.media = out
            return
        targets = self._targets(body)
        out['evaluation'] = sim_evaluation.evaluate_run(out['rows'], **targets)
        response.media = out

    def on_post_run_range(self, request, response):
        body = self._body(request, response)
        if body is None:
            return
        a, f = body.get('assembly'), body.get('feedstock')
        conditions = body.get('conditions') or []
        if not (a and f and conditions):
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'error': 'assembly, feedstock and conditions[] required'}
            return
        targets = self._targets(body)
        results = []
        for cond in conditions:
            out = sim_runner.persist_run(self.manager, a, f, cond)
            if not out.get('ok'):
                results.append({'condition': cond, 'ok': False,
                                'error': out.get('error'),
                                'missing': out.get('missing')})
                continue
            ev = sim_evaluation.evaluate_run(out['rows'], **targets)
            results.append({
                'condition': cond, 'ok': True, 'run_name': out['run_name'],
                'summary': _summary(out['rows']),
                'all_met': ev['all_met'], 'met_count': ev['met_count'],
                'total': ev['total'], 'conditions': ev['conditions']})
        ranked = sorted(
            [r for r in results if r.get('ok')],
            key=lambda r: (-r['met_count'], r['summary'].get('voxel_xy_top_mm',
                                                             9e9)))
        response.media = {
            'ok': True, 'assembly': a, 'feedstock': f,
            'results': results,
            'best_condition': ranked[0]['condition'] if ranked else None}

    def on_get_evaluate(self, request, response):
        params = request.params or {}
        run = params.get('run', '')
        if not run:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'run query param required'}
            return
        rows = _run_rows(self.manager, run)
        if not rows:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no rows for run "{run}"'}
            return
        ev = sim_evaluation.evaluate_run(rows, **self._targets(params))
        response.media = {'ok': True, 'run': run, 'evaluation': ev}

    def on_get_runs(self, request, response):
        table = (getattr(self.manager, 'objectTables', {}) or {}).get(
            'SimulationRun', {}) or {}
        runs = [{'name': getattr(o, 'name', ''),
                 'label': getattr(o, 'label', ''),
                 'steps': getattr(o, 'total_steps', 0)}
                for o in table.values()
                if getattr(o, 'simulation_ref', '') == 'wax-print']
        response.media = {'ok': True, 'runs': runs}
