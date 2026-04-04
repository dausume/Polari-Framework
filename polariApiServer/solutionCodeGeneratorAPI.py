"""
Solution Code Generator API

Provides endpoints for generating code from no-code solution definitions:
- GET /solutionCode/{solutionName}?runtime=python_backend  - Generate code for a named solution
- POST /solutionCode  - Generate code from solution data in request body
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiServer.solutionDefinition import SolutionDefinition
import falcon
import json


# Template maps for each runtime target
PYTHON_TEMPLATES = {
    'InitialState': '# {displayName}: {description}',
    'DirectInvocation': '# Entry point: {displayName}',
    'FormSubscription': '# Subscribe: {sourceName}\n# Trigger: {triggerType}',
    'LogicFlowEntry': '# Entry point (invoked by {parentSolutionName})',
    'BackendStateChange': '# Backend state change trigger',
    'VariableAssignment': '{variableName} = {value}',
    'ConditionalChain': 'if {condition}:\n    {if_body}\nelse:\n    {else_body}',
    'ForLoop': 'for {iterator} in range({start}, {end}, {step}):\n    {body}',
    'WhileLoop': 'while {condition}:\n    {body}',
    'ForEachLoop': 'for {item} in {collection}:\n    {body}',
    'FunctionCall': '{resultVariableName} = {functionName}()',
    'ReturnStatement': 'return {returnValue}',
    'ReturnValue': 'return {returnValue}',
    'StateChangeCommit': '# Commit: {targetFieldName}\nself.save()',
    'EmitEvent': '# Emit: {eventName}',
    'LogOutput': 'print(f"{messageTemplate}")',
    'AwaitBackendCall': '{resultVariable} = await self.call_solution("{targetSolutionName}")',
    'EmitFrontendEvent': 'self.emit_event("{targetSolutionName}", {eventPayload})',
    'ReactiveTransform': '# Transform: {operator}({expression})',
    'MathOperation': '{resultVar} = {leftLabel} {opSymbol} {rightLabel}',
}

TYPESCRIPT_TEMPLATES = {
    'InitialState': '// {displayName}: {description}',
    'DirectInvocation': '// Entry point: {displayName}',
    'FormSubscription': 'this.{sourceName}.pipe(\n    // operators\n).subscribe((value) => {{\n    // Handle subscription\n}});',
    'LogicFlowEntry': '// Entry point (invoked by {parentSolutionName})',
    'BackendStateChange': '// Backend state change trigger (not applicable in TypeScript frontend)',
    'VariableAssignment': 'const {variableName} = {value};',
    'ConditionalChain': 'if ({condition}) {{\n    {if_body}\n}} else {{\n    {else_body}\n}}',
    'ForLoop': 'for (let {iterator} = {start}; {iterator} < {end}; {iterator} += {step}) {{\n    {body}\n}}',
    'WhileLoop': 'while ({condition}) {{\n    {body}\n}}',
    'ForEachLoop': 'for (const {item} of {collection}) {{\n    {body}\n}}',
    'FunctionCall': 'const {resultVariableName} = {functionName}();',
    'ReturnStatement': 'return {returnValue};',
    'ReturnValue': 'return {returnValue};',
    'StateChangeCommit': '// State change commit (backend only)',
    'EmitEvent': 'this.polariService.emitEvent("{eventName}", {eventPayload});',
    'LogOutput': 'console.log(`{messageTemplate}`);',
    'AwaitBackendCall': 'const {resultVariable} = await this.polariService.callSolution("{targetSolutionName}");',
    'EmitFrontendEvent': 'this.polariService.emitEvent("{targetSolutionName}", {eventPayload});',
    'ReactiveTransform': '.pipe({operator}({expression}))',
    'MathOperation': 'const {resultVar} = {leftLabel} {opSymbol} {rightLabel};',
}


def get_template_map(runtime):
    """Get the template map for a given runtime target."""
    if runtime == 'typescript_frontend':
        return TYPESCRIPT_TEMPLATES
    return PYTHON_TEMPLATES


def _resolve_value_source_label(config):
    """Resolve a ValueSourceConfig dict to a code-friendly label string.

    For from_input/from_source_object: returns the variable name (e.g. 'num_a', 'self.sum_result').
    For direct_assignment: returns the literal value.
    Falls back to the config as-is for unknown types.
    """
    if not isinstance(config, dict) or 'sourceType' not in config:
        return str(config) if config is not None else '0'

    source_type = config.get('sourceType', '')

    if source_type == 'from_input':
        return config.get('inputVariableName', '0')
    elif source_type == 'from_source_object':
        return config.get('sourceObjectPath', '0')
    elif source_type == 'direct_assignment':
        return str(config.get('directValue', '0'))
    elif source_type == 'from_field':
        return config.get('fieldPath', config.get('sourceObjectPath', '0'))
    elif source_type == 'literal':
        return str(config.get('literalValue', config.get('directValue', '0')))

    return '0'


# Map from operationType names to Python/TS operator symbols
_MATH_OP_SYMBOLS = {
    'add': '+', 'subtract': '-', 'multiply': '*', 'divide': '/', 'modulo': '%',
    '+': '+', '-': '-', '*': '*', '/': '/', '%': '%', '**': '**',
}


def _preprocess_math_operation(field_values):
    """Pre-process MathOperation field values into template-friendly keys.

    Resolves ValueSourceConfig operands to code labels and maps operationType to a symbol.
    """
    processed = dict(field_values) if field_values else {}

    processed['leftLabel'] = _resolve_value_source_label(field_values.get('leftOperand'))
    processed['rightLabel'] = _resolve_value_source_label(field_values.get('rightOperand'))

    op_type = field_values.get('operationType', field_values.get('operator', 'add'))
    processed['opSymbol'] = _MATH_OP_SYMBOLS.get(op_type, '+')

    # Determine result variable name
    result_var = field_values.get('resultVariableName', '')
    if not result_var:
        result_var = field_values.get('resultFieldPath', '')
    if not result_var:
        result_var = field_values.get('resultVariable', '')
    if not result_var:
        result_var = field_values.get('variableName', 'result')
    processed['resultVar'] = result_var

    return processed


def substitute_template(template, field_values, state_class):
    """Substitute field values into a template string."""
    # Pre-process certain state classes that have structured config
    if state_class == 'MathOperation':
        field_values = _preprocess_math_operation(field_values)

    result = template
    for key, value in (field_values or {}).items():
        placeholder = '{' + key + '}'
        if placeholder in result:
            if isinstance(value, (dict, list)):
                result = result.replace(placeholder, json.dumps(value))
            else:
                result = result.replace(placeholder, str(value))
    # Clean up remaining placeholders
    import re
    result = re.sub(r'\{[^}]+\}', '...', result)
    return result


INITIAL_STATE_CLASSES = {
    'InitialState', 'DirectInvocation', 'FormSubscription',
    'LogicFlowEntry', 'BackendStateChange'
}


def _partition_by_reachability(sorted_states):
    """Partition states into (connected, disconnected) based on reachability from initial states.

    Walks the connector graph starting from any state whose class is an initial state type.
    Connected states are those reachable; disconnected are the rest.
    """
    states_by_name = {}
    for s in sorted_states:
        name = s.get('stateName')
        if name:
            states_by_name[name] = s

    # Find initial states
    visited = set()
    queue = []
    for s in sorted_states:
        cls = s.get('boundObjectClass', s.get('stateClass', ''))
        if cls in INITIAL_STATE_CLASSES:
            name = s.get('stateName')
            if name and name not in visited:
                visited.add(name)
                queue.append(name)

    # BFS
    while queue:
        name = queue.pop(0)
        state = states_by_name.get(name)
        if not state:
            continue
        for slot in state.get('slots', []):
            for conn in slot.get('connectors', []):
                target = conn.get('targetStateName')
                if target and target not in visited:
                    visited.add(target)
                    queue.append(target)

    connected = [s for s in sorted_states if s.get('stateName') in visited]
    disconnected = [s for s in sorted_states if s.get('stateName') not in visited]
    return connected, disconnected


def generate_code_from_solution(solution_data, runtime='python_backend', include_stepping=False):
    """Generate code from a solution definition dict.

    Args:
        solution_data: The solution definition dict
        runtime: 'python_backend' or 'typescript_frontend'
        include_stepping: When True, inserts step_checkpoint() calls between states
    """
    templates = get_template_map(runtime)
    is_python = runtime == 'python_backend'

    solution_name = solution_data.get('solutionName', 'untitled')
    function_name = solution_data.get('functionName', solution_name.split('.')[-1] if '.' in solution_name else solution_name)
    bound_class = solution_data.get('boundClass', {})
    state_instances = solution_data.get('stateInstances', [])

    # Sort states by index
    sorted_states = sorted(state_instances, key=lambda s: s.get('index', 0))

    lines = []

    # Stepping import
    if include_stepping:
        if is_python:
            lines.append('from polariNoCode.stepping import step_checkpoint, StepConfig')
        else:
            lines.append("import { stepCheckpoint, StepConfig } from '../utils/stepping';")
        lines.append('')

    # Imports
    if is_python:
        python_imports = bound_class.get('pythonImports', [])
        for imp in python_imports:
            lines.append(imp)
        if python_imports:
            lines.append('')
    else:
        ts_imports = bound_class.get('typescriptImports', [])
        for imp in ts_imports:
            lines.append(imp)
        if ts_imports:
            lines.append('')

    # Function signature
    input_params = []
    for state in sorted_states:
        state_class = state.get('boundObjectClass', state.get('stateClass', ''))
        if state_class in ('InitialState', 'DirectInvocation'):
            params = (state.get('boundObjectFieldValues') or {}).get('inputParams', [])
            for p in params:
                if p.get('name') and p.get('type'):
                    if is_python:
                        input_params.append(f"{p['name']}: {p['type']}")
                    else:
                        type_map = {'int': 'number', 'float': 'number', 'str': 'string', 'bool': 'boolean', 'dict': 'Record<string, any>', 'list': 'any[]'}
                        ts_type = type_map.get(p['type'], p['type'])
                        input_params.append(f"{p['name']}: {ts_type}")

    # Determine return type
    return_type = 'None' if is_python else 'void'
    for state in sorted_states:
        state_class = state.get('boundObjectClass', state.get('stateClass', ''))
        if state_class in ('ReturnStatement', 'ReturnValue'):
            fv = state.get('boundObjectFieldValues', {})
            rt = fv.get('returnType', '')
            if rt:
                if is_python:
                    return_type = rt
                else:
                    type_map = {'int': 'number', 'float': 'number', 'str': 'string', 'bool': 'boolean', 'None': 'void'}
                    return_type = type_map.get(rt, rt)
            break

    params_str = ', '.join(input_params)
    if is_python:
        lines.append(f'def {function_name}(self, {params_str}) -> {return_type}:' if params_str else f'def {function_name}(self) -> {return_type}:')
    else:
        lines.append(f'async {function_name}({params_str}): Promise<{return_type}> {{' if params_str else f'async {function_name}(): Promise<{return_type}> {{')

    # Add stepping initialization if enabled
    if include_stepping:
        if is_python:
            lines.append('    __config = StepConfig(mode="step", record_context=True)')
            lines.append('    __trace = []')
        else:
            lines.append('    const __config: StepConfig = { mode: "step", recordContext: true };')
            lines.append('    const __trace: any[] = [];')

    # Partition states into connected (reachable from initial) and disconnected
    connected, disconnected = _partition_by_reachability(sorted_states)

    # Generate code body from connected states
    indent = '    '
    has_body = False
    step_counter = [0]  # Use list for mutability in closure
    for state in connected:
        state_class = state.get('boundObjectClass', state.get('stateClass', ''))
        field_values = state.get('boundObjectFieldValues', {})
        state_name = state.get('stateName', 'Unknown')

        template = templates.get(state_class, '')
        if not template:
            lines.append(f'{indent}# {state_name}' if is_python else f'{indent}// {state_name}')
            has_body = True
            continue

        code = substitute_template(template, field_values, state_class)
        for code_line in code.split('\n'):
            lines.append(f'{indent}{code_line}')
        has_body = True

        # Insert stepping checkpoint if enabled
        if include_stepping:
            idx = step_counter[0]
            step_counter[0] += 1
            if is_python:
                lines.append(f"{indent}step_checkpoint({idx}, '{state_name}', '{state_class}', locals(), __config, __trace)")
            else:
                lines.append(f"{indent}stepCheckpoint({idx}, '{state_name}', '{state_class}', {{}}, __config, __trace);")

    if not has_body:
        lines.append(f'{indent}pass' if is_python else f'{indent}// TODO: implement')

    if not is_python:
        lines.append('}')

    # Disconnected templates section
    if disconnected:
        lines.append('')
        if is_python:
            lines.append('# ═══════════════════════════════════════════════════════')
            lines.append('# Disconnected Templates (not yet wired into the flow)')
            lines.append('# ═══════════════════════════════════════════════════════')
        else:
            lines.append('// ═══════════════════════════════════════════════════════')
            lines.append('// Disconnected Templates (not yet wired into the flow)')
            lines.append('// ═══════════════════════════════════════════════════════')
        for state in disconnected:
            state_class = state.get('boundObjectClass', state.get('stateClass', ''))
            field_values = state.get('boundObjectFieldValues', {})
            state_name = state.get('stateName', 'Unknown')
            template = templates.get(state_class, '')
            if template:
                code = substitute_template(template, field_values, state_class)
                comment_char = '#' if is_python else '//'
                lines.append(f'{comment_char} [{state_name}]')
                for code_line in code.split('\n'):
                    lines.append(f'{comment_char} {code_line}')
            else:
                comment_char = '#' if is_python else '//'
                lines.append(f'{comment_char} [{state_name}] (no template)')

    return '\n'.join(lines)


class SolutionCodeGeneratorAPI(treeObject):
    """
    API endpoint for generating code from no-code solution definitions.
    GET /solutionCode/{solutionName}?runtime=python_backend
    POST /solutionCode  (with solution data in request body)
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/solutionCode/{solutionName}'
        self.apiNamePost = '/solutionCode'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiNamePost, self, suffix='generate')

    def on_get(self, request, response, solutionName):
        """Generate code for a named solution stored in the backend."""
        try:
            runtime = request.get_param('runtime') or 'python_backend'

            # Find the solution in stored SolutionDefinitions
            solution_data = None
            for className, polyTypedObj in self.manager.objectTypingDict.items():
                if className == 'SolutionDefinition':
                    for inst_id, inst in polyTypedObj.instancesDict.items():
                        if getattr(inst, 'name', '') == solutionName:
                            definition_str = getattr(inst, 'definition', '{}')
                            try:
                                solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
                            except:
                                solution_data = None
                            break
                    break

            if not solution_data:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Solution "{solutionName}" not found'}
                return

            code = generate_code_from_solution(solution_data, runtime)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'solutionName': solutionName,
                'runtime': runtime,
                'code': code,
                'generated_code': code
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post_generate(self, request, response):
        """Generate code from solution data provided in the request body."""
        try:
            raw = request.bounded_stream.read()
            body = json.loads(raw) if raw else {}
            solution_data = body.get('solutionData', body)
            runtime = body.get('runtime', 'python_backend')

            code = generate_code_from_solution(solution_data, runtime)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'runtime': runtime,
                'code': code,
                'generated_code': code
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
