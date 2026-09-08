"""
@module scoring.objects.scoring.ScoreContext

Row class ScoreContext of the scoring module — one class per file (design §7), split
from scoring_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScoreContext(treeObject):
    """One scenario slice a value can be measured under."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('state-california', 'year-2022').
        name: str = '',
        display_name: str = '',
        # CONTEXT_TYPES key.
        context_type: str = 'custom',
        # Type-specific payload (JSON): location {'granularity':
        # 'state', 'state': 'California'}; timeframe {'start': ...,
        # 'end': ...}; custom anything.
        value_json: str = '{}',
        # Optional parent context name (hierarchy: city → state →
        # country), so specificity chains are walkable.
        parent_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.context_type = context_type
        self.value_json = value_json
        self.parent_name = parent_name
        self.notes = notes
