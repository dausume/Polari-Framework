"""
@module motors.motor_api

/api/motors/* — the Section-C surface: the ladder of buildable
designs (with builder specs), design reports (role checks at
design time), the M0 clock control-case simulation, torque curves,
and torque_parity.

@consumers polariServer (constructed when 'motors' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.magnet_analysis import _rows
from motors.motor_designer import (
    clock_sim, design_report, torque_curve, torque_parity,
)


class MotorsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/motors'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/motors/designs', self, suffix='designs')
            add('/api/motors/report/{design_name}', self,
                suffix='report')
            add('/api/motors/clock-sim/{design_name}', self,
                suffix='clock_sim')
            add('/api/motors/torque/{design_name}', self,
                suffix='torque')
            add('/api/motors/parity', self, suffix='parity')
            add('/api/motors/materials/{design_name}', self,
                suffix='materials')

    def on_get_designs(self, request, response):
        rows = []
        for d in _rows(self.manager, 'MotorDesignDefinition'):
            rows.append({
                'name': getattr(d, 'name', ''),
                'displayName': getattr(d, 'display_name', ''),
                'description': getattr(d, 'description', ''),
                'topology': getattr(d, 'topology', ''),
                'ladderRung': getattr(d, 'ladder_rung', ''),
                'toleranceTier': getattr(d, 'tolerance_tier', ''),
                'buildRequirements': getattr(
                    d, 'build_requirements_json', '{}'),
                'drive': getattr(d, 'drive_json', '{}'),
            })
        rows.sort(key=lambda r: r['ladderRung'])
        return_rows = {'ok': True, 'designs': rows,
                       'count': len(rows),
                       'ladder': 'M0 clock stepper -> M1 '
                                 'reluctance -> M2 ferrite-PM -> '
                                 'M3 dual-stator axial (easiest '
                                 'buildable sample first)'}
        response.media = return_rows

    def on_get_report(self, request, response, design_name):
        try:
            out = design_report(self.manager, design_name)
        except ValueError as exc:
            out = {'ok': False, 'refusal': str(exc)}
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_clock_sim(self, request, response, design_name):
        try:
            pulses = int(request.params.get('pulses', 10))
        except ValueError:
            pulses = 10
        alternating = request.params.get(
            'alternating', 'true').lower() != 'false'
        try:
            out = clock_sim(self.manager, design_name,
                            pulses=max(1, min(pulses, 100000)),
                            alternating=alternating)
        except ValueError as exc:
            out = {'ok': False, 'refusal': str(exc)}
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_torque(self, request, response, design_name):
        try:
            out = torque_curve(self.manager, design_name)
        except ValueError as exc:
            out = {'ok': False, 'refusal': str(exc)}
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_parity(self, request, response):
        cheap = request.params.get('cheap', '')
        if not cheap:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': '?cheap= is required '
                                         '(MagneticMaterialOption '
                                         'name)'}
            return
        out = torque_parity(
            self.manager, cheap,
            reference=request.params.get('reference', 'opt-ndfeb'),
            dual_gap=request.params.get('dualGap', '').lower()
            == 'true')
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_materials(self, request, response, design_name):
        from motors.motor_materials import material_accountability
        out = material_accountability(self.manager, design_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
