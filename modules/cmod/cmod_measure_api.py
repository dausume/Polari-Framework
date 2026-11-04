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
msv-0b (section 5b, the generated step-by-step test and the guided sheet):
GET  .../procedures                                  the frozen TestProcedures;  POST {hex_sha256?, notes?}: generate + freeze (unchanged = the frozen one)
GET  .../procedures/preview                          the generated steps, nothing stored
GET  .../procedures/{procedure}/steps                its steps
GET  .../procedures/{procedure}/steps/{step}/picture the LEFT PANE: where to test, as raw SVG (the generic api-svg-panel inlines it)
GET  .../units/{unit}/sessions                       the unit's TestSessions;  POST {procedure, mode?: guided | touch, who?}: start one
GET  .../sessions/{session}                          the SHEET: one row per step (what to do, what to expect, the answer, the verdict), summary, next
POST .../sessions/{session}/steps/{step}             answer a step: a measure step {value, instrument?, range_max?, note?}; any other {outcome, note?}
POST .../sessions/{session}/resume                   resume: the stimulus steps back to the next step's node are asked again
GET  .../sessions/{session}/print                    the sheet for paper (HTML print view)
GET  .../sessions/{session}/summary                  how many steps per verdict
POST .../sessions/{session}/steps/{step}/take        msv-3 touch and confirm: {endpoint} (a sigrok endpoint on this node) or {instrument, lines}
                                                     (sigrok '-O analog' lines from a Bridge) -> the steady reading, or no-data / not-steady / wrong-mode
404 = no such node / unit / point / instrument / procedure / step / session; 409 = a node with no reached run (run it first), a unit of another
Bench Solution; 422 = a value that is not a number in the point's unit, an answer a step does not take.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import config_rows as R
from cmod.custom import measure_points as MP
from cmod.custom import measure_readings as MR
from cmod.custom import procedure_svg as SVG
from cmod.custom import test_procedures as TP
from cmod.custom import test_sessions as TS
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
            b = '/api/cmod/bench-topology/{bench_solution}'
            add(b + '/procedures', self, suffix='procedures')
            add(b + '/procedures/preview', self, suffix='preview')
            add(b + '/procedures/{procedure}/steps', self, suffix='steps')
            add(b + '/procedures/{procedure}/steps/{step}/picture', self, suffix='picture')
            add(b + '/units/{unit}/sessions', self, suffix='sessions')
            add(b + '/sessions/{session}', self, suffix='sheet')
            add(b + '/sessions/{session}/steps/{step}', self, suffix='answer')
            add(b + '/sessions/{session}/resume', self, suffix='resume')
            add(b + '/sessions/{session}/print', self, suffix='print')
            add(b + '/sessions/{session}/summary', self, suffix='summary')
            add(b + '/sessions/{session}/steps/{step}/take', self, suffix='take')

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

    # msv-0b: the generated procedure and the guided sheet
    def _proc_of(self, bs, proc):
        p = R.get(self.manager, 'TestProcedure', proc)
        if p is None or p['bench_solution'] != bs:
            raise ConfigRefused('no test procedure %r in Bench Solution %r' % (proc, bs), status=404)
        return proc

    def _session_of(self, bs, session):
        s = R.get(self.manager, 'TestSession', session)
        if s is None:
            raise ConfigRefused('no test session %r' % session, status=404)
        _unit_of(self.manager, bs, s['unit'])
        return session

    def on_get_procedures(self, request, response, bench_solution):
        self._do(response, TP.procedures, bench_solution)

    def on_post_procedures(self, request, response, bench_solution):
        self._do(response, TP.freeze, bench_solution, _json(request))

    def on_get_preview(self, request, response, bench_solution):
        self._do(response, lambda m, bs: (lambda g: dict(g, rows=g['steps']))(TP.generate(m, bs)), bench_solution)

    def on_get_steps(self, request, response, bench_solution, procedure):
        self._do(response, lambda m, p: TP.steps(m, self._proc_of(bench_solution, p)), procedure)

    def _raw(self, response, content_type, fn):
        try:
            response.text = fn()
            response.content_type = content_type
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_picture(self, request, response, bench_solution, procedure, step):
        def go():
            self._proc_of(bench_solution, procedure)
            st = R.get(self.manager, 'TestProcedureStep', step)
            if st is None or st['procedure'] != procedure:
                raise ConfigRefused('no step %r in procedure %s' % (step, procedure), status=404)
            return SVG.draw(self.manager, step)
        self._raw(response, 'image/svg+xml', go)

    def on_get_sessions(self, request, response, bench_solution, unit):
        self._do(response, lambda m, u: TS.sessions(m, _unit_of(m, bench_solution, u)), unit)

    def on_post_sessions(self, request, response, bench_solution, unit):
        body = _json(request)
        self._do(response, lambda m, u: TS.start(m, _unit_of(m, bench_solution, u), body), unit)

    def on_get_sheet(self, request, response, bench_solution, session):
        self._do(response, lambda m, s: TS.sheet(m, self._session_of(bench_solution, s)), session)

    def on_post_answer(self, request, response, bench_solution, session, step):
        body = _json(request)
        self._do(response, lambda m, s: TS.answer(m, self._session_of(bench_solution, s), step, body), session)

    def on_post_resume(self, request, response, bench_solution, session):
        self._do(response, lambda m, s: TS.resume(m, self._session_of(bench_solution, s)), session)

    def on_get_print(self, request, response, bench_solution, session):
        self._raw(response, 'text/html', lambda: SVG.print_view(self.manager, self._session_of(bench_solution, session)))

    def on_get_summary(self, request, response, bench_solution, session):
        self._do(response, lambda m, s: TS.sheet(m, self._session_of(bench_solution, s))['summary_rows'], session)

    def on_post_take(self, request, response, bench_solution, session, step):
        body = _json(request)
        self._do(response, lambda m, s: TS.take(m, self._session_of(bench_solution, s), step, body), session)
