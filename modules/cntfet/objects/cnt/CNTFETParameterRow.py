"""
@module cntfet.objects.cnt.CNTFETParameterRow

Row class CNTFETParameterRow of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTFETParameterRow(treeObject):
    """D8 as schema: one parameter, one role, one source — the
    'which conclusions rest on measurement vs calibration' query
    surface. Stamped by the derive act, one row per parameter."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        parameter: str = '',
        value: float = 0.0,
        unit: str = '',
        role: str = '',
        source: str = '',
        confidence: str = '',
        derived_from: str = '',
        equation: str = '',
        stamped_at: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.parameter = parameter
        self.value = value
        self.unit = unit
        self.role = role
        self.source = source
        self.confidence = confidence
        self.derived_from = derived_from
        self.equation = equation
        self.stamped_at = stamped_at
