"""
@module aquaponics.objects.water_batch.WaterBatchSchedule

Row class WaterBatchSchedule of the aquaponics module — one class per file (design §7), split
from water_batch_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WaterBatchSchedule(treeObject):
    """An ordered, optionally-repeating cycle of {waterName,
    holdHours, holdDays} batches. See module docstring for the full
    "go until full, then sit" design."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('basil-stress-cycle').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list: [{"waterName": "...", "holdHours": 0.0,
        # "holdDays": 0.0}, ...] — ordered, at least one entry.
        batches_json: str = '[]',
        # Cycle back to batch 0 once the last batch's hold completes
        # (True), or hold indefinitely at the last batch (False).
        repeat: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.batches_json = batches_json
        self.repeat = repeat
        self.provenance_id = provenance_id
        self.notes = notes
