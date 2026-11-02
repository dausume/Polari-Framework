"""
@module cmod.cmod_confirmations_api

bss-3 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): confirmations, edge checks and test profiles of a Bench Solution's topology. The work is in
cmod.custom.confirmations / node_run / bench_topology; these doors only read the request and say a refusal in words.

GET  /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/confirmations          the node's confirmations, newest first (voided ones kept, marked)
POST /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/confirm                body {who, words, path?}: a person's confirmation
POST /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/hardware-record        body {hex_sha256, source, fields: {field: value}, duration_s, path?}: a real board's
                                                                                   record judged against the node's requirements -> a hardware confirmation or 422 with the field
POST /api/cmod/bench-topology/{bench_solution}/checks                              body {edge, kind, field, value, tolerance, bound_s}: a StructEdgeCheck -> the row
POST /api/cmod/bench-topology/{bench_solution}/profiles                            body {name, title, items: [{kind, signal, object_map}]}: a manual TestProfile -> the profile + items
GET  /api/cmod/bench-topology/{bench_solution}/profiles                            the Bench Solution's and the shared profiles with their items
404 = no such node / edge; 422 = a record that does not meet the requirements, a check without what it needs.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import confirmations as C
from cmod.custom import config_rows as R
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


def _json(request):
    try:
        v = json.loads(request.bounded_stream.read() or b'{}')
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def add_check(manager, bs, body):
    edge = R.get(manager, 'StructEdge', str(body.get('edge') or ''))
    if edge is None or edge['bench_solution'] != bs:
        raise ConfigRefused('no edge %r in Bench Solution %r' % (body.get('edge'), bs), status=404)
    kind = str(body.get('kind') or 'timing')
    field = str(body.get('field') or '')
    if kind == 'timing' and body.get('bound_s') is None:
        raise ConfigRefused('a timing check needs bound_s')
    if kind == 'field-tolerance' and (not field or body.get('tolerance') is None):
        raise ConfigRefused('a field-tolerance check needs the field and a tolerance (an analog field without one cannot be checked)')
    if kind == 'field-range' and (not field or '..' not in str(body.get('value', ''))):
        raise ConfigRefused('a field-range check needs the field and value lo..hi')
    name = '%s:%s:%s' % (edge['name'], kind, field or 'edge')
    return R.upsert(manager, 'StructEdgeCheck', name, edge=edge['name'], kind=kind, field=field, value=str(body.get('value', '')), tolerance=float(body.get('tolerance') or 0),
                    bound_s=float(body['bound_s']) if body.get('bound_s') is not None else -1.0, notes=str(body.get('notes') or ''))


def add_profile(manager, bs, body):
    name = str(body.get('name') or '')
    items = body.get('items') or []
    if not name or not items:
        raise ConfigRefused('a profile needs a name and at least one item')
    prof = R.upsert(manager, 'TestProfile', name, title=str(body.get('title') or ''), bench_solution=bs if body.get('shared') is not True else '', basis='manual')
    R.drop(manager, 'TestProfileItem', profile=name)
    rows = []
    for it in items:
        kind, signal = str(it.get('kind') or 'field'), str(it.get('signal') or '')
        if kind not in ('field', 'pin', 'timing') or not signal:
            raise ConfigRefused('a profile item is a field, a pin or a timing, with its signal named')
        rows.append(R.upsert(manager, 'TestProfileItem', '%s:%s:%s' % (name, kind, signal), profile=name, kind=kind, signal=signal, object_map=str(it.get('object_map') or ''),
                             step_s=float(it.get('step_s', -1.0)), engine=str(it.get('engine') or 'twin')))
    return dict(prof, items=rows)


def profiles(manager, bs):
    out = []
    for p in R.rows(manager, 'TestProfile'):
        if p['bench_solution'] in ('', bs):
            out.append(dict(p, items=R.rows(manager, 'TestProfileItem', profile=p['name'])))
    return sorted(out, key=lambda p: p['name'])


class ConfirmationsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/confirmations', self, suffix='confirmations')
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/confirm', self, suffix='confirm')
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/hardware-record', self, suffix='hardware_record')
            add('/api/cmod/bench-topology/{bench_solution}/checks', self, suffix='checks')
            add('/api/cmod/bench-topology/{bench_solution}/profiles', self, suffix='profiles')

    def _do(self, response, fn, *args):
        try:
            out = fn(self.manager, *args)
            response.media = {'ok': True, 'rows': out} if isinstance(out, list) else dict(out, ok=True)
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_confirmations(self, request, response, bench_solution, slug):
        self._do(response, C.of, '%s:%s' % (bench_solution, slug))

    def on_post_confirm(self, request, response, bench_solution, slug):
        b = _json(request)
        self._do(response, C.attest, '%s:%s' % (bench_solution, slug), str(b.get('who') or ''), str(b.get('words') or ''), str(b.get('path') or ''))

    def on_post_hardware_record(self, request, response, bench_solution, slug):
        b = _json(request)
        self._do(response, C.from_record, '%s:%s' % (bench_solution, slug), str(b.get('path') or ''), b)

    def on_post_checks(self, request, response, bench_solution):
        self._do(response, add_check, bench_solution, _json(request))

    def on_post_profiles(self, request, response, bench_solution):
        self._do(response, add_profile, bench_solution, _json(request))

    def on_get_profiles(self, request, response, bench_solution):
        self._do(response, profiles, bench_solution)
