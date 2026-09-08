"""
@module cntfet.objects.cnt.CNTCalibrationAnchor

Row class CNTCalibrationAnchor of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTCalibrationAnchor(treeObject):
    """One digitized/extracted literature value with FULL D18
    provenance: raw points + figure id + axis scaling + extraction
    method + error estimate + normalizations + any fitted params.
    status='refusing' rows name data we do NOT have (refusal, never
    invention)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        source_reference: str = '',
        doi: str = '',
        figure: str = '',
        extraction_method: str = '',
        digitization_error: str = '',
        axis_scaling_json: str = '{}',
        raw_points_json: str = '[]',
        normalizations_json: str = '{}',
        fitted_params_json: str = '{}',
        value: float = 0.0,
        unit: str = '',
        conditions_json: str = '{}',
        status: str = 'ready',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_reference = source_reference
        self.doi = doi
        self.figure = figure
        self.extraction_method = extraction_method
        self.digitization_error = digitization_error
        self.axis_scaling_json = axis_scaling_json
        self.raw_points_json = raw_points_json
        self.normalizations_json = normalizations_json
        self.fitted_params_json = fitted_params_json
        self.value = value
        self.unit = unit
        self.conditions_json = conditions_json
        self.status = status
        self.notes = notes
