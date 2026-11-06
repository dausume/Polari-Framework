"""
@module mech.objects.assembly.MechJoint

Row class MechJoint of the mech module — one class per file (design §7); mxc-2.
The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.assembly._shared import JOINT_KINDS

class MechJoint(treeObject):
    """A THIN row over composition.InterfaceDefinition (D-mxc-8):
    the joint KIND, feature pair, limits, ratio and preload live
    here; the boundary itself (members, separability, DOF removed,
    retention, failure modes) lives on the interface this row points
    at. The free DOF here is the exact complement of the interface's
    dof_removed_json, and mech.custom.joint_interface is the ONE
    writer that keeps them so."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', kind='fixed',
                 instance_a='', feature_a='', instance_b='',
                 feature_b='', interface_ref='', dof_json='',
                 limits_json='{}', ratio=0.0, preload_json='{}',
                 fastener_refs_json='[]', valid=True, invalid_reason='',
                 notes='', is_prior=True, provenance_id='',
                 manager=None):
        self.name = name
        self.assembly_ref = assembly_ref
        #: JOINT_KINDS — FreeCAD's JointTypes + 'grid'.
        self.kind = kind if kind in JOINT_KINDS else 'fixed'
        #: The two MechPartInstance names and the MechFeature (by
        #: NAME, '<variant>:<feature>') on each that mate: the key
        #: must match and the roles must pair (plan §3.2).
        self.instance_a = instance_a
        self.feature_a = feature_a
        self.instance_b = instance_b
        self.feature_b = feature_b
        #: composition.InterfaceDefinition this joint creates/updates.
        self.interface_ref = interface_ref
        #: JSON list of free axes in the JOINT frame (subset of
        #: DOF_AXES); '' = the kind's default (JOINT_DOF); '[]' = an
        #: explicit NONE (a grid seat held by magnets).
        self.dof_json = dof_json
        #: {length_min, length_max (mm), angle_min, angle_max (deg)}
        #: — FreeCAD's joint limits, 1:1.
        self.limits_json = limits_json
        #: screw pitch (mm/rev), gear or belt ratio, rack mm/rev;
        #: 0 = not a coupled joint.
        self.ratio = ratio
        #: {torque_nm, clamp_n, basis} — the tightening state of a
        #: fastened joint; basis names the table or measurement.
        self.preload_json = preload_json
        #: MechPartInstance names (quantity_role 'fastener') that
        #: REALISE this joint: [screw, T-nut]. One fastener = a pivot
        #: held in rz by friction only (dof_solver says so); two at
        #: distinct positions fix the body. Decides retention
        #: 'fastener' on the interface.
        self.fastener_refs_json = fastener_refs_json
        #: Set by the checks: key/role pairing, fastener presence,
        #: resolvable instances. invalid_reason says WHICH.
        self.valid = valid
        self.invalid_reason = invalid_reason
        self.notes = notes
        self.is_prior = is_prior
        self.provenance_id = provenance_id
