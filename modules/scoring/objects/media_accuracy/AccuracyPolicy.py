"""
@module scoring.objects.media_accuracy.AccuracyPolicy

Row class AccuracyPolicy of the scoring module — one class per file (design §7), split
from media_accuracy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AccuracyPolicy(treeObject):
    """Editable accuracy bands over relative error."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Ordered JSON list of {'label', 'max'} over |claimed −
        # measured| / |measured| (classify_max semantics).
        error_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.error_bands_json = error_bands_json
        self.notes = notes
