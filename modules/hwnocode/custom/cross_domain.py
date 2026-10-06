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


def validate(definition):
    """(ok, why) for ONE SolutionDefinition's parsed `definition` dict (graph_builder shape: {'stateInstances': [...]})
    — refuses the FIRST state whose `stateClass` is not in ALLOWED_KINDS, naming it (his rule: "bridging ... relay
    specifications only"). An AnalysisCall is allowed ONLY as the outbound call a Relay makes to a backend solution
    (fs-0 cannot yet distinguish "calls out" from "computes inline" structurally — both are the same node kind — so
    this is stated as the category's rule, enforced here at the node-kind level: no ConditionalChain/VariableAssignment/
    equation-evaluating kind may ever appear, full stop)."""
    for s in (definition or {}).get('stateInstances', []):
        kind = s.get('stateClass', '')
        if kind in COMPUTE_KINDS:
            return False, ('refused: state %r is %s — a Cross-Domain Solution holds bridging/relay states only '
                           '(Firmware Run, Bridge, Relay, API call, Frontend emit); compute belongs in a backend '
                           'SolutionDefinition a Relay state calls OUT to' % (s.get('stateName', ''), kind))
        if kind not in ALLOWED_KINDS:
            return False, ('refused: state %r is %s, not one of the Cross-Domain kinds (%s)'
                           % (s.get('stateName', ''), kind, ', '.join(sorted(ALLOWED_KINDS))))
    return True, 'ok: every state is a bridging/relay kind (%s)' % ', '.join(sorted(ALLOWED_KINDS))
