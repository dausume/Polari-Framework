"""
@module cmod.cmod_basis

The INDEX of the C-modularization rows (C_MODULARIZATION_PLAN.md §2). Classes live one-per-file under objects/cmod/; this
file re-exports them and holds the class list the server registers.
"""
from cmod.objects.cmod import (CProject, CModule, CFunctionAtom, CPort, CGraph, CGraphNode, CGraphEdge, CGlueBuild,  # noqa: F401
                               TargetDefinition, CapabilityDefinition, CapabilityInstance,
                               FirmwareSolution, ScheduleSlot, RegisterAssignment, PinClaim, PeripheralClaim,
                               HardwareBinding, DerivedOverride, CIsotope,
                               PurposeObservation, PurposeGoalState, PurposeDependsState, PurposeParticipantState, PurposeTriggerState, PurposeOutcomeState, PurposeCriterionState, PurposeObservesState, PurposeTasksState, PurposeProofState, PurposeResolutionState, PurposeObservedState,
                               HardwareMission, MissionGoalState, MissionSettingsState, MissionPurposeState, MissionParticipantState, MissionConstraintState, MissionResolutionState,
                               AtomJob, IsotopeVariant, SolveRun,
                               TaskDefinition, TaskTrigger, TaskStructBinding, TaskPlan,
                               CatomAssertion, StructObjectMap, CatomVariable)

#: every row class of the module, in registration order (cmod-0: the atoms; cmod-1: graphs over them + the generated glue;
#: demo-4: target/capability definitions derived over a graph's nodes/ports; fs-0: a FirmwareSolution over a graph + a
#: board, its DERIVED schedule (D-fs-1) and register map (D-fs-2) — DEMONSTRABLES_PLAN.md §9)
from cmod.objects.cmod.FirmwareExport import FirmwareExport  # noqa: F401  (ucd-0f: the export record)

CMOD_CLASSES = [CProject, CModule, CFunctionAtom, CPort, CGraph, CGraphNode, CGraphEdge, CGlueBuild,
               TargetDefinition, CapabilityDefinition, CapabilityInstance,
               FirmwareSolution, ScheduleSlot, RegisterAssignment,
                FirmwareExport, PinClaim, PeripheralClaim,
                HardwareBinding,  # ucd-0b2b: the hardware-specific mask laying a solution over one board
                DerivedOverride,  # ucd-attest: a person's own correction of one derived field, kept beside it
                CIsotope,  # ucd-iso-0: a C-atom's code interface variant, already carrying one binding's own values
                # fgm-1: what one deployed board does for one Purpose, and the eleven node kinds a Purpose is DRAWN with
                PurposeObservation, PurposeGoalState, PurposeDependsState, PurposeParticipantState, PurposeTriggerState, PurposeOutcomeState, PurposeCriterionState, PurposeObservesState, PurposeTasksState, PurposeProofState, PurposeResolutionState, PurposeObservedState,
                # mis-0: the Hardware Mission above the Purposes, and the six node kinds a Mission is DRAWN with
                HardwareMission, MissionGoalState, MissionSettingsState, MissionPurposeState, MissionParticipantState, MissionConstraintState, MissionResolutionState,
                # iso-0: the jobs a C atom does and every way (route) of doing each
                AtomJob, IsotopeVariant,
                # sol-0: one run of the attempt engine, its inputs fingerprinted
                SolveRun,
                # fgm-3: the Task Plan of a Mission on one Hardware System, derived and editable
                TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding,
                # hsp-3a: what a catom asserts it does to a struct / a bridge (verified by a twin record), and the struct -> Polari class map (D-hsp-8)
                CatomAssertion, StructObjectMap,
                # hsp-3d: Catom variables = the generalized HAL (a named value that is also a defines-role assertion, checked before it counts)
                CatomVariable]

#: the eleven Purpose node kinds (the canvas palette learns them as data via /stateSpaceClasses)
PURPOSE_NODE_KIND_CLASSES = [PurposeGoalState, PurposeDependsState, PurposeParticipantState, PurposeTriggerState, PurposeOutcomeState, PurposeCriterionState, PurposeObservesState, PurposeTasksState, PurposeProofState, PurposeResolutionState, PurposeObservedState]

#: the six Mission node kinds (the canvas palette learns them as data via /stateSpaceClasses)
MISSION_NODE_KIND_CLASSES = [MissionGoalState, MissionSettingsState, MissionPurposeState, MissionParticipantState, MissionConstraintState, MissionResolutionState]
