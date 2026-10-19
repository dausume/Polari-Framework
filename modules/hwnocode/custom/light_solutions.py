"""
@module hwnocode.custom.light_solutions

THE LIGHT TEST's two solutions (slice ucd-light, UNO_CORE_DEMO_PLAN.md §5i), built from the same pieces uno-button-clock
and uno-temp-split use — nothing new in kind:

  uno-light     the Cross-Domain Solution (category 'cross-domain'): Firmware Run (the Firmware Solution uno-light) -> Bridge
                (uno-light-bridge, the board's serial link) -> Relay in (a LightState frame arrived: the row is upserted, latest)
                -> Relay out (the on/off command goes down). Bridging/relay states only; no backend ledger, no analysis.
  light-toggle  a plain backend SolutionDefinition: the screen's button. Run it and the light's state on the LightState row is
                flipped (a ConditionalChain picks the new value, one StateChangeCommit writes led_on). The wire's led_on is
                also the command field, so the write is what asks the board to switch the light.
"""
import json

from polariNoCode import graph_builder as GB
from hwnocode.custom import solutions as S

LIGHT_SOLUTION = 'uno-light'
TOGGLE_SOLUTION = 'light-toggle'
LIGHT_FIRMWARE_SOLUTION = 'uno-light'          # cmod FirmwareSolution (built: cmod_seed)
LIGHT_BRIDGE = 'uno-light'                     # grpcbridge.mapping_basis.LIGHT_BRIDGE
LIGHT_OBJECT_CLASS = 'LightState'
LIGHT_OBJECT_NAME = 'uno-light'                # the Push match key: one row, the board's latest state
LIGHT_BINDING = '%s/%s/0' % (LIGHT_BRIDGE, LIGHT_OBJECT_CLASS)
LIGHT_TWIN_LINK = '/tmp/polari-uno-light-twin-uart'   # its OWN pty — never shares another demo's twin link
LIGHT_DISPLAY = 'uno-core-demo'


def light_route():
    """The hardware-or-twin route (solutions.ROUTE, read once there), with this demo's own twin pty."""
    r = dict(S.ROUTE)
    if r.get('interface_kind') == 'twin-pty':
        r = dict(r, board_instance='twin:arduino-uno-r3#0', port=LIGHT_TWIN_LINK)
    return r


STATE_PURPOSES = {
    'firmware-run': 'Takes the Firmware Solution uno-light (the light, the button, the serial link) and runs it on the '
                    'board or on its simulated twin.',
    'uno-light-bridge': 'The serial link between the board and Polari: the one place the light\'s state crosses from the '
                        'board to the backend and the on/off command crosses back.',
    'relay-in': 'Bridging only: a new LightState frame arrived (the light changed, or a regular report) — the latest '
                'state is written onto the LightState row. Nothing is computed here.',
    'relay-out': 'Bridging only: when led_on on the LightState row is changed from a screen, the command rides the same '
                 'link down to the board, which switches the light.',
}

_LAYOUT = {
    'firmware-run':     {'x': 80,  'y': 560, 'color': '#4527A0', 'label': 'Firmware Run (uno-light)'},
    'uno-light-bridge': {'x': 320, 'y': 560, 'color': '#6D4C41', 'label': 'uno-light-bridge (serial link)'},
    'relay-in':         {'x': 560, 'y': 560, 'color': '#1565C0', 'label': 'Relay in: light state up'},
    'relay-out':        {'x': 800, 'y': 560, 'color': '#FF9800', 'label': 'Relay out: on/off command down'},
}


def _detail_refs():
    return {
        'firmware-run': {'class': 'FirmwareSolution', 'name': LIGHT_FIRMWARE_SOLUTION, 'route': '/display/firmware?solution=%s' % LIGHT_FIRMWARE_SOLUTION},
        'uno-light-bridge': {'class': 'HardwareInterfaceBinding', 'name': LIGHT_BINDING, 'route': '/display/hardware-chain'},
        'relay-in': {'class': 'LightState', 'name': LIGHT_OBJECT_NAME, 'route': '/display/%s' % LIGHT_DISPLAY},
        'relay-out': {'class': 'WireContract', 'name': '%s@%s' % (LIGHT_OBJECT_CLASS, LIGHT_BRIDGE), 'route': '/display/hardware-chain',
                      'why': 'the led_on field of LightState is also the on/off command'},
    }


