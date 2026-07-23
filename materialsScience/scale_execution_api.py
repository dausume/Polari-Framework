"""
@cross-cutting
@module materialsScience.scale_execution_api
@tags @xc:bindings

HTTP surface for the materials basis engines (PeersAPI pattern —
self-registering falcon routes):

  GET  /api/msci/engines/capability      honest FEM+DFT capability
                                         (local layers + worker reach)
  POST /api/msci/scale-definitions/execute   {"name": "<row name>"} →
                                         execute_scale_definition
  POST /api/msci/gates/check             {"material": ..., "levels": [..],
                                         "acceptPartial": bool} →
                                         require_scale_levels verdict
  POST /api/msci/composites/search       {"profileId": ...,
                                         "baseProperties": {...},
                                         ...knobs} → ranked candidates
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.engines import dft_engine, fem_engine
from materialsScience.scale_execution import execute_scale_definition
from materialsScience.scale_presence import require_scale_levels


class ScaleExecutionAPI(treeObject):
    """Materials-basis engine + gate endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/engines/capability', self, suffix='capability')
            polServer.falconServer.add_route(
                '/api/msci/scale-definitions/execute', self,
                suffix='execute')
            polServer.falconServer.add_route(
                '/api/msci/gates/check', self, suffix='gates')
            polServer.falconServer.add_route(
                '/api/msci/composites/search', self, suffix='composites')
            polServer.falconServer.add_route(
                '/api/msci/composites/refine', self, suffix='refine')

    def on_get_capability(self, request, response):
        from materialsScience.engines import (
            lattice_dynamics_engine, md_engine, meso_engine,
        )
        response.media = {
            'fem': fem_engine.capability(),
            'dft': dft_engine.capability(),
            'md': md_engine.capability(),
            'meso': meso_engine.capability(),
            'ssp': lattice_dynamics_engine.capability(),
        }

    def on_post_execute(self, request, response):
        body = json.load(request.bounded_stream)
        name = body.get('name', '')
        if not name:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'name' is required"}
            return
        result = execute_scale_definition(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_gates(self, request, response):
        body = json.load(request.bounded_stream)
        material = body.get('material', '')
        levels = body.get('levels', [])
        if not material or not isinstance(levels, list) or not levels:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "'material' and non-empty 'levels' "
                                       "are required"}
            return
        response.media = require_scale_levels(
            self.manager, material, levels,
            accept_partial=bool(body.get('acceptPartial', False)))

    def on_post_composites(self, request, response):
        from materialsScience.composite_search import search_for_profile
        body = json.load(request.bounded_stream)
        profileId = body.get('profileId', '')
        baseProperties = body.get('baseProperties', {})
        if not profileId or not isinstance(baseProperties, dict):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "'profileId' and 'baseProperties' "
                                       "(dict, manually entered values) "
                                       "are required"}
            return
        knobNames = ('maxAdditives', 'loadingStep', 'perAdditiveCap',
                     'maxTotalLoad', 'stopPolicy', 'continueAfterWinner',
                     'maxCandidates', 'process', 'base_material_name',
                     'thermal_knobs', 'sourcingPolicy')
        knobs = {k: body[k] for k in knobNames if k in body}
        if knobs.get('process'):
            # The no-volatiles gate reads ThermalProcessingProfile rows
            # (seeded from Dustin's Base Wax Properties notes).
            from materialsScience.thermal_windows import profiles_from_rows
            table = (self.manager.objectTables or {}).get(
                'ThermalProcessingProfile', {})
            rows = table.values() if isinstance(table, dict) else table
            knobs['thermal_profiles'] = profiles_from_rows(rows)
        result = search_for_profile(profileId, baseProperties, **knobs)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_refine(self, request, response):
        """Batch-incremental refinement toward a profile's targets —
        returns the inspectable trajectory + gap analysis."""
        from materialsScience.batch_refine import refine_formulation
        from materialsScience.composite_search import (
            load_legacy_seed_data, normalize_targets,
        )
        body = json.load(request.bounded_stream)
        profileId = body.get('profileId', '')
        baseProperties = body.get('baseProperties', {})
        if not profileId or not isinstance(baseProperties, dict):
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "'profileId' and 'baseProperties' "
                                       "are required"}
            return
        data = load_legacy_seed_data()
        targetRows = [t for t in data['targets']
                      if t['profileId'] == profileId]
        if not targetRows:
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'error': f"no PropertyTargets for profile '{profileId}'",
                'knownProfiles': sorted(
                    {t['profileId'] for t in data['targets']})}
            return
        knobNames = ('start_components', 'loadingStep', 'minLoadingStep',
                     'perAdditiveCap', 'maxTotalLoad', 'maxBatches',
                     'process', 'base_material_name', 'thermal_knobs',
                     'sourcingPolicy')
        knobs = {k: body[k] for k in knobNames if k in body}
        knobs['raws'] = data['raws']
        if knobs.get('process'):
            from materialsScience.thermal_windows import profiles_from_rows
            table = (self.manager.objectTables or {}).get(
                'ThermalProcessingProfile', {})
            rows = table.values() if isinstance(table, dict) else table
            knobs['thermal_profiles'] = profiles_from_rows(rows)
        result = refine_formulation(
            baseProperties, normalize_targets(targetRows),
            data['additives'], data['effects'], **knobs)
        result['ok'] = True
        result['profileId'] = profileId
        response.media = result
