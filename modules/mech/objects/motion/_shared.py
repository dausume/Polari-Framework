"""@module mech.objects.motion._shared — what the motion rows share (vocabularies). MECH_FREECAD_INTERCHANGE_PLAN §3.5, slice mxc-4."""

#: How a MechMotionCase drives its joint. `position` / `velocity` are
#: kinematic (the FreeCAD Motion object can run them too); `force` is
#: dynamic and only Polari's engine answers it (D-mxc-4).
DRIVE_KINDS = ('position', 'velocity', 'force')

#: Signals a MechMotionVector may carry — one named series each,
#: extracted from the MechMotionSimState rows of a run.
SIGNALS = ('position_mm', 'angle_rad', 'velocity_mm_s', 'velocity_rad_s',
           'accel_mm_s2', 'accel_rad_s2', 'pull_n', 'torque_nm',
           'friction_n', 'normal_n', 'side_force_n', 'tip_moment_nm',
           'power_w', 'deflection_mm')

#: Check names a MechMotionCase.checks_json entry may use. Every check
#: carries a `knob` (its threshold) — a knob is a declared assumption
#: until a measured run replaces it. `deflection` is NAMED here so a
#: run can report it, but the number comes from a FEMModelDefinition
#: executed by materialsScience's fem_engine, never from mech (D-mxc-7).
CHECK_KINDS = ('opens fully', 'smooth', 'no bind', 'hand effort',
               'stays closed', 'deflection')

#: Engines a MechMotionRun may name. `polari` = the 1-DOF integrator in
#: mech.custom.motion_engine (dynamics); `freecad_motion` = FreeCAD's
#: Assembly Simulation Motion object (kinematics only — position formula).
ENGINE_KINDS = ('polari', 'freecad_motion')

#: Load kinds in MechLoadCase.loads_json.
LOAD_KINDS = ('mass', 'force', 'pressure')

#: Running gear a motion case models between the joint's two bodies.
#: `slide` — a telescoping slide carries the cantilever moment in its
#: tracks (normal force constant, tip moment reported against the rating);
#: `runner` — a fixed runner (legacy wooden drawer) carries it as a
#: couple at the cabinet edge, so the normal force (and the friction)
#: GROWS with extension: N(x) = W + 2·M(x)/overlap(x).
RUNNING_GEAR = ('slide', 'runner')

#: The SimulationDefinition every polari motion run is a SimulationRun of.
MOTION_SIM_DEF = 'mech-motion-1dof'
