"""
@module cmod.cmod_measure_api

msv-0 doors (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md): a node's measurement points, the built units of a Bench Solution and their real readings. The
work is in cmod.custom.measure_points / measure_readings; these doors only read the request and say a refusal in words.

GET  /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/measurement-points    the node's points (what to measure, where, the prediction and its basis)
POST /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/measurement-points    derive them again from the node's latest reached run's circuit state
GET  /api/cmod/bench-topology/{bench_solution}/units                              the Bench Solution's built units
POST /api/cmod/bench-topology/{bench_solution}/units                              body {name?, hex_sha256?, build_method?, built_by?, layout?, notes?}: a BuiltUnit
GET  /api/cmod/bench-topology/{bench_solution}/units/{unit}/readings              every reading of the unit, judged on read, newest first
POST /api/cmod/bench-topology/{bench_solution}/units/{unit}/readings              body {point, value ('14.2 mA' or a number + unit), instrument?, range_max?, who?, note?,
                                                                                  via? (manual), evidence_sha256?}: one reading -> the row + its judgement
404 = no such node / unit / point / instrument; 409 = a node with no reached run (run it first); 422 = a value that is not a number in the point's unit.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import config_rows as R
from cmod.custom import measure_points as MP
from cmod.custom import measure_readings as MR
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


def _json(request):
    try:
        v = json.loads(request.bounded_stream.read() or b'{}')
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _unit_of(manager, bs, unit):
    u = R.get(manager, 'BuiltUnit', unit)
    if u is None or u['bench_solution'] != bs:
        raise ConfigRefused('no built unit %r in Bench Solution %r' % (unit, bs), status=404)
    return unit


class MeasureAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/measurement-points', self, suffix='points')
            add('/api/cmod/bench-topology/{bench_solution}/units', self, suffix='units')
            add('/api/cmod/bench-topology/{bench_solution}/units/{unit}/readings', self, suffix='readings')

    def _do(self, response, fn, *args):
        try:
            out = fn(self.manager, *args)
            response.media = {'ok': True, 'rows': out} if isinstance(out, list) else dict(out, ok=True)
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_points(self, request, response, bench_solution, slug):
        self._do(response, MP.points, '%s:%s' % (bench_solution, slug))

    def on_post_points(self, request, response, bench_solution, slug):
        self._do(response, MP.derive, '%s:%s' % (bench_solution, slug))

    def on_get_units(self, request, response, bench_solution):
        self._do(response, MR.units, bench_solution)

    def on_post_units(self, request, response, bench_solution):
        self._do(response, MR.add_unit, bench_solution, _json(request))

    def on_get_readings(self, request, response, bench_solution, unit):
        self._do(response, lambda m, u: MR.readings(m, _unit_of(m, bench_solution, u)), unit)

    def on_post_readings(self, request, response, bench_solution, unit):
        body = _json(request)
        self._do(response, lambda m, u: MR.add_reading(m, _unit_of(m, bench_solution, u), body), unit)
