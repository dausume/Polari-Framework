"""
@module motors.objects.scale_goals.ClockScaleDefinition

Row class ClockScaleDefinition of the motors module — one class per file (design §7), split
from scale_goals_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ClockScaleDefinition(treeObject):
    """One point on the size ladder, with its geometry priors."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 movement_diameter_mm=0.0, window_mm2=0.0,
                 mean_turn_mm=14.0, hand_mass_g=0.0, hand_r_mm=0.0,
                 mmf_a_turns=0.0, mmf_provenance='',
                 cell_name='', cell_v=1.5, cell_capacity_mah=0.0,
                 pulse_ms=30.0, rate_hz=1.0,
                 tolerance_rung_required='T2', gear_module_mm=0.5,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.movement_diameter_mm = movement_diameter_mm
        #: Winding window PRIOR for this scale — the resource
        #: everything else spends.
        self.window_mm2 = window_mm2
        self.mean_turn_mm = mean_turn_mm
        #: The largest hand: its imbalance m·g·r is what the
        #: movement must beat, and what scales the MMF prior.
        self.hand_mass_g = hand_mass_g
        self.hand_r_mm = hand_r_mm
        #: MMF prior with its provenance SPELLED OUT — these are
        #: scaled/literature figures, not measurements.
        self.mmf_a_turns = mmf_a_turns
        self.mmf_provenance = mmf_provenance
        self.cell_name = cell_name
        self.cell_v = cell_v
        self.cell_capacity_mah = cell_capacity_mah
        self.pulse_ms = pulse_ms
        self.rate_hz = rate_hz
        #: Finest tolerance rung any part of this movement needs.
        self.tolerance_rung_required = tolerance_rung_required
        self.gear_module_mm = gear_module_mm
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
