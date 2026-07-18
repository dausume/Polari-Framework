"""
@module polariNoCode.graph_builder

ncg-1: THE supported way domain code hand-builds SolutionDefinition
graphs — the selftest_composition/selftest_turing helper DSL, promoted
from test scaffolding to a real seam. Domain compilers (judicial forks,
circuit/logic compilers) build graphs through these functions instead
of re-inventing dict shapes; the shapes here are the exact ones the
python AND typescript engines interpret (the parity vectors pin them).

Load-bearing engine facts these helpers encode (from
JUDICIAL_ADJUDICATION_GRAPH_PLAN.md's verified research — do not
"fix" them):
  * Branch routing indexes OUTPUT-SLOT LIST ORDER, not each slot's
    own index field: ConditionalChain slot order = [input, true-branch,
    false-branch]; loop order = [input, body, done].
  * `nestedConditions` is UI-only — only flat `links` lists drive
    execution.
  * `from_dataset` value sources are unimplemented server-side and
    silently resolve None — never emitted here.
  * A body path that dead-ends auto-returns to the innermost loop.

@consumers
  - polariNoCode.selftest_composition / selftest_turing (migrated)
  - polariNoCode.graph_compilers (the domain-compiler seam)
  - scoring judicial adjudication (ncg-2)
"""


def node(name, cls, fields=None, outs=None, index=0):
    """One stateInstance. `outs` is a list of output slots, each a
    list of target state names (slot LIST ORDER is branch order)."""
    slots = [{'isInput': True, 'connectors': []}]
    for targets in (outs if outs is not None else [[]]):
        slots.append({
            'isInput': False,
            'connectors': [{'targetStateName': t} for t in targets],
        })
    return {
        'stateName': name, 'stateClass': cls, 'boundObjectClass': cls,
        'boundObjectFieldValues': fields or {}, 'slots': slots,
        'index': index,
    }


def solution(name, *states):
    """Assemble a SolutionDefinition definition dict (the JSON blob
    both engines interpret). State indexes are positional."""
    return {'solutionName': name,
            'stateInstances': [dict(s, index=i)
                               for i, s in enumerate(states)]}


def entry(name='Start', cls='InitialState', nxt=None):
    return node(name, cls, {}, outs=[[nxt] if nxt else []])


def assign(name, var, value, nxt=None):
    return node(name, 'VariableAssignment',
                {'variableName': var, 'value': value},
                outs=[[nxt] if nxt else []])


def math(name, res, left, op, right, nxt=None):
    return node(name, 'MathOperation',
                {'leftOperand': left, 'operationType': op,
                 'rightOperand': right, 'resultVariable': res},
                outs=[[nxt] if nxt else []])


def log(name, message, nxt=None):
    # The engine's LogOutput handler reads 'messageTemplate' (with
    # {var} substitution) — 'message' would silently emit ''.
    return node(name, 'LogOutput', {'messageTemplate': message},
                outs=[[nxt] if nxt else []])


def ret(name, var):
    """ReturnValue terminal returning a context variable."""
    return node(name, 'ReturnValue',
                {'returnValueSource': 'variable', 'variableName': var},
                outs=[])


def ret_statement(name, value=None):
    """ReturnStatement terminal (void or literal)."""
    fields = {} if value is None else {'returnValue': value}
    return node(name, 'ReturnStatement', fields, outs=[])


def invoke(name, callee, mappings, bindings, nxt=None):
    """SolutionInvocation — solution-as-state composition (P3)."""
    return node(name, 'SolutionInvocation',
                {'solutionRef': callee,
                 'inputMappings': mappings,
                 'resultBindings': bindings},
                outs=[[nxt] if nxt else []])


#: Condition types BOTH engines implement. The engine silently falls
#: back to equals on anything else (between/in/like/regexMatch AND
#: typos included) — so the seam refuses unknowns with a plain error
#: instead of letting a misnamed op flip branches downstream.
KNOWN_CONDITION_TYPES = frozenset({
    '==', '!=', '>', '<', '>=', '<=',
    'equals', 'notEquals', 'greaterThan', 'lessThan',
    'greaterThanOrEqual', 'lessThanOrEqual',
    'not_equals', 'greater_than', 'less_than',
    'greater_than_or_equal', 'less_than_or_equal',
    'contains', 'notContains', 'not_contains',
    'isTrue', 'isFalse', 'isNull', 'isNotNull',
    'startsWith', 'endsWith',
})


def link(left, condition_type, right, logical_operator='and',
         link_id=1, display_name=''):
    """One flat ConditionalChainLink (condition_type must be in
    KNOWN_CONDITION_TYPES — see the fallback note above)."""
    if condition_type not in KNOWN_CONDITION_TYPES:
        known = ', '.join(sorted(KNOWN_CONDITION_TYPES))
        raise ValueError(
            f'condition type {condition_type!r} is not implemented '
            f'by the engines (it would SILENTLY evaluate as equals) '
            f'— use one of: {known}')
    return {'id': link_id, 'displayName': display_name,
            'leftSource': left, 'conditionType': condition_type,
            'rightSource': right, 'logicalOperator': logical_operator,
            'isStateSpaceObject': False}


def cond(name, links, true_next, false_next,
         default_logical_operator='and', display_name=''):
    """ConditionalChain: slot order IS the branch semantics —
    [true, false]."""
    return node(name, 'ConditionalChain',
                {'displayName': display_name or name,
                 'description': '',
                 'defaultLogicalOperator': default_logical_operator,
                 'links': links},
                outs=[[true_next] if true_next else [],
                      [false_next] if false_next else []])


def for_loop(name, iterator, start, end, body_next, done_next,
             step=1):
    """ForLoop (end exclusive). Slots: [body, done]; a dead-ended
    body auto-returns here."""
    return node(name, 'ForLoop',
                {'iteratorVariable': iterator, 'startValue': start,
                 'endValue': end, 'stepValue': step},
                outs=[[body_next] if body_next else [],
                      [done_next] if done_next else []])


def while_loop(name, condition, body_next, done_next):
    return node(name, 'WhileLoop', {'condition': condition},
                outs=[[body_next] if body_next else [],
                      [done_next] if done_next else []])


def foreach(name, item_var, collection, body_next, done_next,
            index_var=None):
    fields = {'itemVariable': item_var, 'collection': collection}
    if index_var is not None:
        fields['indexVariable'] = index_var
    return node(name, 'ForEachLoop', fields,
                outs=[[body_next] if body_next else [],
                      [done_next] if done_next else []])


def var_src(path):
    """Read the flowing context: 'self.<field>' resolves against the
    flat execution context dict."""
    return {'sourceType': 'from_source_object',
            'sourceObjectPath': path}


def lit_src(value):
    """A literal. Type inferred — bool BEFORE int (bool subclasses
    int in python)."""
    if isinstance(value, bool):
        kind = 'bool'
    elif isinstance(value, int):
        kind = 'int'
    elif isinstance(value, float):
        kind = 'float'
    else:
        kind = 'str'
    return {'sourceType': 'direct_assignment', 'directValue': value,
            'directValueType': kind}


def wire(state, slot_index, *targets):
    """Post-hoc wiring: point output slot `slot_index` (0 = first
    output) of an already-built state at target state names."""
    state['slots'][1 + slot_index]['connectors'] = [
        {'targetStateName': t} for t in targets]
    return state


def execute(solution_dict, manager=None, params=None,
            instance_fields=None, record_context=True):
    """Run a built graph through the real engine, stepped + recorded
    — the one execution idiom every consumer shares."""
    from polariNoCode.SolutionExecutionEngine import (
        SolutionExecutionEngine, StepConfig)
    engine = SolutionExecutionEngine(manager=manager)
    return engine.execute(
        solution_data=solution_dict, input_params=params or {},
        config=StepConfig(mode='step', record_context=record_context),
        target_runtime='python_backend',
        instance_fields=instance_fields or {})
