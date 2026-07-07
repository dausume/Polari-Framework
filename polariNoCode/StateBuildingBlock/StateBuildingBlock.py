#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
StateBuildingBlock Model for Polari No-Code System

A StateBuildingBlock ties together a block's identity, its code templates
(Python/TypeScript), and its UI config.  Replaces hardcoded inline template
maps in code generator services.

Classes:
    CodeTemplate - Code template for a specific runtime
    StateBuildingBlock - Defines a building block with code templates
    StateBuildingBlockRegistry - Singleton registry for all building blocks
"""


class CodeTemplate:
    """Code template for a specific runtime."""

    def __init__(self, runtime, template, required_imports=None):
        """
        Args:
            runtime: 'python_backend' or 'typescript_frontend'
            template: Template string with {placeholders}
            required_imports: Optional list of import statements
        """
        self.runtime = runtime
        self.template = template
        self.required_imports = required_imports or []

    def to_dict(self):
        d = {
            'runtime': self.runtime,
            'template': self.template,
        }
        if self.required_imports:
            d['requiredImports'] = self.required_imports
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            runtime=data.get('runtime', ''),
            template=data.get('template', ''),
            required_imports=data.get('requiredImports', []),
        )


# Node classes only the Python engine can execute (SymPy/numpy math,
# instance persistence, simulation-runner nodes). MIRROR of the frontend
# partition in solution-engine/capability.ts and
# state-space-class-registry.ts (BACKEND_ONLY_RUNTIME_CLASSES) — change
# all three together.
BACKEND_ONLY_RUNTIME_CLASSES = {
    'CalculusOperation',        # SymPy equations
    'MatrixEquationOperation',  # numpy matrix engine
    'EngineModelOperation',     # FEM/DFT engine models (msci-18)
    'StateChangeCommit',        # persists instances via the manager/DB
    'SimulationStateStep',      # simulation-runner entry
    'SimStepNextState',         # simulation-runner terminators
    'SimStepContribution',
    'BackendStateChange',       # backend-trust entry intent
}


class StateBuildingBlock:
    """Defines a building block with code templates for the no-code system."""

    def __init__(
        self,
        class_name,
        display_name,
        description,
        category,
        supported_runtimes,
        code_templates,
        default_input_slots,
        default_output_slots,
        display_fields,
        icon='',
        color='',
        is_built_in=True,
        execution_status='real',
        execution_note='',
        runtime_capability=None,
    ):
        self.class_name = class_name
        self.display_name = display_name
        self.description = description
        self.category = category
        self.supported_runtimes = supported_runtimes or []
        self.code_templates = code_templates or []
        self.default_input_slots = default_input_slots or []
        self.default_output_slots = default_output_slots or []
        self.display_fields = display_fields or []
        self.icon = icon
        self.color = color
        self.is_built_in = is_built_in
        # HONESTY TAG (P1): what actually happens when the engine hits
        # this node — 'real' (fully executes), 'stub' (recognized but
        # incomplete), 'authoring-only' (no engine handler yet; the
        # editor can author it but it no-ops at runtime). Surfaced in
        # the editor palette so nobody authors silent no-ops.
        self.execution_status = execution_status
        self.execution_note = execution_note
        # RUNTIME-CAPABILITY TAG (P5): which engine(s) can execute this
        # node — the truth the display-solution-runner partitions on.
        #   'client-and-backend' — the Python engine AND the TypeScript
        #       mirror (polari-platform-angular solution-engine/)
        #       interpret it identically (parity-vector enforced)
        #   'backend-only'       — Python engine only (SymPy/numpy/DB/
        #       simulation-runner nodes)
        #   'authoring-only'     — no engine handler anywhere yet
        # Derived when not declared: authoring-only stays authoring-only;
        # known backend-only classes tag themselves; the rest run on both.
        if runtime_capability is None:
            if execution_status == 'authoring-only':
                runtime_capability = 'authoring-only'
            elif class_name in BACKEND_ONLY_RUNTIME_CLASSES:
                runtime_capability = 'backend-only'
            else:
                runtime_capability = 'client-and-backend'
        self.runtime_capability = runtime_capability

    def get_template(self, runtime):
        """Return the template string for *runtime*, or None."""
        for t in self.code_templates:
            tmpl = t if isinstance(t, CodeTemplate) else CodeTemplate.from_dict(t)
            if tmpl.runtime == runtime:
                return tmpl.template
        return None

    def to_dict(self):
        return {
            'className': self.class_name,
            'displayName': self.display_name,
            'description': self.description,
            'category': self.category,
            'supportedRuntimes': self.supported_runtimes,
            'codeTemplates': [
                (t.to_dict() if isinstance(t, CodeTemplate) else t)
                for t in self.code_templates
            ],
            'defaultInputSlots': self.default_input_slots,
            'defaultOutputSlots': self.default_output_slots,
            'displayFields': self.display_fields,
            'icon': self.icon,
            'color': self.color,
            'isBuiltIn': self.is_built_in,
            'executionStatus': self.execution_status,
            'executionNote': self.execution_note,
            'runtimeCapability': self.runtime_capability,
        }

    @classmethod
    def from_dict(cls, data):
        templates = [
            CodeTemplate.from_dict(t) if isinstance(t, dict) else t
            for t in data.get('codeTemplates', [])
        ]
        return cls(
            class_name=data.get('className', ''),
            display_name=data.get('displayName', ''),
            description=data.get('description', ''),
            category=data.get('category', ''),
            supported_runtimes=data.get('supportedRuntimes', []),
            code_templates=templates,
            default_input_slots=data.get('defaultInputSlots', []),
            default_output_slots=data.get('defaultOutputSlots', []),
            display_fields=data.get('displayFields', []),
            icon=data.get('icon', ''),
            color=data.get('color', ''),
            is_built_in=data.get('isBuiltIn', True),
            execution_status=data.get('executionStatus', 'real'),
            execution_note=data.get('executionNote', ''),
            runtime_capability=data.get('runtimeCapability'),
        )


class StateBuildingBlockRegistry:
    """Singleton registry for all building blocks."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._blocks = {}
            cls._instance.register_built_in_blocks()
        return cls._instance

    # --- CRUD ---

    def register(self, block):
        self._blocks[block.class_name] = block

    def unregister(self, class_name):
        return self._blocks.pop(class_name, None) is not None

    def get(self, class_name):
        return self._blocks.get(class_name)

    def get_all(self):
        return list(self._blocks.values())

    def get_template_map(self, runtime):
        """Return { class_name: template } for *runtime*."""
        result = {}
        for block in self._blocks.values():
            tmpl = block.get_template(runtime)
            if tmpl is not None:
                result[block.class_name] = tmpl
        return result

    # --- Built-in registrations (all 19 blocks) ---

    def register_built_in_blocks(self):
        blocks = [
            # === Typed Initial States ===
            StateBuildingBlock(
                class_name='DirectInvocation',
                display_name='Direct Invocation',
                description='Generic function-call entry point - defines input parameters',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '# Entry point - receive input parameters'),
                    CodeTemplate('typescript_frontend', '// Entry point - receive input parameters'),
                ],
                default_input_slots=[],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='play_circle', color='#4CAF50',
            ),
            StateBuildingBlock(
                class_name='FormSubscription',
                display_name='Form Subscription',
                description='Triggered by a form/page observable - reactive frontend entry point',
                category='Control Flow',
                supported_runtimes=['typescript_frontend'],
                code_templates=[
                    CodeTemplate('typescript_frontend', 'this.{sourceName}.pipe(\n    // operators\n).subscribe((value) => {\n    // Handle subscription\n});'),
                ],
                default_input_slots=[],
                default_output_slots=[{'name': 'subscription', 'displayName': 'Subscription', 'slotType': 'output', 'dataType': 'Subscription', 'isRequired': False}],
                display_fields=[],
                icon='sensors', color='#E91E63',
            ),
            StateBuildingBlock(
                class_name='LogicFlowEntry',
                display_name='Logic Flow Entry',
                description='Invoked by a parent solution - child solution entry point',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '# Entry point (invoked by {parentSolutionName})'),
                    CodeTemplate('typescript_frontend', '// Entry point (invoked by {parentSolutionName})'),
                ],
                default_input_slots=[],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='account_tree', color='#673AB7',
            ),
            StateBuildingBlock(
                class_name='BackendStateChange',
                display_name='Backend State Change',
                description='Triggered by database state changes being committed',
                category='Control Flow',
                supported_runtimes=['python_backend'],
                code_templates=[
                    CodeTemplate('python_backend', '# Triggered by {modelName}.{fieldName} {changeType}'),
                ],
                default_input_slots=[],
                default_output_slots=[{'name': 'output', 'displayName': 'Change Context', 'slotType': 'output', 'dataType': 'object', 'isRequired': False}],
                display_fields=[],
                icon='storage', color='#FF9800',
            ),
            # Legacy alias for backward compatibility
            StateBuildingBlock(
                class_name='InitialState',
                display_name='Initial State',
                description='Legacy initial state - maps to DirectInvocation',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '# Entry point - receive input parameters'),
                    CodeTemplate('typescript_frontend', '// Entry point - receive input parameters'),
                ],
                default_input_slots=[],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='play_circle', color='#4CAF50',
            ),

            # === Control Flow ===
            StateBuildingBlock(
                class_name='ReturnStatement',
                display_name='Return',
                description='Return a value and exit the solution flow',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'return {value}'),
                    CodeTemplate('typescript_frontend', 'return {value};'),
                ],
                default_input_slots=[{'name': 'value', 'displayName': 'Value', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[],
                display_fields=[],
                icon='exit_to_app', color='#F44336',
            ),
            StateBuildingBlock(
                class_name='BreakStatement',
                display_name='Break',
                description='Break out of current loop',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'break'),
                    CodeTemplate('typescript_frontend', 'break;'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[],
                display_fields=[],
                icon='stop', color='#F44336',
            ),
            StateBuildingBlock(
                class_name='ContinueStatement',
                display_name='Continue',
                description='Skip to next loop iteration',
                category='Control Flow',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'continue'),
                    CodeTemplate('typescript_frontend', 'continue;'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[],
                display_fields=[],
                icon='skip_next', color='#FF9800',
            ),

            # === Conditionals ===
            StateBuildingBlock(
                class_name='ConditionalChain',
                display_name='Conditional Chain',
                description='A chainable conditional evaluation system with AND/OR/NOT logic',
                category='Conditionals',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'if {condition}:\n    {if_body}\nelse:\n    {else_body}'),
                    CodeTemplate('typescript_frontend', 'if ({condition}) {\n    {if_body}\n} else {\n    {else_body}\n}'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[
                    {'name': 'true', 'displayName': 'True', 'slotType': 'output', 'dataType': 'boolean', 'isRequired': False},
                    {'name': 'false', 'displayName': 'False', 'slotType': 'output', 'dataType': 'boolean', 'isRequired': False},
                ],
                display_fields=[],
                icon='device_hub', color='#4CAF50',
            ),

            StateBuildingBlock(
                class_name='FormValidation',
                display_name='Form Validation',
                description='Introspects a form\'s fields and generates one output slot per field for individual validation logic. Specific to FormSubscription flows.',
                category='Conditionals',
                supported_runtimes=['python_backend', 'typescript_frontend'],
                code_templates=[
                    CodeTemplate('typescript_frontend', '// Validate each form field individually\n{fieldValidationBlocks}'),
                ],
                default_input_slots=[{'name': 'formData', 'displayName': 'Form Data', 'slotType': 'input', 'dataType': 'object', 'isRequired': True}],
                default_output_slots=[
                    {'name': 'allValid', 'displayName': 'All Valid', 'slotType': 'output', 'dataType': 'boolean', 'isRequired': False},
                    # Additional per-field output slots are dynamically generated based on formReference
                ],
                display_fields=[],
                icon='checklist', color='#00BCD4',
                execution_status='real',
                execution_note=('Validates per-field rules (required/type/range/'
                                'length/pattern) and BRANCHES: valid -> the '
                                '"All Valid" slot; invalid -> the first invalid '
                                "field's own wired slot (or a wired generic "
                                'second slot in the simple two-slot shape). '
                                'With no invalid branch wired the flow ends '
                                'with the verdict in context — an invalid form '
                                'never proceeds down "All Valid".'),
            ),

            # === Loops ===
            StateBuildingBlock(
                class_name='ForLoop',
                display_name='For Loop',
                description='Traditional indexed for loop',
                category='Loops',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'for {iterator} in range({start}, {end}, {step}):\n    {body}'),
                    CodeTemplate('typescript_frontend', 'for (let {iterator} = {start}; {iterator} < {end}; {iterator} += {step}) {\n    {body}\n}'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'body', 'displayName': 'Body', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}, {'name': 'done', 'displayName': 'Done', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='loop', color='#2196F3',
            ),
            StateBuildingBlock(
                class_name='WhileLoop',
                display_name='While Loop',
                description='Condition-based loop that runs while condition is true',
                category='Loops',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'while {condition}:\n    {body}'),
                    CodeTemplate('typescript_frontend', 'while ({condition}) {\n    {body}\n}'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'body', 'displayName': 'Body', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}, {'name': 'done', 'displayName': 'Done', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='refresh', color='#2196F3',
            ),
            StateBuildingBlock(
                class_name='ForEachLoop',
                display_name='For Each Loop',
                description='Iterate over each item in a collection',
                category='Loops',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'for {item} in {collection}:\n    {body}'),
                    CodeTemplate('typescript_frontend', 'for (const {item} of {collection}) {\n    {body}\n}'),
                ],
                default_input_slots=[{'name': 'collection', 'displayName': 'Collection', 'slotType': 'input', 'dataType': 'array', 'isRequired': True}],
                default_output_slots=[{'name': 'body', 'displayName': 'Body', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}, {'name': 'done', 'displayName': 'Done', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='format_list_numbered', color='#2196F3',
            ),

            # === Data Operations ===
            StateBuildingBlock(
                class_name='VariableAssignment',
                display_name='Variable Assignment',
                description='Assign a value to a variable',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{variable} = {value}'),
                    CodeTemplate('typescript_frontend', 'const {variable} = {value};'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='edit', color='#9C27B0',
            ),
            StateBuildingBlock(
                class_name='FunctionCall',
                display_name='Function Call',
                description='Call a function and optionally store the result',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = {function}({arguments})'),
                    CodeTemplate('typescript_frontend', 'const {result} = {function}({arguments});'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='functions', color='#9C27B0',
                execution_status='authoring-only',
                execution_note='Retired legacy node - it never invokes anything '
                               '(sets its result variable to None and says so in '
                               'the trace). Use Solution Invocation instead.',
            ),
            StateBuildingBlock(
                class_name='SolutionInvocation',
                display_name='Solution Invocation',
                description='Run another solution as a single reusable step: map '
                            'inputs from this context, run it in isolation, bind '
                            'its outputs back. The invoked solution\'s contract '
                            '(inputs/returns) is the whole interface — its '
                            'internals stay its own. Recursion allowed '
                            '(depth-guarded).',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = invoke_solution({solutionRef}, {inputs})'),
                    CodeTemplate('typescript_frontend', 'const {result} = await invokeSolution({solutionRef}, {inputs});'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=['solutionRef'],
                icon='account_tree', color='#3F51B5',
                execution_status='real',
            ),
            StateBuildingBlock(
                class_name='FilterList',
                display_name='Filter List',
                description='Filter a list of objects based on type or condition',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = [x for x in {collection} if {condition}]'),
                    CodeTemplate('typescript_frontend', 'const {result} = {collection}.filter(x => {condition});'),
                ],
                default_input_slots=[{'name': 'collection', 'displayName': 'Input List', 'slotType': 'input', 'dataType': 'array', 'isRequired': True}],
                default_output_slots=[{'name': 'result', 'displayName': 'Filtered List', 'slotType': 'output', 'dataType': 'array', 'isRequired': False}],
                display_fields=[],
                icon='filter_list', color='#00BCD4',
            ),
            StateBuildingBlock(
                class_name='MapList',
                display_name='Map List',
                description='Transform each item in a list',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = [{expression} for x in {collection}]'),
                    CodeTemplate('typescript_frontend', 'const {result} = {collection}.map(x => {expression});'),
                ],
                default_input_slots=[{'name': 'collection', 'displayName': 'Input List', 'slotType': 'input', 'dataType': 'array', 'isRequired': True}],
                default_output_slots=[{'name': 'result', 'displayName': 'Mapped List', 'slotType': 'output', 'dataType': 'array', 'isRequired': False}],
                display_fields=[],
                icon='transform', color='#00BCD4',
            ),
            StateBuildingBlock(
                class_name='ReduceList',
                display_name='Reduce List',
                description='Reduce a list to a single value',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = functools.reduce({function}, {collection}, {initial})', required_imports=['import functools']),
                    CodeTemplate('typescript_frontend', 'const {result} = {collection}.reduce({function}, {initial});'),
                ],
                default_input_slots=[{'name': 'collection', 'displayName': 'Input List', 'slotType': 'input', 'dataType': 'array', 'isRequired': True}],
                default_output_slots=[{'name': 'result', 'displayName': 'Reduced Value', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='compress', color='#00BCD4',
            ),
            StateBuildingBlock(
                class_name='MathOperation',
                display_name='Math Operation',
                description='Perform basic math operations: add, subtract, multiply, divide, modulo',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = {left} {operator} {right}'),
                    CodeTemplate('typescript_frontend', 'const {result} = {left} {operator} {right};'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'result', 'displayName': 'Result', 'slotType': 'output', 'dataType': 'number', 'isRequired': False}],
                display_fields=[],
                icon='calculate', color='#2196F3',
            ),

            # === Debug ===
            StateBuildingBlock(
                class_name='LogOutput',
                display_name='Log Output',
                description='Output debug/log messages',
                category='Debug',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', 'print({message})'),
                    CodeTemplate('typescript_frontend', 'console.log({message});'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='bug_report', color='#607D8B',
            ),

            # === Frontend ===
            # Note: StateSubscription removed - absorbed into FormSubscription initial state type
            StateBuildingBlock(
                class_name='ReactiveTransform',
                display_name='Reactive Transform',
                description='Apply RxJS pipe operators',
                category='Frontend',
                supported_runtimes=['typescript_frontend'],
                code_templates=[
                    CodeTemplate('typescript_frontend', 'source$.pipe(\n    {operator}({expression})\n)'),
                ],
                default_input_slots=[{'name': 'source$', 'displayName': 'Source Stream', 'slotType': 'input', 'dataType': 'Observable', 'isRequired': True}],
                default_output_slots=[{'name': 'output$', 'displayName': 'Transformed Stream', 'slotType': 'output', 'dataType': 'Observable', 'isRequired': False}],
                display_fields=[],
                icon='transform', color='#E91E63',
                execution_status='authoring-only',
                execution_note='Frontend-runtime node - arrives with the frontend execution runtime (P5).',
            ),

            # === Cross-Runtime ===
            StateBuildingBlock(
                class_name='AwaitBackendCall',
                display_name='Await Backend Call',
                description='Call a backend Python solution and await response',
                category='Cross-Runtime',
                supported_runtimes=['typescript_frontend', 'python_backend'],
                code_templates=[
                    CodeTemplate('typescript_frontend', "const {resultVariable} = await this.polariService.executeSolution('{targetSolutionName}', params);"),
                ],
                default_input_slots=[{'name': 'params', 'displayName': 'Parameters', 'slotType': 'input', 'dataType': 'object', 'isRequired': False}],
                default_output_slots=[{'name': 'result', 'displayName': 'Backend Response', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='cloud_download', color='#FF5722',
                execution_status='real',
                execution_note=('The explicit cross-runtime bridge (P5): from a '
                                'client-executing solution it ships one named '
                                'solution to the backend engine (inputMappings '
                                'out, resultBindings back); on the backend '
                                'engine it is an in-process invocation.'),
            ),
            StateBuildingBlock(
                class_name='CollectionOperation',
                display_name='Collection Operation',
                description='Get/set/append/measure items in a dict or list variable',
                category='Data',
                supported_runtimes=[],
                code_templates=[
                    CodeTemplate('python_backend', '{result} = {target}[{key}]  # or mutation per operationType'),
                    CodeTemplate('typescript_frontend', 'const {result} = {target}[{key}]; // or mutation per operationType'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input', 'slotType': 'input', 'dataType': 'any', 'isRequired': True}],
                default_output_slots=[{'name': 'output', 'displayName': 'Output', 'slotType': 'output', 'dataType': 'any', 'isRequired': False}],
                display_fields=[],
                icon='dataset', color='#00BCD4',
            ),
            StateBuildingBlock(
                class_name='EmitFrontendEvent',
                display_name='Emit Frontend Event',
                description='Emit an event from backend to trigger a frontend solution',
                category='Cross-Runtime',
                supported_runtimes=['python_backend'],
                code_templates=[
                    CodeTemplate('python_backend', "self.polari_event_bus.emit('{targetSolutionName}', {eventPayload})"),
                ],
                default_input_slots=[{'name': 'eventData', 'displayName': 'Event Data', 'slotType': 'input', 'dataType': 'object', 'isRequired': False}],
                default_output_slots=[],
                display_fields=[],
                icon='cloud_upload', color='#FF5722',
                execution_status='real',
                execution_note=("Terminal. Records the event with "
                                "channel='frontend' in _emitted_events; the "
                                "execution response carries it out and the "
                                "client's displayEvents$ bus dispatches it to "
                                "subscribers (true client-side execution "
                                "arrives with P5)."),
            ),

            # === Display state persistence (P4) ===
            StateBuildingBlock(
                class_name='StateChangeCommit',
                display_name='Commit State Change',
                description=('Persist field changes onto an EXISTING instance '
                             'through the standard object-tree path. Commits '
                             'and continues when wired onward; the flow ends '
                             'naturally when nothing follows.'),
                category='End States',
                supported_runtimes=['python_backend'],
                code_templates=[
                    CodeTemplate('python_backend',
                                 '# Commit {targetClassName} "{instanceRef}" field updates'),
                ],
                default_input_slots=[{'name': 'input', 'displayName': 'Input',
                                      'slotType': 'input', 'dataType': 'object',
                                      'isRequired': True}],
                default_output_slots=[{'name': 'committed',
                                       'displayName': 'Committed',
                                       'slotType': 'output', 'dataType': 'object',
                                       'isRequired': False}],
                display_fields=[],
                icon='save', color='#4CAF50',
                execution_status='real',
                execution_note=("Updates an existing instance's fields "
                                '(targetClassName + instanceRef + '
                                'fieldMappings) and persists via '
                                'saveInstanceInDB. PERMISSION-BLIND until the '
                                'auth/authz nodes land (P6); create/delete '
                                'arrive with the data-access node family.'),
            ),
        ]

        for block in blocks:
            self.register(block)
