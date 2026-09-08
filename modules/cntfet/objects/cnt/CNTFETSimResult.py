"""
@module cntfet.objects.cnt.CNTFETSimResult

Row class CNTFETSimResult of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTFETSimResult(treeObject):
    """One evaluation run (Id-Vg / Id-Vd family, ToB reference,
    calibration pass, or equivalence regression) as a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        kind: str = '',
        engine: str = '',
        physics_fidelity: str = '',
        inputs_json: str = '{}',
        series_json: str = '[]',
        metrics_json: str = '{}',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.kind = kind
        self.engine = engine
        self.physics_fidelity = physics_fidelity
        self.inputs_json = inputs_json
        self.series_json = series_json
        self.metrics_json = metrics_json
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes
