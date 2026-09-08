"""
@module scoring.objects.scoring.ScoreSubject

Row class ScoreSubject of the scoring module — one class per file (design §7), split
from scoring_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScoreSubject(treeObject):
    """The entity being scored — policy, politician, jurisdiction,
    material, proposal … anything with an identity."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('california', 'policy-min-wage-2024').
        name: str = '',
        display_name: str = '',
        # Free kind ('state', 'policy', 'politician', 'material'…).
        kind: str = '',
        # Optional anchor into a live Polari object (JSON objectRef
        # {'kind': 'objectRef', 'className': ..., 'name': ...}) so a
        # subject IS a real object, not a label (object-coherence).
        object_ref_json: str = '',
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.object_ref_json = object_ref_json
        self.description = description
        self.notes = notes
