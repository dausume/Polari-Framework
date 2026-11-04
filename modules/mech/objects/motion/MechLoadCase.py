"""
@module mech.objects.motion.MechLoadCase

Row class MechLoadCase of the mech module — one class per file (design §7).
MECH_FREECAD_INTERCHANGE_PLAN §3.5: the loads on an assembly for one
scenario (e.g. a drawer with 8 bins × 180 g on their grid cells).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechLoadCase(treeObject):
    """What is loaded onto an assembly, instance by instance, and the
    resultant the engine derives from it (total mass, normal force, the
    moment about the driven joint). The resultant is COMPUTED by
    mech.custom.motion_runs.resultant — never typed in."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', loads_json='[]',
                 resultant_json='{}', notes='', manager=None):
        self.name = name
        #: MechAssembly name the loads sit on.
        self.assembly_ref = assembly_ref
        #: JSON list of {instance, kind: mass | force | pressure, value,
        #: point_json {x_mm, y_mm, z_mm[, area_m2]}, basis}. `value` is kg
        #: for mass, N for force, Pa for pressure (needs area_m2). x_mm is
        #: measured along the joint's free axis from the cabinet front
        #: edge (closed position): negative = inside the cabinet.
        self.loads_json = loads_json
        #: JSON dict written by resultant(): {total_mass_kg, total_force_n,
        #: moment_nm_closed, moment_nm_full, basis}.
        self.resultant_json = resultant_json
        self.notes = notes
