"""
@module cntfet.objects.cnt_targets.FETTargetMapping

Row class FETTargetMapping of the cntfet module — one class per file (design §7), split
from cnt_targets_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FETTargetMapping(treeObject):
    """Which targets a FET is engineered for, and WHY — the mapping
    Dustin asked for. Libraries / cells / blocks built on the FET
    inherit it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        targets_json: str = '[]',
        engineered_for: str = '',
        source: str = '',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.device = device
        self.targets_json = targets_json
        self.engineered_for = engineered_for
        self.source = source
        self.notes = notes
        self.is_prior = is_prior
