"""
@module microchip.objects.chip.MicrochipDesignNode

Row class MicrochipDesignNode of the microchip module — one class per file (design §7), split
from chip_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MicrochipDesignNode(treeObject):
    """One node of a concrete design hierarchy. parent follows the
    ladder upward (chip is the root); artifact_refs point at rows
    in OTHER modules ({module, class, name}) or at citation
    anchors ({anchor: name} in cntfet's CNTCalibrationAnchor) —
    the citation-linkage rule made structural."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        design: str = '',
        level: str = '',
        parent: str = '',
        title: str = '',
        artifact_refs_json: str = '[]',
        citation: str = '',
        metrics_json: str = '{}',
        status: str = 'unbuilt',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.design = design
        self.level = level
        self.parent = parent
        self.title = title
        self.artifact_refs_json = artifact_refs_json
        self.citation = citation
        self.metrics_json = metrics_json
        self.status = status
        self.notes = notes
