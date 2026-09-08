"""
@module cntfet.objects.cnt_process.CNTFETMonteCarloRun

Row class CNTFETMonteCarloRun of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTFETMonteCarloRun(treeObject):
    """One MC population run: inputs, per-metric population
    statistics, yield breakdown, dominant limitation — a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        process_set: str = '',
        sample_count: int = 0,
        seed: int = 0,
        inputs_json: str = '{}',
        yield_json: str = '{}',
        population_json: str = '{}',
        dominant_limitation: str = '',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.process_set = process_set
        self.sample_count = sample_count
        self.seed = seed
        self.inputs_json = inputs_json
        self.yield_json = yield_json
        self.population_json = population_json
        self.dominant_limitation = dominant_limitation
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes
