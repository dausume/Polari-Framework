"""
@module hwnocode.custom.solutions

THE SPLIT-APP GRAPH (HARDWARE_NOCODE_PLAN.md §4 variant h, over the EXISTING peripheral, variant b): `uno-temp-split` drawn on the
ONE canvas as a SolutionDefinition — graph_builder shapes, the exact dicts both engines and the canvas read:

    sim-rig        HardwareSubgraph   → cmod CGraph `uno-sim-rig-graph` (UNCHANGED; byte-identical to the shipped firmware)
       │ frames
    uno-twin       HardwareInterface  → HardwareInterfaceBinding `uno-temp-split/SimRigState/0` (the split point; the twin's pty)
       │ the row changes (10 Hz)
    on-temp        BackendStateChange   SimRigState · update · temp_c
    moving-avg     AnalysisCall         `hwnocode-temp-derive`: keep the sample (ring), the moving average over `window` samples
    over?          ConditionalChain     temp_avg > threshold_c
    flag-on/-off   VariableAssignment   over_threshold = true | false
    commit         StateChangeCommit    SimRigTempDerived[uno-twin] ← temp_avg, over_threshold, last_temp_c, last_uptime_ms

Every node kind below the split already exists in the engine (no new arm). The knobs (window, threshold) ride the trigger's
inputs_json — the person's, on the EventTrigger row. The display half is /display/hardware-solutions (hwnocode_page).
"""
from polariNoCode import graph_builder as GB

SOLUTION = 'uno-temp-split'
CGRAPH = 'uno-sim-rig-graph'
BOARD = 'arduino-uno-r3'
TWIN_INSTANCE = 'twin:arduino-uno-r3#0'
BRIDGE = 'uno-temp-split'
OBJECT_CLASS = 'SimRigState'
OBJECT_NAME = 'uno-twin'
BINDING = '%s/%s/0' % (BRIDGE, OBJECT_CLASS)
TWIN_LINK = '/tmp/polari-uno-twin-uart'
ANALYSIS = 'hwnocode-temp-derive'
TRIGGER = 'uno-temp-split-on-temp'
DISPLAY = 'hardware-solutions'
GRAPH = 'hwnocode-uno-temp-split-temp'
KNOBS = {'window': 5, 'threshold_c': 25.0, 'keep': 600}


def split_app_definition(name=SOLUTION):
    """The whole graph — hardware subgraph, the split, the backend nodes — as ONE SolutionDefinition definition dict."""
    n = GB.node
    sim = n('sim-rig', 'HardwareSubgraph', {'cgraph': CGRAPH, 'board_definition': BOARD, 'board_instance': TWIN_INSTANCE,
                                            'firmware_runtime': 'bare-c'}, outs=[['uno-twin']])
    hwi = n('uno-twin', 'HardwareInterface', {'binding': BINDING, 'object_class': OBJECT_CLASS, 'object_name': OBJECT_NAME,
                                              'bridge_name': BRIDGE, 'board_instance': TWIN_INSTANCE, 'port': TWIN_LINK,
                                              'interface_kind': 'twin-pty'}, outs=[['on-temp']])
    entry = n('on-temp', 'BackendStateChange', {'displayName': 'SimRigState temp_c changed', 'modelName': OBJECT_CLASS,
                                                'fieldName': 'temp_c', 'changeType': 'update',
                                                'description': 'fires on every frame the bridge applies to the row'},
              outs=[['moving-avg']])
    avg = n('moving-avg', 'AnalysisCall', {
        'analysis': ANALYSIS, 'resultVariable': 'temp_avg', 'pick': 'temp_avg',
        'params': {'object': GB.var_src('instance.name'), 'uptime_ms': GB.var_src('instance.uptime_ms'),
                   'temp_c': GB.var_src('instance.temp_c'), 'window': GB.var_src('window'), 'keep': GB.var_src('keep'),
                   'solution': name}}, outs=[['over?']])
    over = GB.cond('over?', [GB.link(GB.var_src('temp_avg'), '>', GB.var_src('threshold_c'), display_name='average above the threshold')],
                   'flag-on', 'flag-off')
    on = n('flag-on', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                            'assignmentConfig': {'valueSource': GB.lit_src(True)}}, outs=[['commit']])
    off = n('flag-off', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                              'assignmentConfig': {'valueSource': GB.lit_src(False)}}, outs=[['commit']])
    commit = n('commit', 'StateChangeCommit', {
        'changeType': 'update', 'targetClassName': 'SimRigTempDerived', 'instanceRef': GB.var_src('instance.name'),
        'fields': {'temp_avg': GB.var_src('temp_avg'), 'over_threshold': GB.var_src('over_threshold'),
                   'threshold_c': GB.var_src('threshold_c'), 'window': GB.var_src('window'),
                   'last_temp_c': GB.var_src('instance.temp_c'), 'last_uptime_ms': GB.var_src('instance.uptime_ms')}}, outs=[[]])
    return GB.solution(name, sim, hwi, entry, avg, over, on, off, commit)


def contract():
    return {'description': 'uno-temp-split (hn-0, variant h): the UNO sim-rig subgraph → the bridge → a moving average of temp_c and '
                           'a threshold flag on SimRigTempDerived → a configured chart. The backend half runs per frame.',
            'inputs': [{'name': 'instance.name', 'required': True, 'description': 'the SimRigState row (the trigger payload)'},
                       {'name': 'instance.temp_c', 'required': True, 'description': '°C from the TMP36 frame'},
                       {'name': 'instance.uptime_ms', 'required': True, 'description': 'the firmware clock'},
                       {'name': 'window', 'required': False, 'description': 'samples in the moving average (knob)'},
                       {'name': 'threshold_c', 'required': False, 'description': 'the flag threshold in °C (knob)'}],
            'returns': [], 'executionRights': 'definer'}
