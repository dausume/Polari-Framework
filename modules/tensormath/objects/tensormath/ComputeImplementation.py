"""
@module tensormath.objects.tensormath.ComputeImplementation

Row class ComputeImplementation of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ComputeImplementation(treeObject):
    """ONE WAY a TensorOperator runs (plan §18, §F8): the target rung + kind of the ComputeLOD ladder, the precision and shapes it supports, and its measured/simulated cost — every number from a REAL run or a cited model (derive-or-cite), with `evidence_level` saying which."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        operator: str = '',
        target_rung: str = '',
        target_kind: str = '',
        target_ref: str = '',
        precision: str = 'float64',
        shapes_json: str = '[]',
        latency_s: float = 0.0,
        throughput: float = 0.0,
        memory_bytes: int = 0,
        energy_j: float = 0.0,
        error: float = 0.0,
        config_overhead_s: float = 0.0,
        mapping_status: str = 'proposed',
        evidence_level: str = 'none',
        evidence_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.operator = operator  # TensorOperator.name
        self.target_rung = target_rung  # ComputeLOD.name (e.g. microarchitecture, rtl)
        self.target_kind = target_kind  # ComputeKind.name (e.g. tensor-array, in-order)
        self.target_ref = target_ref  # the implementing row (a MatrixEquationDefinition, an hwfpga RegisterMapDefinition, a MicrochipDesignNode …)
        self.precision = precision
        self.shapes_json = shapes_json  # supported tensor shapes / rank constraints
        self.latency_s = latency_s
        self.throughput = throughput  # operations per second
        self.memory_bytes = memory_bytes
        self.energy_j = energy_j
        self.error = error  # vs the reference implementation
        self.config_overhead_s = config_overhead_s  # e.g. FPGA configuration time
        self.mapping_status = mapping_status  # proposed | implemented | validated
        self.evidence_level = evidence_level  # none | analytical | simulated | measured
        self.evidence_ref = evidence_ref  # the benchmark / run row
        self.notes = notes
