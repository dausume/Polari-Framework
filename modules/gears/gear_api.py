"""
@module gears.gear_api

/api/gears/* — the gr-1 surface: the type taxonomy (with its
geometry gate visible), the train catalog, and the abstract solve.

@consumers polariServer (constructed when 'gears' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from gears.gear_kinematics import (
    solve_train, train_catalog, type_catalog,
)


class GearsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/gears'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/gears/types', self, suffix='types')
            add('/api/gears/trains', self, suffix='trains')
            add('/api/gears/solve/{train_name}', self,
                suffix='solve')

    def on_get_types(self, request, response):
        response.media = type_catalog(self.manager)

    def on_get_trains(self, request, response):
        response.media = train_catalog(self.manager)

    def on_get_solve(self, request, response, train_name):
        def _num(param):
            raw = request.params.get(param)
            if raw in (None, ''):
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        out = solve_train(self.manager, train_name,
                          input_torque_nm=_num('torqueNm'),
                          input_speed_rpm=_num('speedRpm'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out
