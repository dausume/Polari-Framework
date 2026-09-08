"""
@module cntfet.objects.cnt_characterization.CellCharacterizationRun

Row class CellCharacterizationRun of the cntfet module — one class per file (design §7), split
from cnt_characterization_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CellCharacterizationRun(treeObject):
    """One characterization pass of one cell — the D11/D16 schema
    every executor must emit into."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        cell: str = '',
        executor: str = 'polari-own-loop',
        vdd_v: float = 0.6,
        temperature_k: float = 300.0,
        slews_s_json: str = '[]',
        loads_f_json: str = '[]',
        input_cap_f: float = 0.0,
        tables_json: str = '{}',
        liberty_text: str = '',
        sta_gate_json: str = '{}',
        definitions_json: str = '{}',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.cell = cell
        self.executor = executor
        self.vdd_v = vdd_v
        self.temperature_k = temperature_k
        self.slews_s_json = slews_s_json
        self.loads_f_json = loads_f_json
        self.input_cap_f = input_cap_f
        self.tables_json = tables_json
        self.liberty_text = liberty_text
        self.sta_gate_json = sta_gate_json
        self.definitions_json = definitions_json
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes
