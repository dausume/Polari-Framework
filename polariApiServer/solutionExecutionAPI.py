"""
Solution Execution API

Provides endpoints for executing no-code solutions:
- POST /executeSolution         - Execute a solution by name (code generation only)
- POST /executeSolutionStepped  - Execute a solution step-by-step, return full ExecutionTrace
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiServer.solutionCodeGeneratorAPI import generate_code_from_solution
from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine
from polariNoCode.stepping import StepConfig
import falcon
import json
import time


class SolutionExecutionAPI(treeObject):
    """
    API endpoint for executing no-code solutions.
    POST /executeSolution          - Phase 1: code generation
    POST /executeSolutionStepped   - Phase 2: step-by-step execution with full trace
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/executeSolution'
        self.steppedApiName = '/executeSolutionStepped'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.steppedApiName, self, suffix='stepped')

    def on_post(self, request, response):
        """Execute a named solution with optional input parameters."""
        try:
            # Parse multipart form data or JSON body
            solution_name = None
            input_params = {}
            target_runtime = 'python_backend'

            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                solution_name = request.get_param('solutionName')
                input_params_str = request.get_param('inputParams')
                target_runtime = request.get_param('targetRuntime') or 'python_backend'
                if input_params_str:
                    try:
                        input_params = json.loads(input_params_str)
                    except:
                        input_params = {}
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                solution_name = body.get('solutionName', '')
                input_params = body.get('inputParams', {})
                target_runtime = body.get('targetRuntime', 'python_backend')

            if not solution_name:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'solutionName is required'}
                return

            # Find the solution definition
            solution_data = None
            instances = self.manager.objectTables.get('SolutionDefinition', {})
            for inst_id, inst in instances.items():
                if getattr(inst, 'name', '') == solution_name:
                    definition_str = getattr(inst, 'definition', '{}')
                    try:
                        solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
                    except:
                        solution_data = None
                    break

            if not solution_data:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Solution "{solution_name}" not found'}
                return

            # Phase 1: Generate code (execution engine to come later)
            generated_code = generate_code_from_solution(solution_data, target_runtime)

            # Generate code
            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'solutionName': solution_name,
                'targetRuntime': target_runtime,
                'status': 'code_generated',
                'generatedCode': generated_code,
                'message': 'Code generated successfully.'
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post_stepped(self, request, response):
        """Execute a solution step-by-step, returning a full ExecutionTrace."""
        try:
            # Parse multipart form data or JSON body
            solution_name = None
            input_params = {}
            target_runtime = 'python_backend'
            step_config_data = {}

            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                solution_name = request.get_param('solutionName')
                input_params_str = request.get_param('inputParams')
                target_runtime = request.get_param('targetRuntime') or 'python_backend'
                step_config_str = request.get_param('stepConfig')
                if input_params_str:
                    try:
                        input_params = json.loads(input_params_str)
                    except Exception:
                        input_params = {}
                if step_config_str:
                    try:
                        step_config_data = json.loads(step_config_str)
                    except Exception:
                        step_config_data = {}
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                solution_name = body.get('solutionName', '')
                input_params = body.get('inputParams', {})
                target_runtime = body.get('targetRuntime', 'python_backend')
                step_config_data = body.get('stepConfig', {})

            if not solution_name:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'solutionName is required'}
                return

            # Find the solution definition
            solution_data = None
            instances = self.manager.objectTables.get('SolutionDefinition', {})
            for inst_id, inst in instances.items():
                if getattr(inst, 'name', '') == solution_name:
                    definition_str = getattr(inst, 'definition', '{}')
                    try:
                        solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
                    except Exception:
                        solution_data = None
                    break

            if not solution_data:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Solution "{solution_name}" not found'}
                return

            # Build StepConfig
            config = StepConfig.from_dict(step_config_data) if step_config_data else StepConfig(mode='step', record_context=True)

            # Execute via the engine
            engine = SolutionExecutionEngine()
            trace = engine.execute(solution_data, input_params, config, target_runtime)

            # Convert to plain dict before any treeObject interaction
            trace_dict = trace.to_dict()

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'solutionName': solution_name,
                'targetRuntime': target_runtime,
                'trace': trace_dict,
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
