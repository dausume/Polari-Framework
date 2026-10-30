"""
@module pcb.objects.pcb.SpiceVector

SpiceVector — one class per file (design §7); kxc-3b, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SpiceVector(treeObject):
    """What it is: ONE RESULT VECTOR of a `SpiceRun` - a node voltage (/rect_out), a branch current (v1#branch) or the run's scale (time, frequency), with
    its values exactly as the solver returned them. A transient vector is real; an AC vector is complex, kept as magnitude + phase (degrees). `unit` is
    DERIVED from the name by ngspice's own conventions: the scale is s (time) or Hz (frequency), '#branch' is a current (A), anything else a voltage (V).
    Related concepts: `SpiceRun` (the run it belongs to), the run chart (pcb.custom.spice_runs.chart).
    """

    plain_words = 'One measured signal from a simulation run - a voltage at a point, a current through a part, or the time axis - with all its values.'

    @treeObjectInit
    def __init__(self, name: str = '', run: str = '', vector: str = '', role: str = 'value', unit: str = '', complex_values: bool = False, points: int = 0,
                 values_json: str = '[]', phase_json: str = '[]', min_value: float = 0.0, max_value: float = 0.0, manager=None):
        self.name = name                    # '<run>:<vector>'
        self.run = run                      # the SpiceRun
        self.vector = vector                # ngspice's vector name
        self.role = role                    # scale (the x axis) | value
        self.unit = unit                    # s | Hz | V | A
        self.complex_values = complex_values
        self.points = points
        self.values_json = values_json      # real values, or magnitudes when complex
        self.phase_json = phase_json        # phase in degrees (complex only)
        self.min_value = min_value
        self.max_value = max_value