def _lay_out(definition):
    refs = _detail_refs()
    for s in definition.get('stateInstances') or []:
        name = s.get('stateName')
        spot = _LAYOUT.get(name, {'x': 80, 'y': 80, 'color': '#9E9E9E', 'label': name or ''})
        s['stateLocationX'], s['stateLocationY'] = spot['x'], spot['y']
        s['shapeType'] = s['stateSvgName'] = 'rectangle'
        s['layerName'] = 'rectangle-layer'
        s['backgroundColor'] = spot['color']
        s['slotRadius'] = 5
        s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 170, 90, 8
        s['stateSvgRadius'] = None
        s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        fields = dict(s.get('boundObjectFieldValues') or {})
        fields.setdefault('displayName', spot['label'])
        fields.setdefault('purpose', STATE_PURPOSES.get(name, ''))
        fields['detail_ref'] = refs.get(name, {})
        if name == 'uno-light-bridge':   # ucd-app: the interconnect with the Hardware App, as data (it links back)
            fields['links'] = [{'label': 'The Hardware App that runs this bridge', 'route': '/display/hardware-solutions?solution=uno-light-app'}]
        s['boundObjectFieldValues'] = fields
    return S._wire_connectors(definition)


def light_definition(name=LIGHT_SOLUTION):
    """uno-light: Firmware Run -> Bridge -> Relay in -> Relay out, as ONE graph_builder definition."""
    n = GB.node
    r = light_route()
    run = n('firmware-run', 'FirmwareRunState', {'firmware_solution': LIGHT_FIRMWARE_SOLUTION, 'board_variable': S.BOARD,
                                                 'mode': r['mode']}, outs=[['uno-light-bridge']])
    hwi = n('uno-light-bridge', 'HardwareInterface', {'binding': LIGHT_BINDING, 'object_class': LIGHT_OBJECT_CLASS,
                                                      'object_name': LIGHT_OBJECT_NAME, 'bridge_name': LIGHT_BRIDGE,
                                                      'board_instance': r['board_instance'], 'port': r['port'],
                                                      'interface_kind': r['interface_kind'], 'hardware_mode': r['mode'],
                                                      'route_report': r['route_report']}, outs=[['relay-in']])
    relay_in = n('relay-in', 'BackendStateChange', {'displayName': 'Relay in: light state up', 'modelName': LIGHT_OBJECT_CLASS,
                                                    'fieldName': 'seq', 'changeType': 'update',
                                                    'description': 'fires on every frame the bridge applies to the row — bridging only'},
                 outs=[['relay-out']])
    relay_out = n('relay-out', 'BackendStateChange', {'displayName': 'Relay out: on/off command down', 'modelName': LIGHT_OBJECT_CLASS,
                                                      'fieldName': 'led_on', 'changeType': 'update',
                                                      'description': 'bridging only: led_on set from a screen rides the command '
                                                                     'path down to the board'}, outs=[[]])
    return _lay_out(GB.solution(name, run, hwi, relay_in, relay_out))


def light_contract():
    return {'description': 'uno-light (Cross-Domain): Firmware Run (uno-light) -> Bridge (uno-light-bridge) -> Relay in (the '
                           'light\'s state up) -> Relay out (the on/off command down). Bridging/relay only.',
            'inputs': [{'name': 'instance.name', 'required': True, 'description': 'the LightState row'}],
            'returns': [], 'executionRights': 'definer'}


