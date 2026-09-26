"""
@module computelod.objects.computelod.CharacterizationMapping

Row class CharacterizationMapping of the computelod module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CharacterizationMapping(treeObject):
    """UPWARD: what does this implementation produce (plan §6, §F2). NOT the inverse of a ComputeMapping. A characteristic without its CONDITIONS (voltage, temperature, load, corner) is misleading, so a non-theoretical row without them is refused. OpenSTA/ngspice results are `simulated`; `measured` is fabricated hardware."""

    plain_words = ('A characterization mapping records a measurement of one level against another, for example the delay of a '
                   'logic cell as our transistor simulation predicts it versus the number the foundry publishes, so that the '
                   'two can be compared honestly.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        source_rung: str = '',
        source_ref: str = '',
        target_rung: str = '',
        target_ref: str = '',
        characteristic: str = '',
        method: str = '',
        conditions_json: str = '{}',
        result: float = 0.0,
        units: str = '',
        mapping_status: str = 'proposed',
        evidence_level: str = 'none',
        evidence_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source_rung = source_rung
        self.source_ref = source_ref
        self.target_rung = target_rung
        self.target_ref = target_ref
        self.characteristic = characteristic  # propagation_delay | dynamic_power | leakage | area | latency | throughput | …
        self.method = method  # OpenSTA | ngspice | Verilator | bench | analytical
        self.conditions_json = conditions_json  # {voltage, temperature, load, corner, …} — load-bearing
        self.result = result
        self.units = units
        self.mapping_status = mapping_status
        self.evidence_level = evidence_level
        self.evidence_ref = evidence_ref
        self.notes = notes
