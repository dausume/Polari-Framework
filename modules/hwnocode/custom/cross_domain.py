"""
@module hwnocode.custom.cross_domain

CROSS-DOMAIN SOLUTIONS (fs-0/fs-2, DEMONSTRABLES_PLAN.md §9; D-fs-3 ruled "go with your picks": bridging/relay ONLY,
no compute — "even a one-line conversion required to live in a backend solution the Relay state calls"). A
`SolutionDefinition` is a Cross-Domain Solution when its `category` field is 'cross-domain'; its states may ONLY be
one of the kinds below — a plain function of the EXISTING engine node kinds + fs-0's new `FirmwareRunState`, never a
new row. `validate()` refuses and NAMES the first offending state — never a silent pass.

fs-1 (the uno-temp-split migration, DEMONSTRABLES_PLAN.md §9 "Migration of uno-temp-split"): the "call temp-analysis"
reference is `SolutionInvocation` (`polariNoCode.graph_builder.invoke` — the engine's OWN "solution-as-state
composition" seam, P3, already proven elsewhere — not a new kind). It is bridging, never compute: the Relay state
calls OUT, the compute runs inside the CALLEE's own (plain backend) SolutionDefinition, never inline here.
`AnalysisCall` stays allowed too (fs-0's original provision) for a future Cross-Domain solution that calls out to a
registered analysis function directly rather than another SolutionDefinition — uno-temp-split itself uses
SolutionInvocation.
"""

#: the four categories his message names, mapped onto EXISTING engine node kinds (reused, never duplicated) + fs-0's
#: new FirmwareRunState (the ONLY new kind this arc adds)
FIRMWARE_RUN_KINDS = {'FirmwareRunState', 'firmware-run'}
BRIDGE_KINDS = {'HardwareInterface', 'hw-interface'}
RELAY_KINDS = {'BackendStateChange', 'StateChangeCommit'}
API_CALL_KINDS = {'AnalysisCall'}          # reused ONLY as an outbound call to another (compute-holding) solution —
                                           # see NOTE below; never evaluated inline by a Cross-Domain solution itself
SUB_SOLUTION_KINDS = {'SolutionInvocation'}  # fs-1: "call temp-analysis" — the engine's own solution-as-state seam
FRONTEND_EMIT_KINDS = {'EmitFrontendEvent'}

ALLOWED_KINDS = FIRMWARE_RUN_KINDS | BRIDGE_KINDS | RELAY_KINDS | API_CALL_KINDS | SUB_SOLUTION_KINDS | FRONTEND_EMIT_KINDS

#: kinds that ARE compute — explicitly named so a refusal reads as a rule, not a guess
COMPUTE_KINDS = {'ConditionalChain', 'VariableAssignment', 'MatrixEquationOperation', 'EquationEvaluate', 'FilterChainApply'}


#: slice ucd-app: category 'hardware-app' (the native Hardware App's no-code definition) — same posture, no compute; its states
#: may only be steps of the native JavaFX shell (runtime javafx-native) or the Java bridge (runtime java-bridge)
HARDWARE_APP_CATEGORY = 'hardware-app'
NATIVE_KINDS = {'NativeAppStep'}
HARDWARE_APP_KINDS = NATIVE_KINDS | BRIDGE_KINDS


#: fgm-1: category 'purpose' (a Purpose drawn in no-code, cmod.custom.purpose_nocode) - DECLARATIVE: its states may only be the
#: eleven Purpose kinds (class name and node kind both accepted); every compute or runtime kind is refused by name
PURPOSE_CATEGORY = 'purpose'
PURPOSE_KINDS = {'PurposeGoalState', 'PurposeDependsState', 'PurposeParticipantState', 'PurposeTriggerState', 'PurposeOutcomeState',
                 'PurposeCriterionState', 'PurposeObservesState', 'PurposeTasksState', 'PurposeProofState', 'PurposeResolutionState',
                 'PurposeObservedState', 'purpose-goal', 'purpose-depends', 'purpose-participant', 'purpose-trigger', 'purpose-outcome',
                 'purpose-criterion', 'purpose-observes', 'purpose-tasks', 'purpose-proof', 'purpose-resolution', 'purpose-observed'}
#: runtime kinds of the other categories - named so a refusal reads as a rule
RUNTIME_KINDS = FIRMWARE_RUN_KINDS | BRIDGE_KINDS | RELAY_KINDS | API_CALL_KINDS | SUB_SOLUTION_KINDS | FRONTEND_EMIT_KINDS | {'NativeAppStep'}


def validate(definition, category='cross-domain'):
    """(ok, why) for ONE SolutionDefinition's parsed `definition` dict (graph_builder shape: {'stateInstances': [...]})
    — refuses the FIRST state whose `stateClass` is not in ALLOWED_KINDS, naming it (his rule: "bridging ... relay
    specifications only"). An AnalysisCall is allowed ONLY as the outbound call a Relay makes to a backend solution
    (fs-0 cannot yet distinguish "calls out" from "computes inline" structurally — both are the same node kind — so
    this is stated as the category's rule, enforced here at the node-kind level: no ConditionalChain/VariableAssignment/
    equation-evaluating kind may ever appear, full stop). `category='hardware-app'` (ucd-app) holds the same posture for the
    Hardware App: native-shell steps (javafx-native) and bridge states (java-bridge) only; compute refused by name."""
    allowed, label = ALLOWED_KINDS, 'Cross-Domain'
    if category == PURPOSE_CATEGORY:
        for s in (definition or {}).get('stateInstances', []):
            kind = s.get('stateClass', '')
            if kind in COMPUTE_KINDS or kind in RUNTIME_KINDS:
                return False, ('refused: state %r is %s, a %s kind - a Purpose drawing is a declaration, never executed; it holds '
                               'Purpose states only' % (s.get('stateName', ''), kind, 'compute' if kind in COMPUTE_KINDS else 'runtime'))
            if kind not in PURPOSE_KINDS:
                return False, 'refused: state %r is %s, not one of the Purpose kinds (%s)' % (s.get('stateName', ''), kind, ', '.join(sorted(k for k in PURPOSE_KINDS if k[0] == 'P')))
        return True, 'ok: every state is a Purpose kind (declarative, never executed)'
    if category == HARDWARE_APP_CATEGORY:
        allowed, label = HARDWARE_APP_KINDS, 'Hardware App'
    for s in (definition or {}).get('stateInstances', []):
        kind = s.get('stateClass', '')
        if kind in COMPUTE_KINDS:
            return False, ('refused: state %r is %s — a %s Solution holds %s only; compute belongs in a backend '
                           'SolutionDefinition it calls OUT to' % (
                               s.get('stateName', ''), kind, label,
                               'native-shell steps and bridge states' if allowed is HARDWARE_APP_KINDS else
                               'bridging/relay states (Firmware Run, Bridge, Relay, API call, Frontend emit)'))
        if kind not in allowed:
            return False, ('refused: state %r is %s, not one of the %s kinds (%s)'
                           % (s.get('stateName', ''), kind, label, ', '.join(sorted(allowed))))
    return True, 'ok: every state is a %s kind (%s)' % ('native-shell/bridge' if allowed is HARDWARE_APP_KINDS else 'bridging/relay',
                                                      ', '.join(sorted(allowed)))
