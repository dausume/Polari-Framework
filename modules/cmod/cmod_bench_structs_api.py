"""
@module cmod.cmod_bench_structs_api

hsp-3b door (HARDWARE_SYSTEM_PINS_PLAN.md §7 "The two bench views"): the Structs view's rows, derived on read from the stored rows (PolariBridgeInstance,
BridgePath, HardwareInterfaceBinding, StructObjectMap, CatomAssertion - the seeds where a table is empty). Model: `cmod.custom.bench_structs`.

GET /api/cmod/bench-structs/{bench}[?view=instances|fields|path&instance=I&field=F&bridge=B]
        instances = one row per struct instance on the bench (`bridge` narrows it to the structs crossing one bridge - the Bridges view's list);
        fields = the instance's fields with the Polari attribute, the catoms that change / read each, the pins and the verdict (needs `instance`);
        path = the signal paths that change the field, one row per hop (route, step, kind pin | catom | field | bridge | object | gap, status) (needs
        `instance` + `field`). An empty `instance` / `field` (nothing clicked yet) = no rows, said. 422 unknown view; 404 an instance not on the bench.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import bench_structs as BS


class BenchStructsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/bench-structs/{bench}', self)

    def _table(self, cls):
        return list(((getattr(self.manager, 'objectTables', None) or {}).get(cls) or {}).values()) or None

    def _rows(self):
        return {'bridge_rows': self._table('PolariBridgeInstance'), 'path_rows': self._table('BridgePath'), 'binding_rows': self._table('HardwareInterfaceBinding'),
                'map_rows': self._table('StructObjectMap'), 'assertion_rows': self._table('CatomAssertion')}

    def on_get(self, request, response, bench):
        view = request.get_param('view') or 'instances'
        if view not in BS.VIEWS:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'view must be one of %s' % ', '.join(BS.VIEWS)}
            return
        rows = self._rows()
        instance, field = request.get_param('instance') or '', request.get_param('field') or ''
        if view == 'instances':
            # `tab` = the page tab a click on the row opens (the Bridges view's crossing list jumps into Structs at the instance)
            out = [dict(r, tab='structs') for r in BS.instances(bench, bridge=request.get_param('bridge') or '', **rows)]
        elif not instance or (view == 'path' and not field):
            response.media = {'ok': True, 'bench': bench, 'view': view, 'count': 0, 'rows': [],
                              'note': 'pick a struct instance%s first' % ('' if view == 'fields' else ' and one of its fields')}
            return
        else:
            out = BS.fields(bench, instance, **rows) if view == 'fields' else BS.path(bench, instance, field, **rows)
            if out is None:
                response.status = falcon.HTTP_404
                response.media = {'ok': False, 'error': 'no struct instance %r on bench %r' % (instance, bench)}
                return
        response.media = {'ok': True, 'bench': bench, 'view': view, 'count': len(out), 'rows': out}