# ------------------------------------------------------------------ light-toggle: the screen's button
def toggle_definition(name=TOGGLE_SOLUTION, object_class=LIGHT_OBJECT_CLASS, command_field='led_on'):
    """Flip the light: entry marker -> ConditionalChain on the light's current state -> the opposite value -> ONE
    StateChangeCommit of led_on onto the LightState row. `object` = the row (default uno-light, the instance a run is
    started on), `led_on` = its state now (a run on the row supplies it; absent reads as off, so the light turns on).
    scl: `object_class` / `command_field` default to LightState / led_on (the definition is unchanged); board.custom.light_struct builds the same-shaped solution for ButtonClockState / set_led."""
    n = GB.node
    entry = n('toggle-requested', 'BackendStateChange', {'displayName': 'Toggle the light', 'modelName': object_class,
                                                         'fieldName': command_field, 'changeType': 'update',
                                                         'description': 'entry marker: a person asked for the light to change'},
              outs=[['light-is-on?']])
    is_on = GB.cond('light-is-on?', [GB.link(GB.var_src('led_on'), 'isTrue', GB.lit_src(True), display_name='the light is on now')],
                    'turn-off', 'turn-on')
    off = n('turn-off', 'VariableAssignment', {'variableName': 'new_led_on', 'value': '',
                                               'assignmentConfig': {'valueSource': GB.lit_src(False)}}, outs=[['flip']])
    on = n('turn-on', 'VariableAssignment', {'variableName': 'new_led_on', 'value': '',
                                             'assignmentConfig': {'valueSource': GB.lit_src(True)}}, outs=[['flip']])
    flip = n('flip', 'StateChangeCommit', {'changeType': 'update', 'targetClassName': object_class,
                                           'instanceRef': GB.var_src('object'),
                                           'fields': {command_field: GB.var_src('new_led_on')}}, outs=[[]])
    d = GB.solution(name, entry, is_on, off, on, flip)
    purposes = {'toggle-requested': 'A person asked for the light to change (this button).',
                'light-is-on?': 'Looks at whether the light is on right now.',
                'turn-off': 'The light is on, so the new value is off.', 'turn-on': 'The light is off, so the new value is on.',
                'flip': 'Writes the new on/off value onto the LightState row; the link to the board carries it down and the '
                        'board switches the light.'}
    xs = {'toggle-requested': (80, 80), 'light-is-on?': (320, 80), 'turn-off': (560, -20), 'turn-on': (560, 180), 'flip': (800, 80)}
    for s in d['stateInstances']:
        nm = s['stateName']
        x, y = xs[nm]
        s['stateLocationX'], s['stateLocationY'] = x, y
        diamond = nm == 'light-is-on?'
        s['shapeType'] = s['stateSvgName'] = 'diamond' if diamond else 'rectangle'
        s['layerName'] = '%s-layer' % s['shapeType']
        s['backgroundColor'] = '#4CAF50' if diamond else '#1565C0'
        s['slotRadius'] = 5
        if diamond:
            s['stateSvgRadius'] = 70
            s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        else:
            s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 160, 90, 8
            s['stateSvgRadius'] = None
            s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        f = dict(s.get('boundObjectFieldValues') or {})
        f.setdefault('displayName', nm)
        f.setdefault('purpose', purposes[nm])
        s['boundObjectFieldValues'] = f
    return S._wire_connectors(d)


def toggle_contract():
    return {'description': 'light-toggle: the screen\'s button for the light test. Flips led_on on the LightState row; '
                           'the same field is the on/off command, so the board follows.',
            'inputs': [{'name': 'object', 'required': False, 'description': 'the LightState row to flip (default uno-light)'},
                       {'name': 'led_on', 'required': False, 'description': 'whether the light is on now (a run on the row supplies it; absent = off)'}],
            'returns': [], 'executionRights': 'definer'}


# ------------------------------------------------------------------ light-toggle-v2: the screen's button WITH command confirmation (fgm-6a)
TOGGLE_V2_SOLUTION = 'light-toggle-v2'
TOGGLE_V2_ANALYSIS = 'board-light-v2-send'
LIGHT_V2_OBJECT_CLASS = 'LightStateV2'
LIGHT_V2_OBJECT_NAME = 'uno-light-v2'


