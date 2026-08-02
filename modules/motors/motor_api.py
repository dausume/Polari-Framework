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
from motors.m1_sequencing import (
    holding_torque, m1_minimum_drive_current, sequence_sim,
)
# m1-2: importing m1_views registers the M1 section sources into
# clock_views.SECTION_SOURCES before any view payload assembles.
import motors.m1_views  # noqa: F401
# m2-3: the same registration for the M2 rung — one import, and
# every view-m2-* row's sections can find their engines.
import motors.m2_views  # noqa: F401


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
            # m1-1: the sequencing solver (clock_sim's analog for
            # the reluctance rung).
            add('/api/motors/m1-sequence/{design_name}', self,
                suffix='m1_sequence')
            add('/api/motors/m1-holding/{design_name}', self,
                suffix='m1_holding')
            add('/api/motors/m1-min-current/{design_name}', self,
                suffix='m1_min_current')
            # m1-5: the printer-axis positioning proof.
            add('/api/motors/m1-axis/{design_name}', self,
                suffix='m1_axis')
            add('/api/motors/m1-positioning-proof/{design_name}',
                self, suffix='m1_positioning_proof')
            # mq-3: inter-part correlations + the overlap gap.
            add('/api/motors/m1-relations', self,
                suffix='m1_relations')
            add('/api/motors/m1-overlap-gap', self,
                suffix='m1_overlap_gap')
            add('/api/motors/m1-arc-rule', self,
                suffix='m1_arc_rule')
            # m2-1/m2-5: the PM rung — rotation, its duty limit,
            # the back-EMF constant, and THE LIFT PROOF.
            add('/api/motors/m2-rotation/{design_name}', self,
                suffix='m2_rotation')
            add('/api/motors/m2-pull-out/{design_name}', self,
                suffix='m2_pull_out')
            add('/api/motors/m2-back-emf/{design_name}', self,
                suffix='m2_back_emf')
            add('/api/motors/m2-hoist/{design_name}', self,
                suffix='m2_hoist')
            add('/api/motors/m2-lift-proof/{design_name}', self,
                suffix='m2_lift_proof')
            add('/api/motors/m2-relations', self,
                suffix='m2_relations')
            # mq-4: the engine-number accountability report.
            add('/api/motors/materials-audit', self,
                suffix='materials_audit')
            add('/api/motors/parity', self, suffix='parity')
            add('/api/motors/materials/{design_name}', self,
                suffix='materials')
            add('/api/motors/drive/{design_name}', self,
                suffix='drive')
            add('/api/motors/stator-variants', self,
                suffix='stator_variants')
            # view-1: discipline-split views as data + the
            # component-focused view.
            add('/api/motors/clock-views', self,
                suffix='clock_views')
            add('/api/motors/clock-view/{view_name}', self,
                suffix='clock_view')
            add('/api/motors/clock-scene/{view_name}', self,
                suffix='clock_scene')
            add('/api/motors/clock-assembly', self,
                suffix='clock_assembly')
            add('/api/motors/timekeeping-proof', self,
                suffix='timekeeping_proof')
            add('/api/motors/product-routes', self,
                suffix='product_routes')
            add('/api/motors/bench-campaign', self,
                suffix='bench_campaign')
            add('/api/motors/distributed-traction', self,
                suffix='distributed_traction')
            add('/api/motors/component-view/{part_name}', self,
                suffix='component_view')
            # goal-1..3: goals + constraints over composition's
            # equations — the scale study.
            add('/api/motors/goals', self, suffix='goals')
            add('/api/motors/goal/{goal_name}', self, suffix='goal')
            add('/api/motors/scale-study', self,
                suffix='scale_study')
            # arch-8: the design as a composition view (wrap, not
            # port) + Boothroyd-gated promotion suggestions.
            add('/api/motors/composition-view/{design_name}', self,
                suffix='composition_view')
            add('/api/motors/promotion-candidates/{design_name}',
                self, suffix='promotion_candidates')
            add('/api/motors/simplest', self,
                suffix='simplest')
            add('/api/motors/road-to-advanced', self,
                suffix='road_to_advanced')
            add('/api/motors/wire-insulation', self,
                suffix='wire_insulation')
            add('/api/motors/local-wire-route', self,
                suffix='local_wire_route')
            add('/api/motors/inductance', self,
                suffix='inductance')
            add('/api/motors/inductance-turns', self,
                suffix='inductance_turns')
            add('/api/motors/model-validity', self,
                suffix='model_validity')
            add('/api/motors/local-route', self,
                suffix='local_route')
            add('/api/motors/producible-clock', self,
                suffix='producible_clock')
            add('/api/motors/turns-sweep', self,
                suffix='turns_sweep')
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
            add('/api/motors/true-price/{design_name}/'
                '{part_name}', self, suffix='true_price')
            add('/api/motors/contact/{design_name}/{part_name}',
                self, suffix='contact')
            add('/api/motors/equations', self, suffix='equations')
            add('/api/motors/product/{design_name}', self,
                suffix='product')
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

    def on_get_m1_sequence(self, request, response, design_name):
        def num(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        steps = int(max(1, min(num('steps', 12), 100000)))
        amps = request.params.get('amps')
        try:
            amps = float(amps) if amps is not None else None
        except (TypeError, ValueError):
            amps = None
        out = sequence_sim(
            self.manager, design_name, steps=steps,
            load_torque_nm=num('load', 0.0),
            direction=int(num('direction', 1)),
            start_deg=num('start', 0.0), amps=amps)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_holding(self, request, response, design_name):
        amps = request.params.get('amps')
        try:
            amps = float(amps) if amps is not None else None
        except (TypeError, ValueError):
            amps = None
        out = holding_torque(self.manager, design_name, amps=amps)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_min_current(self, request, response,
                              design_name):
        load = request.params.get('load')
        try:
            load = float(load) if load is not None else None
        except (TypeError, ValueError):
            load = None
        out = m1_minimum_drive_current(self.manager, design_name,
                                       load_torque_nm=load)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_axis(self, request, response, design_name):
        from motors.m1_positioning import axis_report
        out = axis_report(self.manager, design_name)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_positioning_proof(self, request, response,
                                    design_name):
        from motors.m1_positioning import positioning_proof
        def num(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        steps = int(max(1, min(num('steps', 48), 100000)))
        load = request.params.get('load')
        try:
            load = float(load) if load is not None else None
        except (TypeError, ValueError):
            load = None
        out = positioning_proof(
            self.manager, design_name, commanded_steps=steps,
            load_torque_nm=load,
            direction=int(num('direction', 1)))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_relations(self, request, response):
        from motors.m1_relations import relation_report
        out = relation_report(self.manager)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_overlap_gap(self, request, response):
        from motors.m1_relations import overlap_model_gap
        out = overlap_model_gap(self.manager)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m1_arc_rule(self, request, response):
        """cons-3: the SRM arc feasibility rules read off the LIVE
        shape rows — the check that caught the seeded M1 unable to
        start once the exact overlap was adopted."""
        from motors.m1_relations import arc_rule_report
        out = arc_rule_report(self.manager)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_rotation(self, request, response, design_name):
        from motors.m2_rotation import rotation_sim

        def num(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        steps = int(max(3, min(num('steps', 12), 10000)))
        amps = request.params.get('amps')
        try:
            amps = float(amps) if amps is not None else None
        except (TypeError, ValueError):
            amps = None
        out = rotation_sim(
            self.manager, design_name, steps=steps,
            load_torque_nm=num('load', 0.0),
            direction=int(num('direction', 1)), amps=amps,
            rotor_material=request.params.get('rotor', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_pull_out(self, request, response, design_name):
        from motors.m2_rotation import pull_out_load_limit
        out = pull_out_load_limit(
            self.manager, design_name,
            rotor_material=request.params.get('rotor', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_back_emf(self, request, response, design_name):
        from motors.m2_rotation import back_emf_constant
        out = back_emf_constant(
            self.manager, design_name,
            rotor_material=request.params.get('rotor', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_hoist(self, request, response, design_name):
        from motors.m2_lift import hoist_report
        out = hoist_report(self.manager, design_name)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_lift_proof(self, request, response, design_name):
        from motors.m2_lift import lift_proof
        out = lift_proof(self.manager, design_name)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_m2_relations(self, request, response):
        from motors.m2_composition import m2_relation_report
        out = m2_relation_report(self.manager)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_materials_audit(self, request, response):
        from motors.materials_audit import materials_audit
        out = materials_audit(
            self.manager,
            request.params.get('design', 'reluctance-6s4p-m1'))
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

    def on_get_true_price(self, request, response, design_name,
                          part_name):
        from motors.lifecycle_cost import cheapest_configuration
        try:
            hz = float(request.params.get('horizonYears', 10.0))
        except (TypeError, ValueError):
            hz = 10.0
        out = cheapest_configuration(
            self.manager, design_name, part_name,
            kind=request.params.get('kind', 'timekeeper'),
            horizon_years=hz)
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

    def on_get_product(self, request, response, design_name):
        from motors.clock_product import product_datasheet
        out = product_datasheet(
            self.manager, design_name,
            train_name=request.params.get('train',
                                          'clock-train-m0'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_equations(self, request, response):
        from motors.physics_equations import (
            equation_catalog, evaluate_named,
        )
        name = request.params.get('evaluate')
        if not name:
            response.media = equation_catalog()
            return
        bindings = {}
        for k, v in request.params.items():
            if k == 'evaluate':
                continue
            try:
                bindings[k] = float(v)
            except (TypeError, ValueError):
                bindings[k] = v
        out = evaluate_named(name, bindings, manager=self.manager)
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

    def on_get_local_route(self, request, response):
        from motors.local_route import solve_local_route
        out = solve_local_route(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_producible_clock(self, request, response):
        from motors.local_route import producible_clock
        out = producible_clock(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_turns_sweep(self, request, response):
        from motors.local_route import turns_sweep
        out = turns_sweep(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'),
            rotor_material=request.params.get('rotor', ''),
            stator_material=request.params.get('stator', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_inductance(self, request, response):
        from motors.inductance import pulse_response
        out = pulse_response(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'),
            stator_material=request.params.get('stator', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_inductance_turns(self, request, response):
        from motors.inductance import inductance_across_turns
        out = inductance_across_turns(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'),
            stator_material=request.params.get('stator', ''))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_model_validity(self, request, response):
        from motors.inductance import model_validity
        out = model_validity(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_wire_insulation(self, request, response):
        from motors.wire_insulation import (
            insulated_winding_effect, insulation_catalog,
        )
        def i(k, d):
            try:
                return int(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        out = insulated_winding_effect(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'),
            turns=i('turns', 15000), awg=i('awg', 46))
        if out.get('ok'):
            out['catalog'] = insulation_catalog()
        else:
            response.status = '400 Bad Request'
        response.media = out

    def on_get_local_wire_route(self, request, response):
        from motors.wire_insulation import local_wire_route
        out = local_wire_route(
            self.manager,
            request.params.get('design', 'clock-lavet-m0'))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_simplest(self, request, response):
        from motors.simple_first import manufacturable_ladder
        def f(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        out = manufacturable_ladder(
            self.manager, mmf=f('mmf', 21.45),
            supply=request.params.get('supply', 'one-alkaline-cell'),
            target_years=f('targetYears', 4.0),
            max_window_mm2=f('maxWindowMm2', 900.0))
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out

    def on_get_road_to_advanced(self, request, response):
        from motors.simple_first import road_to_advanced
        response.media = road_to_advanced(self.manager)

    def on_get_clock_views(self, request, response):
        from composition.data_refs import rows as _crows
        out = []
        for v in _crows(self.manager, 'ClockViewDefinition'):
            out.append({'name': getattr(v, 'name', ''),
                        'displayName': getattr(v, 'display_name',
                                               ''),
                        'discipline': getattr(v, 'discipline', ''),
                        'scaleSupport': getattr(v, 'scale_support',
                                                ''),
                        'description': getattr(v, 'description',
                                               '')})
        out.sort(key=lambda r: r['name'])
        response.media = {'ok': True, 'views': out,
                          'count': len(out)}

    def on_get_clock_view(self, request, response, view_name):
        from motors.clock_views import view_payload
        response.media = view_payload(
            self.manager, view_name,
            design=request.params.get('design', 'clock-lavet-m0'),
            goal=request.params.get('goal', ''),
            component=request.params.get('component', ''),
            policy=request.params.get('policy', ''))

    def on_get_clock_scene(self, request, response, view_name):
        """viz-1: the view's 3D assembly — base scene + stackable
        layer data. Refused layers stay listed with reasons."""
        from motors.clock_scene import clock_scene_payload
        response.media = clock_scene_payload(
            self.manager, view_name,
            design=request.params.get('design', 'clock-lavet-m0'),
            scene_name=request.params.get('scene', ''))

    def on_get_clock_assembly(self, request, response):
        """as-1: the genuine assembly bill — motor + train + hands,
        every mass from its own geometry x material density."""
        from motors.clock_assembly import clock_assembly_report
        response.media = clock_assembly_report(self.manager)

    def on_get_timekeeping_proof(self, request, response):
        """as-3: sim steps -> solved ratios -> hand angles vs true
        time. ?pulses=N (default 120)."""
        from motors.clock_assembly import timekeeping_proof
        response.media = timekeeping_proof(
            self.manager,
            pulses=int(request.params.get('pulses', 120)))

    def on_get_product_routes(self, request, response):
        """mp0: the complete product, twice — pure-local vs
        commercial sourcing, gaps and blockers kept."""
        from motors.product_routes import product_routes
        response.media = product_routes(
            self.manager,
            design_name=request.params.get('design',
                                           'clock-lavet-m0b'))

    def on_get_bench_campaign(self, request, response):
        """bench-1: the W2 measurement protocol with LIVE
        predictions and record-back seams."""
        from motors.bench_campaign import bench_campaign
        response.media = bench_campaign(
            self.manager,
            design_name=request.params.get('design',
                                           'clock-lavet-m0b'))

    def on_get_distributed_traction(self, request, response):
        """dt-1: per-axle traction requirements swept over axle
        count (?mass_t=&speed_kmh=&grade_pct=&wheel_radius_m=
        &max_axles=)."""
        from motors.distributed_traction import (
            distributed_traction,
        )
        q = request.params
        response.media = distributed_traction(
            mass_t=float(q.get('mass_t', 2.0)),
            speed_kmh=float(q.get('speed_kmh', 10.0)),
            grade_pct=float(q.get('grade_pct', 2.0)),
            wheel_radius_m=float(q.get('wheel_radius_m', 0.15)),
            max_axles=int(q.get('max_axles', 12)))

    def on_get_component_view(self, request, response, part_name):
        from motors.clock_views import component_view
        response.media = component_view(
            self.manager, part_name,
            design=request.params.get('design', 'clock-lavet-m0'))

    def on_get_goals(self, request, response):
        from composition.data_refs import rows as _crows
        out = []
        for g in _crows(self.manager, 'MotorGoalSpec'):
            out.append({'name': getattr(g, 'name', ''),
                        'displayName': getattr(g, 'display_name',
                                               ''),
                        'scale': getattr(g, 'scale_ref', ''),
                        'policy': getattr(g, 'material_policy', ''),
                        'lifeTargetYr': getattr(
                            g, 'battery_life_target_yr', None)})
        response.media = {'ok': True, 'goals': out,
                          'count': len(out)}

    def on_get_goal(self, request, response, goal_name):
        from motors.scale_goals import goal_feasibility
        response.media = goal_feasibility(self.manager, goal_name)

    def on_get_scale_study(self, request, response):
        from motors.scale_goals import scale_study
        policy = request.params.get('policy',
                                    'local-plus-imported-wire')
        response.media = scale_study(self.manager, policy)

    def on_get_composition_view(self, request, response,
                                design_name):
        from motors.composition_splice import composition_view
        response.media = composition_view(self.manager, design_name)

    def on_get_promotion_candidates(self, request, response,
                                    design_name):
        from motors.composition_splice import promotion_candidates
        response.media = promotion_candidates(self.manager,
                                              design_name)

    def on_get_stator_variants(self, request, response):
        from motors.stator_construction import (
            compare_variants, variant_catalog,
        )
        def f(k, d):
            try:
                return float(request.params.get(k, d))
            except (TypeError, ValueError):
                return d
        out = compare_variants(
            self.manager, awg=int(f('awg', 32)),
            wall_mm=f('wallMm', 0.03),
            window_mm2=f('windowMm2', 606.0),
            nested=request.params.get('nested', '').lower() == 'true')
        if out.get('ok'):
            out['catalog'] = variant_catalog()
        else:
            response.status = '400 Bad Request'
        response.media = out
