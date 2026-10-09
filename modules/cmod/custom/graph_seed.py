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
BC_GRAPH = 'uno-button-clock-graph'


def _n(instance, kind, order, atom='', stage='', bindings='', params='', notes='', graph=GRAPH):
    return {'name': '%s:%s' % (graph, instance), 'graph': graph, 'instance': instance, 'kind': kind, 'atom': atom, 'stage': stage,
            'order': order, 'bindings': bindings, 'params': params, 'notes': notes}


def _e(i, kind, from_node, from_port, to_node, to_port='', order=0, notes='', graph=GRAPH):
    return {'name': '%s#%02d' % (graph, i), 'graph': graph, 'kind': kind, 'from_node': from_node, 'from_port': from_port,
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


#: ucd-0e2b (UNO_CORE_DEMO_PLAN.md §1/§5f/§5g): `uno-button-clock-graph` = the hand-written button-clock app
#: (board/custom/firmware/uno/apps/button_clock.c, variant uno-button-clock) expressed as nodes over the atoms:
#:
#:   init      hal_usart_init -> hal_tick_init -> hal_led_init -> l_led_init -> hal_button_init -> hal_sense_init,
#:             boot_session_mint (its return wired into state.boot_session, an init-scope FIELD edge — AFTER the
#:             class memset, before sei() — cmod.custom.glue's own fixed order)                        (then sei())
#:   on-rx     hal_rx_pop(&b) -> the frame parser (polari_rx_feed) -> apply_command(&rx) on a complete frame
#:   loop      clock (hal_millis) every pass -> led_toggle(now) -> sense_isr() -> the 10 Hz telemetry tick
#:   tick      telemetry_send(now): one ButtonClockState frame (ATOMIC_BLOCK snapshot), then events_drain()
#:             (ButtonClockEvent frames) — both already copied verbatim from button_clock.c, which assembles and
#:             sends the frames itself; the glue supplies no class/frame/parser machinery for THIS wire beyond the
#:             'state'/'rx' instances the copied bodies reference by name
#:   called    clock_tick/clock_set/events_queue/queue_pop/events_drain/hal_usart_send/hal_led/l_led_set/
#:             hal_presses/hal_take_toggle_pending/hal_sense_read — each copied in because a loop/init atom's OWN
#:             copied body calls it directly (one `calls` edge per node, from any one of its real callers — the
#:             graph's own truthful record, cmod.custom.graph.resolve: "a calls edge records what the C does")
#:
#: D2 (button, INT0) and D3 (sense, INT1) are matched to their init atoms by the uses(BUTTON_PIN)/uses(SENSE_PIN)
#: annotations added in ucd-0e2b (hal.c); D13 (the on-board L LED) by uses(L_LED_PIN) on l_led_set, both fixed
#: labels never guessed from a register name (cmod.custom.targets._FIXED_DECLARED_CANONICALS).
BC_SEED_GRAPHS = [{
    'name': BC_GRAPH, 'project': 'uno', 'board': 'arduino-uno-r3', 'base_configuration': 'uno-button-clock', 'class_name': 'ButtonClockState',
    'replaces': 'uno:apps/button_clock.c (variant uno-button-clock)', 'generated_project': 'cmod/custom/graphs/uno-button-clock-graph',
    'title': 'The button-clock demo as a graph over the UNO atoms',
    'purpose': 'The whole button-clock app (D2 debounced button toggles D6+D13, D3 independently witnesses the LED line, a '
               'software wall clock synced from the host, a bounded ButtonClockEvent queue) wired from atoms instead of '
               'written as main(); the generated glue must reproduce the hand-written app\'s frames on the simavr twin '
               '(the proof that the GENERATED interrupt configuration equals the hand-written one, ucd-0e2b).',
    'notes': 'ButtonClockEvent (the second wire class) is never a class/frame glue node — telemetry_send/events_drain '
             '(copied verbatim) assemble and send both classes\' frames themselves, exactly as button_clock.c does.'}]

BC_SEED_GRAPH_NODES = [
    _n('usart_init', 'c-atom', 1, 'uno:hal.hal_usart_init', 'init', graph=BC_GRAPH),
    _n('tick_init', 'c-atom', 2, 'uno:hal.hal_tick_init', 'init', graph=BC_GRAPH),
    _n('led_init', 'c-atom', 3, 'uno:hal.hal_led_init', 'init', graph=BC_GRAPH),
    _n('l_led_init', 'c-atom', 4, 'uno:apps/button_clock.l_led_init', 'init', graph=BC_GRAPH),
    _n('button_init', 'c-atom', 5, 'uno:hal.hal_button_init', 'init', graph=BC_GRAPH),
    _n('sense_init', 'c-atom', 6, 'uno:hal.hal_sense_init', 'init', graph=BC_GRAPH),
    _n('boot_session_mint', 'c-atom', 7, 'uno:apps/button_clock.boot_session_mint', 'init', graph=BC_GRAPH,
       notes='its return is wired into state.boot_session by a field edge, scoped init (after the class memset)'),
    _n('state', 'class', 8, params='class=ButtonClockState; name=RIG_NAME; status=IDLE', graph=BC_GRAPH,
       notes='the class instance the frames carry; every atom below writes it by this name'),
    _n('rx', 'parser', 9, params='class=ButtonClockState', graph=BC_GRAPH,
       notes='the generated header\'s receiver (polari_rx_t + polari_rx_feed)'),
    _n('rx_pop', 'c-atom', 10, 'uno:hal.hal_rx_pop', 'loop', graph=BC_GRAPH),
    _n('apply', 'c-atom', 11, 'uno:apps/button_clock.apply_command', 'loop', graph=BC_GRAPH),
    _n('clock_tick', 'c-atom', 12, 'uno:apps/button_clock.clock_tick', 'called', graph=BC_GRAPH),
    _n('clock_set', 'c-atom', 13, 'uno:apps/button_clock.clock_set', 'called', graph=BC_GRAPH),
    _n('events_queue', 'c-atom', 14, 'uno:apps/button_clock.events_queue', 'called', graph=BC_GRAPH),
    _n('queue_pop', 'c-atom', 15, 'uno:apps/button_clock.queue_pop', 'called', graph=BC_GRAPH),
    _n('events_drain', 'c-atom', 16, 'uno:apps/button_clock.events_drain', 'called', graph=BC_GRAPH),
    _n('usart_send', 'c-atom', 17, 'uno:hal.hal_usart_send', 'called', graph=BC_GRAPH),
    _n('led', 'c-atom', 18, 'uno:hal.hal_led', 'called', graph=BC_GRAPH),
    _n('l_led', 'c-atom', 19, 'uno:apps/button_clock.l_led_set', 'called', graph=BC_GRAPH),
    _n('button', 'c-atom', 20, 'uno:hal.hal_presses', 'called', graph=BC_GRAPH),
    _n('toggle_pending', 'c-atom', 21, 'uno:hal.hal_take_toggle_pending', 'called', graph=BC_GRAPH),
    _n('sense', 'c-atom', 22, 'uno:hal.hal_sense_read', 'called', graph=BC_GRAPH),
    _n('clock', 'c-atom', 23, 'uno:hal.hal_millis', 'loop', graph=BC_GRAPH),
    _n('led_toggle', 'c-atom', 24, 'uno:apps/button_clock.led_toggle', 'loop', graph=BC_GRAPH),
    _n('sense_isr', 'c-atom', 25, 'uno:apps/button_clock.sense_isr', 'loop', graph=BC_GRAPH),
    _n('telemetry', 'tick', 26, params='period_ms=TELEMETRY_MS', graph=BC_GRAPH),
    _n('telemetry_send', 'c-atom', 27, 'uno:apps/button_clock.telemetry_send', 'loop', graph=BC_GRAPH),
]

BC_SEED_GRAPH_EDGES = [
    _e(1, 'on-rx', 'rx_pop', 'b', 'rx', 'byte', graph=BC_GRAPH),
    _e(2, 'on-command', 'rx', 'frame', 'apply', 'r', graph=BC_GRAPH),
    _e(3, 'calls', 'apply', '', 'clock_set', notes='apply_command: SET_TIME -> clock_set', graph=BC_GRAPH),
    _e(4, 'calls', 'led_toggle', '', 'clock_tick', graph=BC_GRAPH),
    _e(5, 'calls', 'led_toggle', '', 'events_queue', graph=BC_GRAPH),
    _e(6, 'calls', 'led_toggle', '', 'led', 'on', graph=BC_GRAPH),
    _e(7, 'calls', 'led_toggle', '', 'l_led', 'on', graph=BC_GRAPH),
    _e(8, 'calls', 'led_toggle', '', 'button', 'return', graph=BC_GRAPH),
    _e(9, 'calls', 'led_toggle', '', 'toggle_pending', 'return', graph=BC_GRAPH),
    _e(10, 'calls', 'sense_isr', '', 'sense', graph=BC_GRAPH),
    _e(11, 'calls', 'events_drain', '', 'queue_pop', graph=BC_GRAPH),
    _e(12, 'calls', 'events_drain', '', 'usart_send', 'b', graph=BC_GRAPH),
    _e(13, 'calls', 'telemetry_send', '', 'events_drain', graph=BC_GRAPH),
    _e(14, 'data', 'clock', 'return', 'telemetry', 'now', graph=BC_GRAPH),
    _e(15, 'data', 'clock', 'return', 'led_toggle', 'now_ms', graph=BC_GRAPH),
    _e(16, 'data', 'clock', 'return', 'telemetry_send', 'now_ms', graph=BC_GRAPH),
    _e(17, 'tick', 'telemetry', '', 'telemetry_send', graph=BC_GRAPH),
    _e(18, 'field', 'boot_session_mint', 'return', 'state', 'boot_session',
       notes='init-scope: after the class memset, before sei() (cmod.custom.glue\'s own fixed order)', graph=BC_GRAPH),
]

SEED_GRAPHS += BC_SEED_GRAPHS
SEED_GRAPH_NODES += BC_SEED_GRAPH_NODES
SEED_GRAPH_EDGES += BC_SEED_GRAPH_EDGES


def seed_graph(name=GRAPH):
    """{'graph': row, 'nodes': [...], 'edges': [...]} of a seeded graph."""
    g = [x for x in SEED_GRAPHS if x['name'] == name]
    if not g:
        return None
    return {'graph': dict(g[0]), 'nodes': [dict(n) for n in SEED_GRAPH_NODES if n['graph'] == name],
            'edges': [dict(e) for e in SEED_GRAPH_EDGES if e['graph'] == name]}
