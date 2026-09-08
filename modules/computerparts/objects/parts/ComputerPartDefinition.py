"""
@module computerparts.objects.parts.ComputerPartDefinition

Row class ComputerPartDefinition of the computerparts module — one class per file (design §7), split
from parts_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComputerPartDefinition(treeObject):
    """One buyable part with a DATED price."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('gpu-rtx3090-used').
        name: str = '',
        title: str = '',
        # PART_KINDS entry.
        kind: str = 'gpu',
        model: str = '',
        # CONDITIONS entry.
        condition: str = 'new',
        # Kind-specific specs: gpu {vram_mb}, cpu {cores, threads},
        # ram {capacity_mb}, storage {capacity_mb}, psu {watts}.
        specs_json: str = '{}',
        price_amount: float = 0.0,
        price_unit: str = 'USD',
        price_as_of: str = '',
        price_source: str = '',
        price_note: str = '',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.kind = kind
        self.model = model
        self.condition = condition
        self.specs_json = specs_json
        self.price_amount = price_amount
        self.price_unit = price_unit
        self.price_as_of = price_as_of
        self.price_source = price_source
        self.price_note = price_note
        self.notes = notes
        self.published = published
        self.is_prior = is_prior
