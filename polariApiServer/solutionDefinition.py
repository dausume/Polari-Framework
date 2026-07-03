from objectTreeDecorators import treeObject, treeObjectInit

class SolutionDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', function_name='', target_runtime='python_backend',
                 definition='{}', contract_json='{}', manager=None):
        self.name = name
        self.function_name = function_name
        self.target_runtime = target_runtime  # 'python_backend' or 'typescript_frontend'
        self.definition = definition  # JSON blob of the full solution data
        # The solution's CONTRACT — what it needs and what it produces —
        # so other solutions (SolutionInvocation) and modules can use it
        # as a reusable, opaque state without reading its internals:
        #   {
        #     "description": "<what this solution does, for consumers>",
        #     "inputs":  [{"name", "required": bool, "description", "type"?}],
        #     "returns": [{"name", "description", "type"?}],
        #     "executionRights": "invoker" | "definer"
        #   }
        # `executionRights` declares WHOSE permissions the solution runs
        # under when invoked by someone other than its author:
        #   invoker (default) — the caller's rights; the safe default for
        #                       module-shipped solutions.
        #   definer           — the author's rights (a privileged helper).
        # DECLARATIVE for now: stored and surfaced so authors state
        # intent; runtime enforcement arrives with the auth/authz node
        # family (P6), which injects the identity context this needs.
        # Empty '{}' = legacy solution with no declared contract (callable
        # with unchecked inputs; SolutionInvocation validates only what a
        # contract declares).
        self.contract_json = contract_json