def toggle_v2_definition(name=TOGGLE_V2_SOLUTION):
    """The v2 screen button: entry marker -> ONE AnalysisCall (`board-light-v2-send`, board.custom.light_confirm:analysis_send), which mints a
    command_id (a u16, monotonic per backend start, never the number the board last answered), writes command_id + led_on on the LightStateV2 row
    (that write rides the Commands stream down) and records a LightCommand in the ledger. The light's report that names the command confirms it
    (or a restart makes it `unknown-resend`; silence makes it `unconfirmed`) - read it on the door GET /api/board/light-v2 (`pending_command`).
    NOT seeded by default: the v1 `light-toggle` stays the screen's button until the app and the page switch."""
    n = GB.node
    entry = n('toggle-requested', 'BackendStateChange', {'displayName': 'Toggle the light (with confirmation)', 'modelName': LIGHT_V2_OBJECT_CLASS,
                                                         'fieldName': 'command_id', 'changeType': 'update',
                                                         'description': 'entry marker: a person asked for the light to change'},
              outs=[['send-command']])
    send = n('send-command', 'AnalysisCall', {'analysis': TOGGLE_V2_ANALYSIS, 'resultVariable': 'sent', 'pick': '',
                                              'params': {'object': GB.var_src('object'), 'led_on': GB.var_src('led_on')}}, outs=[[]])
    d = GB.solution(name, entry, send)
    purposes = {'toggle-requested': 'A person asked for the light to change (this button).',
                'send-command': 'Numbers the command (command_id), writes it with the new on/off value onto the LightStateV2 row, and records it. '
                                'It is DONE only when the light reports that number back from the same board start.'}
    xs = {'toggle-requested': (80, 80), 'send-command': (360, 80)}
    for s in d['stateInstances']:
        nm = s['stateName']
        s['stateLocationX'], s['stateLocationY'] = xs[nm]
        s['shapeType'] = s['stateSvgName'] = 'rectangle'
        s['layerName'] = 'rectangle-layer'
        s['backgroundColor'] = '#1565C0'
        s['slotRadius'] = 5
        s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 190, 90, 8
        s['stateSvgRadius'] = None
        s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        f = dict(s.get('boundObjectFieldValues') or {})
        f.setdefault('displayName', nm)
        f.setdefault('purpose', purposes[nm])
        s['boundObjectFieldValues'] = f
    return S._wire_connectors(d)


def toggle_v2_contract():
    return {'description': 'light-toggle-v2: the screen\'s button for the v2 light. Mints a command_id and sends SET_LED; the command is confirmed '
                           'only by a report from the light that names it (see GET /api/board/light-v2).',
            'inputs': [{'name': 'object', 'required': False, 'description': 'the LightStateV2 row (default uno-light-v2)'},
                       {'name': 'led_on', 'required': False, 'description': 'the value to set; absent = toggle'}],
            'returns': [{'name': 'command_id', 'description': 'the number the command was sent with'},
                        {'name': 'command_status', 'description': 'pending at once; confirmed / rejected-* / unknown-resend / unconfirmed later, on the door'}],
            'executionRights': 'definer'}


def toggle_v2_rows():
    """The rows that make the v2 button real - a SolutionDefinition and the AnalysisDefinition it calls - for the step that switches the app
    and the page to v2 to seed (they are NOT in definition_rows(): the v1 light-toggle stays the default)."""
    return {'solution': {'name': TOGGLE_V2_SOLUTION, 'function_name': TOGGLE_V2_SOLUTION.replace('-', '_'), 'target_runtime': 'python_backend',
                         'definition': json.dumps(toggle_v2_definition()), 'contract_json': json.dumps(toggle_v2_contract()), 'category': ''},
            'analysis': {'name': TOGGLE_V2_ANALYSIS, 'domain': 'board', 'callable_ref': 'board.custom.light_confirm:analysis_send',
                         'description': 'fgm-6a: mint a command_id and send the v2 light\'s SET_LED; record it for confirmation.',
                         'params_json': json.dumps({'object': LIGHT_V2_OBJECT_NAME, 'led_on': None}), 'enabled': True, 'is_prior': True,
                         'provenance_id': '', 'notes': ''}}


def definition_rows():
    """The two SolutionDefinition seed rows (hwnocode.custom.seed_rows appends them)."""
    return [
        {'name': LIGHT_SOLUTION, 'function_name': LIGHT_SOLUTION.replace('-', '_'), 'target_runtime': 'python_backend',
         'definition': json.dumps(light_definition()), 'contract_json': json.dumps(light_contract()), 'category': 'cross-domain'},
        {'name': TOGGLE_SOLUTION, 'function_name': TOGGLE_SOLUTION.replace('-', '_'), 'target_runtime': 'python_backend',
         'definition': json.dumps(toggle_definition()), 'contract_json': json.dumps(toggle_contract()), 'category': ''}]


def binding_row():
    r = light_route()
    return {'name': LIGHT_BINDING, 'bridge_name': LIGHT_BRIDGE, 'object_class': LIGHT_OBJECT_CLASS, 'object_name': LIGHT_OBJECT_NAME,
            'board_instance': r['board_instance'], 'board_definition': S.BOARD, 'interface_kind': r['interface_kind'],
            'interface_name': 'usart0', 'port': r['port'], 'adapter': '', 'instance_index': 0, 'wire_version': 2, 'origin': 'seeded',
            'notes': 'The light test\'s link: LightState upserted by name (the latest state of the one light), on its own twin '
                     'pty link; one instance on the bridge, so no index on the wire.'}
