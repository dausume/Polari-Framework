"""
@module hwnocode.custom.temp_analysis

TEMP-ANALYSIS (fs-1, DEMONSTRABLES_PLAN.md §9 migration): a PLAIN backend `SolutionDefinition` (object `temp-analysis`,
category '' — ordinary compute, never cross-domain) holding the moving-average/threshold math that used to sit INLINE
on `uno-temp-split`'s own canvas (his message: "this seems to more so be a Cross-Domain Solution" read literally — the
split MOVES the compute out, the math itself is UNCHANGED): on-temp (entry marker) -> moving-avg (AnalysisCall,
`hwnocode-temp-derive`, unchanged) -> over? (ConditionalChain, unchanged) -> flag-on/flag-off (VariableAssignment,
unchanged) -> commit (StateChangeCommit onto SimRigTempDerived, unchanged).

Invoked FROM `uno-temp-split`'s "call temp-analysis" state (a `SolutionInvocation`, `polariNoCode.graph_builder.invoke`
— the engine's existing solution-as-state seam, P3): the caller maps its OWN context (the frame's `instance.*` fields
plus the window/threshold_c/keep knobs) onto this solution's flat input params (`object`, `temp_c`, `uptime_ms`,
`window`, `threshold_c`, `keep`, `solution`) — a SolutionInvocation callee's context holds ONLY its mapped inputs (the
abstraction boundary the engine itself enforces), so every value source here reads a FLAT top-level var, never
`instance.*` (that nesting was uno-temp-split's own trigger-payload shape, not this solution's).
"""
from polariNoCode import graph_builder as GB

NAME = 'temp-analysis'
ANALYSIS = 'hwnocode-temp-derive'

STATE_PURPOSES = {
    'on-temp': 'Entry: receives one frame\'s temp_c + uptime_ms (mapped in by the caller\'s SolutionInvocation) — a '
               'plain pass-through marker, no compute of its own.',
    'moving-avg': 'The backend analysis: the moving average of temp_c over the trigger\'s window.',
    'over?': 'The threshold check: is the moving average over threshold_c?',
    'flag-on': 'Sets the LED command on, because the average is over the threshold.',
    'flag-off': 'Sets the LED command off, because the average is at or under the threshold.',
    'commit': 'Commits temp_avg and over_threshold onto SimRigTempDerived — read back by uno-temp-split\'s Bridge to '
              'relay the command down to the device.',
}

_LAYOUT = {
    'on-temp':    {'x': 80,   'y': 80, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'temp_c received'},
    'moving-avg': {'x': 320,  'y': 80, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'Moving average (temp_avg)'},
    'over?':      {'x': 560,  'y': 80, 'shape': 'diamond',   'color': '#4CAF50', 'label': 'Over threshold?'},
    'flag-on':    {'x': 800,  'y': -20, 'shape': 'rectangle', 'color': '#4CAF50', 'label': 'Flag on'},
    'flag-off':   {'x': 800,  'y': 180, 'shape': 'rectangle', 'color': '#F44336', 'label': 'Flag off'},
    'commit':     {'x': 1040, 'y': 80, 'shape': 'rectangle', 'color': '#FF9800', 'label': 'Commit SimRigTempDerived'},
}


def _lay_out(definition):
    """Same convention as hwnocode.custom.solutions._lay_out (positions/shape/size fields the Angular canvas reads,
    a plain-words purpose, connector id/slot indices the renderer needs) — duplicated in miniature rather than
    imported, since temp-analysis's own layout is a different shape (a straight pipeline, no hardware column)."""
    for s in definition.get('stateInstances') or []:
        name = s.get('stateName')
        spot = _LAYOUT.get(name, {'x': 80, 'y': 80, 'shape': 'rectangle', 'color': '#9E9E9E', 'label': name or ''})
        s['stateLocationX'], s['stateLocationY'] = spot['x'], spot['y']
        s['shapeType'] = s['stateSvgName'] = spot['shape']
        s['layerName'] = '%s-layer' % spot['shape']
        s['backgroundColor'] = spot['color']
        s['slotRadius'] = 5
        if spot['shape'] == 'diamond':
            s['stateSvgRadius'] = 70
            s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        else:
            s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 160, 90, 8
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
    """The six states moved out of uno-temp-split, byte-for-byte the SAME field configs (D-fs-3: the split moves,
    the math does not) — only the value sources are now flat (object/temp_c/uptime_ms/window/threshold_c/keep),
    matching what a SolutionInvocation callee actually receives."""
    n = GB.node
    entry = n('on-temp', 'BackendStateChange', {'displayName': 'temp_c received', 'modelName': 'SimRigState',
                                                'fieldName': 'temp_c', 'changeType': 'update',
                                                'description': 'entry marker: the caller already detected the frame — '
                                                               'this solution just receives its mapped inputs'},
              outs=[['moving-avg']])
    avg = n('moving-avg', 'AnalysisCall', {
        'analysis': ANALYSIS, 'resultVariable': 'temp_avg', 'pick': 'temp_avg',
        'params': {'object': GB.var_src('object'), 'uptime_ms': GB.var_src('uptime_ms'), 'temp_c': GB.var_src('temp_c'),
                   'window': GB.var_src('window'), 'keep': GB.var_src('keep'), 'solution': GB.var_src('solution')}},
        outs=[['over?']])
    over = GB.cond('over?', [GB.link(GB.var_src('temp_avg'), '>', GB.var_src('threshold_c'), display_name='average above the threshold')],
                   'flag-on', 'flag-off')
    on = n('flag-on', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                            'assignmentConfig': {'valueSource': GB.lit_src(True)}}, outs=[['commit']])
    off = n('flag-off', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                              'assignmentConfig': {'valueSource': GB.lit_src(False)}}, outs=[['commit']])
    commit = n('commit', 'StateChangeCommit', {
        'changeType': 'update', 'targetClassName': 'SimRigTempDerived', 'instanceRef': GB.var_src('object'),
        'fields': {'temp_avg': GB.var_src('temp_avg'), 'over_threshold': GB.var_src('over_threshold'),
                   'threshold_c': GB.var_src('threshold_c'), 'window': GB.var_src('window'),
                   'last_temp_c': GB.var_src('temp_c'), 'last_uptime_ms': GB.var_src('uptime_ms')}}, outs=[[]])
    return _lay_out(GB.solution(name, entry, avg, over, on, off, commit))


def contract():
    return {'description': 'temp-analysis (fs-1): a plain backend solution — the moving average of temp_c over a window, '
                           'flagged against a threshold, committed onto SimRigTempDerived. Called BY a Cross-Domain '
                           'Relay state (SolutionInvocation), never computes inline anywhere else.',
            'inputs': [{'name': 'object', 'required': True, 'description': 'the SimRigState row name to commit the verdict onto'},
                       {'name': 'temp_c', 'required': True, 'description': '°C from the TMP36 frame'},
                       {'name': 'uptime_ms', 'required': True, 'description': 'the firmware clock'},
                       {'name': 'window', 'required': False, 'description': 'samples in the moving average (knob)'},
                       {'name': 'threshold_c', 'required': False, 'description': 'the flag threshold in °C (knob)'},
                       {'name': 'keep', 'required': False, 'description': 'ring buffer depth (knob)'},
                       {'name': 'solution', 'required': False, 'description': 'the calling solution\'s name (ring bookkeeping)'}],
            'returns': [{'name': 'temp_avg', 'description': 'the moving average just computed'},
                        {'name': 'over_threshold', 'description': 'the flag verdict'}],
            'executionRights': 'invoker'}
