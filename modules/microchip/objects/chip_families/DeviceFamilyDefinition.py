"""
@module microchip.objects.chip_families.DeviceFamilyDefinition

Row class DeviceFamilyDefinition of the microchip module — one class per file (design §7), split
from chip_families_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DeviceFamilyDefinition(treeObject):
    """One rank-1 device family: its physics, its characterization
    contract (as revisable data), which Polari classes hold LIVE
    artifacts (empty for shells), and what it composes into."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        physics: str = '',
        # 'live' (device rows + characterization basis exist) or
        # 'shell' (contract defined, no classes yet — by rule).
        status: str = 'shell',
        # JSON list of {module, class} rows that ARE this family's
        # artifacts ([] for shells).
        artifact_classes_json: str = '[]',
        # JSON list of {quantity, unit, why} a characterized device
        # of this family must provide — the contract AS DATA.
        contract_json: str = '[]',
        # JSON list of example mixed-family compositions at rung 2+.
        composes_json: str = '[]',
        first_target: str = '',
        plan_pointer: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.physics = physics
        self.status = status
        self.artifact_classes_json = artifact_classes_json
        self.contract_json = contract_json
        self.composes_json = composes_json
        self.first_target = first_target
        self.plan_pointer = plan_pointer
        self.notes = notes
