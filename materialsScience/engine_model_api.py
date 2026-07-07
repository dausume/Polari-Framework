"""
@module materialsScience.engine_model_api

HTTP surface for the engine-model layer (PeersAPI pattern —
self-registering falcon routes; separate module keeps the other msci
APIs at size):

  GET  /api/msci/engine-templates
       The catalog with a LIVE capability verdict per template (which
       physics/calculations can actually execute right now).
  POST /api/msci/models/{name}/validate
       Configuration-time check: schema + FEM/DFT section honesty.
  POST /api/msci/models/{name}/execute   {"stageContext"?: {...}}
       Full execution (422 on refusal; the refusal names the exact
       missing knob/capability).

CRUDE covers create/read/update of EngineModelTemplate /
FEMModelDefinition / DFTModelDefinition rows for free.
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.component_binding import validate_model
from materialsScience.model_execution import (
    check_capability_requirements, execute_model, find_model,
)


class EngineModelAPI(treeObject):
    """Engine-model catalog + model validate/execute endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/engine-templates', self, suffix='templates')
            polServer.falconServer.add_route(
                '/api/msci/models/{name}/validate', self,
                suffix='validate')
            polServer.falconServer.add_route(
                '/api/msci/models/{name}/execute', self,
                suffix='execute')

    def on_get_templates(self, request, response):
        table = (self.manager.objectTables or {}).get(
            'EngineModelTemplate', {}) or {}
        rows = table.values() if isinstance(table, dict) else table

        def _payload(row):
            def _loads(attr, default):
                try:
                    return json.loads(getattr(row, attr, '') or '')
                except (TypeError, ValueError):
                    return default
            return {
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'description': getattr(row, 'description', ''),
                'engineKind': getattr(row, 'engine_kind', ''),
                'engineKey': getattr(row, 'engine_key', ''),
                'parameterSchema': _loads('parameter_schema_json', []),
                'sectionMap': _loads('section_map_json', {}),
                'outputs': _loads('outputs_json', []),
                'costClass': getattr(row, 'cost_class', ''),
                'capabilityRequirements': _loads(
                    'capability_requirements_json', []),
                'capability': check_capability_requirements(row),
                'notes': getattr(row, 'notes', ''),
                'enabled': getattr(row, 'enabled', True),
            }

        response.media = {'success': True,
                          'data': sorted((_payload(r) for r in rows),
                                         key=lambda t: t['name'])}

    def on_post_validate(self, request, response, name):
        model, model_class = find_model(self.manager, name)
        if model is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no model definition named "
                                       f"'{name}'"}
            return
        verdict = validate_model(self.manager, model)
        verdict['model'] = name
        verdict['modelClass'] = model_class
        response.media = verdict

    def on_post_execute(self, request, response, name):
        try:
            body = json.load(request.bounded_stream)
        except Exception:
            body = {}
        report = execute_model(
            self.manager, name,
            stage_context=body.get('stageContext') or None)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report
