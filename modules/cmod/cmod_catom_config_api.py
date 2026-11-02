"""
@module cmod.cmod_catom_config_api

cfg-0 doors (AI-Notes/plans/CATOM_CONFIG_PLAN.md): a catom's configuration in one firmware solution, judged in one Bench Solution. The work is in
cmod.custom.catom_config; these doors only read the request and say the refusal in words.

GET  /api/cmod/config-groups                                    the variable groups, verdicts, option levels and check layers (the words)
GET  /api/cmod/catom-config/{bench_solution}/{catom}            the stored view: the configuration, per group the chosen option (flagged when invalid
                                                                here), every option's verdict, score and checks, the choice's verdict elsewhere
POST /api/cmod/catom-config/{bench_solution}/{catom}/evaluate   run the checks, write the verdicts, set the automatic choices -> the view
POST /api/cmod/catom-config/{bench_solution}/{catom}/choose     body {option}: a person's choice (422 when invalid here, with why); option '' = back
                                                                to the automatic choice -> the view
POST /api/cmod/catom-config/{bench_solution}/{catom}/isotope    body {isotope}: how the catom does its job (changes the code); re-evaluated -> the view
404 = no such Bench Solution / conditions / option; 409 = no live server to keep rows in.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import catom_config as CF
from cmod.custom import config_checks as CC
from cmod.custom import config_groups as G
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


def _json(request):
    try:
        v = json.loads(request.bounded_stream.read() or b'{}')
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


class CatomConfigAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            app = polServer.falconServer
            app.add_route('/api/cmod/config-groups', self, suffix='groups')
            app.add_route('/api/cmod/catom-config/{bench_solution}/{catom}', self)
            app.add_route('/api/cmod/catom-config/{bench_solution}/{catom}/evaluate', self, suffix='evaluate')
            app.add_route('/api/cmod/catom-config/{bench_solution}/{catom}/choose', self, suffix='choose')
            app.add_route('/api/cmod/catom-config/{bench_solution}/{catom}/isotope', self, suffix='isotope')

    def _do(self, response, fn, *args):
        try:
            response.media = fn(self.manager, *args)
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_groups(self, request, response):
        response.media = {'ok': True, 'verdicts': list(G.VERDICTS), 'levels': list(G.LEVELS), 'layers': G.LAYERS,
                          'rows': [dict(v, group=k, checks=CC.checks(k)) for k, v in G.GROUPS.items()]}

    def on_get(self, request, response, bench_solution, catom):
        self._do(response, CF.view, bench_solution, catom)

    def on_post_evaluate(self, request, response, bench_solution, catom):
        self._do(response, CF.evaluate, bench_solution, catom)

    def on_post_choose(self, request, response, bench_solution, catom):
        self._do(response, CF.choose, bench_solution, catom, str(_json(request).get('option') or ''))

    def on_post_isotope(self, request, response, bench_solution, catom):
        isotope = str(_json(request).get('isotope') or '')

        def go(manager, bs, cat):
            ctx = CF.context(manager, bs)
            CF.set_isotope(manager, ctx['firmware_solution'], cat, isotope)
            return CF.evaluate(manager, bs, cat)
        self._do(response, go, bench_solution, catom)
