"""
@module aquaponics.objects.plant_stress.StressResponseCurve

Row class StressResponseCurve of the aquaponics module — one class per file (design §7), split
from plant_stress_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StressResponseCurve(treeObject):
    """One (plant, part, stress_type)'s response — Tier A bounds always
    set, Tier B equation_ref optional override. See module docstring
    for the two-tier design."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-root-oxygen').
        name: str = '',
        plant_name: str = '',
        # PLANT_PARTS entry (plant_basis.PLANT_PARTS).
        part: str = 'leaf',
        # STRESS_TYPES entry.
        stress_type: str = 'temperature',
        # Tier A — trapezoidal response over STRESS_TYPE_FIELDS[
        # stress_type]'s real scalar. Below min or above max -> 0.
        min_value: float = 0.0,
        optimal_low: float = 0.0,
        optimal_high: float = 0.0,
        max_value: float = 0.0,
        # Tier B — optional. When set, OVERRIDES the Tier-A trapezoid
        # entirely for this curve. Name of a real
        # matrices.MatrixEquationDefinition row.
        equation_ref: str = '',
        # symbol -> {"source": "atmosphere"|"water"|"soil", "field":
        # "<real attribute name>"} — how the equation's own variables
        # map onto real rows. Only consulted when equation_ref is set.
        input_bindings_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plant_name = plant_name
        self.part = part
        self.stress_type = stress_type
        self.min_value = min_value
        self.optimal_low = optimal_low
        self.optimal_high = optimal_high
        self.max_value = max_value
        self.equation_ref = equation_ref
        self.input_bindings_json = input_bindings_json
        self.provenance_id = provenance_id
        self.notes = notes
