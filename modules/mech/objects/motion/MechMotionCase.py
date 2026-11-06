"""
@module mech.objects.motion.MechMotionCase

Row class MechMotionCase of the mech module — one class per file (design §7).
MECH_FREECAD_INTERCHANGE_PLAN §3.5: how one joint of an assembly is driven
over time, and which checks the run must answer.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechMotionCase(treeObject):
    """A drive on one joint plus its acceptance checks. The formula uses
    the FreeCAD Motion Formula syntax (`time`, + - * / ^, parentheses,
    sin, cos — NOT min/max, which FreeCAD silently refuses) so the same
    row exports to a FreeCAD Motion object unchanged."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', joint_ref='',
                 drive='position', formula='', force_n=-1.0,
                 torque_nm=-1.0, duration_s=1.0, step_s=0.01,
                 checks_json='[]', contact_ref='', running_gear='slide',
                 notes='', manager=None):
        self.name = name
        self.assembly_ref = assembly_ref
        #: MechJoint name — the driven joint (its limits are the hard stops).
        self.joint_ref = joint_ref
        #: position | velocity | force (DRIVE_KINDS).
        self.drive = drive
        #: Position (mm or deg) or velocity formula of `time`, FreeCAD
        #: Motion syntax, e.g. '100*time'. For a force drive it may hold a
        #: force-of-time formula; empty = the constant force_n / torque_nm.
        self.formula = formula
        #: Constant drive force (N) for a linear force drive; -1 = undetermined.
        self.force_n = force_n
        #: Constant drive torque (N·m) for a rotary force drive; -1 = undetermined.
        self.torque_nm = torque_nm
        self.duration_s = duration_s
        #: Recording step (s) — also FreeCAD's cTimeStepOutput on export.
        self.step_s = step_s
        #: JSON list of {name (CHECK_KINDS), criterion, knob}.
        self.checks_json = checks_json
        #: '' = every `sliding` MechContact of the assembly on this joint;
        #: else the one MechContact whose mu_json applies (the legacy
        #: wooden-runner variant names its own).
        self.contact_ref = contact_ref
        #: slide | runner (RUNNING_GEAR) — how the cantilever moment is carried.
        self.running_gear = running_gear
        self.notes = notes
