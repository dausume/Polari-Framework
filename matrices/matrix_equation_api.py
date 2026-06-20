"""
Matrix Equation API — evaluate / validate a MatrixEquationDefinition.

CRUD comes from registering the class in defClassList. This API adds:

POST /api/matrix-equations/evaluate
    Body: { name?: string, definition?: {...}, bindings?: {...} }
    Response: { success, shape, dtype, data, error, warnings }

POST /api/matrix-equations/validate
    Body: { name? | definition? }
    Response: { valid, errors, warnings, kind }
"""

from objectTreeDecorators import treeObject, treeObjectInit
from matrices.matrix_equation_executor import evaluate_equation, validate_equation
from matrices.matrix_executor import MatrixEvalError
from matrices.matrix_api import MatrixAPI  # reuse array→json + binding helpers
import falcon
import json
from types import SimpleNamespace

import numpy as np

_DEF_FIELDS = {
    'name': '',
    'description': '',
    'latex': '',
    'operation_json': '{}',
    'operands_json': '{}',
    'tags': '',
}


class MatrixEquationAPI(treeObject):

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.evaluateApiName = '/api/matrix-equations/evaluate'
        self.validateApiName = '/api/matrix-equations/validate'
        if polServer is not None:
            polServer.falconServer.add_route(self.evaluateApiName, self)
            polServer.falconServer.add_route(self.validateApiName, self, suffix='validate')

    def on_post(self, request, response):
        try:
            body = self._parse_body(request)
            eq_def, err = self._resolve_definition(body)
            if err:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': err, 'warnings': []}
                return
            bindings = MatrixAPI._normalize_bindings(self, body.get('bindings') or {})
            arr = evaluate_equation(eq_def, binding_values=bindings, manager=self.manager)
            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'shape': list(arr.shape),
                'dtype': MatrixAPI._dtype_label(arr),
                'data': MatrixAPI._array_to_json(arr),
                'error': None,
                'warnings': [],
            }
        except MatrixEvalError as e:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': str(e), 'warnings': []}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'{type(e).__name__}: {e}', 'warnings': []}

    def on_post_validate(self, request, response):
        try:
            body = self._parse_body(request)
            eq_def, err = self._resolve_definition(body)
            if err:
                response.status = falcon.HTTP_400
                response.media = {'valid': False, 'errors': [err], 'warnings': []}
                return
            response.status = falcon.HTTP_200
            response.media = validate_equation(eq_def, manager=self.manager)
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'valid': False, 'errors': [f'{type(e).__name__}: {e}'], 'warnings': []}

    # ------------------------------------------------------------------

    def _parse_body(self, request):
        raw = request.bounded_stream.read()
        return json.loads(raw) if raw else {}

    def _resolve_definition(self, body):
        name = (body.get('name') or '').strip()
        if name:
            found = self._find_by_name(name)
            if found is None:
                return None, f"MatrixEquationDefinition '{name}' not found"
            return found, None
        definition = body.get('definition')
        if isinstance(definition, dict):
            return self._wrap_inline(definition), None
        return None, "request must include 'name' or 'definition'"

    def _wrap_inline(self, definition: dict) -> SimpleNamespace:
        ns = SimpleNamespace()
        for field, default in _DEF_FIELDS.items():
            value = definition.get(field, default)
            if field in ('operation_json', 'operands_json') and not isinstance(value, str):
                value = json.dumps(value)
            setattr(ns, field, value)
        return ns

    def _find_by_name(self, name: str):
        instances = self.manager.objectTables.get('MatrixEquationDefinition', {}) or {}
        for inst in instances.values():
            if getattr(inst, 'name', '') == name:
                return inst
        return None
