"""
@module mech.mech_assembly_basis

mxc-2 (MECH_FREECAD_INTERCHANGE_PLAN §3.4, §9.1, D-mxc-8): the
ASSEMBLY GRAPH as data — instances (placed catalogue variants),
joints (FreeCAD's joint kinds + Gridfinity 'grid'), contacts (where
friction lives) and conflicts (what the fit checks found).

The ruling that shapes every row here: mech EXTENDS composition.
  MechAssembly.node_ref      -> composition.CompositionNode (members =
                                the BOM; there is NO BOM row in mech)
  MechPartInstance.component_ref -> composition.PartComponentDefinition
                                (material + shape live there)
  MechJoint.interface_ref    -> composition.InterfaceDefinition —
                                the joint is THIN: kind, feature pair,
                                limits, ratio, preload here; members,
                                separability, dof_removed, retention,
                                failure modes THERE. free DOF ==
                                complement(dof_removed), and
                                custom/joint_interface.py is the one
                                writer keeping both sides equal.
  MechConflict               = fit checks only; failure MODES stay
                                composition.FailureModeDefinition.

Honesty pinned here so it travels on every payload:
- the DOF solver is a Grübler/Kutzbach COUNT per body, not a rank
  test: it cannot see parallel axes, geometric singularities, or
  a single-slide drawer's droop (custom/dof_solver.py says so);
- thread-engagement factors and friction values are KNOBS with a
  stated basis until a measurement replaces them;
- a single fastener is a pivot: it fixes five DOF; the sixth (rz
  about the screw) is friction-held and reported as under-constraint.

@consumers mech.custom.dof_solver, mech.custom.fit_checks,
mech.custom.joint_interface, mech.mech_assembly_seed, polariServer
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/assembly/;
# this file re-exports them (imports keep working) and holds what they share.

from objectTreeDecorators import treeObject, treeObjectInit  # noqa: F401

from mech.objects.assembly._shared import (  # noqa: F401
    ASSEMBLY_KINDS, CONFLICT_KINDS, CONFLICT_SEVERITIES, CONTACT_KINDS,
    DOF_AXES, INSTANCE_ROLES, JOINT_COUPLING, JOINT_DOF, JOINT_KINDS,
    MOTION_KINDS, ROLE_PAIRS, complement, joint_free_axes, loads,
    roles_pair,
)
from mech.objects.assembly.MechAssembly import MechAssembly  # noqa: F401
from mech.objects.assembly.MechPartInstance import MechPartInstance  # noqa: F401
from mech.objects.assembly.MechJoint import MechJoint  # noqa: F401
from mech.objects.assembly.MechContact import MechContact  # noqa: F401
from mech.objects.assembly.MechConflict import MechConflict  # noqa: F401
