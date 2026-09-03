"""
@module polariNoCode.analysis_calls

cal-4 — AnalysisDefinition rows + the AnalysisCall node: the bridge
that lets a no-code solution USE a registered backend analysis (a
shopping list, a prep schedule, a price compare) as one step, so
event logic stays authorable as data while the arithmetic stays
where it already lives. Same convention as GraphCompilerDefinition
(compiler_ref) and the accountability matrix's runners: the callable
is named on a row ('module:function'), the row is the knob (enabled
= False refuses plainly), and every call stamps provenance into the
result.

An analysis callable is `fn(manager, **params) -> dict`.

@consumers SolutionExecutionEngine (AnalysisCall handler), nutrition
  calendar seeds (purchase / bulk / coordination analyses)
"""

import importlib

from objectTreeDecorators import treeObject, treeObjectInit


class AnalysisDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', domain: str = '', callable_ref: str = '',
                 description: str = '', params_json: str = '{}',
                 enabled: bool = True, is_prior: bool = True,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.domain = domain
        # 'module:function' — fn(manager, **params) -> dict
        self.callable_ref = callable_ref
        self.description = description
        # documented parameter names + defaults (for the editor).
        self.params_json = params_json
        self.enabled = enabled
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def resolve_callable(ref):
    """'module:function' → the function, or a plain ValueError."""
    if not ref or ':' not in str(ref):
        raise ValueError(f"analysis callable '{ref}' is not 'module:function'")
    module_name, func_name = str(ref).split(':', 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, func_name, None)
    if fn is None:
        raise ValueError(f"analysis callable '{ref}': {module_name} has no {func_name}")
    return fn


def call_analysis(manager, analysis, params=None):
    """Run an analysis by AnalysisDefinition NAME (a row) or by a bare
    'module:function' ref. Returns the analysis dict with provenance
    stamped under `_analysis`."""
    ref = str(analysis or '')
    row = None
    for inst in ((getattr(manager, 'objectTables', {}) or {})
                 .get('AnalysisDefinition', {}) or {}).values():
        if str(getattr(inst, 'name', '')) == ref:
            row = inst
            break
    if row is not None:
        if not getattr(row, 'enabled', True):
            raise ValueError(f"analysis '{ref}' is disabled on its row")
        ref = getattr(row, 'callable_ref', '')
    elif ':' not in ref:
        raise ValueError(f"analysis '{analysis}' is neither an AnalysisDefinition "
                         f"row nor a 'module:function' ref")
    fn = resolve_callable(ref)
    result = fn(manager, **(params or {}))
    if isinstance(result, dict):
        result = dict(result)
        result['_analysis'] = {'name': getattr(row, 'name', '') if row else '',
                               'callable': ref, 'params': dict(params or {})}
    return result
