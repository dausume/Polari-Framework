"""
@module cmod.custom.purpose_seeds

The light test's four declared Purposes (fgm-1, FIRMWARE_GENERATION_MODULE_PLAN.md §8.3): `initialization`, then the three that
depend on it. Each carries its goal, life stage, its fulfillment contract (`criteria_json`), what Polari must observe
(`observes_json`) and its participants. Numbers are CITED, never invented: 30 ms debounce and 10 Hz report rate are the
uno-light variant's own knobs (board.custom.variants), the 100 ms bound is one report period and the acceptance Scenarios' own
`window_ms`. Every atom of `uno-light-graph` is named by at least one of these (the coverage check in cmod_selftest).
`light-from-polari` / `light-from-button` are kept (retired) in capabilities.py - their runs stay as history.
"""
import json

LIGHT_GRAPH = 'uno-light-graph'


def _t(c_device, java_bridge=(), python_backend=()):
    return json.dumps({'c-device': ['%s:%s' % (LIGHT_GRAPH, n) for n in c_device], 'java-bridge': list(java_bridge),
                       'python-backend': list(python_backend), 'typescript-browser': []})


_PARTICIPANTS = json.dumps([
    {'role': 'board', 'kind': 'board', 'ref': 'arduino-uno-r3', 'variant': 'pending'},
    {'role': 'chip', 'kind': 'soc', 'ref': 'atmega328p'},
    {'role': 'host', 'kind': 'host', 'ref': 'host'},
    {'role': 'Polari', 'kind': 'polari', 'ref': 'polari'}])

_LIGHT_FIELDS = 'led_on,toggles,source'
_BASE = {'graph': LIGHT_GRAPH, 'required_targets': '', 'instance_count': 1, 'status': 'planned', 'last_proof': '',
         'lifecycle': 'enabled', 'participants_json': _PARTICIPANTS}

PURPOSE_SEEDS = [
    dict(_BASE, name='initialization', title='Initialization', exposes_fields='boot_session',
         goal='the board is set up and ready to run its tasks and accept commands',
         purpose='Why these are in the light firmware: nothing else works until the serial link, the clock, the light pin, the button '
                 'and the boot session number are set up.',
         tasks_by_runtime_json=_t(['usart_init', 'tick_init', 'led_init', 'button_init', 'boot_session_mint']),
         acceptance_scenario='initialization-acceptance', depends_on='',
         criteria_json=json.dumps({'trigger': {'kind': 'boot', 'what': 'the board starts or restarts'},
                                   'outcome': {'what': 'the first report arrives carrying a new boot session number'},
                                   'criteria': [{'key': 'max_latency_ms', 'value': 100, 'unit': 'ms'}]}),
         observes_json=json.dumps([{'item': 'LightState.boot_session', 'kind': 'field', 'delivery': 'latest'}]),
         notes='fgm-1 seed; fsc-0b: proven by initialization-acceptance (board.custom.light_boot_twin): the first report inside 100 ms of reset carries boot_session, '
               'and after a second reset the first report carries a different one; four negative controls go through the same judge.'),
    dict(_BASE, name='ensure-button-controls-light', title='The board\'s button controls the light', exposes_fields=_LIGHT_FIELDS,
         goal='a press on the board\'s button turns the light on or off, and Polari learns of the change',
         purpose='Up: the pushbutton on D2 (debounced) flips the light on D6, the board counts the change, says source=button in its '
                 'next report, and the bridge writes that onto the LightState row so a screen can show it.',
         tasks_by_runtime_json=_t(['button_init', 'toggle_pending', 'led_toggle', 'led', 'clock', 'state'], java_bridge=['uno-light:relay-in']),
         acceptance_scenario='light-from-button-acceptance', depends_on='initialization',
         criteria_json=json.dumps({'trigger': {'kind': 'button', 'what': 'a press on the button on D2'},
                                   'outcome': {'what': 'LightState.led_on flips and D6 follows'},
                                   'criteria': [{'key': 'debounce_ms', 'value': 30, 'unit': 'ms'},
                                                {'key': 'max_latency_ms', 'value': 100, 'unit': 'ms'},
                                                {'key': 'delivery', 'value': 'latest'}]}),
         observes_json=json.dumps([{'item': 'LightState.led_on', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.toggles', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.source', 'kind': 'field', 'delivery': 'latest'}]),
         notes='fgm-1 seed; takes over light-from-button\'s acceptance Scenario (same steps)'),
    dict(_BASE, name='ensure-polari-observes-hardware-state', title='Polari observes the hardware state', exposes_fields=_LIGHT_FIELDS + ',boot_session',
         goal='whatever the board does to the light, Polari sees it within one report and the report says who changed it',
         purpose='The board sends a state report ten times a second; the bridge writes each onto the LightState row, so a screen or '
                 'a Purpose can always read the light as the board last reported it.',
         tasks_by_runtime_json=_t(['state', 'clock', 'telemetry', 'telemetry_send', 'usart_send'], java_bridge=['uno-light:relay-in']),
         acceptance_scenario='ensure-polari-observes-hardware-state-acceptance', depends_on='initialization',
         criteria_json=json.dumps({'trigger': {'kind': 'period', 'what': 'every report period (10 reports a second)'},
                                   'outcome': {'what': 'the LightState row on Polari matches what the board last reported'},
                                   'criteria': [{'key': 'freshness_ms', 'value': 100, 'unit': 'ms'},
                                                {'key': 'delivery', 'value': 'latest'}]}),
         observes_json=json.dumps([{'item': 'LightState.led_on', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.toggles', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.source', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.boot_session', 'kind': 'field', 'delivery': 'latest'}]),
         notes='fgm-1 seed. Its test is its own Scenario that reuses the button test\'s frame checks (the light flips on every press, '
               'the toggle count equals the presses, source is button): the frames Polari reads are the evidence.'),
    dict(_BASE, name='ensure-polari-can-control-light', title='Polari can control the light', exposes_fields=_LIGHT_FIELDS,
         goal='Polari turns the board\'s light on and off on command, and the board reports that the light changed',
         purpose='Down: a person presses the light button on a Polari screen, led_on on the LightState row changes, the command rides '
                 'the serial link to the board, the board switches the light on D6 and says source=command in its next report.',
         tasks_by_runtime_json=_t(['rx_pop', 'rx', 'apply', 'led', 'state'], java_bridge=['uno-light:relay-out'], python_backend=['light-toggle:flip']),
         acceptance_scenario='light-from-polari-acceptance', depends_on='initialization',
         criteria_json=json.dumps({'trigger': {'kind': 'command', 'what': 'a command from Polari: SET_LED, carrying a command_id'},
                                   'outcome': {'what': 'LightState.led_on equals the command and D6 follows'},
                                   'criteria': [{'key': 'max_latency_ms', 'value': 100, 'unit': 'ms'},
                                                {'key': 'delivery', 'value': 'latest-value, confirmed by command_id'}]}),
         observes_json=json.dumps([{'item': 'LightState.led_on', 'kind': 'field', 'delivery': 'latest'},
                                   {'item': 'LightState.last_command_id and last_command_result', 'kind': 'correlation',
                                    'delivery': 'not on the wire yet: the light report does not carry them'}]),
         notes='fgm-1 seed; takes over light-from-polari\'s acceptance Scenario (same steps). The command_id echo is declared here '
               'but not yet sent by the firmware, so the existing test confirms the light follows the command, not the id.'),
]
