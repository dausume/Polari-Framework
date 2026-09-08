"""
@module casting.objects.sprue.SprueStrategyDefinition

Row class SprueStrategyDefinition of the casting module — one class per file (design §7), split
from sprue_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from casting.objects.sprue._shared import GATE_STYLES, REMOVAL_MODES, VENT_PLACEMENTS

class SprueStrategyDefinition(treeObject):
    """A reusable gating strategy — the knobs, not the geometry."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # GATE_STYLES entry.
        gate_style: str = 'top-gate',
        n_vents: int = 2,
        # VENT_PLACEMENTS entry — high-points uses the cast-2 grid
        # connectivity to find cavity ceilings air must escape from.
        vent_placement: str = 'high-points',
        sprue_taper_deg: float = 2.0,
        # neck cross-section ÷ LOCAL part section at the attachment —
        # the removability knob. Checked against NECK_RATIO_LIMITS.
        neck_area_ratio: float = 0.2,
        # REMOVAL_MODES entry: snap needs a brittle part + small
        # neck; cut tolerates more; melt-with-master only when the
        # sprue material IS the sacrificial master.
        removal_mode: str = 'snap',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.gate_style = (gate_style if gate_style in GATE_STYLES
                           else 'top-gate')
        self.n_vents = n_vents
        self.vent_placement = (vent_placement
                               if vent_placement in VENT_PLACEMENTS
                               else 'high-points')
        self.sprue_taper_deg = sprue_taper_deg
        self.neck_area_ratio = neck_area_ratio
        self.removal_mode = (removal_mode
                             if removal_mode in REMOVAL_MODES
                             else 'snap')
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
