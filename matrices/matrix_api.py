"""
Matrix API — evaluate / validate a MatrixDefinition.

CRUD for MatrixDefinition comes for free from registering the class in
`polariServer.defClassList` (same as EquationDefinition). This API adds the
math-logic routes:

POST /api/matrices/evaluate
    Body: {
      name?: string,           # evaluate a saved MatrixDefinition by name
      definition?: { ... },    # OR an inline definition (Test tab, pre-save)
      bindings?: { [name]: number | number[][] }   # runtime scalars/arrays
    }
    Response: { success, shape, dtype, data, error, warnings }
      data is the resolved array as nested lists (complex → {re, im}).

POST /api/matrices/validate
    Body: { name? | definition? }
    Response: { valid, errors, warnings, shape, composedShape, elementType, kind }
"""

from objectTreeDecorators import treeObject, treeObjectInit
from matrices.matrix_executor import evaluate, MatrixEvalError
from matrices.matrix_validator import validate as validate_matrix
import falcon
import json
from types import SimpleNamespace

import numpy as np


# Fields a definition object must expose for the executor/validator. Inline
# definitions from the Test tab are wrapped in a SimpleNamespace with these.
_DEF_FIELDS = {
    'name': '',
    'description': '',
    'shape_json': '[]',
    'element_type': 'float',
    'element_matrix_ref': '',
    'values_json': '[]',
    'computation_json': '{"kind": "literal"}',
    'is_template': False,
    'tags': '',
}


class MatrixAPI(treeObject):

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.evaluateApiName = '/api/matrices/evaluate'
        self.validateApiName = '/api/matrices/validate'
        if polServer is not None:
            polServer.falconServer.add_route(self.evaluateApiName, self)
            polServer.falconServer.add_route(self.validateApiName, self, suffix='validate')

    # ------------------------------------------------------------------
    # POST /api/matrices/evaluate
    # ------------------------------------------------------------------
    def on_post(self, request, response):
        try:
            body = self._parse_body(request)
            matrix_def, err = self._resolve_definition(body)
            if err:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': err, 'warnings': []}
                return
            bindings = self._normalize_bindings(body.get('bindings') or {})
            arr = evaluate(matrix_def, binding_values=bindings, manager=self.manager)
            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'shape': list(arr.shape),
                'dtype': self._dtype_label(arr),
                'data': self._array_to_json(arr),
                'error': None,
                'warnings': [],
            }
        except MatrixEvalError as e:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': str(e), 'warnings': []}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'{type(e).__name__}: {e}', 'warnings': []}

    # ------------------------------------------------------------------
    # POST /api/matrices/validate
    # ------------------------------------------------------------------
    def on_post_validate(self, request, response):
        try:
            body = self._parse_body(request)
            matrix_def, err = self._resolve_definition(body)
            if err:
                response.status = falcon.HTTP_400
                response.media = {'valid': False, 'errors': [err], 'warnings': []}
                return
            result = validate_matrix(matrix_def, manager=self.manager)
            response.status = falcon.HTTP_200
            response.media = result
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'valid': False, 'errors': [f'{type(e).__name__}: {e}'], 'warnings': []}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parse_body(self, request):
        raw = request.bounded_stream.read()
        if not raw:
            return {}
        return json.loads(raw)

    def _resolve_definition(self, body):
        """Return (definition_obj, error). Prefers a saved matrix by name;
        otherwise wraps an inline definition dict in a SimpleNamespace."""
        name = (body.get('name') or '').strip()
        if name:
            found = self._find_matrix_by_name(name)
            if found is None:
                return None, f"MatrixDefinition '{name}' not found"
            return found, None
        definition = body.get('definition')
        if isinstance(definition, dict):
            return self._wrap_inline(definition), None
        return None, "request must include 'name' or 'definition'"

    def _wrap_inline(self, definition: dict) -> SimpleNamespace:
        ns = SimpleNamespace()
        for field, default in _DEF_FIELDS.items():
            value = definition.get(field, default)
            # Allow shape/values/computation to arrive as JSON values OR strings.
            if field in ('shape_json', 'values_json', 'computation_json') and not isinstance(value, str):
                value = json.dumps(value)
            setattr(ns, field, value)
        return ns

    def _find_matrix_by_name(self, name: str):
        instances = self.manager.objectTables.get('MatrixDefinition', {}) or {}
        for inst in instances.values():
            if getattr(inst, 'name', '') == name:
                return inst
        return None

    def _normalize_bindings(self, bindings: dict) -> dict:
        """Pass scalars through; turn nested lists into ndarrays so they can
        be used directly as matrix operands."""
        out = {}
        for k, v in bindings.items():
            out[k] = np.asarray(v) if isinstance(v, list) else v
        return out

    @staticmethod
    def _dtype_label(arr: np.ndarray) -> str:
        if np.iscomplexobj(arr):
            return 'complex'
        if np.issubdtype(arr.dtype, np.integer):
            return 'int'
        return 'float'

    @classmethod
    def _array_to_json(cls, arr: np.ndarray):
        """Nested lists; complex values become {re, im} so JSON survives."""
        if arr.ndim == 0:
            return cls._scalar_to_json(arr.item())
        return [cls._array_to_json(sub) if isinstance(sub, np.ndarray) and sub.ndim > 0
                else cls._scalar_to_json(sub.item() if hasattr(sub, 'item') else sub)
                for sub in arr]

    @staticmethod
    def _scalar_to_json(v):
        if isinstance(v, complex):
            return {'re': v.real, 'im': v.imag}
        return v
