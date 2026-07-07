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
from typing import Any, Dict, List, Optional

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

# Reused for surfacing each binding's declared simStepRole on the
# `/solutions` endpoint so the editor sidebar can render the per-class
# coordination summary without each frontend re-parsing the solution
# JSON itself.
from simulations.simulation_runner import (
    _detect_step_role as detect_step_role,
    _load_solution_data as load_solution_data,
    _initial_field_values as initial_field_values,
)

from .storage_predictor import predict_storage, estimate_run_storage
from .simulation_runner import run_step, validate_initial_conditions


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
            # Set initial conditions on an already-created run. A run is
            # created uninitialized (no step 0); this writes the per-run
            # IC overrides / dt / field-save overrides onto it. Rejected
            # once the run has a committed step 0 (ICs are then locked).
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/initial-conditions',
                self, suffix='initial_conditions'
            )
            # Single-step advancer — the user-facing "is this step
            # coherent?" check. Reuses the no-code engine; never streams.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/step', self, suffix='step'
            )
            # Batch run — loops the single-step engine N times in one
            # request. Body: { steps, timeStepSeconds? }. The optional
            # dt override updates run.time_step_seconds so subsequent
            # Step Once calls use the same resolution.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/run', self, suffix='run'
            )
            # GET /api/simulations/runs/{run_name}/current-state
            # Returns the most-recent persisted row per participating
            # *SimState class so the run panel can show a live "current
            # values" readout without re-fetching the whole snapshot.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/current-state',
                self, suffix='current_state',
            )
            # POST /runs creates a fresh SimulationRun row — handled by
            # on_post_runs on the same `/runs` route as on_get_runs.
            # GET/POST /api/simulations/{sim_ref}/solutions
            # Lists or creates SimulationExecutionSolution rows for a
            # SimulationDefinition. Multiple rows per (sim, class) are
            # allowed; the runner orders them by `order_index` and
            # chains contexts (Partial → Composition pattern).
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/solutions', self, suffix='solutions',
            )
            # DELETE /api/simulations/solutions/{solution_name}
            polServer.falconServer.add_route(
                self.apiName + '/solutions/{solution_name}', self,
                suffix='solution_one',
            )
            # GET /api/simulations/by-solution/{solution_name} — list
            # SimulationExecutionSolution rows that reference this
            # SolutionDefinition. Drives the no-code editor's
            # SimulationStateStep overlay so users can see which
            # simulations consume the solution they're editing.
            polServer.falconServer.add_route(
                self.apiName + '/by-solution/{solution_name}', self,
                suffix='by_solution',
            )
            # POST /api/simulations/{sim_ref}/validate-initial-conditions
            # Body: { overrides: { '<class>': { '<field>': <value>, … }, … } }
            # Runs the sim def's initial_conditions_validator_ref (if any)
            # against the merged conditions (class defaults + sim
            # overrides + posted per-run overrides). Drives the live
            # debounced editor UI feedback.
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/validate-initial-conditions',
                self, suffix='validate_ic',
            )
            # POST /api/simulations/{sim_ref}/storage-estimate
            # Body: {
            #   fieldSaveOverrides?: { '<class>.<field>': {policy, interval}, ... },
            #   timeStepSeconds?: number,
            # }
            # Computes per-class + per-field storage estimates against
            # the posted hypothetical overrides — drives the IC editor's
            # live "this run will use ~X MB" readout. Source-tagged so
            # the UI can distinguish static defaults from measured data
            # (once PolyTyping is collecting samples).
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/storage-estimate',
                self, suffix='storage_estimate',
            )
            # GET /api/simulations/runs/{run_name}/series
            #   ?class=<SimStateClass>&fields=a,b,c
            #   &stepFrom=&stepTo=&sinceStep=
            # Per-run timeseries for graphs-over-time (generic CRUDE can't
            # filter by run/step). Row filter is the SHARED run scope, so a
            # coupled run's series can read its source runs' classes.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/series', self, suffix='series',
            )
            # POST /api/simulations/multi-scale/{msim_name}/stages/{stage_key}/gate
            # Body: { run: '<run name>' }. Evaluates the stage's no-code
            # gate solution over the run's results (same engine flow as the
            # IC validator) and resolves the stage's `derive` map — drives
            # the multi-scale page's progression stepper.
            polServer.falconServer.add_route(
                self.apiName + '/multi-scale/{msim_name}/stages/{stage_key}/gate',
                self, suffix='stage_gate',
            )
            # POST /api/simulations/multi-scale/{msim_name}/stages/{stage_key}/search
            # Body: { batchSize?: int }. Advances the stage's SOLUTION
            # SEARCH by one batch: multiple candidate parameter points
            # attempted (each an ordinary run with per-run parameter
            # overrides), gate-judged, first valid solution wins.
            # Stateless/resumable — repeat calls continue the search.
            polServer.falconServer.add_route(
                self.apiName + '/multi-scale/{msim_name}/stages/{stage_key}/search',
                self, suffix='stage_search',
            )
            # GET /api/simulations/intents — the simulation-intents
            # taxonomy (what each intent requires/produces and where it
            # plugs in). Drives the authoring wizard's first question.
            polServer.falconServer.add_route(
                self.apiName + '/intents', self, suffix='intents',
            )
            # POST /api/simulations/multi-scale/{msim_name}/validate-composition
            # Checks the composition against the intent coherence rules;
            # returns plain-language findings (errors + warnings).
            polServer.falconServer.add_route(
                self.apiName + '/multi-scale/{msim_name}/validate-composition',
                self, suffix='validate_composition',
            )
            # GET /api/simulations/resources — the machine's memory/disk
            # budget (container-aware). Feeds the run controls' live
            # resource readout.
            polServer.falconServer.add_route(
                self.apiName + '/resources', self, suffix='resources',
            )
            # POST /api/simulations/runs/{run_name}/project
            # Body: { steps }. Projects steps x measured average step
            # cost (StepCostProfile; static estimate before measurements)
            # against the budget — Dustin's "this would nearly drain your
            # memory" detection, BEFORE running.
            polServer.falconServer.add_route(
                self.apiName + '/runs/{run_name}/project',
                self, suffix='project',
            )
            # GET /api/simulations/{sim_ref}/resource-suggestions —
            # ranked, one-click-appliable data-saving proposals from the
            # sim's MEASURED per-field sizes.
            polServer.falconServer.add_route(
                self.apiName + '/{sim_ref}/resource-suggestions',
                self, suffix='resource_suggestions',
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
    # ------------------------------------------------------------------
    # POST /api/simulations/runs/{run_name}/initial-conditions
    # Body: { initialConditionsOverrides?, timeStepSeconds?, fieldSaveOverrides? }
    # Writes per-run initial conditions onto an existing, uninitialized
    # run. Once step 0 is committed the ICs are locked and this 409s.
    # ------------------------------------------------------------------
    def on_post_initial_conditions(self, request, response, run_name):
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        # Locked once a step-0 row exists — ICs are baked into that row.
        recorded = int(getattr(run, 'recorded_steps', 0) or 0)
        last_step = int(getattr(run, 'last_recorded_step', 0) or 0)
        if recorded > 0 or last_step > 0:
            response.status = falcon.HTTP_409
            response.media = {
                'success': False,
                'error': 'Initial conditions are locked — this run already has a committed step 0.',
            }
            return
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        ic_overrides = body.get('initialConditionsOverrides') or {}
        if not isinstance(ic_overrides, dict):
            ic_overrides = {}
        field_save_overrides = body.get('fieldSaveOverrides') or {}
        if not isinstance(field_save_overrides, dict):
            field_save_overrides = {}
        try:
            time_step_seconds = float(body.get('timeStepSeconds') or 0)
        except (TypeError, ValueError):
            time_step_seconds = 0.0
        # Per-run PARAMETER overrides (layered over the sim def's
        # parameters_json by the runner) — the channel configured IC
        # interfaces (material picker) and stage `derive` outputs use.
        param_overrides = body.get('parameterOverrides') or {}
        if not isinstance(param_overrides, dict):
            param_overrides = {}
        # Mirror on_post_run's pattern: mutate the in-memory treeObject;
        # the framework persists the attribute writes.
        run.initial_conditions_overrides_json = json.dumps(ic_overrides)
        run.field_save_overrides_json = json.dumps(field_save_overrides)
        run.parameter_overrides_json = json.dumps(param_overrides)
        if time_step_seconds > 0:
            run.time_step_seconds = time_step_seconds
        response.media = {
            'success': True,
            'data': {'name': run_name, 'status': getattr(run, 'status', 'pending')},
        }
        response.status = falcon.HTTP_200

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
    # POST /api/simulations/runs/{run_name}/run
    # Body: { steps: <int>, timeStepSeconds?: <float> }
    # Loops run_step `steps` times. When `timeStepSeconds > 0` is
    # supplied, the run's dt is updated BEFORE the loop so subsequent
    # Step Once calls inherit the new resolution.
    # Aborts on the first failed step; returns counts of committed
    # steps + the final time.
    # ------------------------------------------------------------------
    def on_post_run(self, request, response, run_name):
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        try:
            steps = int(body.get('steps') or 0)
        except (TypeError, ValueError):
            steps = 0
        if steps <= 0:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': "'steps' must be a positive integer."}
            return
        # Optional dt override — updates the SimulationRun row so the
        # change is sticky across this batch and any subsequent
        # Step Once calls.
        if 'timeStepSeconds' in body and body['timeStepSeconds'] is not None:
            try:
                new_dt = float(body['timeStepSeconds'])
                if new_dt > 0:
                    run.time_step_seconds = new_dt
            except (TypeError, ValueError):
                pass

        # RESOURCE GUARD — project this batch against the machine's
        # budget BEFORE running (Dustin's rule: detect "this would
        # nearly drain your memory" up front). The projection rides on
        # every response; a critical projection REFUSES unless the
        # caller explicitly overrides.
        projection = None
        try:
            from simulations.resource_monitor import project_run
            from simulations.resource_suggestions import suggestions_for
            sim_def_for_run = self._find_sim_def(getattr(run, 'simulation_ref', ''))
            if sim_def_for_run is not None:
                projection = project_run(self.manager, run, sim_def_for_run, steps)
        except Exception as e:
            print(f'[Resources] projection skipped: {e}', flush=True)
        if projection and projection.get('level') == 'critical' \
                and not body.get('overrideResourceWarning'):
            try:
                suggestions = suggestions_for(
                    self.manager, getattr(run, 'simulation_ref', ''))
            except Exception:
                suggestions = []
            response.media = {
                'success': False,
                'error': projection.get('message'),
                'data': {
                    'refusedByResourceGuard': True,
                    'projection': projection,
                    'suggestions': suggestions,
                    'howToProceed': ('Reduce the steps, apply a suggestion '
                                     '(per-run field save overrides), or '
                                     'resend with overrideResourceWarning: '
                                     'true to run anyway.'),
                },
            }
            response.status = falcon.HTTP_409
            return

        committed: List[Dict] = []
        warnings_all: List[str] = []
        last_result: Optional[Dict] = None
        for _ in range(steps):
            result = run_step(self.manager, run)
            warnings_all.extend(result.get('warnings') or [])
            if not result.get('success'):
                response.media = {
                    'success': False,
                    'data': {
                        'committedSteps': len(committed),
                        'finalStep': committed[-1]['step'] if committed else None,
                        'finalTime': committed[-1]['time'] if committed else None,
                        'lastFailedStep': result.get('step'),
                        'error': result.get('error'),
                        'warnings': warnings_all,
                        'committed': committed,
                    },
                }
                response.status = falcon.HTTP_400
                return
            committed.append({
                'step': result.get('step'),
                'time': result.get('time'),
            })
            last_result = result
        response.media = {
            'success': True,
            'data': {
                'committedSteps': len(committed),
                'finalStep': committed[-1]['step'] if committed else None,
                'finalTime': committed[-1]['time'] if committed else None,
                'warnings': warnings_all,
                'committed': committed,
                'lastSolutionTraces': (last_result or {}).get('solutionTraces') or [],
                'lastRowsByClass': (last_result or {}).get('rowsByClass') or {},
                # Always attached: what this batch was projected to cost
                # (level 'warning' proceeds but the UI should surface it).
                'resourceProjection': projection,
            },
        }
        response.status = falcon.HTTP_200

    def _find_sim_def(self, sim_ref: str):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        return next((r for r in defs.values()
                     if getattr(r, 'name', '') == sim_ref), None)

    # ------------------------------------------------------------------
    # GET /api/simulations/resources
    # ------------------------------------------------------------------
    def on_get_resources(self, request, response):
        from simulations.resource_monitor import system_resources
        response.media = {'success': True, 'data': system_resources()}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/runs/{run_name}/project
    # ------------------------------------------------------------------
    def on_post_project(self, request, response, run_name):
        from simulations.resource_monitor import project_run
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        sim_def = self._find_sim_def(getattr(run, 'simulation_ref', ''))
        if sim_def is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': 'Run has no resolvable SimulationDefinition.'}
            return
        try:
            body = request.media or {}
        except Exception:
            body = {}
        try:
            steps = int(body.get('steps') or 0)
        except (TypeError, ValueError):
            steps = 0
        if steps <= 0:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': "'steps' must be a positive integer."}
            return
        projection = project_run(self.manager, run, sim_def, steps)
        response.media = {'success': True, 'data': projection}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/{sim_ref}/resource-suggestions
    # ------------------------------------------------------------------
    def on_get_resource_suggestions(self, request, response, sim_ref):
        from simulations.resource_suggestions import suggestions_for
        if self._find_sim_def(sim_ref) is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return
        response.media = {
            'success': True,
            'data': {'suggestions': suggestions_for(self.manager, sim_ref)},
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/runs/{run_name}/current-state
    # Latest persisted row per participating *SimState class. Returns:
    #   {
    #     step:      <max committed step across classes>,
    #     time:      <seconds at that step (from the row)>,
    #     perClass:  { '<cls>': { '<field>': <value>, ..., 'step': N, 'time': T } }
    #   }
    # Each class's row is whichever row for this run carries the highest
    # `step`. Drives the run panel's live current-state readout.
    # ------------------------------------------------------------------
    def on_get_current_state(self, request, response, run_name):
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        sim_ref = getattr(run, 'simulation_ref', '')
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        sim_def = next((r for r in defs.values() if getattr(r, 'name', '') == sim_ref), None)
        if sim_def is None:
            response.media = {
                'success': True,
                'data': {'step': None, 'time': None, 'perClass': {}},
            }
            response.status = falcon.HTTP_200
            return
        # Optional `?step=N` — return the row at exactly that step
        # instead of the most-recent one. The IC editor uses ?step=0 to
        # show a locked run's committed initial conditions.
        target_step = None
        raw_param = request.get_param('step')
        if raw_param is not None and raw_param != '':
            try:
                target_step = int(raw_param)
            except (TypeError, ValueError):
                target_step = None
        participating = self._parse_json_list(
            getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]'
        )
        per_class: Dict[str, Dict[str, Any]] = {}
        max_step = -1
        max_time: Optional[float] = None
        skip = {'manager', 'branch', 'inTree', 'polariId'}
        for cls_name in participating:
            if not isinstance(cls_name, str):
                continue
            table = self.manager.objectTables.get(cls_name, {}) or {}
            best_row = None
            best_step = -1
            for inst in table.values():
                if getattr(inst, 'simulation_run_ref', '') != run_name:
                    continue
                raw = getattr(inst, 'step', None)
                try:
                    step_val = int(raw) if raw is not None else -1
                except (TypeError, ValueError):
                    step_val = -1
                if target_step is not None:
                    # Exact-step mode: take the row matching target_step.
                    if step_val == target_step:
                        best_step = step_val
                        best_row = inst
                        break
                elif step_val > best_step:
                    best_step = step_val
                    best_row = inst
            if best_row is None:
                continue
            row_dict: Dict[str, Any] = {}
            for k, v in vars(best_row).items():
                if k.startswith('_') or k in skip:
                    continue
                row_dict[k] = v
            per_class[cls_name] = row_dict
            if best_step > max_step:
                max_step = best_step
                try:
                    max_time = float(getattr(best_row, 'time', 0.0))
                except (TypeError, ValueError):
                    max_time = None
        response.media = {
            'success': True,
            'data': {
                'step': max_step if max_step >= 0 else None,
                'time': max_time,
                'perClass': per_class,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/runs/{run_name}/series
    # ------------------------------------------------------------------
    def on_get_series(self, request, response, run_name):
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        class_name = request.get_param('class') or ''
        if not class_name:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': "'class' query param is required."}
            return
        fields_raw = request.get_param('fields') or ''
        fields = [f.strip() for f in fields_raw.split(',') if f.strip()]

        def _int_param(name):
            raw = request.get_param(name)
            if raw is None or raw == '':
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        from simulations.simulation_series import build_series
        try:
            data = build_series(
                self.manager, run_name, class_name, fields,
                step_from=_int_param('stepFrom'),
                step_to=_int_param('stepTo'),
                since_step=_int_param('sinceStep'),
            )
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Series build failed: {e}'}
            return
        response.media = {'success': True, 'data': data}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/multi-scale/{msim_name}/stages/{stage_key}/gate
    # ------------------------------------------------------------------
    def on_post_stage_gate(self, request, response, msim_name, stage_key):
        from simulations.multi_scale_stages import (
            apply_derive, evaluate_stage_gate, find_stage,
        )
        table = self.manager.objectTables.get('MultiScaleSimulationDefinition', {}) or {}
        msim = next((r for r in table.values() if getattr(r, 'name', '') == msim_name), None)
        if msim is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'MultiScaleSimulationDefinition "{msim_name}" not found'}
            return
        stage = find_stage(msim, stage_key)
        if stage is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'Stage "{stage_key}" not found on "{msim_name}"'}
            return
        try:
            body = request.media or {}
        except Exception:
            body = {}
        run_name = body.get('run') or ''
        # engineModel stages gate over the model row's persisted last
        # result; subModel stages re-check the child's stage gates
        # read-only. Neither uses SimulationRun rows.
        if stage.get('kind') == 'engineModel':
            from simulations.engine_model_stage import (
                evaluate_engine_model_gate,
            )
            from materialsScience.model_execution import find_model
            model, _ = find_model(self.manager,
                                  stage.get('modelRef', ''))
            if model is None:
                response.status = falcon.HTTP_404
                response.media = {
                    'success': False,
                    'error': ('no model definition named '
                              f'"{stage.get("modelRef", "")}" for '
                              f'stage "{stage_key}"')}
                return
            verdict = evaluate_engine_model_gate(self.manager, stage,
                                                 model)
            verdict['deriveResolved'] = apply_derive(
                stage, verdict.get('derivedValues') or {})
            response.media = {'success': True, 'data': verdict}
            response.status = falcon.HTTP_200
            return
        if stage.get('kind') == 'subModel':
            from simulations.sub_model_stage import (
                evaluate_sub_model_gate,
            )
            verdict = evaluate_sub_model_gate(self.manager, stage)
            verdict['deriveResolved'] = apply_derive(
                stage, verdict.get('derivedValues') or {})
            response.media = {'success': True, 'data': verdict}
            response.status = falcon.HTTP_200
            return
        # formulationSearch stages gate over a FormulationSearchRun row
        # (their runs are formulation runs, not SimulationRuns). The
        # newest run for the stage's search is used when none is named.
        if stage.get('kind') == 'formulationSearch':
            from materialsScience.formulation_stage import (
                evaluate_formulation_gate,
            )
            ftable = self.manager.objectTables.get(
                'FormulationSearchRun', {}) or {}
            frows = list(ftable.values()) if isinstance(ftable, dict) \
                else list(ftable)
            if run_name:
                frun = next((r for r in frows
                             if getattr(r, 'name', '') == run_name), None)
            else:
                search_ref = stage.get('formulationSearchRef') or ''
                candidates = [r for r in frows
                              if getattr(r, 'search_ref', '') == search_ref]
                frun = max(candidates,
                           key=lambda r: getattr(r, 'name', ''),
                           default=None)
            if frun is None:
                if run_name:
                    # A specific run was asked for and doesn't exist —
                    # that IS an error.
                    response.status = falcon.HTTP_404
                    response.media = {
                        'success': False,
                        'error': ('no FormulationSearchRun named '
                                  f'"{run_name}" for stage "{stage_key}"')}
                    return
                # No run yet is a STATE, not an HTTP error: the honest
                # verdict is simply "not complete — run the search".
                response.media = {'success': True, 'data': {
                    'complete': False,
                    'hasGate': False,
                    'reason': 'The formulation search has not run yet — '
                              'run it from this stage (or the '
                              'formulation-search page).',
                    'derivedValues': None,
                    'error': None,
                    'deriveResolved': {'params': {}, 'fields': {}},
                }}
                response.status = falcon.HTTP_200
                return
            verdict = evaluate_formulation_gate(self.manager, stage, frun)
            verdict['deriveResolved'] = apply_derive(
                stage, verdict.get('derivedValues') or {})
            response.media = {'success': True, 'data': verdict}
            response.status = falcon.HTTP_200
            return
        run = self._find_run(run_name)
        if run is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationRun "{run_name}" not found'}
            return
        verdict = evaluate_stage_gate(self.manager, stage, run)
        verdict['deriveResolved'] = apply_derive(stage, verdict.get('derivedValues') or {})
        response.media = {'success': True, 'data': verdict}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/multi-scale/{msim_name}/stages/{stage_key}/search
    # ------------------------------------------------------------------
    def on_post_stage_search(self, request, response, msim_name, stage_key):
        from simulations.multi_scale_stages import apply_derive, find_stage
        from simulations.multi_scale_search import run_stage_search
        table = self.manager.objectTables.get('MultiScaleSimulationDefinition', {}) or {}
        msim = next((r for r in table.values() if getattr(r, 'name', '') == msim_name), None)
        if msim is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'MultiScaleSimulationDefinition "{msim_name}" not found'}
            return
        stage = find_stage(msim, stage_key)
        if stage is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'Stage "{stage_key}" not found on "{msim_name}"'}
            return
        try:
            body = request.media or {}
        except Exception:
            body = {}
        # Non-stepping stage kinds each have their own executor that
        # reshapes into this endpoint's exact contract (lazy imports,
        # same style as the rest of this module): formulationSearch
        # drives a FormulationSearchDefinition, engineModel executes a
        # configured FEM/DFT model definition, subModel runs a NESTED
        # msim (recursive composition).
        _kind = stage.get('kind')
        if _kind in ('formulationSearch', 'engineModel', 'subModel'):
            if _kind == 'formulationSearch':
                from materialsScience.formulation_stage import (
                    run_formulation_stage,
                )
                report = run_formulation_stage(
                    self.manager, msim_name, stage, body)
            elif _kind == 'engineModel':
                from simulations.engine_model_stage import (
                    run_engine_model_stage,
                )
                report = run_engine_model_stage(
                    self.manager, msim_name, stage, body, msim=msim)
            else:
                from simulations.sub_model_stage import (
                    run_sub_model_stage,
                )
                report = run_sub_model_stage(
                    self.manager, msim_name, stage, body)
            if report.get('winner'):
                report['deriveResolved'] = apply_derive(
                    stage, report['winner'].get('derivedValues') or {})
            response.media = {'success': report.get('error') is None,
                              'data': report}
            response.status = (falcon.HTTP_200
                               if report.get('error') is None
                               else falcon.HTTP_400)
            return
        if not (stage.get('search') or {}).get('candidates'):
            response.status = falcon.HTTP_400
            response.media = {'success': False,
                              'error': f'Stage "{stage_key}" declares no solution search '
                                       f'(search.candidates).'}
            return
        try:
            batch_size = int(body.get('batchSize') or 0) or None
        except (TypeError, ValueError):
            batch_size = None
        # Substance-specific searches: fixedParams merge into every
        # candidate (substance identity); attemptTag namespaces the
        # attempt runs so each substance's search resumes independently.
        fixed_params = body.get('fixedParams') or {}
        if not isinstance(fixed_params, dict):
            fixed_params = {}
        attempt_tag = str(body.get('attemptTag') or '')
        # Parallel attempts (DISTRIBUTED_COMPUTE_PLAN track 1): fresh
        # candidates run as pure tasks on the chosen backend. Omitted =
        # the stage's search.executionBackend default, else serial.
        execution_backend = body.get('executionBackend') or None
        try:
            max_workers = int(body.get('maxWorkers') or 0) or None
        except (TypeError, ValueError):
            max_workers = None
        # Cross-instance dask: address of an existing distributed
        # scheduler (e.g. tcp://prf-dask-scheduler:8786). Omitted =
        # POLARI_DASK_SCHEDULER env, else a local cluster.
        dask_scheduler = str(body.get('daskScheduler') or '') or None
        # "Find more solutions": keep sweeping past an existing winner,
        # accumulating every valid solution into report.winners.
        continue_after_winner = bool(body.get('continueAfterWinner'))
        report = run_stage_search(self.manager, msim_name, stage, batch_size,
                                  fixed_params=fixed_params,
                                  attempt_tag=attempt_tag,
                                  execution_backend=execution_backend,
                                  max_workers=max_workers,
                                  dask_scheduler=dask_scheduler,
                                  continue_after_winner=continue_after_winner)
        if report.get('winner'):
            report['deriveResolved'] = apply_derive(
                stage, report['winner'].get('derivedValues') or {})
        response.media = {'success': report.get('error') is None, 'data': report}
        response.status = falcon.HTTP_200 if report.get('error') is None else falcon.HTTP_400

    # ------------------------------------------------------------------
    # GET /api/simulations/intents
    # ------------------------------------------------------------------
    def on_get_intents(self, request, response):
        from simulations.simulation_intents import intents_catalog
        response.media = {'success': True, 'data': intents_catalog()}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/multi-scale/{msim_name}/validate-composition
    # ------------------------------------------------------------------
    def on_post_validate_composition(self, request, response, msim_name):
        from simulations.simulation_intents import validate_composition
        table = self.manager.objectTables.get('MultiScaleSimulationDefinition', {}) or {}
        msim = next((r for r in table.values() if getattr(r, 'name', '') == msim_name), None)
        if msim is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'MultiScaleSimulationDefinition "{msim_name}" not found'}
            return
        findings = validate_composition(self.manager, msim)
        response.media = {
            'success': True,
            'data': {
                'coherent': not any(f['level'] == 'error' for f in findings),
                'findings': findings,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/{sim_ref}/solutions
    # Returns the SimulationExecutionSolution rows for a
    # SimulationDefinition, with role detection. The editor sidebar
    # surfaces this so the analyst can see which SimState class is
    # wired to which solution and jump to the no-code editor for any
    # of them.
    # ------------------------------------------------------------------
    def on_get_solutions(self, request, response, sim_ref):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        sim_def = next((r for r in defs.values() if getattr(r, 'name', '') == sim_ref), None)
        if sim_def is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return

        # Participating classes from the sim_def roster (NOT a reverse
        # scan of class-level attributes — the explicit roster is the
        # source of truth for this sim).
        roster = self._parse_json_list(
            getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]'
        )
        participating = [c for c in roster if isinstance(c, str)]

        sol_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        out: List[Dict] = []
        for s in sol_table.values():
            if getattr(s, 'simulation_definition_ref', '') != sim_ref:
                continue
            solution_def_ref = getattr(s, 'solution_definition_ref', '') or ''
            role, role_error = self._probe_role(solution_def_ref)
            out.append({
                'name': getattr(s, 'name', ''),
                'description': getattr(s, 'description', ''),
                'simStateClassName': getattr(s, 'sim_state_class_name', ''),
                'solutionDefinitionRef': solution_def_ref,
                'expectedInputs': self._parse_json_list(
                    getattr(s, 'expected_inputs_json', '') or '[]'
                ),
                'expectedOutputs': self._parse_json_list(
                    getattr(s, 'expected_outputs_json', '') or '[]'
                ),
                'orderIndex': int(getattr(s, 'order_index', 0) or 0),
                'dependsOn': self._parse_json_list(
                    getattr(s, 'depends_on_json', '') or '[]'
                ),
                'enabled': bool(getattr(s, 'enabled', True)),
                # Detected simStepRole. `null` when the row is unwired
                # or the linked solution doesn't declare a role the
                # runner would accept.
                'simStepRole': role,
                'simStepRoleError': role_error,
            })
        out.sort(key=lambda x: (x['simStateClassName'], x['orderIndex'], x['name']))

        # Available SolutionDefinitions for the "pick a solution"
        # dropdown.
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

        # Per-class initial-conditions hybrid view: class defaults +
        # sim-level overrides. Lets the editor render the merged
        # baseline alongside which side each field came from.
        sim_overrides = self._parse_json_dict(
            getattr(sim_def, 'initial_conditions_overrides_json', '') or '{}'
        )
        initial_conditions: Dict[str, Dict[str, Any]] = {}
        for cls_name in participating:
            class_defaults = self._class_default_initial_values(cls_name)
            override_values = sim_overrides.get(cls_name) if isinstance(sim_overrides, dict) else {}
            if not isinstance(override_values, dict):
                override_values = {}
            initial_conditions[cls_name] = {
                'classDefaults': class_defaults,
                'simOverrides': override_values,
            }

        # Per-class field-save policies — class declaration +
        # sim-def-level overrides. Mirrors initialConditions shape so
        # the editor can render a per-field toggle the same way.
        field_save_overrides = self._parse_json_dict(
            getattr(sim_def, 'field_save_overrides_json', '') or '{}'
        )
        field_policies: Dict[str, Dict[str, Any]] = {}
        for cls_name in participating:
            class_policy = self._class_field_save_policy(cls_name)
            cls_sim_overrides: Dict[str, Dict[str, Any]] = {}
            prefix = f'{cls_name}.'
            for key, rule in field_save_overrides.items():
                if isinstance(key, str) and key.startswith(prefix) and isinstance(rule, dict):
                    cls_sim_overrides[key[len(prefix):]] = rule
            field_policies[cls_name] = {
                'classDefaults': class_policy,
                'simOverrides': cls_sim_overrides,
            }

        response.media = {
            'success': True,
            'data': {
                'solutions': out,
                'availableSolutions': available_solutions,
                'simStateClasses': participating,
                'initialConditions': initial_conditions,
                'fieldPolicies': field_policies,
            },
        }
        response.status = falcon.HTTP_200

    def _class_default_initial_values(self, cls_name: str) -> Dict[str, Any]:
        """Read a `*SimState` class's `default_initial_field_values`
        attribute (used to compose the t=0 row alongside sim
        overrides)."""
        typing_obj = (self.manager.objectTypingDict or {}).get(cls_name)
        cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
        defaults = getattr(cls, 'default_initial_field_values', None) if cls else None
        return dict(defaults) if isinstance(defaults, dict) else {}

    def _class_field_save_policy(self, cls_name: str) -> Dict[str, str]:
        """Read a `*SimState` class's `field_save_policy` attribute.
        Each value is one of 'core' | 'derivable'; unlisted fields are
        treated as 'core' by the runner."""
        typing_obj = (self.manager.objectTypingDict or {}).get(cls_name)
        cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
        raw = getattr(cls, 'field_save_policy', None) if cls else None
        if not isinstance(raw, dict):
            return {}
        return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}

    # ------------------------------------------------------------------
    # POST /api/simulations/{sim_ref}/solutions
    # Body: { simStateClassName, solutionDefinitionRef?, orderIndex?,
    #         dependsOn?, name?, description?, enabled?,
    #         expectedInputs?, expectedOutputs? }
    # Creates a new SimulationExecutionSolution row scoped to this sim.
    # ------------------------------------------------------------------
    def on_post_solutions(self, request, response, sim_ref):
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
        # <sim>.<Class>[.<n>] — `n` disambiguates multiples per class.
        sol_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        existing_names = {getattr(r, 'name', '') for r in sol_table.values()}
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
            response.media = {'success': False, 'error': f'Solution row "{name}" already exists.'}
            return
        depends_on = body.get('dependsOn') or []
        if not isinstance(depends_on, list):
            depends_on = []
        order_index = body.get('orderIndex')
        try:
            order_index = int(order_index) if order_index is not None else 0
        except (TypeError, ValueError):
            order_index = 0
        expected_inputs = body.get('expectedInputs') or []
        expected_outputs = body.get('expectedOutputs') or []
        from simulations.simulation_execution_solution import SimulationExecutionSolution as _SES
        try:
            _SES(
                name=name,
                description=body.get('description') or '',
                simulation_definition_ref=sim_ref,
                sim_state_class_name=sim_state_class_name,
                solution_definition_ref=body.get('solutionDefinitionRef') or '',
                expected_inputs_json=json.dumps(expected_inputs),
                expected_outputs_json=json.dumps(expected_outputs),
                order_index=order_index,
                depends_on_json=json.dumps(depends_on),
                enabled=bool(body.get('enabled', True)),
                manager=self.manager,
            )
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Failed to create solution row: {e}'}
            return
        response.media = {'success': True, 'data': {'name': name}}
        response.status = falcon.HTTP_201

    # ------------------------------------------------------------------
    # DELETE /api/simulations/solutions/{solution_name}
    # ------------------------------------------------------------------
    def on_delete_solution_one(self, request, response, solution_name):
        sol_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        to_remove = None
        for key, inst in sol_table.items():
            if getattr(inst, 'name', '') == solution_name:
                to_remove = key
                break
        if to_remove is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Solution row "{solution_name}" not found.'}
            return
        try:
            del sol_table[to_remove]
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Failed to delete solution row: {e}'}
            return
        response.media = {'success': True, 'data': {'name': solution_name}}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simulations/by-solution/{solution_name}
    # Returns every SimulationExecutionSolution whose
    # `solution_definition_ref` matches the supplied SolutionDefinition
    # name. Lets the no-code editor's initial-state overlay surface
    # "this solution is used by N simulations" without scanning every
    # simulation in turn.
    # ------------------------------------------------------------------
    def on_get_by_solution(self, request, response, solution_name):
        sol_table = self.manager.objectTables.get('SimulationExecutionSolution', {}) or {}
        out: List[Dict] = []
        for s in sol_table.values():
            if getattr(s, 'solution_definition_ref', '') != solution_name:
                continue
            out.append({
                'solutionRowName': getattr(s, 'name', ''),
                'simulationRef': getattr(s, 'simulation_definition_ref', ''),
                'simStateClassName': getattr(s, 'sim_state_class_name', ''),
                'enabled': bool(getattr(s, 'enabled', True)),
                'orderIndex': int(getattr(s, 'order_index', 0) or 0),
            })
        out.sort(key=lambda x: (x['simulationRef'], x['orderIndex'], x['solutionRowName']))
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/{sim_ref}/validate-initial-conditions
    # ------------------------------------------------------------------
    def on_post_validate_ic(self, request, response, sim_ref):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        sim_def = next((r for r in defs.values() if getattr(r, 'name', '') == sim_ref), None)
        if sim_def is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        posted_overrides = body.get('overrides') or {}
        if not isinstance(posted_overrides, dict):
            posted_overrides = {}
        # Optional parameter overrides — validated exactly as they'll run.
        posted_params = body.get('parameterOverrides') or {}
        if not isinstance(posted_params, dict):
            posted_params = {}

        sim_overrides = self._parse_json_dict(
            getattr(sim_def, 'initial_conditions_overrides_json', '') or '{}'
        )
        roster = self._parse_json_list(
            getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]'
        )
        participating = [c for c in roster if isinstance(c, str)]

        # Build the merged initial conditions per class — same resolution
        # order the runner uses at step 0.
        initial_by_class: Dict[str, Dict[str, Any]] = {}
        for cls_name in participating:
            initial_by_class[cls_name] = initial_field_values(
                self.manager, cls_name, sim_overrides, posted_overrides,
            )

        verdict = validate_initial_conditions(
            self.manager, sim_def, initial_by_class,
            param_overrides=posted_params,
        )
        response.media = {
            'success': True,
            'data': {
                **verdict,
                'mergedInitialConditions': initial_by_class,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/simulations/{sim_ref}/storage-estimate
    # Body: { fieldSaveOverrides?, timeStepSeconds? }
    # Returns per-class + per-field byte estimates against the posted
    # hypothetical overrides. The IC editor calls this on debounce so
    # users see how their tweaks affect overall storage before
    # committing to a run.
    # ------------------------------------------------------------------
    def on_post_storage_estimate(self, request, response, sim_ref):
        defs = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        sim_def = next((r for r in defs.values() if getattr(r, 'name', '') == sim_ref), None)
        if sim_def is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimulationDefinition "{sim_ref}" not found.'}
            return
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}

        # Build a transient SimulationRun stand-in carrying the posted
        # overrides so the estimator's resolution pipeline (class →
        # sim def → run) applies the user's hypotheticals without
        # mutating any real row.
        posted_overrides = body.get('fieldSaveOverrides') or {}
        if not isinstance(posted_overrides, dict):
            posted_overrides = {}
        try:
            posted_dt = float(body.get('timeStepSeconds') or 0)
        except (TypeError, ValueError):
            posted_dt = 0.0

        class _TransientRun:
            pass
        transient = _TransientRun()
        transient.name = ''
        transient.field_save_overrides_json = json.dumps(posted_overrides)
        transient.initial_conditions_overrides_json = '{}'
        transient.time_step_seconds = posted_dt

        estimate = estimate_run_storage(self.manager, sim_def, transient)
        response.media = {'success': True, 'data': estimate}
        response.status = falcon.HTTP_200

    @staticmethod
    def _parse_json_list(text: str):
        try:
            v = json.loads(text)
            return v if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _parse_json_dict(text: str):
        try:
            v = json.loads(text)
            return v if isinstance(v, dict) else {}
        except (ValueError, TypeError):
            return {}

    def _probe_role(
        self, solution_definition_ref: str
    ) -> "tuple[Optional[str], Optional[str]]":
        """Resolve a SimulationExecutionSolution's `solution_definition_ref`
        to the declared `simStepRole`. Returns `(role, error)`:
          - `(role, None)` when the role parses cleanly,
          - `(None, message)` when the row is unwired, the linked
            solution is missing, or its SimulationStateStep entry
            doesn't declare a valid role.
        Never raises — the editor sidebar needs to render mixed states
        of authoring (some rows wired, others not) without an
        endpoint failure.
        """
        if not solution_definition_ref:
            return None, 'no solution wired'
        solution_data = load_solution_data(self.manager, solution_definition_ref)
        if solution_data is None:
            return None, f"solution '{solution_definition_ref}' not found"
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
                # {source_sim: source_run} — non-empty means this run is a
                # COUPLED run (multi-scale); the page defaults to one.
                'coupledRunRefs': self._parse_json_dict(
                    getattr(r, 'coupled_run_refs_json', '') or '{}'
                ),
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
        # Per-run initial-conditions overrides — applied on top of the
        # sim def's defaults at step 0. Accept either parsed JSON or a
        # plain dict from the request body.
        ic_overrides = body.get('initialConditionsOverrides') or {}
        if not isinstance(ic_overrides, dict):
            ic_overrides = {}
        # Per-run dt override. 0 / missing = inherit the sim def's value.
        try:
            time_step_seconds = float(body.get('timeStepSeconds') or 0)
        except (TypeError, ValueError):
            time_step_seconds = 0.0
        # Per-run field-save overrides (Phase B). Layered on top of the
        # sim def's overrides at runtime; sim def wins over class
        # declarations; run wins over both.
        field_save_overrides = body.get('fieldSaveOverrides') or {}
        if not isinstance(field_save_overrides, dict):
            field_save_overrides = {}
        # Per-run parameter overrides (material picker / stage derive).
        param_overrides = body.get('parameterOverrides') or {}
        if not isinstance(param_overrides, dict):
            param_overrides = {}
        # Coupled source runs {source_sim: source_run} — a new run of a
        # multi-scale sim must name its sources or it runs uncoupled
        # (defaults). The page passes the template run's pairing through.
        coupled_run_refs = body.get('coupledRunRefs') or {}
        if not isinstance(coupled_run_refs, dict):
            coupled_run_refs = {}
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
                initial_conditions_overrides_json=json.dumps(ic_overrides),
                time_step_seconds=time_step_seconds,
                field_save_overrides_json=json.dumps(field_save_overrides),
                parameter_overrides_json=json.dumps(param_overrides),
                coupled_run_refs_json=json.dumps(coupled_run_refs),
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
