"""
@module instruments.instruments_api

osc-0 doors (OSCILLOSCOPE_PLAN.md §2):
    GET  /api/instruments                             the models with the card's text fields ({ok, rows})
    GET  /api/instruments/bench-options?bench=        the models with on_bench / can_add for the workbench picker
    GET  /api/instruments/bench/{bench}               the instruments on a bench
    POST /api/instruments/bench/{bench}/add           {model, count?, note?}   -> 201 {ok, bench, added, count, rows}
    POST /api/instruments/bench/{bench}/remove        {model}                  -> 200 {ok, bench, removed, rows}
osc-3 (instruments.custom.captures):
    GET  /api/instruments/endpoints                   the reachable instruments (address typed, never seeded)
    POST /api/instruments/endpoints                   {name, instrument, transport, address, port?, resource?, note?} -> 201
    POST /api/instruments/emulators                   {profile?, name?, strict_idn?, refuse_wav_data?, sources?} -> starts an emulator in this
                                                      process on a free loopback port and adds its endpoint -> 201 {endpoint, port, session}
    POST /api/instruments/emulators/{name}/stop       -> 200
    POST /api/instruments/emulators/{name}/source     {channel, source: {kind, ...}} -> 200
    POST /api/instruments/emulators/{name}/feed       osc-4: {stimulus, channels: {"1": "PD2", "2": "adc0"}} | {events, cps, seconds, channels} -> 200
    POST /api/instruments/endpoints/{name}/idn        asks *IDN? -> 200 {idn} | 502 {error: the refusal words}
    POST /api/instruments/endpoints/{name}/capture    {channels?, max_points?, fmt?} -> 201 {acquisition, rows: per-channel summary}
    GET  /api/instruments/captures                    every capture's summary (sha, points, span, v min/max/mean)
    GET  /api/instruments/captures/{acq}/chart?max=   long-form {t_s, ch1..ch4} rows for named-graph-panel (stride-decimated to <= max, default 4000)
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: falcon.HTTP_200, 201: falcon.HTTP_201, 400: falcon.HTTP_400, 404: falcon.HTTP_404, 409: falcon.HTTP_409, 502: falcon.HTTP_502}


class InstrumentsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/instruments', self, suffix='models')
            add('/api/instruments/bench-options', self, suffix='bench_options')
            add('/api/instruments/bench/{bench}', self, suffix='bench')
            add('/api/instruments/bench/{bench}/add', self, suffix='add')
            add('/api/instruments/bench/{bench}/remove', self, suffix='remove')
            add('/api/instruments/endpoints', self, suffix='endpoints')
            add('/api/instruments/endpoints/{name}/idn', self, suffix='idn')
            add('/api/instruments/endpoints/{name}/capture', self, suffix='capture')
            add('/api/instruments/emulators', self, suffix='emulators')
            add('/api/instruments/emulators/{name}/stop', self, suffix='emulator_stop')
            add('/api/instruments/emulators/{name}/source', self, suffix='emulator_source')
            add('/api/instruments/emulators/{name}/feed', self, suffix='emulator_feed')
            add('/api/instruments/captures', self, suffix='captures')
            add('/api/instruments/captures/{acq}/chart', self, suffix='chart')

    def _get(self, request, response, which, bench=''):
        from instruments.custom import catalog as C
        status, payload = C.get_door(self.manager, request.params, which, bench)
        response.status, response.media = _STATUS[status], payload

    def _post(self, request, response, which, bench):
        from instruments.custom import catalog as C
        try:
            body = json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = falcon.HTTP_400, {'ok': False, 'error': 'the body is not JSON'}
            return
        status, payload = C.post_door(self.manager, bench, which, body)
        response.status, response.media = _STATUS[status], payload

    def on_get_models(self, request, response):
        self._get(request, response, 'models')

    def on_get_bench_options(self, request, response):
        self._get(request, response, 'bench-options')

    def on_get_bench(self, request, response, bench):
        self._get(request, response, 'bench', bench)

    def on_post_add(self, request, response, bench):
        self._post(request, response, 'add', bench)

    def on_post_remove(self, request, response, bench):
        self._post(request, response, 'remove', bench)

    # ---------------------------------------------------------------- osc-3
    def _body(self, request, response):
        try:
            return json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = falcon.HTTP_400, {'ok': False, 'error': 'the body is not JSON'}
            return None

    def _answer(self, response, status, payload):
        response.status, response.media = _STATUS.get(status, falcon.HTTP_502), payload

    def on_get_endpoints(self, request, response):
        from instruments.custom import captures as X
        self._answer(response, 200, {'ok': True, 'rows': X.endpoints(self.manager)})

    def on_post_endpoints(self, request, response):
        from instruments.custom import captures as X
        body = self._body(request, response)
        if body is not None:
            self._answer(response, *X.add_endpoint(self.manager, body))

    def on_post_emulators(self, request, response):
        from instruments.custom import captures as X
        body = self._body(request, response)
        if body is not None:
            self._answer(response, *X.start_emulator(self.manager, body))

    def on_post_emulator_stop(self, request, response, name):
        from instruments.custom import captures as X
        self._answer(response, *X.stop_emulator(self.manager, name))

    def on_post_emulator_source(self, request, response, name):
        from instruments.custom import captures as X
        body = self._body(request, response)
        if body is not None:
            self._answer(response, *X.set_source(self.manager, name, body))

    def on_post_emulator_feed(self, request, response, name):
        from instruments.custom import captures as X
        body = self._body(request, response)
        if body is not None:
            self._answer(response, *X.feed_device(self.manager, name, body))

    def on_post_idn(self, request, response, name):
        from instruments.custom import captures as X
        self._answer(response, *X.idn(self.manager, name))

    def on_post_capture(self, request, response, name):
        from instruments.custom import captures as X
        body = self._body(request, response)
        if body is not None:
            self._answer(response, *X.capture(self.manager, name, body))

    def on_get_captures(self, request, response):
        from instruments.custom import captures as X
        self._answer(response, 200, {'ok': True, 'rows': X.capture_rows(self.manager)})

    def on_get_chart(self, request, response, acq):
        from instruments.custom import captures as X
        try:
            max_rows = int(request.params.get('max') or 4000)
        except ValueError:
            max_rows = 4000
        self._answer(response, *X.chart_rows(self.manager, acq, max_rows))
