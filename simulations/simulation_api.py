"""
@cross-cutting
@module simulations.simulation_api
@tags @xc:bindings

Simulation-related endpoints:

    POST /api/simulations/predict-storage
        Body: { className, durationSeconds, timeStepSeconds, recordingIntervalSteps }
        Returns: storage prediction (see storage_predictor.predict_storage)

    GET  /api/simulations/runs?simulationRef=<name>
        Lists SimulationRun rows, optionally filtered to one definition.

    (future) POST /api/simulations/run
        Body: { simulationRef, recordingIntervalSteps?, durationSeconds? }
        Kicks off the engine. Lands with the simulation runtime.

@consumers
  - polariServer (route registration)
  - (future) frontend Simulation runner UI
@see /OVERLAP_MAP.md
"""

import json
from typing import Dict, List, Optional

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

# Reused for surfacing each binding's declared simStepRole on the
# `/solutions` endpoint so the editor sidebar can render the per-class
# coordination summary without each frontend re-parsing the solution
# JSON itself.
from simulations.simulation_runner import (
    _detect_step_role as detect_step_role,
    _load_solution_data as load_solution_data,
)

from .storage_predictor import predict_storage
from .simulation_runner import run_step


class SimulationAPI(treeObject):
    """Endpoint routes for simulation control + introspection."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/simulations'
        if polServer is not None:
            polServer.falconServer.add_route(
                self.apiName + '/predict-storage', self, suffix='predict_storage'
            )
            polServer.falconServer.add_route(
                self.apiName + '/runs', self, suffix='runs'
            )
            # Single-step advancer — the user-facing "is this step
            # coherent?" check. Reuses the no-code engine; never streams.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/step', self, suffix='step'
            )
            # POST /runs creates a fresh SimulationRun row — handled by
            # on_post_runs on the same `/runs` route as on_get_runs.
            # Per-simulation roster — bindings + solutions linked to a
            # SimulationDefinition. Powers the SimSpace editor sidebar's
            # "Simulation solutions" section (jump-to-editor links).
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/solutions', self, suffix='solutions',
            )
            # POST /api/simulations/{sim_ref}/bindings — create a new
            # SimStateStepBinding row tying a SolutionDefinition to a
            # SimState class within this simulation. Multiple bindings
            # per (sim, class) are allowed; the runner orders them by
            # `order_index` and chains their contexts.
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/bindings', self, suffix='bindings',
            )
            # DELETE /api/simulations/bindings/{binding_name}
            polServer.falconServer.add_route(
                self.apiName + '/bindings/{binding_name}', self, suffix='binding_one',
            )
            # GET /api/simulations/by-solution/{solution_name} — list
            # the bindings that reference this SolutionDefinition (or
            # SimulationExecutionSolution that wraps it). Drives the
            # no-code editor's SimulationStateStep overlay so users
            # can see which simulations consume the solution they're
            # editing.
            polServer.falconServer.add_route(
                self.apiName + '/by-solution/{solution_name}', self,
                suffix='by_solution',
            )

    # ------------------------------------------------------------------
    # POST /api/simulations/predict-storage
    # ------------------------------------------------------------------
    def on_post_predict_storage(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        class_name = body.get('className', '')
        try:
            duration = float(body.get('durationSeconds', 0))
            time_step = float(body.get('timeStepSeconds', 0))
            interval = int(body.get('recordingIntervalSteps', 1))
        except (TypeError, ValueError):
            response.status = falcon.HTTP_400
            response.media = {
                'success': False,
                'error': 'durationSeconds + timeStepSeconds + recordingIntervalSteps must be numeric.',
            }
            return
        if not class_name:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'className is required.'}
            return
        prediction = predict_storage(
            self.manager, class_name, duration, time_step, interval
        )
        response.media = {'success': True, 'data': prediction}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/runs/{run_name}/step
    # Advance one timestep using the no-code execution engine. Optional
    # JSON body: {"targetStep": <int>} — defaults to last_recorded_step+1
    # (or 0 if no rows exist yet for this run).
    # ------------------------------------------------------------------
    def on_post_step(self, request, response, run_name):
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        target_step = None
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
            if 'targetStep' in body and body['targetStep'] is not None:
                target_step = int(body['targetStep'])
        except (ValueError, TypeError):
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': "'targetStep' must be integer when provided."}
            return
        except Exception:
            body = {}

        result = run_step(self.manager, run, target_step=target_step)
        response.media = {'success': result.get('success', False), 'data': result}
        response.status = falcon.HTTP_200 if result.get('success') else falcon.HTTP_400

    # ------------------------------------------------------------------
    # GET /api/simulations/{sim_ref}/solutions
    # Returns the SimStateStepBindings for a SimulationDefinition,
    # joined with the SimulationExecutionSolution each one references.
    # The editor sidebar surfaces this so the analyst can see which
    # SimState class is wired to which solution and jump to the no-code
    # editor for any of them.
    # ------------------------------------------------------------------
    def on_get_solutions(self, request, response, sim_ref):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        if not any(getattr(r, 'name', '') == sim_ref for r in defs.values()):
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return

        # Build a name → row map for solutions for the join.
        sol_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        sols_by_name = {getattr(s, 'name', ''): s for s in sol_table.values()}

        bindings_table = self.manager.objectTables.get('SimStateStepBinding', {}) or {}
        out: List[Dict] = []
        for b in bindings_table.values():
            if getattr(b, 'simulation_definition_ref', '') != sim_ref:
                continue
            step_solution_ref = getattr(b, 'step_solution_ref', '') or ''
            sol = sols_by_name.get(step_solution_ref) if step_solution_ref else None

            # Detect the step solution's role + reason so the sidebar can
            # show a coloured pill per binding and the per-class
            # coordination summary. Detection mirrors what the runner
            # does at dispatch time, so the editor preview and the
            # runtime decision can't diverge.
            role, role_error = self._probe_role(step_solution_ref)

            out.append({
                'bindingName': getattr(b, 'name', ''),
                'simStateClassName': getattr(b, 'sim_state_class_name', ''),
                'stepSolutionRef': step_solution_ref,
                'dependsOn': self._parse_json_list(
                    getattr(b, 'depends_on_json', '') or '[]'
                ),
                'enabled': bool(getattr(b, 'enabled', True)),
                'orderIndex': int(getattr(b, 'order_index', 0) or 0),
                # Detected simStepRole. `null` when the binding is
                # unwired or the linked solution doesn't declare a role
                # the runner would accept — `simStepRoleError` carries
                # the human-readable detail for the warning UI.
                'simStepRole': role,
                'simStepRoleError': role_error,
                'solution': {
                    'name': getattr(sol, 'name', ''),
                    'description': getattr(sol, 'description', ''),
                    'simStateClassName': getattr(sol, 'sim_state_class_name', ''),
                    'expectedInputs': self._parse_json_list(
                        getattr(sol, 'expected_inputs_json', '') or '[]'
                    ),
                    'expectedOutputs': self._parse_json_list(
                        getattr(sol, 'expected_outputs_json', '') or '[]'
                    ),
                } if sol is not None else None,
            })
        out.sort(key=lambda x: (x['simStateClassName'], x['orderIndex'], x['bindingName']))

        # Also surface the available SolutionDefinitions so the sidebar
        # can populate the "pick a solution" dropdown when the user adds
        # a new binding. Cheap — small table.
        sol_def_table = self.manager.objectTables.get('SolutionDefinition', {}) or {}
        available_solutions = sorted(
            [
                {
                    'name': getattr(s, 'name', ''),
                    'targetRuntime': getattr(s, 'target_runtime', 'python_backend'),
                }
                for s in sol_def_table.values()
                if getattr(s, 'name', '')
            ],
            key=lambda s: s['name'],
        )
        # The participating SimState classes — derived from class-level
        # metadata, same logic the SimSpace snapshot uses. Lets the
        # sidebar offer a class dropdown without an extra roundtrip.
        sim_state_classes = self._participating_sim_state_classes(sim_ref)
        response.media = {
            'success': True,
            'data': {
                'bindings': out,
                'availableSolutions': available_solutions,
                'simStateClasses': sim_state_classes,
            },
        }
        response.status = falcon.HTTP_200

    def _participating_sim_state_classes(self, sim_ref: str) -> List[str]:
        """All registered class names whose class-level
        `simulation_definition_name` matches sim_ref. Used by the
        sidebar's class dropdown when adding a new binding."""
        out: List[str] = []
        typing_dict = getattr(self.manager, 'objectTypingDict', {}) or {}
        for cls_name, typing_obj in typing_dict.items():
            cls = getattr(typing_obj, 'classDefinition', None)
            if cls is None:
                continue
            if getattr(cls, 'simulation_definition_name', '') == sim_ref:
                out.append(cls_name)
        out.sort()
        return out

    # ------------------------------------------------------------------
    # POST /api/simulations/{sim_ref}/bindings
    # Body: { simStateClassName, stepSolutionRef?, orderIndex?,
    #         dependsOn?, name?, description?, enabled? }
    # Creates a new SimStateStepBinding row scoped to this simulation.
    # ------------------------------------------------------------------
    def on_post_bindings(self, request, response, sim_ref):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        if not any(getattr(r, 'name', '') == sim_ref for r in defs.values()):
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        sim_state_class_name = (body.get('simStateClassName') or '').strip()
        if not sim_state_class_name:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'simStateClassName is required.'}
            return
        # Auto-name when not provided. Pattern matches the seed:
        # <sim>.<Class>[.<n>] — `n` disambiguates multiple bindings
        # against the same class.
        bindings_table = self.manager.objectTables.get('SimStateStepBinding', {}) or {}
        existing_names = {getattr(r, 'name', '') for r in bindings_table.values()}
        name = (body.get('name') or '').strip()
        if not name:
            base = f'{sim_ref}.{sim_state_class_name}'
            name = base
            i = 2
            while name in existing_names:
                name = f'{base}.{i}'
                i += 1
        elif name in existing_names:
            response.status = falcon.HTTP_409
            response.media = {'success': False, 'error': f'Binding "{name}" already exists.'}
            return
        depends_on = body.get('dependsOn') or []
        if not isinstance(depends_on, list):
            depends_on = []
        order_index = body.get('orderIndex')
        try:
            order_index = int(order_index) if order_index is not None else 0
        except (TypeError, ValueError):
            order_index = 0
        from simulations.sim_state_step_binding import SimStateStepBinding as _SSB
        try:
            _SSB(
                name=name,
                description=body.get('description') or '',
                simulation_definition_ref=sim_ref,
                sim_state_class_name=sim_state_class_name,
                step_solution_ref=body.get('stepSolutionRef') or '',
                depends_on_json=json.dumps(depends_on),
                enabled=bool(body.get('enabled', True)),
                order_index=order_index,
                manager=self.manager,
            )
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Failed to create binding: {e}'}
            return
        response.media = {'success': True, 'data': {'name': name}}
        response.status = falcon.HTTP_201

    # ------------------------------------------------------------------
    # DELETE /api/simulations/bindings/{binding_name}
    # ------------------------------------------------------------------
    def on_delete_binding_one(self, request, response, binding_name):
        bindings_table = self.manager.objectTables.get('SimStateStepBinding', {}) or {}
        to_remove = None
        for key, inst in bindings_table.items():
            if getattr(inst, 'name', '') == binding_name:
                to_remove = key
                break
        if to_remove is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Binding "{binding_name}" not found.'}
            return
        try:
            del bindings_table[to_remove]
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Failed to delete binding: {e}'}
            return
        response.media = {'success': True, 'data': {'name': binding_name}}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/by-solution/{solution_name}
    # Returns every SimStateStepBinding whose step_solution_ref matches
    # either:
    #   - the supplied SolutionDefinition name directly, OR
    #   - a SimulationExecutionSolution name whose
    #     solution_definition_ref points at this SolutionDefinition.
    # Lets the no-code editor's initial-state overlay surface "this
    # solution is used by N simulations" without scanning every
    # simulation in turn.
    # ------------------------------------------------------------------
    def on_get_by_solution(self, request, response, solution_name):
        # Collect the names that effectively reference this solution:
        # the direct name plus any SimulationExecutionSolution that
        # wraps it.
        target_names = {solution_name}
        sol_def_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        for inst in sol_def_table.values():
            if getattr(inst, 'solution_definition_ref', '') == solution_name:
                nm = getattr(inst, 'name', '')
                if nm:
                    target_names.add(nm)
        bindings_table = self.manager.objectTables.get('SimStateStepBinding', {}) or {}
        out: List[Dict] = []
        for b in bindings_table.values():
            ref = getattr(b, 'step_solution_ref', '')
            if ref not in target_names:
                continue
            out.append({
                'bindingName': getattr(b, 'name', ''),
                'simulationRef': getattr(b, 'simulation_definition_ref', ''),
                'simStateClassName': getattr(b, 'sim_state_class_name', ''),
                'enabled': bool(getattr(b, 'enabled', True)),
                'orderIndex': int(getattr(b, 'order_index', 0) or 0),
            })
        out.sort(key=lambda x: (x['simulationRef'], x['orderIndex'], x['bindingName']))
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    @staticmethod
    def _parse_json_list(text: str):
        try:
            v = json.loads(text)
            return v if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    def _probe_role(
        self, step_solution_ref: str
    ) -> "tuple[Optional[str], Optional[str]]":
        """Resolve a binding's `step_solution_ref` to its declared
        `simStepRole`. Returns `(role, error)`:
          - `(role, None)` when the role parses cleanly,
          - `(None, message)` when the binding is unwired, the linked
            solution is missing, or its SimulationStateStep entry
            doesn't declare a valid role.
        Never raises — the editor sidebar needs to render mixed states
        of authoring (some bindings wired, others not) without an
        endpoint failure.
        """
        if not step_solution_ref:
            return None, 'no solution wired'
        solution_data = load_solution_data(self.manager, step_solution_ref)
        if solution_data is None:
            return None, f"solution '{step_solution_ref}' not found"
        try:
            return detect_step_role(solution_data), None
        except ValueError as exc:
            return None, str(exc)

    def _find_run(self, name: str):
        rows = self.manager.objectTables.get('SimulationRun', {}) or {}
        for r in rows.values():
            if getattr(r, 'name', '') == name:
                return r
        return None

    # ------------------------------------------------------------------
    # GET /api/simulations/runs[?simulationRef=<name>]
    # ------------------------------------------------------------------
    def on_get_runs(self, request, response):
        sim_filter = request.get_param('simulationRef')
        rows = self.manager.objectTables.get('SimulationRun', {}) or {}
        out: List[Dict] = []
        for r in rows.values():
            if sim_filter and getattr(r, 'simulation_ref', '') != sim_filter:
                continue
            out.append({
                'name': getattr(r, 'name', ''),
                'simulationRef': getattr(r, 'simulation_ref', ''),
                'status': getattr(r, 'status', 'pending'),
                'startedAt': getattr(r, 'started_at', ''),
                'completedAt': getattr(r, 'completed_at', ''),
                'totalSteps': getattr(r, 'total_steps', 0),
                'recordedSteps': getattr(r, 'recorded_steps', 0),
                'lastRecordedStep': getattr(r, 'last_recorded_step', 0),
                'label': getattr(r, 'label', ''),
                'errorMessage': getattr(r, 'error_message', ''),
            })
        out.sort(key=lambda x: x['startedAt'] or x['name'], reverse=True)
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/runs
    # Create a new SimulationRun. Body:
    #   { "simulationRef": "<sim-def>", "label"?: "<str>", "name"?: "<str>" }
    # `name` defaults to "<simulationRef>-live-<isoSeconds>" so duplicate
    # button clicks don't collide. Status starts at 'pending'.
    # ------------------------------------------------------------------
    def on_post_runs(self, request, response):
        from datetime import datetime, timezone
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        sim_ref = (body.get('simulationRef') or '').strip()
        if not sim_ref:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'simulationRef is required.'}
            return
        # Confirm the SimulationDefinition exists.
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        if not any(getattr(r, 'name', '') == sim_ref for r in defs.values()):
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return
        now = datetime.now(timezone.utc)
        default_suffix = now.strftime('%Y%m%d-%H%M%S')
        name = (body.get('name') or f'{sim_ref}-live-{default_suffix}').strip()
        # Reject duplicate names — Step Once needs a deterministic lookup.
        runs_table = self.manager.objectTables.get('SimulationRun', {}) or {}
        if any(getattr(r, 'name', '') == name for r in runs_table.values()):
            response.status = falcon.HTTP_409
            response.media = {'success': False, 'error': f'SimulationRun "{name}" already exists.'}
            return
        # Find the registered class.
        from simulations.simulation_run import SimulationRun as _SR
        try:
            _SR(
                name=name,
                simulation_ref=sim_ref,
                status='pending',
                started_at=now.isoformat(),
                completed_at='',
                total_steps=0,
                recorded_steps=0,
                last_recorded_step=0,
                error_message='',
                label=body.get('label') or '',
                manager=self.manager,
            )
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Failed to create run: {e}'}
            return
        response.media = {
            'success': True,
            'data': {
                'name': name,
                'simulationRef': sim_ref,
                'status': 'pending',
            },
        }
        response.status = falcon.HTTP_201
