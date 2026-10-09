"""
@module hwnocode.custom.button_clock_ledger

button-clock-ledger (ucd-1): a PLAIN backend `SolutionDefinition` (category '' — ordinary compute, never cross-domain),
the SAME shape as `hwnocode.custom.temp_analysis` — two states: on-frame (entry marker, receives the caller's mapped
inputs) -> derive (AnalysisCall `hwnocode-button-clock-derive`, hwnocode.custom.button_clock.button_clock_derive) ->
commit (StateChangeCommit onto ButtonClockDerived with the AnalysisCall's own result bindings). Unlike temp-analysis
there is no ConditionalChain/VariableAssignment branch here: the invariant and presses_per_min are BOTH computed by
the one AnalysisCall (no threshold decision to branch on) — still bridging/relay-free compute, called OUT to by
`uno-button-clock`'s "call-button-clock-ledger" state (a SolutionInvocation), never inline on that cross-domain canvas.
"""
from polariNoCode import graph_builder as GB

NAME = 'button-clock-ledger'
ANALYSIS = 'hwnocode-button-clock-derive'

STATE_PURPOSES = {
    'on-frame': 'Entry: receives one ButtonClockState frame\'s board_instance (mapped in by the caller\'s '
               'SolutionInvocation) — a plain pass-through marker, no compute of its own.',
    'derive': 'The backend analysis: presses_per_min over the last minute of the device\'s own clock, and the '
             'sense_rises/sense_falls/button_presses/led_on invariant (UNO_CORE_DEMO_PLAN.md §1), named on a break.',
    'commit': 'Commits board_instance, presses_per_min, invariant_ok/why, events_seen, dropped_events_total, '
             'last_sync_generation and drift_ms onto ButtonClockDerived — read back by /display/uno-core-demo.',
}

_LAYOUT = {
    'on-frame': {'x': 80,  'y': 80, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'ButtonClockState frame received'},
    'derive':   {'x': 400, 'y': 80, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'Derive (presses/min + invariant)'},
    'commit':   {'x': 720, 'y': 80, 'shape': 'rectangle', 'color': '#FF9800', 'label': 'Commit ButtonClockDerived'},
}


def _lay_out(definition):
    """Same convention as hwnocode.custom.solutions._lay_out / temp_analysis._lay_out (the canvas fields the Angular
    rendering actually reads — positions/shape/size, a lane colour, a plain-words purpose, connector id/slot indices)."""
    for s in definition.get('stateInstances') or []:
        name = s.get('stateName')
        spot = _LAYOUT.get(name, {'x': 80, 'y': 80, 'shape': 'rectangle', 'color': '#9E9E9E', 'label': name or ''})
        s['stateLocationX'], s['stateLocationY'] = spot['x'], spot['y']
        s['shapeType'] = s['stateSvgName'] = spot['shape']
        s['layerName'] = '%s-layer' % spot['shape']
        s['backgroundColor'] = spot['color']
        s['slotRadius'] = 5
        s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 200, 90, 8
        s['stateSvgRadius'] = None
        s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        fields = dict(s.get('boundObjectFieldValues') or {})
        fields.setdefault('displayName', spot['label'])
        fields.setdefault('purpose', STATE_PURPOSES.get(name, ''))
        s['boundObjectFieldValues'] = fields
    next_id = 1
    for s in definition.get('stateInstances') or []:
        for i, slot in enumerate(s.get('slots') or []):
            slot['index'] = i
            for c in slot.get('connectors') or []:
                c['id'] = next_id
                c['sourceSlot'] = i
                c['sinkSlot'] = 0
                next_id += 1
    return definition


def definition(name=NAME):
    n = GB.node
    entry = n('on-frame', 'BackendStateChange', {'displayName': 'ButtonClockState frame received', 'modelName': 'ButtonClockState',
                                                 'fieldName': 'seq', 'changeType': 'update',
                                                 'description': 'entry marker: the caller already detected the frame — '
                                                                'this solution just receives its mapped inputs'},
              outs=[['derive']])
    derive = n('derive', 'AnalysisCall', {
        'analysis': ANALYSIS, 'resultVariable': 'derived', 'pick': '',
        'params': {'board_instance': GB.var_src('board_instance'), 'object': GB.var_src('object'), 'solution': GB.var_src('solution')}},
        outs=[['commit']])
    commit = n('commit', 'StateChangeCommit', {
        'changeType': 'update', 'targetClassName': 'ButtonClockDerived', 'instanceRef': GB.var_src('board_instance'),
        'fields': {'board_instance': GB.var_src('board_instance'), 'presses_per_min': GB.var_src('presses_per_min'),
                   'invariant_ok': GB.var_src('invariant_ok'), 'invariant_why': GB.var_src('invariant_why'),
                   'events_seen': GB.var_src('events_seen'), 'dropped_events_total': GB.var_src('dropped_events_total'),
                   'last_sync_generation': GB.var_src('last_sync_generation'), 'drift_ms': GB.var_src('drift_ms')}}, outs=[[]])
    return _lay_out(GB.solution(name, entry, derive, commit))


def contract():
    return {'description': 'button-clock-ledger (ucd-1): a plain backend solution — presses_per_min over the device\'s '
                           'own clock and the sense/press/LED invariant (UNO_CORE_DEMO_PLAN.md §1), committed onto '
                           'ButtonClockDerived. Called BY a Cross-Domain Relay state (SolutionInvocation), never '
                           'computes inline anywhere else.',
            'inputs': [{'name': 'board_instance', 'required': True, 'description': 'the ButtonClockState row name to read and commit the verdict onto'},
                       {'name': 'object', 'required': False, 'description': 'the trigger payload\'s row name (same as board_instance)'},
                       {'name': 'solution', 'required': False, 'description': 'the calling solution\'s name (bookkeeping)'}],
            'returns': [{'name': 'presses_per_min', 'description': 'presses in the last minute of the device\'s own clock'},
                        {'name': 'invariant_ok', 'description': 'sense_rises + sense_falls == button_presses and led_on == (sense_rises > sense_falls)'},
                        {'name': 'invariant_why', 'description': 'plain words naming the numbers, always, not only on a break'}],
            'executionRights': 'invoker'}
