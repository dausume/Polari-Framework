"""
@module firmwarefaults.custom.api_sc2

The sc-2 / sc-2b doors of FirmwareFaultsAPI (a mixin, so firmwarefaults_api.py stays small):

GET  /api/firmwarefaults/campaigns     the ScenarioCampaign rows (seeded definition + the last run's results)
POST /api/firmwarefaults/campaign      body {campaign, seeds?, rates?} — RUNS the campaign here (minutes): ScenarioStatistic +
                                       FaultLikelihood rows, the fault row's rate_source, the claims' statistics tier
GET  /api/firmwarefaults/likelihoods   the likelihood table per fault kind (FaultLikelihood rows)
GET  /api/firmwarefaults/formal        the FormalCheck rows + where cbmc-check / mthread-check WOULD run (the two ladders)
POST /api/firmwarefaults/formal        body {checks: [name…]} — runs CBMC or Mthread (sc-2c) here, per check; refused (409) naming
                                       FORMAL_ENGINES_URL when that engine does not resolve (both live in prf-formal-engines)
GET  /api/firmwarefaults/static        the StaticCheck rows (cppcheck per variant) + their findings count
POST /api/firmwarefaults/static        body {variants: [name…]} — runs cppcheck here; findings are rows, never a failure
"""
import json

import falcon

ROUTES = (('/api/firmwarefaults/campaigns', 'campaigns'), ('/api/firmwarefaults/campaign', 'campaign'),
          ('/api/firmwarefaults/likelihoods', 'likelihoods'), ('/api/firmwarefaults/formal', 'formal'),
          ('/api/firmwarefaults/static', 'static'))


def _body(request, response):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception as e:  # noqa: BLE001
        response.status = falcon.HTTP_400
        response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
        return None


def _clean(d):
    return {k: v for k, v in d.items() if not k.startswith('_') and k != 'repro_json'}


class Sc2Doors:
    def add_sc2_routes(self, add):
        for path, suffix in ROUTES:
            add(path, self, suffix=suffix)

    def on_get_campaigns(self, request, response):
        response.media = {'ok': True, 'campaigns': [self._d(r) for r in sorted(self._rows('ScenarioCampaign'), key=lambda r: r.name)]}

    def on_post_campaign(self, request, response):
        from firmwarefaults.custom import campaign as C
        from firmwarefaults.custom.sink import ManagerSink
        from firmwarefaults.custom.runner import ScenarioRefused
        from board.custom.engine_run import EngineRefused
        body = _body(request, response)
        if body is None:
            return
        name, seeds = body.get('campaign') or '', body.get('seeds')
        if not C.find(name) or (seeds is not None and not 1 <= int(seeds) <= 200):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'body needs {campaign: %s, seeds?: 1..200, rates?: [..]}' % ' | '.join(c['name'] for c in C.SEED_CAMPAIGNS)}
            return
        try:
            c = C.run_campaign(name, ManagerSink(self.manager), seeds=seeds, rates=body.get('rates'),
                               rows=[self._d(r) for r in self._rows('ScenarioCampaign')] or None)
        except (ScenarioRefused, EngineRefused) as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'campaign': _clean(c) | {'_results': c.get('_results')}}

    def on_get_likelihoods(self, request, response):
        rows = sorted(self._rows('FaultLikelihood'), key=lambda r: (r.fault_class, r.fault, r.parameter_value))
        response.media = {'ok': True, 'likelihoods': [self._d(r) for r in rows]}

    def on_get_formal(self, request, response):
        from firmwarefaults.custom import formal_engines
        response.media = {'ok': True, 'checks': [self._d(r) for r in sorted(self._rows('FormalCheck'), key=lambda r: r.name)],
                          'engines': formal_engines.placement()}

    def on_post_formal(self, request, response):
        from firmwarefaults.custom import formal_mthread as M, formal_engines as fe
        from firmwarefaults.custom.sink import ManagerSink
        body = _body(request, response)
        if body is None:
            return
        names = body.get('checks') or [c['name'] for c in M.all_checks()]
        bad = [n for n in names if not M.find_any(n)]
        if bad:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'unknown FormalCheck %s — one of %s' % (bad, [c['name'] for c in M.all_checks()])}
            return
        sink, out = ManagerSink(self.manager), []
        try:
            for n in names:
                out.append(_clean(M.run_any(n, sink)))
        except fe.FormalRefused as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'checks': out}

    def on_get_static(self, request, response):
        response.media = {'ok': True, 'checks': [self._d(r) for r in sorted(self._rows('StaticCheck'), key=lambda r: r.name)],
                          'findings': len(self._rows('StaticFinding'))}

    def on_post_static(self, request, response):
        from firmwarefaults.custom import static_rules as SR, formal_engines as fe
        from firmwarefaults.custom.sink import ManagerSink
        body = _body(request, response)
        if body is None:
            return
        variants = body.get('variants') or SR.all_variants()
        try:
            out = [_clean(r) for r in SR.run_all(ManagerSink(self.manager), variants)]
        except fe.FormalRefused as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'checks': out, 'not_run': SR.NOT_RUN}
