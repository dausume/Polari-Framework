"""
Equation Execution API

The primary flow is name-based: the frontend POSTs an equation name plus a
configuration of variable values; the backend loads the saved EquationDefinition,
resolves the bindings, executes the equation via equation_executor, and publishes
the result both as a synchronous HTTP response AND on a STOMP topic so subscribed
clients see it asynchronously (matches how the rest of the platform broadcasts
state changes — see polariCRUDE.py).

Endpoints
---------
POST /executeEquation
    Body: {
      name: string,                            # EquationDefinition name
      variableBindings?: { [symbol]: value },  # supplements / overrides stored bindings
      requestId?: string                       # echoed back for correlation
    }
    Response: { success, result_latex, result_numeric, error, warnings, requestId }
    Publishes on:
      /topic/EquationExecution                 (all results)
      /topic/EquationExecution/<name>          (per-equation channel)

POST /executeEquationDirect
    Ad-hoc execution without a saved EquationDefinition (useful for the
    Equations page test runner before a draft has been saved). Body matches
    the equation_executor signature directly.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode.equation_executor import execute_equation
import falcon
import json


class EquationExecutionAPI(treeObject):

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.executeApiName = '/executeEquation'
        self.directApiName = '/executeEquationDirect'
        if polServer is not None:
            polServer.falconServer.add_route(self.executeApiName, self)
            polServer.falconServer.add_route(self.directApiName, self, suffix='direct')

    # ------------------------------------------------------------------
    # POST /executeEquation — load equation by name, resolve bindings, run.
    # ------------------------------------------------------------------
    def on_post(self, request, response):
        try:
            body = self._parse_body(request)
            name = body.get('name', '')
            override_bindings = body.get('variableBindings') or {}
            request_id = body.get('requestId')

            if not name:
                response.status = falcon.HTTP_400
                response.media = self._wrap_error('name is required', request_id)
                return

            equation = self._find_equation_by_name(name)
            if not equation:
                response.status = falcon.HTTP_404
                response.media = self._wrap_error(f"Equation '{name}' not found.", request_id)
                return

            try:
                config = json.loads(equation.definition) if isinstance(equation.definition, str) else equation.definition
            except Exception as parse_err:
                response.status = falcon.HTTP_400
                response.media = self._wrap_error(
                    f"Equation '{name}' has invalid JSON definition: {parse_err}", request_id
                )
                return

            # Stored literal bindings + caller overrides. Non-literal sources
            # (dataset_field / object_variable / parameter) are caller-supplied.
            stored_bindings = self._resolve_stored_literal_bindings(config.get('variableBindings', []))
            stored_bindings.update(override_bindings)

            result = execute_equation(
                latex_expression=config.get('latexExpression', ''),
                operation_type=config.get('operationType', ''),
                variable_bindings=stored_bindings,
                bounds=config.get('bounds'),
                options=config.get('options') or {},
            )

            # Augment the payload before broadcasting / returning.
            result['name'] = name
            result['requestId'] = request_id

            self._publish_result(name, result)

            response.status = falcon.HTTP_200 if result.get('success') else falcon.HTTP_400
            response.media = result

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = self._wrap_error(f'{type(e).__name__}: {e}', body.get('requestId') if 'body' in locals() else None)

    # ------------------------------------------------------------------
    # POST /executeEquationDirect — ad-hoc, no saved definition required.
    # ------------------------------------------------------------------
    def on_post_direct(self, request, response):
        try:
            body = self._parse_body(request)
            request_id = body.get('requestId')

            result = execute_equation(
                latex_expression=body.get('latexExpression', ''),
                operation_type=body.get('operationType', ''),
                variable_bindings=body.get('variableBindings') or {},
                bounds=body.get('bounds'),
                options=body.get('options') or {},
            )
            result['requestId'] = request_id
            self._publish_result(name=None, result=result)

            response.status = falcon.HTTP_200 if result.get('success') else falcon.HTTP_400
            response.media = result

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = self._wrap_error(f'{type(e).__name__}: {e}',
                                              body.get('requestId') if 'body' in locals() else None)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parse_body(self, request):
        raw = request.bounded_stream.read()
        if not raw:
            return {}
        return json.loads(raw)

    def _find_equation_by_name(self, name: str):
        instances = self.manager.objectTables.get('EquationDefinition', {})
        for inst in instances.values():
            if getattr(inst, 'name', '') == name:
                return inst
        return None

    def _resolve_stored_literal_bindings(self, bindings_list) -> dict:
        out = {}
        for binding in bindings_list or []:
            symbol = binding.get('symbol')
            source = binding.get('source') or {}
            if source.get('type') == 'literal' and symbol:
                out[symbol] = source.get('value')
        return out

    def _publish_result(self, name, result):
        """Broadcast on STOMP topics so subscribed clients see results asynchronously."""
        try:
            from polariApiServer.stompWebSocketServer import get_stomp_server
            stompServer = get_stomp_server()
            if stompServer is None:
                return
            stompServer.publish('/topic/EquationExecution', result)
            if name:
                stompServer.publish(f'/topic/EquationExecution/{name}', result)
        except Exception:
            # Telemetry only — never block the API response on broadcast failure.
            pass

    def _wrap_error(self, message: str, request_id):
        return {
            'success': False,
            'result_latex': None,
            'result_numeric': None,
            'error': message,
            'warnings': [],
            'requestId': request_id,
        }
