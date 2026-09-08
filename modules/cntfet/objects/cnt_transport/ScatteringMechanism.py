"""
@module cntfet.objects.cnt_transport.ScatteringMechanism

Row class ScatteringMechanism of the cntfet module — one class per file (design §7), split
from cnt_transport_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScatteringMechanism(treeObject):
    """One scattering contributor as a ROW: its mfp law (data), the
    bias condition that switches it on, the process knob that feeds
    it, its time profile (PRIOR) and what it enforces on the FET."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        description: str = '',
        # text of the equation — data the page shows, never hidden
        lambda_formula: str = '',
        # reference mfp at (d0, T0); 0.0 = not a mean free path
        lambda0_nm: float = 0.0,
        # λ ∝ (T0/T)^k
        temperature_exponent: float = 0.0,
        # λ ∝ (d/d0)^k
        diameter_exponent: float = 0.0,
        # {"activates_when": "...", ...} — empty = always active
        bias_condition_json: str = '{}',
        # which process row/field feeds this mechanism
        process_knob_json: str = '{}',
        # PRIOR aging law, labelled
        time_profile_json: str = '{}',
        # what the mechanism does to Ion, v_inj, μ_app, SS
        enforced_properties_json: str = '{}',
        confidence: str = 'low',
        origin: str = 'seeded',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.description = description
        self.lambda_formula = lambda_formula
        self.lambda0_nm = lambda0_nm
        self.temperature_exponent = temperature_exponent
        self.diameter_exponent = diameter_exponent
        self.bias_condition_json = bias_condition_json
        self.process_knob_json = process_knob_json
        self.time_profile_json = time_profile_json
        self.enforced_properties_json = enforced_properties_json
        self.confidence = confidence
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior
