"""
@module microchip.objects.chip.DesignLevelDefinition

Row class DesignLevelDefinition of the microchip module — one class per file (design §7), split
from chip_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DesignLevelDefinition(treeObject):
    """One rung of the design ladder — vocabulary + which Polari
    classes hold artifacts at this level + which orthogonal scale
    axes apply there."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        rank: int = 0,
        description: str = '',
        # JSON list of {module, class} rows that ARE artifacts at
        # this level (empty = no implementation exists yet).
        artifact_classes_json: str = '[]',
        # JSON list of the orthogonal scale axes live at this level
        # (e.g. the device level's manufacturing_regime knob).
        scale_axes_json: str = '[]',
        status: str = 'unbuilt',
        plan_pointer: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.rank = rank
        self.description = description
        self.artifact_classes_json = artifact_classes_json
        self.scale_axes_json = scale_axes_json
        self.status = status
        self.plan_pointer = plan_pointer
        self.notes = notes
