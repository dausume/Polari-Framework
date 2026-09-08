"""
@module gears.gear_api

/api/gears/* — the gr-1 surface: the type taxonomy (with its
geometry gate visible), the train catalog, and the abstract solve.

@consumers polariServer (constructed when 'gears' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from gears.custom.gear_kinematics import (
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
            add('/api/gears/motor-drive/{train_name}', self,
                suffix='motor_drive')
            add('/api/gears/planetary', self, suffix='planetary')
            add('/api/gears/clock-face/{train_name}', self,
                suffix='clock_face')

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

    def on_get_planetary(self, request, response):
        from gears.custom.planetary import (
            motion_works_ratio, planetary_ratio,
        )
        def i(k, d):
            try:
                return int(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        out = planetary_ratio(
            i('sun', 12), i('ring', 132),
            configuration=request.params.get('configuration',
                                             'ring-fixed'),
            n_planets=i('planets', 3))
        if out.get('ok'):
            out['motionWorksAlternative'] = motion_works_ratio()
        else:
            response.status = '400 Bad Request'
        response.media = out

    def on_get_clock_face(self, request, response, train_name):
        from gears.custom.planetary import clock_face_sizing
        cb = request.params.get('counterbalanced', '').lower() \
            == 'true'
        out = clock_face_sizing(self.manager, train_name,
                                counterbalanced=cb)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_motor_drive(self, request, response, train_name):
        # Imported here, not at module import: the splice reaches
        # into motors, and gears must stay usable with motors off
        # (the refusal inside says so by name).
        from gears.custom.gear_motor import motor_driven_train

        def _num(param):
            raw = request.params.get(param)
            if raw in (None, ''):
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        out = motor_driven_train(
            self.manager, train_name,
            design_name=request.params.get('design', ''),
            speed_rpm=_num('speedRpm'),
            required_output_torque_nm=_num('requiredTorqueNm'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out
