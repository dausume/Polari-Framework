"""
@cross-cutting
@module simSpace.sim_space_api
@tags @xc:render-shared, @xc:bindings

Snapshot endpoint — the dimension-dispatching surface the frontend hits
to render a SimSpace. One URL, one envelope, dimension-specific compilers:

    GET /api/simspace                  list (filterable by ?dimensionality=)
    GET /api/simspace/{name}/snapshot  compile + return

Response envelope (regardless of dimensionality):
    {
      "success": true,
      "data": {
        "definition":       SimSpaceDefinitionPayload,
        "objects":          [SimSpaceObject, ...],
        "connections":      [SimSpaceConnection, ...],
        "resolvedBindings": [SimSpaceResolvedBinding, ...],
        "warnings":         [string, ...]
      }
    }

The dimension-specific compile logic lives in `compilers/` — this file
only wires the route handlers and delegates.

@consumers
  - polariServer (route registration)
  - frontend SimSpaceService
@impact-on-edit
  Changing the response shape is a frontend breaking change. Update
  SimSpaceSnapshot in sim-space-types.ts in the same PR.
@see /OVERLAP_MAP.md
"""

import json
from typing import Dict, List, Optional

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

from .compilers import compile_2d, compile_3d
from .compilers.common import load_bound_overrides
from simulations.equation_evaluation import (
    collect_evaluation_metadata,
    evaluate_at_step,
)


class SimSpaceAPI(treeObject):
    """Routes:
        GET /api/simspace                  list all SimSpaceDefinitions
        GET /api/simspace/{name}/snapshot  compile + return the snapshot
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/simspace'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(
                self.apiName + '/{name}/snapshot', self, suffix='snapshot'
            )
            # On-demand single-step evaluation. The viewer fires this
            # (debounced) when the user pauses on a particular scrubber
            # time; it returns the same metadata shape as the snapshot's
            # `evaluations`, but with `perStep` carrying exactly one
            # entry for the requested step. No batch / no caching layer —
            # the parse-cache inside the evaluator covers the LaTeX
            # parse cost across repeated stops.
            polServer.falconServer.add_route(
                self.apiName + '/{name}/evaluations/at', self,
                suffix='evaluations_at',
            )

    # ------------------------------------------------------------------
    # GET /api/simspace — list (filterable by ?dimensionality=2d|3d)
    # ------------------------------------------------------------------
    def on_get(self, request, response):
        dim_filter = request.get_param('dimensionality')
        rows = self.manager.objectTables.get('SimSpaceDefinition', {}) or {}
        out: List[Dict] = []
        for r in rows.values():
            if dim_filter and getattr(r, 'dimensionality', '2d') != dim_filter:
                continue
            out.append(self._row_to_summary(r))
        out.sort(key=lambda x: x['name'])
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simspace/{name}/snapshot
    # ------------------------------------------------------------------
    def on_get_snapshot(self, request, response, name):
        row = self._find_by_name(name)
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimSpace "{name}" not found'}
            return
        dim = getattr(row, 'dimensionality', '2d')
        warnings: List[str] = []
        resolved_bindings: List[Dict] = []
        # Optional ?run=<run_name> — restrict *SimState rows to one
        # SimulationRun. Without this, multiple runs in the same scene
        # would render their rows overlaid. Frontend defaults to the
        # latest-complete run when no explicit selection.
        run_filter = request.get_param('run') or None
        # State-Projection arrows (3D only for now); 2D leaves it empty.
        vectors: List[Dict] = []
        try:
            if dim == '2d':
                objects, connections = compile_2d(
                    self.manager, row, warnings, resolved_bindings,
                    run_filter=run_filter,
                )
            elif dim == '3d':
                objects, connections, vectors = compile_3d(
                    self.manager, row, warnings, resolved_bindings,
                    run_filter=run_filter,
                )
            else:
                objects, connections = [], []
                warnings.append(f"Unknown dimensionality '{dim}' — returning empty snapshot.")
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Snapshot compile failed: {e}'}
            return

        # Equation overlay metadata only — values are computed on-demand
        # when the user stops on a particular time (the /evaluations/at
        # endpoint, fired from the viewer with a debounce). Keeps the
        # snapshot endpoint free of SymPy work and parses each LaTeX at
        # most once per stop, not 200+ times per snapshot.
        try:
            evaluations = collect_evaluation_metadata(
                self.manager, row, warnings,
            )
        except Exception as e:
            evaluations = []
            warnings.append(f'Equation metadata pass failed: {e}')

        response.media = {
            'success': True,
            'data': {
                'definition': self._row_to_payload(row),
                'objects': objects,
                'connections': connections,
                'vectors': vectors,
                'resolvedBindings': resolved_bindings,
                'evaluations': evaluations,
                'warnings': warnings,
                'activeRunRef': run_filter,
                # Independent of instance count — derived from the scene's
                # bound *SimState classes' class-level
                # `simulation_definition_name` metadata. The run panel
                # uses this so it stays visible even on a fresh empty run.
                'participatingSimulations': self._participating_sims_for(row),
                # Per-sim config (dt, time_unit) for each participating
                # SimulationDefinition. Drives the run-panel placeholder
                # for the dt override input + result-time formatting
                # without an extra round trip.
                'simulationDefaultsByName': self._simulation_defaults_for(
                    self._participating_sims_for(row),
                ),
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simspace/{name}/evaluations/at?step=<int> or ?time=<float>
    # Evaluate every SimSpaceEvaluationEquation in the scene at ONE step.
    # Fired (debounced) by the viewer when the user pauses on a scrubber
    # position they're interested in. Cheap — one substitute + numeric
    # eval per overlay, leveraging the LaTeX parse cache.
    # ------------------------------------------------------------------
    def on_get_evaluations_at(self, request, response, name):
        row = self._find_by_name(name)
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimSpace "{name}" not found'}
            return
        step_param = request.get_param('step')
        time_param = request.get_param('time')
        # Scope the evaluation to the SAME run the viewer is rendering
        # (snapshot's `?run=`). Without it, a stale run's rows can pin the
        # readouts to frozen values while the renderer shows the live run.
        run_filter = request.get_param('run') or None
        target_step: Optional[int] = None
        target_time: Optional[float] = None
        if step_param is not None:
            try:
                target_step = int(step_param)
            except (TypeError, ValueError):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': "'step' must be integer."}
                return
        elif time_param is not None:
            try:
                target_time = float(time_param)
            except (TypeError, ValueError):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': "'time' must be numeric."}
                return
        warnings: List[str] = []
        try:
            evaluations = evaluate_at_step(
                self.manager, row, warnings,
                step=target_step, time_value=target_time,
                run_filter=run_filter,
            )
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Evaluation failed: {e}'}
            return
        response.media = {
            'success': True,
            'data': {
                'evaluations': evaluations,
                'warnings': warnings,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # Helpers (small enough to keep alongside the routes)
    # ------------------------------------------------------------------
    def _simulation_defaults_for(self, sim_names: List[str]) -> Dict[str, Dict]:
        """Look up `time_step_seconds` + `time_unit` per SimulationDefinition.
        Returned as a dict keyed by sim name so the frontend can pull
        defaults by the same `simulationDefinitionName` it's already
        using for the run panel.
        """
        out: Dict[str, Dict] = {}
        if not sim_names:
            return out
        sims_table = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        wanted = set(sim_names)
        for s in sims_table.values():
            name = getattr(s, 'name', '')
            if name not in wanted:
                continue
            try:
                dt = float(getattr(s, 'time_step_seconds', 0.0) or 0.0)
            except (TypeError, ValueError):
                dt = 0.0
            out[name] = {
                'timeStepSeconds': dt,
                'timeUnit': getattr(s, 'time_unit', 'second') or 'second',
            }
        return out

    def _participating_sims_for(self, scene_row) -> List[str]:
        """Walk the scene's bound *SimState classes and collect each
        class-level `simulation_definition_name`. Deduped; preserves
        first-seen order. Independent of instance count — a brand-new
        live run with zero rows still shows up here so the viewer keeps
        the run panel visible.

        Scoped to THIS scene's `bound_classes_json`. SimSpaceBindingDefinitions
        are global per (class_name, dimensionality), not per-scene, so without
        this scope a scene inherits EVERY same-dimension binding's simulation —
        e.g. the 3D newtonian scene picking up the `defaultVisible` 3D bindings
        of the 2D pendulum and (first-seen) defaulting its whole run panel /
        play / eval scope to `pendulum-2d`, which starves the newtonian run.

        A scene that declares NO bound classes gets NO participating
        simulations — not a fallback to "every enabled binding of the
        dimension." That fallback existed briefly (legacy) and leaked
        every same-dimension simulation into every unscoped scene: e.g.
        WindFieldGridState's 3D binding (real, needed by
        newtonian-pendulum-viz, which explicitly lists it) was also
        showing up as "participating" in demo-3d, the material/periodic
        selector scenes, and the aquaponics pot scenes — none of which
        have anything to do with wind, or with each other's runs at
        all (found 2026-07-14). A freestanding or otherwise unscoped
        scene has no class-bound content to run a simulation against in
        the first place, so an empty result is the correct/honest
        answer, not an under-scoped guess."""
        dim = getattr(scene_row, 'dimensionality', '2d')
        scene_classes = set(load_bound_overrides(scene_row, []).keys())
        if not scene_classes:
            return []
        bindings_table = self.manager.objectTables.get('SimSpaceBindingDefinition', {}) or {}
        seen: List[str] = []
        for b in bindings_table.values():
            if getattr(b, 'dimensionality', '') != dim:
                continue
            if not getattr(b, 'enabled', False):
                continue
            cls_name = getattr(b, 'class_name', '')
            if not cls_name:
                continue
            # Scope to the scene's declared bound classes.
            if cls_name not in scene_classes:
                continue
            typing_obj = self.manager.objectTypingDict.get(cls_name)
            cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
            if cls is None:
                sample_table = self.manager.objectTables.get(cls_name, {}) or {}
                for inst in sample_table.values():
                    cls = inst.__class__
                    break
            sim_def_name = getattr(cls, 'simulation_definition_name', '') if cls else ''
            if sim_def_name and sim_def_name not in seen:
                seen.append(sim_def_name)
        return seen

    def _find_by_name(self, name: str):
        rows = self.manager.objectTables.get('SimSpaceDefinition', {}) or {}
        for r in rows.values():
            if getattr(r, 'name', '') == name:
                return r
        return None

    def _row_to_summary(self, row) -> Dict:
        return {
            'name': row.name,
            'description': getattr(row, 'description', ''),
            'dimensionality': getattr(row, 'dimensionality', '2d'),
            'coordinateSystem': getattr(row, 'coordinate_system', 'math'),
        }

    def _row_to_payload(self, row) -> Dict:
        try:
            viewport = json.loads(getattr(row, 'viewport_json', '') or 'null')
        except (ValueError, TypeError):
            viewport = None
        try:
            bound_classes = json.loads(getattr(row, 'bound_classes_json', '') or '[]')
        except (ValueError, TypeError):
            bound_classes = []
        try:
            axis_labels = json.loads(getattr(row, 'axis_labels_json', '') or '{}')
        except (ValueError, TypeError):
            axis_labels = {}
        try:
            camera = json.loads(getattr(row, 'camera_json', '') or 'null')
        except (ValueError, TypeError):
            camera = None
        try:
            configured_interfaces = json.loads(
                getattr(row, 'configured_interfaces_json', '') or '[]')
        except (ValueError, TypeError):
            configured_interfaces = []
        if not isinstance(configured_interfaces, list):
            configured_interfaces = []
        configured_interfaces = [
            ci for ci in configured_interfaces
            if isinstance(ci, dict) and ci.get('componentName')
        ]
        return {
            'id': row.name,
            'name': row.name,
            'description': getattr(row, 'description', ''),
            'dimensionality': getattr(row, 'dimensionality', '2d'),
            'coordinateSystem': getattr(row, 'coordinate_system', 'math'),
            'unitScale': getattr(row, 'unit_scale', 1.0),
            'viewport': viewport,
            'boundClasses': bound_classes,
            'definition': getattr(row, 'definition', '{}'),
            'axisLabels': axis_labels,
            'camera': camera,
            'configuredInterfaces': configured_interfaces,
        }
