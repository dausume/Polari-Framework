"""
@module electrodevice.objects.device.CircuitRunResult

Row class CircuitRunResult of the electrodevice module — one class per file (design §7), split
from device_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CircuitRunResult(treeObject):
    """One ngspice run of a circuit using the device — inputs,
    per-pin outputs, and an honest verdict, as a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_name: str = '',
        circuit: str = 'fpga-pin-led',
        inputs_json: str = '{}',
        outputs_json: str = '{}',
        verdict: str = '',
        engine: str = 'ngspice',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.circuit = circuit
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.verdict = verdict
        self.engine = engine
        self.ran_at = ran_at
        self.notes = notes
