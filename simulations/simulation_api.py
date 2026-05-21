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

from typing import Dict, List

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

from .storage_predictor import predict_storage


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
