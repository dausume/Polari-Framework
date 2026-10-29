"""
@module cmod.cmod_catom_api

hsp-3a doors (HARDWARE_SYSTEM_PINS_PLAN.md §7): Catom assertions and what is derived from them. The rows are the stored CatomAssertion / StructObjectMap rows
(the seeds when the table is empty); every status is recomputed from the variant's cycle record on read.

GET /api/cmod/catom-assertions/{variant}[?view=assertions|bindings|gaps|draft|maps]
        assertions = the rows + status (verified | unverified | false) and why; bindings = one row per (pin, field) an assertion couples (the struct-pin
        bindings, derived); gaps = struct fields no catom asserts + the notebook draft's fields the struct lacks; draft = his draft field -> firmware field;
        maps = StructObjectMap field -> attribute. Without `view`: {ok, variant, assertions, bindings, gaps}. 404 no assertions for the variant; 422 unknown view.
GET /api/cmod/catom-variables/{variant}[?view=variables|assertions|pins|header|slots&variable=V]       hsp-3d: the generalized HAL
        variables = each with value + scope + verdict (accepted | warning | refused) and why; assertions = the defines-role assertions they make; pins = what the
        pin view draws (pin, role, variable, verdict); header = {text} the HAL lines the firmware is generated with; slots = the pins a role slot offers (needs
        `variable`). 404 no variables for the variant; 422 unknown view / variable.
POST /api/cmod/catom-variables/{variant}/check  body {variable, value}  -> {verdict, why[], pin, function}: the same check a value passes before it counts;
        NOTHING is written (choosing a slot writes the bench value in hsp-3c).
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import catom_assertions as CA
from cmod.custom import catom_variables as CV


class CatomAssertionAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/catom-assertions/{variant}', self)

    def _stored(self):
        table = (getattr(self.manager, 'objectTables', None) or {}).get('CatomAssertion') or {}
        return list(table.values()) or None

    def on_get(self, request, response, variant):
        rows = self._stored()
        if not CA.assertions(variant, rows, rec=None):
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no catom assertions for variant %r' % variant}
            return
        view = request.get_param('view') or ''
        if not view:
            response.media = {'ok': True, 'variant': variant, 'assertions': CA.assertions(variant, rows), 'bindings': CA.struct_pin_bindings(variant, rows),
                              'gaps': CA.gaps(variant, rows)}
            return
        if view not in CA.VIEWS:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'view must be one of %s' % ', '.join(CA.VIEWS)}
            return
        out = CA.VIEWS[view](variant, rows)
        response.media = {'ok': True, 'variant': variant, 'view': view, 'count': len(out), 'rows': out}


def _json(request):
    import json
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


class CatomVariableAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}', self)
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}/check', self, suffix='check')

    def _stored(self):
        table = (getattr(self.manager, 'objectTables', None) or {}).get('CatomVariable') or {}
        return list(table.values()) or None

    def _fail(self, response, status, text):
        response.status = status
        response.media = {'ok': False, 'error': text}

    def on_get(self, request, response, variant):
        rows = self._stored()
        vs = CV.variables(variant, rows)
        if not vs:
            return self._fail(response, falcon.HTTP_404, 'no catom variables for variant %r' % variant)
        view = request.get_param('view') or 'variables'
        if view == 'variables':
            out = vs
        elif view == 'assertions':
            out = CV.role_assertions(variant, rows)
        elif view == 'pins':
            out = CV.pin_roles(variant, rows)
        elif view == 'header':
            response.media = {'ok': True, 'variant': variant, 'view': view, 'text': CV.render_header(variant, rows)}
            return
        elif view == 'slots':
            var = next((v for v in vs if v['variable'] == request.get_param('variable')), None)
            if var is None:
                return self._fail(response, falcon.HTTP_422, 'slots needs variable= one of %s' % ', '.join(v['variable'] for v in vs))
            response.media = dict(CV.slots(var, vs), ok=True, variant=variant, view=view)
            return
        else:
            return self._fail(response, falcon.HTTP_422, 'view must be variables, assertions, pins, header or slots')
        response.media = {'ok': True, 'variant': variant, 'view': view, 'count': len(out), 'rows': out}

    def on_post_check(self, request, response, variant):
        body = _json(request)
        vs = CV.variables(variant, self._stored())
        var = next((v for v in vs if v['variable'] == body.get('variable')), None)
        if var is None:
            return self._fail(response, falcon.HTTP_422, 'variable must be one of %s' % ', '.join(v['variable'] for v in vs))
        response.media = dict(CV.check(var, body.get('value', ''), vs), ok=True, variant=variant, variable=var['variable'], written=False)
