"""
@module cmod.cmod_catom_api

hsp-3a doors (HARDWARE_SYSTEM_PINS_PLAN.md §7): Catom assertions and what is derived from them. The rows are the stored CatomAssertion / StructObjectMap rows
(the seeds when the table is empty); every status is recomputed from the variant's cycle record on read.

GET /api/cmod/catom-assertions/{variant}[?view=assertions|bindings|gaps|draft|maps]
        assertions = the rows + status (verified | unverified | false) and why; bindings = one row per (pin, field) an assertion couples (the struct-pin
        bindings, derived); gaps = struct fields no catom asserts + the notebook draft's fields the struct lacks; draft = his draft field -> firmware field;
        maps = StructObjectMap field -> attribute. Without `view`: {ok, variant, assertions, bindings, gaps}. 404 no assertions for the variant; 422 unknown view.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import catom_assertions as CA


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
