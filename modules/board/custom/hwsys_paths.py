"""
@module board.custom.hwsys_paths

hsp-1 (L7): THE THREE SIGNAL PATHS of `uno-light-system`, DERIVED every time from the rows in hand (tables, links) and the owners of each check (board.custom.hwsys_chain, hwsys_context):
  button-to-polari   the person presses SW1 -> D2 -> INT0 -> the firmware -> USART0 TXD -> RN4A -> the 16U2 -> USB -> the host -> the Java bridge -> gRPC -> the LightState row -> the Polari page
  polari-to-led      the page's Toggle -> the backend -> gRPC -> the bridge -> serial -> the 16U2 -> RN4B -> USART0 RXD -> the firmware's command handler -> PD6 -> D6 -> R1 -> LED1 -> the light
  led-line-to-d3     D6 drives LED_CONTROL -> the bench jumper -> D3 -> INT1 -> the firmware's sense counter -> reported in the state (the sense isotope is fgm-5: `not-yet` until then)
A path walks origin -> destination with NO gap: each hop resolves to a row or is an explicit blocked / undetermined hop naming what is missing (a removed D6 -> D3 BoardPinNet breaks led-line-to-d3 by name).
"""
import json

from board.custom import hwsys_chain as CH
from board.custom.hwsys_context import finish, worst


def _net_hop(ctx, canon, net, rung_pin, fn, what, rules, match, missing_blocks=True):
    """A bench wire (BoardPinNet) tie: ladder rung 4 (the bench net on the line) + the electrical rules that own it."""
    from board.custom import board_pin_nets as BPN
    lad = ctx.ladder(rung_pin, fn)
    v4, d4, x = ctx.rungs_hop(lad, (4,), 'net')
    parts, dets = [v4], [d4]
    for rule, m in zip(rules, match):
        v, d = ctx.findings((rule,), m)
        parts.append(v)
        dets.append(d)
    return ctx.hop('net', 'BoardPinNet:%s' % BPN._name(canon, net), what, 'ladder rung 4 + electrical rule(s) %s' % ', '.join(rules), worst(parts), ' | '.join(dets), missing_blocks=missing_blocks, **x)


def _electrical(ctx, ref, what, rules, match, label):
    vs, ds = [], []
    for r, m in zip(rules, match):
        v, d = ctx.findings((r,), m)
        vs.append(v)
        ds.append(d)
    return ctx.hop('net' if ref.startswith('CircuitNet') else 'participant', ref, what, 'electrical rule %s' % label, worst(vs), ' | '.join(ds))


def button_to_polari(ctx, links):
    h = [ctx.hop('participant', 'Person:bench-operator', 'a person presses the button SW1', 'none', 'unchecked', 'the person is a participant role')]
    v, d = ctx.findings(('input_threshold',), 'D2 button')
    sw = [p for p in json.loads(ctx.system['participants_json']) if p['role'] == 'button SW1'][0]['ref']
    h.append(ctx.hop('participant', sw, 'button SW1 closes BUTTON_INPUT to GND', 'electrical rule (h) input_threshold', v, d))
    h.append(_net_hop(ctx, 'D2', 'BUTTON_INPUT', 'D2', 'INT0', 'net BUTTON_INPUT is tied to D2 (the bench wire)', ('pull_defined',), ('D2',)))
    h += CH.pin_in(ctx, 'D2', 'INT0')
    h.append(CH.firmware_hop(ctx, 'the firmware: INT0 ISR -> debounce (30 ms) -> toggle_pending -> led_toggle -> the state report (source=button)', 'ensure-button-controls-light'))
    fn, cross = CH.uart_pin(ctx, 'D1', 'TXD', links.get('u1-usart0-u2-usart1'))
    h += [fn, cross]
    pad, usb, ucross = CH.u2_hops(ctx, links, 'PD2', 'RXD1')
    port, jb, grpc = CH.host_hops(ctx, links)
    h += [pad, usb, ucross, port, jb, grpc]
    h.append(CH.contract_hop(ctx, 'the LightState v1 frame is decoded into the backend LightState row (led_on, toggles, source)', need=('led_on', 'toggles', 'source')))
    h.append(ctx.hop('participant', 'Runtime:typescript-browser', 'the Polari page indicator shows the light', 'none', 'unchecked', 'the page /display/uno-core-demo; no browser pass has run here'))
    return dict(finish(h), direction='up', origin='the person presses the button SW1', destination='the Polari page indicator (LightState)',
                title='Button press to the Polari page')


