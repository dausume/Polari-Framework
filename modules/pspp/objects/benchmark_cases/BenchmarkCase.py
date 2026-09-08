"""
@module pspp.objects.benchmark_cases.BenchmarkCase

Row class BenchmarkCase of the pspp module — one class per file (design §7), split
from benchmark_cases_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BenchmarkCase(treeObject):
    """One near-complete book experiment: inputs + measured outcomes
    + the engine hooks (family/cation/MR) the overlay runs with."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        source_reference: str = '',
        # As-printed inputs (recipe, oxide ratios, procedure) — JSON.
        inputs_json: str = '{}',
        # As-printed measured outcomes — JSON (anomalies kept, never
        # reconciled silently).
        observed_outcomes_json: str = '{}',
        # Engine hooks.
        window_family: str = '',
        cation: str = '',
        mr: float = 0.0,
        # JSON list of framework species names actually observed.
        observed_frameworks_json: str = '[]',
        # JSON list of DigitizedDataset names carrying this case's
        # measured series.
        measured_datasets_json: str = '[]',
        use: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_reference = source_reference
        self.inputs_json = inputs_json
        self.observed_outcomes_json = observed_outcomes_json
        self.window_family = window_family
        self.cation = cation
        self.mr = mr
        self.observed_frameworks_json = observed_frameworks_json
        self.measured_datasets_json = measured_datasets_json
        self.use = use
        self.provenance_id = provenance_id
        self.notes = notes
