"""
@module tensortree.objects.tensortree.UnresolvedTensorSpace

Row class UnresolvedTensorSpace of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class UnresolvedTensorSpace(treeObject):
    """WHAT IS NOT YET UNDERSTOOD, kept with everything that IS known (plan §13). Allowed anywhere: under the root, under a node, and BETWEEN two resolved nodes. `unresolved_kind` says which research task it is (plan §F6.2)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tree: str = '',
        parent: str = '',
        title: str = '',
        unresolved_kind: str = 'semantic',
        known_dims_json: str = '[]',
        known_semantics_json: str = '{}',
        constraints_json: str = '[]',
        candidate_mappings_json: str = '[]',
        candidate_bindings_json: str = '[]',
        hypotheses_json: str = '[]',
        evidence_json: str = '[]',
        open_questions_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tree = tree
        self.parent = parent
        self.title = title
        self.unresolved_kind = unresolved_kind  # semantic | structural | visualization | mapping | validation
        self.known_dims_json = known_dims_json
        self.known_semantics_json = known_semantics_json
        self.constraints_json = constraints_json
        self.candidate_mappings_json = candidate_mappings_json
        self.candidate_bindings_json = candidate_bindings_json
        self.hypotheses_json = hypotheses_json
        self.evidence_json = evidence_json
        self.open_questions_json = open_questions_json
        self.notes = notes