def polari_to_led(ctx, links):
    h = [ctx.hop('participant', 'Runtime:typescript-browser', 'the Toggle button on the Polari page', 'none', 'unchecked', 'the page /display/uno-core-demo; no browser pass has run here'),
         ctx.hop('participant', 'SolutionDefinition:light-toggle', 'the backend flips led_on on the LightState row (SET_LED rides the same field)', 'none', 'unchecked', 'the solution row is cited; no run is checked here')]
    h.append(CH.contract_hop(ctx, 'led_on is the command field of LightState v1 (SET_LED)', need=('led_on', 'command_id'),
                             gap='KNOWN GAP: LightState v1 has no command_id, so a command is confirmed by correlated state only (source=command in the next report); fgm-6 adds v2'))
    port, jb, grpc = CH.host_hops(ctx, links)
    pad, usb, ucross = CH.u2_hops(ctx, links, 'PD3', 'TXD1')
    h += [grpc, jb, port, ucross, usb, pad]
    fn, cross = CH.uart_pin(ctx, 'D0', 'RXD', links.get('u1-usart0-u2-usart1'))
    h += [cross, fn]
    h.append(CH.firmware_hop(ctx, 'the firmware: rx_pop -> rx -> apply (command handler) -> led -> the state report (source=command)', 'ensure-polari-can-control-light'))
    h += CH.pin_out(ctx, 'D6', 'GPIO')
    h.append(_net_hop(ctx, 'D6', 'LED_CONTROL', 'D6', 'GPIO', 'D6 drives net LED_CONTROL (the one driver)', ('single_driver',), ('LED_CONTROL',)))
    parts = {p['role']: p['ref'] for p in json.loads(ctx.system['participants_json'])}
    h.append(_electrical(ctx, parts['resistor R1'], 'R1 220 ohm limits the LED current', ('led_current',), ('',), '(a) led_current'))
    h.append(_electrical(ctx, parts['LED1'], 'LED1 lights: the current through it and the pin level it needs', ('led_current', 'voh_under_load'), ('', 'D6'), '(a) led_current + (f) voh_under_load'))
    return dict(finish(h), direction='down', origin='the Toggle on the Polari page', destination='LED1 on the bench lights', title='Polari toggle to the LED')


def led_line_to_d3(ctx, links):
    h = [_net_hop(ctx, 'D6', 'LED_CONTROL', 'D6', 'GPIO', 'D6 drives net LED_CONTROL (the driver end of the jumper)', ('single_driver',), ('LED_CONTROL',)),
         _net_hop(ctx, 'D3', 'LED_CONTROL', 'D3', 'INT1', 'the jumper wire lands on D3 (net LED_CONTROL, role input)', ('level_compatible', 'input_threshold'), ('LED_CONTROL', 'D6 -> D3')),
         CH.link_hop(ctx, links, 'd6-d3-jumper', 'the bench jumper wire D6 -> D3')]
    if not links.get('d6-d3-jumper'):
        from board.custom import board_pin_nets as BPN
        h[2]['detail'] = 'the D6 -> D3 jumper is not wired: BoardPinNet %s is not in the tables' % BPN._name('D3', 'LED_CONTROL')
    h += CH.pin_in(ctx, 'D3', 'INT1')
    nodes = []
    try:
        from cmod.custom.graph_seed import seed_graph
        nodes = [n['instance'] for n in (seed_graph('%s-graph' % ctx.firmware)['nodes'])]
    except Exception:   # noqa: BLE001
        nodes = None
    sense = [n for n in (nodes or []) if 'sense' in n]
    if nodes is None:
        h.append(ctx.hop('firmware', CH.LIGHT_FW, 'the firmware\'s INT1 sense counter', 'cmod graph nodes', 'unchecked', 'cmod is absent: the firmware graph cannot be read'))
    elif not sense:
        h.append(ctx.hop('firmware', CH.LIGHT_FW, 'the firmware\'s INT1 sense counter (counts the edges on D3)', 'cmod graph nodes', 'not-yet',
                         'the firmware graph %s-graph has no sense node (%d nodes read); the D3 sense isotope lands in fgm-5' % (ctx.firmware, len(nodes))))
    else:
        h.append(ctx.hop('firmware', CH.LIGHT_FW, 'the firmware\'s INT1 sense counter', 'cmod graph nodes', 'unchecked', 'sense node(s) %s exist; no proof is read for them' % sense))
    v, d, x = CH.contract_check(ctx, need=('sense_rises', 'sense_falls'))
    h.append(ctx.hop('contract', 'WireContract:LightState@uno-light', 'the sense count is reported in the state', 'contract hash',
                     'not-yet' if v in ('conditional', 'ok') and 'has no field' in d else v, ('LightState v1 carries no sense counter: ' + d) if 'has no field' in d else d, **x))
    return dict(finish(h), direction='loop', origin='D6 drives LED_CONTROL', destination='the sense count reported in the state', title='LED line to the D3 sense pin')


PATHS = (('button-to-polari', button_to_polari), ('polari-to-led', polari_to_led), ('led-line-to-d3', led_line_to_d3))
