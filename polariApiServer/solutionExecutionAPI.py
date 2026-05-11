"""
Solution Execution API

Provides endpoints for executing no-code solutions:
- POST /executeSolution            - Execute a solution by name (code generation only)
- POST /executeSolutionStepped     - Execute a solution step-by-step, return full ExecutionTrace
- POST /executeSolutionTestCase    - Run a single test case with assertions
- POST /executeSolutionTestSuite   - Run all test cases for a solution
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
        self.testCaseApiName = '/executeSolutionTestCase'
        self.testSuiteApiName = '/executeSolutionTestSuite'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.steppedApiName, self, suffix='stepped')
            polServer.falconServer.add_route(self.testCaseApiName, self, suffix='test_case')
            polServer.falconServer.add_route(self.testSuiteApiName, self, suffix='test_suite')

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

            instance_fields = {}

            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                solution_name = request.get_param('solutionName')
                input_params_str = request.get_param('inputParams')
                target_runtime = request.get_param('targetRuntime') or 'python_backend'
                step_config_str = request.get_param('stepConfig')
                instance_fields_str = request.get_param('instanceFields')
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
                if instance_fields_str:
                    try:
                        instance_fields = json.loads(instance_fields_str)
                    except Exception:
                        instance_fields = {}
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                solution_name = body.get('solutionName', '')
                input_params = body.get('inputParams', {})
                target_runtime = body.get('targetRuntime', 'python_backend')
                step_config_data = body.get('stepConfig', {})
                instance_fields = body.get('instanceFields', {})

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
            engine = SolutionExecutionEngine(manager=self.manager)
            trace = engine.execute(solution_data, input_params, config, target_runtime, instance_fields=instance_fields)

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

    def on_post_test_case(self, request, response):
        """Run a single test case with its assertions against a solution."""
        try:
            from polariNoCode.assertionEvaluator import evaluate_all_assertions

            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                test_case_id = request.get_param('testCaseId') or ''
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                test_case_id = body.get('testCaseId', '')

            if not test_case_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'testCaseId is required'}
                return

            # Load the test case
            tc_instances = self.manager.objectTables.get('SolutionTestCase', {})
            test_case = tc_instances.get(test_case_id)
            if test_case is None:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'SolutionTestCase "{test_case_id}" not found'}
                return

            solution_id = getattr(test_case, 'solution_id', '')
            target_runtime = getattr(test_case, 'target_runtime', 'python_backend')

            # Parse input params and instance fields
            input_params_str = getattr(test_case, 'input_params', '{}')
            instance_fields_str = getattr(test_case, 'instance_fields', '{}')
            try:
                input_params = json.loads(input_params_str) if isinstance(input_params_str, str) else input_params_str
            except Exception:
                input_params = {}
            try:
                instance_fields = json.loads(instance_fields_str) if isinstance(instance_fields_str, str) else instance_fields_str
            except Exception:
                instance_fields = {}

            # Find the solution definition by solution_id
            sol_instances = self.manager.objectTables.get('SolutionDefinition', {})
            solution_inst = sol_instances.get(solution_id)
            if solution_inst is None:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'SolutionDefinition "{solution_id}" not found'}
                return

            definition_str = getattr(solution_inst, 'definition', '{}')
            try:
                solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
            except Exception:
                solution_data = {}

            # Execute the solution
            config = StepConfig(mode='step', record_context=True)
            engine = SolutionExecutionEngine(manager=self.manager)
            start_time = time.time()
            trace = engine.execute(solution_data, input_params, config, target_runtime, instance_fields=instance_fields)
            duration_ms = int((time.time() - start_time) * 1000)
            trace_dict = trace.to_dict()

            # Load assertions for this test case
            assertion_instances = self.manager.objectTables.get('ExecutionStepAssertion', {})
            assertions = [
                inst for inst in assertion_instances.values()
                if getattr(inst, 'test_case_id', '') == test_case_id
            ]

            # Evaluate assertions
            assertion_results = evaluate_all_assertions(assertions, trace_dict)
            overall_passed = all(r['passed'] for r in assertion_results) if assertion_results else True

            # Check expected status if set
            expected_status = getattr(test_case, 'expected_status', '')
            if expected_status and trace_dict.get('status') != expected_status:
                overall_passed = False

            # Check expected return value if set
            expected_return = getattr(test_case, 'expected_return_value', '')
            if expected_return:
                actual_return = trace_dict.get('finalReturnValue')
                if str(actual_return) != str(expected_return):
                    overall_passed = False

            # Update test case with last run info
            now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            test_case.last_run_at = now
            test_case.last_run_passed = overall_passed

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'testCaseId': test_case_id,
                'overallPassed': overall_passed,
                'trace': trace_dict,
                'assertionResults': assertion_results,
                'durationMs': duration_ms,
                'runAt': now,
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post_test_suite(self, request, response):
        """Run all test cases for a solution."""
        try:
            from polariNoCode.assertionEvaluator import evaluate_all_assertions

            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                solution_id = request.get_param('solutionId') or ''
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                solution_id = body.get('solutionId', '')

            if not solution_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'solutionId is required'}
                return

            # Find the solution definition
            sol_instances = self.manager.objectTables.get('SolutionDefinition', {})
            solution_inst = sol_instances.get(solution_id)
            if solution_inst is None:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'SolutionDefinition "{solution_id}" not found'}
                return

            definition_str = getattr(solution_inst, 'definition', '{}')
            try:
                solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
            except Exception:
                solution_data = {}

            # Load all test cases for this solution
            tc_instances = self.manager.objectTables.get('SolutionTestCase', {})
            test_cases = [
                inst for inst in tc_instances.values()
                if getattr(inst, 'solution_id', '') == solution_id
            ]

            assertion_instances = self.manager.objectTables.get('ExecutionStepAssertion', {})
            results = []
            total_passed = 0
            total_failed = 0

            for tc in test_cases:
                tc_id = getattr(tc, 'polariId', '')
                target_runtime = getattr(tc, 'target_runtime', 'python_backend')

                # Parse inputs
                try:
                    input_params = json.loads(getattr(tc, 'input_params', '{}'))
                except Exception:
                    input_params = {}
                try:
                    instance_fields = json.loads(getattr(tc, 'instance_fields', '{}'))
                except Exception:
                    instance_fields = {}

                # Execute
                config = StepConfig(mode='step', record_context=True)
                engine = SolutionExecutionEngine(manager=self.manager)
                start_time = time.time()
                trace = engine.execute(solution_data, input_params, config, target_runtime, instance_fields=instance_fields)
                duration_ms = int((time.time() - start_time) * 1000)
                trace_dict = trace.to_dict()

                # Load and evaluate assertions for this test case
                assertions = [
                    inst for inst in assertion_instances.values()
                    if getattr(inst, 'test_case_id', '') == tc_id
                ]
                assertion_results = evaluate_all_assertions(assertions, trace_dict)
                case_passed = all(r['passed'] for r in assertion_results) if assertion_results else True

                # Check expected status/return
                expected_status = getattr(tc, 'expected_status', '')
                if expected_status and trace_dict.get('status') != expected_status:
                    case_passed = False
                expected_return = getattr(tc, 'expected_return_value', '')
                if expected_return and str(trace_dict.get('finalReturnValue')) != str(expected_return):
                    case_passed = False

                # Update cached result
                now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                tc.last_run_at = now
                tc.last_run_passed = case_passed

                if case_passed:
                    total_passed += 1
                else:
                    total_failed += 1

                results.append({
                    'testCaseId': tc_id,
                    'testCaseName': getattr(tc, 'name', ''),
                    'passed': case_passed,
                    'assertionResults': assertion_results,
                    'durationMs': duration_ms,
                    'runAt': now,
                })

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'solutionId': solution_id,
                'totalTests': len(test_cases),
                'passed': total_passed,
                'failed': total_failed,
                'results': results,
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
