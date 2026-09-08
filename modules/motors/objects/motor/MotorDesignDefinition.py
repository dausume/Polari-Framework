"""
@module motors.objects.motor.MotorDesignDefinition

Row class MotorDesignDefinition of the motors module — one class per file (design §7), split
from motor_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.motor._shared import LADDER_RUNGS, MOTOR_TOPOLOGIES, TOLERANCE_TIERS

class MotorDesignDefinition(treeObject):
    """One motor design = one rung of the ladder made concrete."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 topology='lavet-clock-stepper', ladder_rung='M0',
                 tolerance_tier='T0', params_json='{}',
                 drive_json='{}', build_requirements_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.topology = (topology if topology in MOTOR_TOPOLOGIES
                         else 'lavet-clock-stepper')
        self.ladder_rung = (ladder_rung
                            if ladder_rung in LADDER_RUNGS else 'M0')
        self.tolerance_tier = (tolerance_tier
                               if tolerance_tier in TOLERANCE_TIERS
                               else 'T0')
        #: Topology-specific geometry/winding/materials — material
        #: slots are MagneticMaterialOption names (roles checked by
        #: the designer, gates travel). See motor_designer for the
        #: per-topology vocabularies.
        self.params_json = params_json
        #: {'rate_hz': f, 'kind': 'alternating-pulse' | '3-phase'}.
        self.drive_json = drive_json
        #: {'tools': [...], 'materials': [{'ref': catalog-or-item,
        #: 'note': ...}], 'skills': [...], 'rough_hours': h} — the
        #: buildable-sample spec, honest difficulty like the
        #: research-tools tree.
        self.build_requirements_json = build_requirements_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
