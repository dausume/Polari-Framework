"""
@module polariNoCode.graph_compilers

ncg-1: the domain-compiler contract + the external-orchestrator idiom
— the TWO shared shapes both no-code generalization clients (judicial
adjudication, circuit/logic compilation) converged on:

  1. COMPILER: domain rows -> a small SolutionDefinition definition
     dict (built via polariNoCode.graph_builder) + optional generated
     artifacts, with provenance STAMPED ON the output (what compiler,
     what source rows) so a compiled graph can always answer "where
     did you come from".
  2. ORCHESTRATOR: the engine has NO pause/resume (verified; still
     true) — human- or device-paced flows run MANY SMALL COMPLETE
     executions with state persisted on a domain row between runs
     (evaluate_stage_gate's pattern). `advance()` is that step,
     factored once.

Compilers are object-coherent: each registers a GraphCompilerDefinition
row (name, domain, compiler_ref) so the tree answers "what compilers
exist" like it answers everything else. Registration is data; the
callable lives at compiler_ref ('module:function'), same convention as
the accountability matrix's callable runners.

@consumers
  - scoring judicial fork compiler (ncg-2)
  - hwdigital logic compiler / circuit netlist compiler (ncg-3/4)
  - testing.selftest_* (matrix rows)
"""

import importlib

from objectTreeDecorators import treeObject, treeObjectInit


class GraphCompilerDefinition(treeObject):
    """One registered domain compiler — a row, configurable at the
    row ([[object-coherence]])."""

    @treeObjectInit
    def __init__(self, name: str = '', domain: str = '',
                 compiler_ref: str = '', description: str = '',
                 enabled: bool = True):
        self.name = name
        # 'judicial' | 'hwdigital' | 'circuit' | ...
        self.domain = domain
        # 'module:function' — fn(domain_rows: dict) -> compile result
        self.compiler_ref = compiler_ref
        self.description = description
        # The knob: a disabled compiler refuses with a plain error
        # instead of compiling ([[knobs-and-suggestions]]).
        self.enabled = enabled


#: Registered domain compilers (ncg-1/2). Rows, so the enable knob
#: and the "what compilers exist" question live in the tree.
SEED_GRAPH_COMPILERS = [
    {
        'name': 'judicial-fork',
        'domain': 'judicial',
        'compiler_ref': 'scoring.court_case:compile_fork_graph',
        'description': 'One decision-procedure fork + its resolved '
                       'criterion + its edge-declared outcomes -> '
                       'one small executable SolutionDefinition '
                       '(JUDICIAL_ADJUDICATION_GRAPH_PLAN).',
        'enabled': True,
    },
    {
        'name': 'hwdigital-logic',
        'domain': 'hwdigital',
        'compiler_ref': 'hwdigital.logic_compile:compile_logic_design',
        'description': 'LogicBlockNode diagram rows -> synthesizable '
                       'Verilog + self-checking bench (python '
                       'reference evaluator supplies expected '
                       'values); iCE40 is the synthesis target.',
        'enabled': True,
    },
    {
        'name': 'circuit-netlist',
        'domain': 'circuit',
        'compiler_ref': 'electrodevice.circuit_netlist'
                        ':compile_circuit',
        'description': 'Circuit rows (components wired by net) -> a '
                       'runnable SPICE netlist; device components '
                       'pull msci-derived subckt cards with '
                       'provenance.',
        'enabled': True,
    },
    {
        'name': 'data-gathering',
        'domain': 'scoring',
        'compiler_ref': 'scoring.data_gathering'
                        ':compile_gathering_solution',
        'description': "An organization's data-gathering procedure "
                       '(collection/submission/validation/'
                       'transformation steps) -> an executable '
                       'SolutionDefinition whose validation steps '
                       'gate like judicial fork criteria.',
        'enabled': True,
    },
    {
        'name': 'breadboard-netlist',
        'domain': 'circuit',
        'compiler_ref': 'electrodevice.breadboard_netlist'
                        ':compile_breadboard',
        'description': 'ComponentPlacement + BoardJumper rows -> a '
                       'runnable SPICE netlist; tie-point '
                       'connectivity IS the wiring, jumpers union '
                       'nets across boards, boards re-wrap as '
                       '.subckt components.',
        'enabled': True,
    },
]


