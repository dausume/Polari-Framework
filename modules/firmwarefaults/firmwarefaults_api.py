"""
@module firmwarefaults.firmwarefaults_api

GET  /api/firmwarefaults                 the summary: faults per family, techniques, scenarios (runnable or why not), the
                                         latest run per (scenario, side), the step-kind catalogue, where the engines run
GET  /api/firmwarefaults/faults          every fault row, grouped by family (layer), with its kind fields
GET  /api/firmwarefaults/techniques      the techniques: seeded cost + measured cost (+ the run that measured it)
GET  /api/firmwarefaults/scenarios       the scenarios with their ordered steps and whether each is runnable
GET  /api/firmwarefaults/runs            every ScenarioRun (newest first)
GET  /api/firmwarefaults/runs/{run}      one run + its trace rows + the claim it wrote
GET  /api/firmwarefaults/engines         where avr-twin / avr-objdump / avr-nm / vcd-window WOULD run (nothing is run)
GET  /api/firmwarefaults/statistics      sc-1: the ScenarioStatistic rows (seeded rates with their Wilson intervals)
POST /api/firmwarefaults/stats           sc-1: body {scenario: uart-residual-frame-loss | torn-millis-read, seeds?, bers?} — runs the
                                         statistics batch HERE (minutes) and writes the rows + the fault row's measured rate
POST /api/firmwarefaults/run             body {scenario, side: before|after|both|natural|control, seconds?, seed?} — RUNS it here (the
                                         engines resolve on THIS server's device), writes ScenarioRun + ScenarioTraceCycle rows,
                                         the MathClaim + ProofRun, a pair's measured technique cost, a natural run's measured rate
sc-2 / sc-2b (custom/api_sc2.py): GET /campaigns · POST /campaign · GET /likelihoods · GET|POST /formal · GET|POST /static
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.custom.api_sc2 import Sc2Doors


class FirmwareFaultsAPI(Sc2Doors, treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/firmwarefaults', self, suffix='summary')
            add('/api/firmwarefaults/faults', self, suffix='faults')
            add('/api/firmwarefaults/techniques', self, suffix='techniques')
            add('/api/firmwarefaults/scenarios', self, suffix='scenarios')
            add('/api/firmwarefaults/runs', self, suffix='runs')
            add('/api/firmwarefaults/runs/{run}', self, suffix='run_one')
            add('/api/firmwarefaults/engines', self, suffix='engines')
            add('/api/firmwarefaults/run', self, suffix='run')
            add('/api/firmwarefaults/statistics', self, suffix='statistics')
            add('/api/firmwarefaults/stats', self, suffix='stats')
            self.add_sc2_routes(add)

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row, keys=None):
        import inspect
        keys = keys or [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def on_get_summary(self, request, response):
        from firmwarefaults.firmwarefaults_basis import FAULT_KINDS
        from firmwarefaults.custom import scenarios as SC
        fams = {fam: {c.__name__: len(self._rows(c.__name__)) for c in classes} for fam, classes in FAULT_KINDS.items()}
        runs = sorted(self._rows('ScenarioRun'), key=lambda r: getattr(r, 'ran_at', '') or '', reverse=True)
        latest = {}
        for r in runs:
            latest.setdefault('%s/%s' % (r.scenario, r.side), {k: getattr(r, k, '') for k in ('name', 'outcome', 'fault_cycle', 'fault_symbol', 'landed_symbol',
                                                                                         'torn_value', 'cost_flash_bytes_delta', 'cost_cycles_delta',
                                                                                         'latency_delta_cycles', 'claim', 'ran_at')})
        steps = [self._d(s) for s in self._rows('ScenarioStep')]
        response.media = {'ok': True, 'faults_by_family': fams, 'fault_rows': sum(sum(v.values()) for v in fams.values()),
                          'techniques': len(self._rows('Technique')), 'assumptions': len(self._rows('Assumption')),
                          'primitives': len(self._rows('ConcurrencyPrimitive')),
                          'scenarios': [{'name': s.name, 'status': s.status, 'runnable': SC.runnable(s.name, steps or None)}
                                        for s in sorted(self._rows('Scenario'), key=lambda s: s.name)],
                          'latest_runs': latest, 'step_kinds': {k: {'forcible': ok, 'how_or_why': why} for k, (ok, why) in SC.STEP_KINDS.items()}}

    def on_get_faults(self, request, response):
        from firmwarefaults.firmwarefaults_basis import FAULT_KINDS
        response.media = {'ok': True, 'families': {fam: [dict(self._d(r), kind=c.__name__) for c in classes for r in self._rows(c.__name__)]
                                                   for fam, classes in FAULT_KINDS.items()}}

    def on_get_techniques(self, request, response):
        response.media = {'ok': True, 'techniques': [self._d(t) for t in sorted(self._rows('Technique'), key=lambda t: t.name)]}

    def on_get_scenarios(self, request, response):
        from firmwarefaults.custom import scenarios as SC
        steps = [self._d(s) for s in self._rows('ScenarioStep')]
        out = []
        for s in sorted(self._rows('Scenario'), key=lambda s: s.name):
            d = self._d(s)
            d['steps'] = SC.steps_of(s.name, steps)
            d['runnable'] = SC.runnable(s.name, steps)
            out.append(d)
        response.media = {'ok': True, 'scenarios': out}

    def on_get_runs(self, request, response):
        keys = ('name', 'scenario', 'side', 'variant', 'build_name', 'technique_applied', 'outcome', 'verdict_words', 'fault_cycle', 'fault_pc',
                'fault_symbol', 'landed_pc', 'landed_symbol', 'torn_value', 'frames_seen', 'frames_backwards', 'cost_flash_bytes_delta',
                'cost_cycles_delta', 'latency_delta_cycles', 'claim', 'trace_sha256', 'firmware_sha256', 'seed', 'ran_at', 'observable_value',
                'reset_count', 'isr_cycles_max')
        runs = sorted(self._rows('ScenarioRun'), key=lambda r: getattr(r, 'ran_at', '') or '', reverse=True)
        response.media = {'ok': True, 'runs': [self._d(r, keys) for r in runs]}

    def on_get_run_one(self, request, response, run):
        r = next((x for x in self._rows('ScenarioRun') if x.name == run), None)
        if r is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no ScenarioRun %r' % run}
            return
        trace = sorted((self._d(t) for t in self._rows('ScenarioTraceCycle') if t.run == run), key=lambda t: t['idx'])
        claim = next((self._d(c) for c in self._rows('MathClaim') if c.name == r.claim), None)
        response.media = {'ok': True, 'run': self._d(r), 'trace': trace, 'claim': claim}

    def on_get_engines(self, request, response):
        from firmwarefaults.custom.fault_engines import placement, harness_digest
        response.media = {'ok': True, 'engines': placement(), 'harness': harness_digest()}

    def on_get_statistics(self, request, response):
        rows = sorted(self._rows('ScenarioStatistic'), key=lambda r: getattr(r, 'name', ''))
        response.media = {'ok': True, 'statistics': [self._d(r) for r in rows]}

    def on_post_stats(self, request, response):
        from firmwarefaults.custom import statistics as ST
        from firmwarefaults.custom.sink import ManagerSink
        from firmwarefaults.custom.runner import ScenarioRefused
        from board.custom.engine_run import EngineRefused
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        name, seeds = body.get('scenario') or '', int(body.get('seeds') or ST.SEEDS)
        if name not in ('uart-residual-frame-loss', 'torn-millis-read') or not 1 <= seeds <= 200:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'body needs {scenario: uart-residual-frame-loss | torn-millis-read, seeds: 1..200}'}
            return
        sink = ManagerSink(self.manager)
        try:
            if name == 'uart-residual-frame-loss':
                out = ST.uart_ber(sink, bers=tuple(float(b) for b in (body.get('bers') or ST.BERS)), seeds=seeds)
                rows = list(out.values())
            else:
                out = ST.tear_phase_sweep(sink, seeds=seeds)
                rows = [out['natural_row'], out['sweep']]
        except (ScenarioRefused, EngineRefused) as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'scenario': name, 'statistics': [{k: v for k, v in r.items() if k != 'repro_json'} for r in rows]}

    def on_post_run(self, request, response):
        from firmwarefaults.custom import runner
        from firmwarefaults.custom.sink import ManagerSink
        from board.custom.engine_run import EngineRefused
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        name, side = body.get('scenario') or '', body.get('side') or 'both'
        if not name:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'body needs {scenario, side: before|after|both|natural|control}'}
            return
        steps = [self._d(s) for s in self._rows('ScenarioStep')] or None
        scen = [self._d(s) for s in self._rows('Scenario')] or None
        try:
            out = runner.run_scenario(name, side, ManagerSink(self.manager), seconds=body.get('seconds'), seed=body.get('seed'),
                                      scenario_rows=scen, step_rows=steps)
        except (runner.ScenarioRefused, EngineRefused) as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'scenario': name, 'runs': [{k: v for k, v in r.items() if not k.startswith('_') and k != 'observed_json' and k != 'repro_json'}
                                                                 | {'claim_flip': list(r.get('_claim_flip', ())), 'trace_rows': len(r.get('_trace_rows', []))}
                                                                 for r in out['runs']]}
