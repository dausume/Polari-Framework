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
            add('/api/motors/drive/{design_name}', self,
                suffix='drive')
            add('/api/motors/verify/{design_name}', self,
                suffix='verify')
            add('/api/motors/parts/{design_name}', self,
                suffix='parts')
            add('/api/motors/loads/{design_name}', self,
                suffix='loads')
            add('/api/motors/criterion/{material}', self,
                suffix='criterion')
            add('/api/motors/stress/{design_name}/{part_name}',
                self, suffix='stress')
            add('/api/motors/contact/{design_name}/{part_name}',
                self, suffix='contact')
            add('/api/motors/roles/{part_name}', self,
                suffix='roles')
            add('/api/motors/role-screen/{part_name}', self,
                suffix='role_screen')
            add('/api/motors/fatigue/{design_name}/{part_name}',
                self, suffix='fatigue')
            add('/api/motors/substitutes/{design_name}/'
                '{part_name}', self, suffix='substitutes')
            add('/api/motors/winding/{design_name}', self,
                suffix='winding')
            add('/api/motors/winding-sweep/{design_name}', self,
                suffix='winding_sweep')

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

    def on_get_drive(self, request, response, design_name):
        from motors.motor_drive import simplefoc_config
        out = simplefoc_config(
            self.manager, design_name,
            profile_name=request.params.get('profile', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_parts(self, request, response, design_name):
        from motors.motor_parts import part_report
        out = part_report(self.manager, design_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_loads(self, request, response, design_name):
        from motors.motor_stress import load_cases
        try:
            handling = float(request.params.get('handlingN', 5.0))
        except (TypeError, ValueError):
            handling = 5.0
        out = load_cases(self.manager, design_name,
                         handling_force_n=handling)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_criterion(self, request, response, material):
        from motors.motor_stress import failure_criterion
        out = failure_criterion(self.manager, material)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_stress(self, request, response, design_name,
                      part_name):
        from motors.motor_stress import part_stress
        def num(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        out = part_stress(
            self.manager, design_name, part_name,
            refine=int(num('refine', 3)),
            handling_force_n=num('handlingN', 5.0),
            assumption=request.params.get('assumption',
                                          'plane-stress'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_contact(self, request, response, design_name,
                       part_name):
        from motors.contact_wear import contact_stress
        out = contact_stress(
            self.manager, design_name, part_name,
            mating_material=request.params.get('mate') or None)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_roles(self, request, response, part_name):
        from motors.part_roles import part_role_report
        out = part_role_report(self.manager, part_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_role_screen(self, request, response, part_name):
        from motors.part_roles import screen_candidates
        out = screen_candidates(self.manager, part_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def _fatigue_kw(self, request):
        def num(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        return {'years': num('years', 10.0),
                'survival': num('survival', 0.99),
                'required_sf': num('requiredSf', 4.0),
                'handling_force_n': num('handlingN', 5.0)}

    def on_get_fatigue(self, request, response, design_name,
                       part_name):
        from motors.motor_fatigue import part_fatigue
        out = part_fatigue(self.manager, design_name, part_name,
                           **self._fatigue_kw(request))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_substitutes(self, request, response, design_name,
                           part_name):
        from motors.motor_fatigue import substitution_search
        out = substitution_search(self.manager, design_name,
                                  part_name,
                                  **self._fatigue_kw(request))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def _winding_params(self, request):
        def num(param, default=None):
            raw = request.params.get(param)
            if raw in (None, ''):
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default
        awg = num('awg')
        return {'awg': int(awg) if awg is not None else None,
                'temp_c': num('tempC', 20.0),
                'supply_voltage_v': num('supplyV')}

    def on_get_winding(self, request, response, design_name):
        from motors.motor_winding import winding_report
        out = winding_report(self.manager, design_name,
                             **self._winding_params(request))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_winding_sweep(self, request, response, design_name):
        from motors.motor_winding import gauge_sweep
        p = self._winding_params(request)
        p.pop('awg', None)
        out = gauge_sweep(self.manager, design_name, **p)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_verify(self, request, response, design_name):
        from motors.motor_verify import verification_summary
        out = verification_summary(self.manager, design_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_post_verify(self, request, response, design_name):
        import json as json_mod
        from motors.motor_verify import record_verification_run
        try:
            payload = json_mod.load(request.bounded_stream)
        except Exception as exc:  # noqa: BLE001 — bad client body
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': f'bad JSON payload: {exc}'}
            return
        out = record_verification_run(
            self.manager, design_name,
            kind=payload.get('kind', ''),
            steps_commanded=payload.get('stepsCommanded'),
            steps_taken=payload.get('stepsTaken'),
            duration_s=payload.get('durationS'),
            notes=payload.get('notes', ''))
        if not out.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = out
