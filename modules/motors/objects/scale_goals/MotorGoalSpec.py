"""
@module motors.objects.scale_goals.MotorGoalSpec

Row class MotorGoalSpec of the motors module — one class per file (design §7), split
from scale_goals_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.scale_goals._shared import MATERIAL_POLICIES

class MotorGoalSpec(treeObject):
    """A goal: scale + material policy + targets + scoring weights.
    All knobs."""

    @treeObjectInit
    def __init__(self, name='', display_name='', scale_ref='',
                 material_policy='local-made-only',
                 battery_life_target_yr=4.0,
                 wire_rung_ceiling='W2', tolerance_ceiling='T2',
                 weights_json='{}', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.scale_ref = scale_ref
        self.material_policy = (
            material_policy if material_policy in MATERIAL_POLICIES
            else 'local-made-only')
        self.battery_life_target_yr = battery_life_target_yr
        #: The capability rungs this goal is allowed to ASSUME —
        #: W2/T2 is where our stack demonstrably stands (mag-25,
        #: tolerance ladder). Raising them is a decision, not a
        #: default.
        self.wire_rung_ceiling = wire_rung_ceiling
        self.tolerance_ceiling = tolerance_ceiling
        #: {'drive':w,'life':w,'fit':w,'capability':w,'materials':w}
        self.weights_json = weights_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