def resolve_compiler(compiler_ref):
    """'module:function' -> callable. Plain errors, no magic."""
    module_name, sep, fn_name = compiler_ref.partition(':')
    if not sep or not module_name or not fn_name:
        raise ValueError(
            f"compiler_ref {compiler_ref!r} must be 'module:function'")
    return getattr(importlib.import_module(module_name), fn_name)


def stamp_provenance(definition, compiler_name, source_rows,
                     notes=''):
    """Stamp WHERE a compiled graph came from onto the definition
    dict itself. The engines ignore unknown top-level keys (verified:
    only solutionName/stateInstances are read), so the stamp rides
    the artifact without touching execution."""
    definition['compiledBy'] = {
        'compiler': compiler_name,
        'sourceRows': source_rows,
        'notes': notes,
    }
    return definition


def compile_with(compiler_row, domain_rows):
    """Run one registered compiler over its domain rows ->
    {'definition': <stamped dict>, 'artifacts': [...]}. A compiler
    may return either a bare definition dict or that full shape."""
    if not getattr(compiler_row, 'enabled', True):
        raise RuntimeError(
            f"compiler '{compiler_row.name}' is disabled (the knob "
            f"is on the GraphCompilerDefinition row — enable it "
            f"there)")
    fn = resolve_compiler(compiler_row.compiler_ref)
    result = fn(domain_rows)
    if isinstance(result, dict) and 'stateInstances' in result:
        result = {'definition': result, 'artifacts': []}
    # A compiler may target artifacts only (HDL, netlists, firmware)
    # with no solution graph — definition None is a legal shape; the
    # artifacts then carry their own generated-by headers.
    definition = result.get('definition')
    if isinstance(definition, dict) and 'compiledBy' not in definition:
        stamp_provenance(definition, compiler_row.name,
                         sorted(domain_rows)
                         if isinstance(domain_rows, dict) else [])
    result.setdefault('artifacts', [])
    return result


def final_context_of(trace):
    """Unwrap the last step snapshot's variables into a plain dict —
    the same consumer contract selftest_turing pins."""
    if not getattr(trace, 'steps', None):
        return {}
    variables = trace.steps[-1].context_after.variables
    return {k: (v.get('value')
                if isinstance(v, dict) and 'value' in v else v)
            for k, v in variables.items()}


def advance(solution_dict, stored_context, new_input, manager=None):
    """ONE orchestrator step: merge the persisted domain context with
    this step's fresh input, run the compiled graph to completion,
    and hand back everything the domain needs to route + persist:

      {'outcome': final_return_value,
       'status': trace.status,
       'final_context': the run's ending context dict,
       'trace': the full ExecutionTrace}

    The DOMAIN owns persistence and routing (what part of
    final_context to keep, which fork/stage comes next) — this helper
    owns only the execute step, so every client paces flows the same
    proven way instead of fighting the engine for a pause that does
    not exist."""
    import copy
    from polariNoCode.graph_builder import execute
    if stored_context is not None \
            and not isinstance(stored_context, dict):
        raise ValueError('stored_context must be a dict (the flat '
                         'persisted fact bag) — got '
                         f'{type(stored_context).__name__}')
    if new_input is not None and not isinstance(new_input, dict):
        raise ValueError('new_input must be a dict — got '
                         f'{type(new_input).__name__}')
    params = dict(stored_context or {})
    params.update(new_input or {})
    trace = execute(solution_dict, manager=manager, params=params)
    # Deep copy: trace snapshots alias nested objects from the
    # caller's stored context — a client persisting final_context
    # onward must never share live references with its own row.
    final_context = copy.deepcopy(final_context_of(trace))
    return {'outcome': getattr(trace, 'final_return_value', None),
            'status': getattr(trace, 'status', None),
            'final_context': final_context,
            'trace': trace}
