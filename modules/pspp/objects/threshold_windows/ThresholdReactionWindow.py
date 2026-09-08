"""
@module pspp.objects.threshold_windows.ThresholdReactionWindow

Row class ThresholdReactionWindow of the pspp module — one class per file (design §7), split
from threshold_windows_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ThresholdReactionWindow(treeObject):
    """One banded (asymmetric/threshold) window for one descriptor."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('k-ps:SiO2/Al2O3:banded').
        name: str = '',
        # Windows never transfer between families (invariant I5).
        material_family: str = '',
        # The computed descriptor it grades ('SiO2/Al2O3', 'MR'…).
        descriptor: str = '',
        # JSON ordered band list: [{"lo": n|null, "hi": n|null,
        # "grade": "<GRADES>", "note": "..."}] — contiguous half-open
        # [lo, hi) bands covering the whole line.
        bands_json: str = '[]',
        # 'quality' grades a composition; 'condition-gate' opens or
        # closes reaction pathways (failure = closed).
        window_role: str = 'quality',
        behavior_note: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_family = material_family
        self.descriptor = descriptor
        self.bands_json = bands_json
        self.window_role = window_role
        self.behavior_note = behavior_note
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
