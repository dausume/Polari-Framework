"""
@module computerparts.objects.parts.ComputerBuildDefinition

Row class ComputerBuildDefinition of the computerparts module — one class per file (design §7), split
from parts_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComputerBuildDefinition(treeObject):
    """One assemblable machine: a parts list + effective specs.
    Total cost is DERIVED from the part rows — never stored."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('build-used-3090').
        name: str = '',
        title: str = '',
        # What this build is FOR ('local AI — 30B-class models').
        purpose: str = '',
        # JSON list of ComputerPartDefinition names.
        parts_json: str = '[]',
        # The build's effective machine specs (the ai-6 gauge
        # vocabulary): cores, ram_mb, disk_mb, gpu_model, vram_mb.
        specs_json: str = '{}',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.purpose = purpose
        self.parts_json = parts_json
        self.specs_json = specs_json
        self.notes = notes
        self.published = published
        self.is_prior = is_prior
