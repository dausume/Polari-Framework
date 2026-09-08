"""
@module nutrition.objects.activity.ActivityDefinition

Row class ActivityDefinition of the nutrition module — one class per file (design §7), split
from activity_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.objects.activity._shared import COMPENDIUM_ATTRIBUTION

class ActivityDefinition(treeObject):
    """One Compendium activity (code + MET, verbatim)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('walking-25mph-level').
        name: str = '',
        display_name: str = '',
        # the Compendium activity code — the real pin.
        activity_code: str = '',
        met_value: float = 0.0,
        category: str = '',
        # INTENSITY_BANDS entry, derived from the MET cutoffs.
        intensity: str = 'moderate',
        source: str = COMPENDIUM_ATTRIBUTION,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.activity_code = activity_code
        self.met_value = met_value
        self.category = category
        self.intensity = intensity
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
