"""
@module hwnocode.custom.app_solution

THE HARDWARE APP, DEFINED IN NO-CODE (slice ucd-app, UNO_CORE_DEMO_PLAN.md §5l): the native desktop app that flashes the light
demo's firmware onto the board and then hosts the Java bridge. A `SolutionDefinition` with category 'hardware-app' whose six
states are the app's own steps, in order, every one run by the native JavaFX shell (runtime `javafx-native`):

    open-bundle -> gate -> detect-board -> flash -> host-bridge -> sync-state

Each state carries a plain-words `purpose` and the links back into the rest of the demo (the interconnect is DATA, the same
`detail_ref` + `links` idiom the cross-domain `uno-light` uses): open-bundle -> the demo page's downloads, flash -> the firmware
and its no-code, host-bridge -> the wire contract, sync-state -> the light page. The cross-domain `uno-light` links here from
its Bridge state (light_solutions._lay_out).

The state kind is `NativeAppStep` (an engine-less node kind on the canvas, mapped to the Runtime `javafx-native` by
hwnocode.custom.runtimes.runtime_for_kind) — the app's steps run in the native shell, not in the Python engine.
"""
import json

from polariNoCode import graph_builder as GB
from hwnocode.custom import solutions as S

APP_SOLUTION = 'uno-light-app'
APP_CATEGORY = 'hardware-app'
NATIVE_KIND = 'NativeAppStep'
APP_RUNTIME = 'javafx-native'
FIRMWARE_ROUTE = '/display/firmware?solution=uno-light'
CANVAS_ROUTE = '/display/c-canvas?graph=uno-light-graph'
APP_ROUTE = '/display/firmware?solution=%s' % APP_SOLUTION
DEMO_ROUTE = '/display/uno-core-demo'
CHAIN_ROUTE = '/display/hardware-chain'

#: the six steps, in order: (name, label, purpose, [(link label, route)])
STEPS = [
    ('open-bundle', 'Open the demo bundle',
     'Opens the demo bundle: either the folder you downloaded and unpacked, or the same bundle fetched from Polari. The bundle '
     'holds the firmware to flash, its install notes, the bridge program and the settings the bridge starts with.',
     [('Where to download the bundle', DEMO_ROUTE)]),
    ('gate', 'Check the firmware is the right one',
     'Compares the fingerprint (sha256) of the firmware file with the one written in the bundle\'s install notes and with the '
     'one Polari has on record. If they are all the same the app goes on. If a record is missing or the proof for a real board is '
     'still open, the app tells you but lets you continue. Only a fingerprint that differs stops it, because that file is not the '
     'firmware that was made.',
     [('The firmware and its readiness', FIRMWARE_ROUTE)]),
    ('detect-board', 'Find the board',
     'Looks at the USB devices plugged in and picks out the Arduino Uno by its USB identity (2341:0043, 2341:0001 or 2a03:0043) '
     'and tells you which serial port it is on. If none is found it says so and waits; it never guesses a port.',
     []),
    ('flash', 'Flash the firmware',
     'Writes the firmware onto the board with avrdude, using a fixed command (the same one written in the install notes), then '
     'reads the flash back and compares every byte. It always asks a person to confirm before it writes.',
     [('The firmware solution', FIRMWARE_ROUTE), ('The firmware\'s no-code', CANVAS_ROUTE)]),
    ('host-bridge', 'Run the bridge',
     'Starts the bridge program (polari-hw-bridge.jar) as a child of the app, pointed at Polari, so the board\'s reports travel '
     'up and Polari\'s commands travel down. If the bridge stops, the app says so and offers to start it again.',
     [('The wire between board and Polari', CHAIN_ROUTE)]),
    ('sync-state', 'Keep the light in step',
     'Passes the light\'s state up to Polari (the LightState row) every time the board reports, and passes a switch command from '
     'Polari down to the board (set the light on or off). You can watch the result on the light page.',
     [('The light right now', DEMO_ROUTE)]),
]

_LAYOUT_Y = 120


def _lay_out(definition):
    by_name = {n: (label, purpose, links) for n, label, purpose, links in STEPS}
    for i, s in enumerate(definition.get('stateInstances') or []):
        name = s.get('stateName')
        label, purpose, links = by_name[name]
        s['stateLocationX'], s['stateLocationY'] = 80 + 230 * i, _LAYOUT_Y
        s['shapeType'] = s['stateSvgName'] = 'rectangle'
        s['layerName'] = 'rectangle-layer'
        s['backgroundColor'] = '#00695C'
        s['slotRadius'] = 5
        s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 190, 90, 8
        s['stateSvgRadius'] = None
        s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        f = dict(s.get('boundObjectFieldValues') or {})
        f.setdefault('displayName', '%d. %s' % (i + 1, label))
        f.setdefault('purpose', purpose)
        f['runtime'] = APP_RUNTIME
        if links:
            f['detail_ref'] = {'class': 'LinkTarget', 'name': links[0][0], 'route': links[0][1]}
            f['links'] = [{'label': a, 'route': b} for a, b in links]
        s['boundObjectFieldValues'] = f
    return S._wire_connectors(definition)


def app_definition(name=APP_SOLUTION):
    """uno-light-app: the six steps as ONE graph_builder definition, in order."""
    names = [n for n, _l, _p, _k in STEPS]
    nodes = [GB.node(n, NATIVE_KIND, {'runtime': APP_RUNTIME, 'step': i + 1},
                     outs=[[names[i + 1]]] if i + 1 < len(names) else [[]])
             for i, n in enumerate(names)]
    return _lay_out(GB.solution(name, *nodes))


def app_contract():
    return {'description': 'uno-light-app (Hardware App): open the demo bundle, check the firmware, find the board, flash it, run '
                           'the bridge, keep the light in step. Every step runs in the native JavaFX shell.',
            'inputs': [{'name': 'bundle', 'required': True, 'description': 'the demo bundle folder, or Polari\'s address to fetch it from'}],
            'returns': [], 'executionRights': 'definer'}


def definition_rows():
    return [{'name': APP_SOLUTION, 'function_name': APP_SOLUTION.replace('-', '_'), 'target_runtime': 'python_backend',
             'definition': json.dumps(app_definition()), 'contract_json': json.dumps(app_contract()), 'category': APP_CATEGORY}]
