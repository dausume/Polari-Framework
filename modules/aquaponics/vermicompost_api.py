"""
@cross-cutting
@module aquaponics.vermicompost_api
@tags @xc:bindings

HTTP surface for aqp-7 vermicompost enrichment:

  GET  /api/aquaponics/compost-bins/{name}/release
        the bed's steady soluble release profile (no flow yet).
  POST /api/aquaponics/compost-loops/{name}/simulate
        body {mode?, hours?} -> per-species enrichment timeline +
        cycle-averaged + pulse peaks + limiting factor; PERSISTS a
        snapshot to enrichment_result_json (saveInstanceInDB).
  GET  /api/aquaponics/compost-loops/{name}/compare-modes?hours=..
        direct vs periodic side by side + an evidence-bearing
        recommendation (knobs-and-suggestions).
  GET  /api/aquaponics/compost-loops/{name}/enriched-water?hours=..
        the enriched water profile the coupled pot draws (base vs
        uplift vs enriched).

Bins / profiles / loops are edited through standard CRUDE
(object-coherence).

@consumers
  - aquaponics frontend (later); scoring via enrichment_result_json
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-7
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.custom.vermicompost_analysis import (
    compare_modes, enriched_water_profile, simulate_enrichment,
    steady_release,
)


class AquaponicsCompostAPI(treeObject):
    """aqp-7 vermicompost endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/compost-bins'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/compost-bins/{name}/release', self,
                suffix='release')
            polServer.falconServer.add_route(
                '/api/aquaponics/compost-loops/{name}/simulate', self,
                suffix='simulate')
            polServer.falconServer.add_route(
                '/api/aquaponics/compost-loops/{name}/compare-modes',
                self, suffix='compare')
            polServer.falconServer.add_route(
                '/api/aquaponics/compost-loops/{name}/enriched-water',
                self, suffix='enriched')

    def _loop(self, name):
        table = (self.manager.objectTables or {}).get(
            'CompostLoopDefinition', {})
        rows = table.values() if isinstance(table, dict) else table
        for row in rows:
            if getattr(row, 'name', '') == name:
                return row
        return None

    def on_get_release(self, request, response, name):
        result = steady_release(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_post_simulate(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        loop = self._loop(name)
        if loop is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no CompostLoopDefinition "
                                       f"named '{name}'"}
            return
        mode = body.get('mode') or getattr(loop, 'mode', '') or None
        hours = float(body.get('hours', 24.0) or 24.0)
        flow = getattr(loop, 'assumed_flow_l_per_hr', None)
        result = simulate_enrichment(
            self.manager, getattr(loop, 'bin_name', ''), mode=mode,
            hours=hours,
            flow_l_per_hr=float(flow) if flow is not None else None)
        if not result.get('ok'):
            response.status = '400 Bad Request'
            response.media = result
            return
        # Persist a compact snapshot for the scoring bridge.
        nitrogen = (result['cycleAveragedMgPerL'].get('nitrate-n', 0.0)
                    + result['cycleAveragedMgPerL'].get('ammonium-n',
                                                        0.0))
        snapshot = {
            'mode': result['mode'],
            'totalLeachedMg': round(
                sum(result['cumulativeLeachedMg'].values()), 4),
            'nitrogenUpliftMgPerL': round(nitrogen, 4),
            'phosphorusUpliftMgPerL':
                result['cycleAveragedMgPerL'].get('phosphorus-p', 0.0),
            'pulsePeakNMgPerL':
                result['pulsePeakMgPerL'].get('nitrate-n', 0.0)}
        loop.enrichment_result_json = json.dumps(snapshot)
        try:
            self.manager.db.saveInstanceInDB(loop)
        except Exception:
            pass   # in-memory managers / selftests have no db
        result['persistedSnapshot'] = snapshot
        response.media = result

    def on_get_compare(self, request, response, name):
        loop = self._loop(name)
        if loop is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no CompostLoopDefinition "
                                       f"named '{name}'"}
            return
        hours = float((request.params or {}).get('hours', 24.0) or 24.0)
        flow = getattr(loop, 'assumed_flow_l_per_hr', None)
        result = compare_modes(
            self.manager, getattr(loop, 'bin_name', ''), hours=hours,
            flow_l_per_hr=float(flow) if flow is not None else None)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_enriched(self, request, response, name):
        hours = float((request.params or {}).get('hours', 24.0) or 24.0)
        result = enriched_water_profile(self.manager, name, hours=hours)
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no CompostLoop' in str(result.get('error', '')) \
                else '400 Bad Request'
        response.media = result
