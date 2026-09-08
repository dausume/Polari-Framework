"""
@module electrodevice.objects.photo.SolarStackDefinition

Row class SolarStackDefinition of the electrodevice module — one class per file (design §7), split
from photo_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SolarStackDefinition(treeObject):
    """The panel: ordered layers + the absorber-selection knob.
    The optimize act ranks candidate absorbers by blackbody ultimate
    efficiency and stamps the choice + honest loss notes."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # JSON list of absorber candidates:
        # {name, gapRecord | simModel, demonstrated?, caveats?}.
        absorber_candidates_json: str = '[]',
        # KNOB: what picks the absorber — 'sq-limit' (the physics
        # ceiling) | 'demonstrated' (what has actually produced
        # power in someone's hands). Disagreement -> a suggestion.
        selection_policy: str = 'sq-limit',
        chosen_absorber: str = '',
        chosen_gap_ev: float = 0.0,
        ultimate_efficiency: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.absorber_candidates_json = absorber_candidates_json
        self.selection_policy = selection_policy
        self.chosen_absorber = chosen_absorber
        self.chosen_gap_ev = chosen_gap_ev
        self.ultimate_efficiency = ultimate_efficiency
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
