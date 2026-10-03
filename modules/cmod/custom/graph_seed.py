"""
@module cmod.custom.graph_seed

THE FIRST GRAPH (C_MODULARIZATION_PLAN.md §10 cmod-1): `uno-sim-rig-graph` = the hand-written sim-rig app
(board/custom/firmware/uno/apps/sim_rig.c, variant uno-sim-rig) expressed as nodes over the atoms cmod-0 derived:

    init      hal_usart_init → hal_tick_init → hal_led_init → hal_pwm_init → hal_adc_init      (then sei())
    on-rx     hal_rx_pop(&b) → the frame parser (polari_rx_feed, the generated header)
    on-cmd    a complete SimRigState frame → apply_command(&rx)  (which itself calls hal_led / hal_pwm_apply — `calls` edges)
    clock     hal_millis() every pass → the 10 Hz telemetry tick (period TELEMETRY_MS, a board_config.h knob)
    tick      hal_millis → state.uptime_ms;  hal_adc_read(ADC_CHANNEL) → sensor_value → state.temp_c;  the status rule
              (boot → ok once the clock passes 1000 ms);  the telemetry frame (SimRigState_encode + _frame, the fields
              uptime_ms, status, temp_c, led_on, pwm_duty, name) → hal_usart_send

Rows are written here as dicts (the seeds); a person adds a graph as rows (CRUDE) and `pol cmod render <graph>` renders it.
"""

GRAPH = 'uno-sim-rig-graph'


def _n(instance, kind, order, atom='', stage='', bindings='', params='', notes=''):
    return {'name': '%s:%s' % (GRAPH, instance), 'graph': GRAPH, 'instance': instance, 'kind': kind, 'atom': atom, 'stage': stage,
            'order': order, 'bindings': bindings, 'params': params, 'notes': notes}


def _e(i, kind, from_node, from_port, to_node, to_port='', order=0, notes=''):
    return {'name': '%s#%02d' % (GRAPH, i), 'graph': GRAPH, 'kind': kind, 'from_node': from_node, 'from_port': from_port,
            'to_node': to_node, 'to_port': to_port, 'order': order or i, 'scale': '', 'offset': '', 'notes': notes}


SEED_GRAPHS = [{
    'name': GRAPH, 'project': 'uno', 'board': 'arduino-uno-r3', 'base_configuration': 'uno-sim-rig', 'class_name': 'SimRigState',
    'replaces': 'uno:apps/sim_rig.c (variant uno-sim-rig)', 'generated_project': 'cmod/custom/graphs/uno-sim-rig-graph',
    'title': 'The sim rig as a graph over the UNO atoms',
    'purpose': 'The whole sim-rig app (TMP36 on A0, LED on D13, PWM on D6, commands applied, 10 Hz SimRigState telemetry) wired '
               'from atoms instead of written as main(); the generated glue must reproduce the hand-written app\'s frames on '
               'the simavr twin.',
    'notes': ''}]

SEED_GRAPH_NODES = [
    _n('usart_init', 'c-atom', 1, 'uno:hal.hal_usart_init', 'init'),
    _n('tick_init', 'c-atom', 2, 'uno:hal.hal_tick_init', 'init'),
    _n('led_init', 'c-atom', 3, 'uno:hal.hal_led_init', 'init'),
    _n('pwm_init', 'c-atom', 4, 'uno:hal.hal_pwm_init', 'init'),
    _n('adc_init', 'c-atom', 5, 'uno:hal.hal_adc_init', 'init'),
    _n('state', 'class', 6, params='class=SimRigState; name=RIG_NAME; status=BOOT',
       notes='the class instance the frames carry; apply_command writes it by this name'),
    _n('rx', 'parser', 7, params='class=SimRigState', notes='the generated header\'s receiver (polari_rx_t + polari_rx_feed)'),
    _n('rx_pop', 'c-atom', 10, 'uno:hal.hal_rx_pop', 'loop'),
    _n('apply', 'c-atom', 11, 'uno:apps/sim_rig.apply_command', 'loop'),
    _n('led', 'c-atom', 12, 'uno:hal.hal_led', 'called'),
    _n('pwm', 'c-atom', 13, 'uno:hal.hal_pwm_apply', 'called'),
    _n('clock', 'c-atom', 20, 'uno:hal.hal_millis', 'loop'),
    _n('telemetry', 'tick', 21, params='period_ms=TELEMETRY_MS'),
    _n('adc', 'c-atom', 22, 'uno:hal.hal_adc_read', 'loop', bindings='channel=ADC_CHANNEL'),
    _n('temp', 'c-atom', 23, 'uno:apps/sim_rig.sensor_value', 'loop'),
    _n('boot_ok', 'rule', 24, params='rule=after-ms; class=state; field=status; from=BOOT; to=OK; after_ms=1000'),
    _n('frame', 'frame', 25, params='class=state; device_id=DEVICE_ID; fields=uptime_ms,status,temp_c,led_on,pwm_duty,name'),
    _n('send', 'c-atom', 26, 'uno:hal.hal_usart_send', 'loop'),
]

SEED_GRAPH_EDGES = [
    _e(1, 'on-rx', 'rx_pop', 'b', 'rx', 'byte'),
    _e(2, 'on-command', 'rx', 'frame', 'apply', 'r'),
    _e(3, 'calls', 'apply', '', 'led', 'on'),
    _e(4, 'calls', 'apply', '', 'pwm', 'duty'),
    _e(5, 'data', 'clock', 'return', 'telemetry', 'now'),
    _e(6, 'tick', 'telemetry', '', 'state', 'uptime_ms', notes='sample the clock into the frame on the tick only'),
    _e(7, 'field', 'clock', 'return', 'state', 'uptime_ms'),
    _e(8, 'tick', 'telemetry', '', 'adc'),
    _e(9, 'data', 'adc', 'return', 'temp', 'adc'),
    _e(10, 'field', 'temp', 'return', 'state', 'temp_c'),
    _e(11, 'tick', 'telemetry', '', 'boot_ok'),
    _e(12, 'data', 'clock', 'return', 'boot_ok', 'now'),
    _e(13, 'tick', 'telemetry', '', 'frame'),
    _e(14, 'data', 'frame', 'wire', 'send', 'b'),
    _e(15, 'data', 'frame', 'length', 'send', 'n'),
]


def seed_graph(name=GRAPH):
    """{'graph': row, 'nodes': [...], 'edges': [...]} of a seeded graph."""
    g = [x for x in SEED_GRAPHS if x['name'] == name]
    if not g:
        return None
    return {'graph': dict(g[0]), 'nodes': [dict(n) for n in SEED_GRAPH_NODES if n['graph'] == name],
            'edges': [dict(e) for e in SEED_GRAPH_EDGES if e['graph'] == name]}
