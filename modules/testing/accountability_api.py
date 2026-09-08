"""
@module testing.accountability_api

acct-0: the accountability matrix HTTP surface (msci scale-presence
idiom — capability x status x evidence, "why is this red" always
answerable):

  GET  /api/accountability            the matrix; ?category= filters.
  GET  /api/accountability/runs       recent CheckRun summaries.
  POST /api/accountability/run        run the matrix (or a slice) NOW
                                      {category?, checks?, timeout?};
                                      persists the CheckRun, updates
                                      rows, emits the YAML report.

TEST-BUILD ONLY: instantiated in polariServer.__init__ behind
module_enabled('testing') — a normal build never registers these
routes (testing.custom.absence_probe pins that).
"""

import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from testing.custom.matrix_runner import (
    run_matrix, select_checks, sync_capability_checks,
)


class AccountabilityAPI(treeObject):
    """acct-0 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/accountability'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/accountability', self, suffix='matrix')
            polServer.falconServer.add_route(
                '/api/accountability/runs', self, suffix='runs')
            polServer.falconServer.add_route(
                '/api/accountability/run', self, suffix='run')

    def _check_rows(self):
        rows = sync_capability_checks(self.manager)
        return [
            {'name': row.name, 'category': row.category,
             'kind': row.kind, 'criticality': row.criticality,
             'runnerRef': row.runner_ref,
             'description': row.description,
             'lastStatus': row.last_status,
             'lastEvidence': row.last_evidence,
             'lastRunAt': row.last_run_at,
             'lastDurationMs': row.last_duration_ms}
            for row in rows.values()
        ]

    def on_get_matrix(self, request, response):
        category = (request.params or {}).get('category')
        checks = self._check_rows()
        if category:
            checks = [c for c in checks if c['category'] == category]
        checks.sort(key=lambda c: (c['category'], c['name']))
        statuses = {}
        for check in checks:
            statuses[check['lastStatus']] = statuses.get(
                check['lastStatus'], 0) + 1
        response.media = {'ok': True, 'count': len(checks),
                          'statusTotals': statuses,
                          'checks': checks}

    def on_get_runs(self, request, response):
        runs = (self.manager.objectTables.get('CheckRun', {})
                or {}).values()
        summaries = [
            {'name': run.name, 'startedAt': run.started_at,
             'finishedAt': run.finished_at,
             'blockingGreen': bool(run.blocking_green),
             'totals': json.loads(run.totals_json or '{}'),
             'environment': json.loads(
                 run.environment_json or '{}'),
             'reportPath': run.report_path}
            for run in runs
        ]
        summaries.sort(key=lambda s: s['startedAt'], reverse=True)
        response.media = {'ok': True, 'count': len(summaries),
                          'runs': summaries}

    def on_post_run(self, request, response):
        body = request.get_media() or {}
        category = body.get('category')
        names = body.get('checks')
        timeout = body.get('timeout')
        if not (category or names or body.get('all')):
            # A bare POST must never start the ~30min full matrix
            # (the api-sweep probes every route with a minimal body
            # — this refusal is what keeps the sweep from recursing
            # into a nested full run). Full runs are an explicit ask.
            response.status = falcon.HTTP_400
            response.media = {
                'ok': False,
                'refusal': 'unfiltered run must be explicit — the '
                           'full matrix takes tens of minutes',
                'suggestion': "pass {'all': true} for the full "
                              "matrix, or filter with 'category' / "
                              "'checks'"}
            return
        if not select_checks(category=category, names=names):
            response.status = falcon.HTTP_404
            response.media = {
                'ok': False,
                'refusal': 'no catalog checks match that filter',
                'category': category, 'checks': names}
            return
        record = run_matrix(category=category, names=names,
                            manager=self.manager, timeout=timeout)
        response.media = {'ok': True, 'runId': record['id'],
                          'totals': record['totals'],
                          'blockingGreen': record['blocking_green'],
                          'reportPath': record['report_path'],
                          'results': record['results']}
