"""
@module board.custom.hwsys_links

hsp-1 (L6): THE SEVEN SystemLinks of `uno-light-system`, DERIVED — never typed twice. The crossings a link rides on are the hsp-0 EnclosureContact rows found by their cited part (RN4A/RN4B, RN3A/RN3D,
C5) or by the pin; the bench wires come from the BoardPinNet rows (a link whose rows are gone from the tables is NOT listed — that is how a removed jumper shows); the host and
bridge ends come from the grpcbridge light bridge seed; the protocol is the PINNED LightState v1 wire contract (board/custom/contracts). Verification is the weakest of the rows it rides on.
  a  u1-usart0-u2-usart1   U1 PD0/PD1 <-> U2 PD3/PD2 through RN4B / RN4A 1 kOhm      e  button-d2          SW1 -> BUTTON_INPUT -> D2 (internal pull-up if the firmware claims it)
  b  u2-usb-host           U2 D+/D- -> USB connector -> the host's serial port        f  d6-r1-led1-gnd     D6 -> R1 -> LED1 -> GND
  c  u2-dtr-u1-reset       U2 PD7 (DTR) -> C5 100 nF -> U1 RESET                      g  bridge-backend-grpc  Java bridge <-> backend (gRPC :3002) <-> Polari page
  d  d6-d3-jumper          the bench wire from the D6 output to the D3 sense input
"""
from board.custom import board_pin_nets as BPN   # D-pv-7: signal roles (output | input), is_output()
import json

from board.custom import exposure_view as V
from board.custom.hwsys_context import VERIFY
from board.custom.hwsys_system import LIGHT

RANK = ('conflicted', 'unverified', 'partial', 'verified')


def _weakest(vs):
    vs = [v for v in vs if v in RANK]
    return min(vs, key=RANK.index) if vs else 'unverified'


def slug(system, s):
    return '%s:%s' % (system, s)


def _socs(tables, contact_refs):
    by = {'PackageContact:%s' % c['name']: c for c in tables.get('PackageContact', [])}
    return ['SocPin:%s' % by[r]['soc_pin'] for r in contact_refs if r in by and by[r].get('soc_pin')]


def _cites(cs):
    out = []
    for c in cs:
        for s in (c.get('fact'), ('%s — %s' % (c['document'], c['page_table'])) if c.get('document') else ''):
            if s and s not in out:
                out.append(s)
    return out


def _link(system, key, title, a, b, medium, kind, cs, protocol='', verification='', und=(), notes='', cites=None):
    return {'name': slug(system, key), 'title': title, 'system': system, 'endpoint_a_json': json.dumps(a), 'endpoint_b_json': json.dumps(b), 'medium': medium,
            'signal_kind': kind, 'protocol': protocol, 'via_refs_json': json.dumps(['EnclosureContact:%s' % c['name'] for c in cs]),
            'verification': verification or _weakest([c['verification'] for c in cs]), 'undetermined': '; '.join(u for u in und if u),
            'citations_json': json.dumps(cites if cites is not None else _cites(cs)), 'notes': notes}


def _e2(tables, board, **kw):
    return [c for c in V.board_rows(tables, board) if c['level'] == 'E2' and all(c.get(k) == v for k, v in kw.items())]


def _net(ctx, canonical, net=None):
    """The BoardPinNet row tying a board pin to a circuit net (net = the net's LABEL, e.g. 'LED_CONTROL', read off the CircuitNetDefinition the row names)."""
    labels = {n['name']: n.get('net') for n in ctx.tables.get('CircuitNetDefinition', [])}
    return next((n for n in ctx.tables.get('BoardPinNet', []) if n.get('board_pin') == '%s:%s' % (ctx.board, canonical) and n.get('circuit') == ctx.circuit
                 and (net is None or labels.get(n.get('circuit_net')) == net)), None)


def _mcu(ctx):
    return next((x for x in ctx.tables.get('BoardComponent', []) if x['board'] == ctx.board and x['role'] == 'mcu'), {})


def _leg_crossings(ctx, canonical):
    """(E2 crossings of a board pin's package leg to the header, SocPin) — derived: BoardPin -> SocPin -> PackageContact -> EnclosureContact."""
    mcu = _mcu(ctx)
    bp = next((b for b in ctx.tables.get('BoardPin', []) if b['board'] == ctx.board and b['canonical'] == canonical), None)
    sp = next((s for s in ctx.tables.get('SocPin', []) if bp and s['name'] == '%s:%s' % (mcu.get('soc'), bp['soc_pin'])), None)
    legs = {'PackageContact:%s' % c['name'] for c in ctx.tables.get('PackageContact', []) if sp and c.get('soc_pin') == sp['name'] and c['package'] == mcu.get('package')}
    return [c for c in _e2(ctx.tables, ctx.board) if c['inner_ref'] in legs and c['exposed']], sp


def links(ctx, system):
    T, B, out = ctx.tables, ctx.board, []
    pin = lambda canon: 'BoardPin:%s:%s' % (B, canon)   # noqa: E731
    contract = ctx.contract()
    proto = ('LightState v%s (contract hash %s, msg_type %s, pinned snapshot)' % (contract['contract_version'], contract['contract_hash'], contract['msg_type'])) if contract else ''
    try:
        from grpcbridge.mapping_basis import SEED_LIGHT_BRIDGE as BR
    except Exception:   # noqa: BLE001
        BR = {'name': 'uno-light-bridge', 'serial_device': '', 'baud': 0, 'grpc_target': ''}
    bridge = 'HardwareBridgeDefinition:%s' % BR['name']
    # a ---- the two chips talk
    cs = [c for c in _e2(T, B) if c['via_part'] in ('RN4A', 'RN4B')]
    if len(cs) == 2:
        out.append(_link(system, 'u1-usart0-u2-usart1', 'U1 USART0 (PD0/PD1) <-> U2 USART1 through RN4A / RN4B 1 kOhm',
                         {'participant': 'chip U1 (mcu)', 'refs': [pin('D0'), pin('D1')] + _socs(T, [c['inner_ref'] for c in cs]) + [c['inner_ref'] for c in cs], 'what': 'PD0 RXD / PD1 TXD (USART0)'},
                         {'participant': 'chip U2 (usb-bridge)', 'refs': _socs(T, [c['outer_ref'] for c in cs]) + [c['outer_ref'] for c in cs], 'what': 'PD3 TXD1 / PD2 RXD1 (USART1)'},
                         'series-resistor', 'uart', cs, notes='D0/D1 are the USB-serial transport on this board: reserved (pin lifecycle) while transport=usb-serial'))
    # b ---- the 16U2's USB to the host, through the USB connector
    cs = [c for c in _e2(T, B) if c['via_part'] in ('RN3A', 'RN3D')]
    bd = next((x for x in T.get('BoardDefinition', []) if x['name'] == B), {})
    ifaces = [u for u in T.get('UsbInterfaceDefinition', []) if u['name'] in json.loads(bd.get('allowed_usb_interfaces_json') or '[]')]
    if cs:
        v = _weakest([u['verification'] for u in ifaces] + [c['verification'] for c in cs])
        und = ['the bench board\'s USB interface is PENDING identification: %s' % ', '.join('%s %s' % (u['name'], u['verification']) for u in ifaces),
               '; '.join(sorted({c['undetermined'] for c in cs if c['undetermined']}))]
        out.append(_link(system, 'u2-usb-host', 'U2 USB D+/D- -> the USB connector -> the host serial port',
                         {'participant': 'chip U2 (usb-bridge)', 'refs': [c['inner_ref'] for c in cs] + ['UsbInterfaceDefinition:%s' % u['name'] for u in ifaces], 'what': 'USB D+ / D-'},
                         {'participant': 'host serial / bridge', 'refs': [bridge], 'what': 'the host serial port %s at %s baud' % (BR.get('serial_device') or '(undetermined)', BR.get('baud') or '?')},
                         'usb', 'usb', cs, protocol=proto, verification='partial' if len({u['verification'] for u in ifaces}) > 1 and v != 'conflicted' else v, und=und,
                         notes='the board->host data link: LightState frames ride the USB-CDC serial port', cites=_cites(cs) + ['UsbInterfaceDefinition:%s' % u['name'] for u in ifaces]))
    # c ---- DTR -> RESET: every serial reconnect reboots the UNO
    cs = [c for c in _e2(T, B) if c['via_part'] == 'C5']
    if cs:
        out.append(_link(system, 'u2-dtr-u1-reset', 'U2 DTR (PD7) -> C5 100 nF -> U1 RESET',
                         {'participant': 'chip U2 (usb-bridge)', 'refs': _socs(T, [cs[0]['inner_ref']]) + [cs[0]['inner_ref']], 'what': 'PD7, the DTR line'},
                         {'participant': 'chip U1 (mcu)', 'refs': [cs[0]['outer_ref']], 'what': 'RESET (leg 1)'}, 'capacitor', 'reset', cs,
                         notes='EVERY serial reconnect by the host pulses DTR and reboots the UNO (auto-reset) — the firmware starts again and picks a new boot_session'))
    # d ---- the bench jumper D6 -> D3
    drv, sns = _net(ctx, 'D6', 'LED_CONTROL'), _net(ctx, 'D3', 'LED_CONTROL')
    if drv and sns and drv['circuit_net'] == sns['circuit_net'] and BPN.is_output(drv['role']) and sns['role'] == 'input':
        cs = [c for p in ('D6', 'D3') for c in _leg_crossings(ctx, p)[0]]
        out.append(_link(system, 'd6-d3-jumper', 'the bench jumper wire D6 -> D3 (the sense pin)',
                         {'participant': 'jumper D6-D3', 'refs': [pin('D6'), 'BoardPinNet:%s' % drv['name']], 'what': 'D6 drives net LED_CONTROL'},
                         {'participant': 'chip U1 (mcu)', 'refs': [pin('D3'), 'BoardPinNet:%s' % sns['name']], 'what': 'D3 (INT1) listens to the same net (role input, never a second driver)'},
                         'jumper-wire', 'digital', cs, verification='unverified',
                         und=['the wire is a bench-wiring row (design intent, UNO_CORE_DEMO_PLAN.md §1), not measured on a bench'],
                         notes='the MCU independently detects the edges on the LED line through a real wire, never by reading its own output latch', cites=[drv['name'], sns['name']]))
    # e ---- the button on D2
    btn = _net(ctx, 'D2', 'BUTTON_INPUT')
    if btn:
        pull_v, pull_d = ctx.findings(('pull_defined',), 'D2')
        und = [] if pull_v == 'ok' else ['the pull on D2 is not defined: %s' % pull_d]
        out.append(_link(system, 'button-d2', 'the button SW1 -> net BUTTON_INPUT -> D2 (INT0)',
                         {'participant': 'button SW1', 'refs': ['CircuitNetDefinition:%s' % btn['circuit_net'], 'CircuitComponentDefinition:%s' % _part(ctx, 'switch')], 'what': 'BUTTON_INPUT to GND, closed while pressed'},
                         {'participant': 'chip U1 (mcu)', 'refs': [pin('D2'), 'BoardPinNet:%s' % btn['name']], 'what': 'D2 reads the net; the internal pull-up (PinClaim pull=up of the firmware) holds it high when open'},
                         'jumper-wire', 'digital', _leg_crossings(ctx, 'D2')[0], verification='unverified' if und else 'partial', und=und, cites=[btn['name'], pull_d]))
    # f ---- the LED branch
    if drv:
        out.append(_link(system, 'd6-r1-led1-gnd', 'D6 -> R1 -> LED1 -> GND',
                         {'participant': 'chip U1 (mcu)', 'refs': [pin('D6'), 'BoardPinNet:%s' % drv['name']], 'what': 'D6 (PD6) drives net LED_CONTROL'},
                         {'participant': 'LED1', 'refs': ['CircuitComponentDefinition:%s' % _part(ctx, 'resistor'), 'CircuitComponentDefinition:%s' % _part(ctx, 'led'), 'CircuitNetDefinition:ubc-net-gnd'],
                          'what': 'R1 220 ohm in series, LED1 anode to cathode on GND'},
                         'series-resistor', 'digital', _leg_crossings(ctx, 'D6')[0], verification='partial',
                         und=['the LED forward voltage is assumed, not cited (electrical rules led_current / voh_under_load say undetermined)'], cites=[drv['name']]))
    # g ---- the bridge to the backend, and on to the page
    out.append(_link(system, 'bridge-backend-grpc', 'the Java bridge <-> the backend (gRPC) <-> the Polari page',
                     {'participant': 'host bridge runtime', 'refs': [bridge, 'Runtime:java-bridge'], 'what': 'decodes LightState frames up, routes the on/off command down'},
                     {'participant': 'Polari backend', 'refs': ['Runtime:python-backend', 'LightState:%s' % LIGHT, 'Runtime:typescript-browser'], 'what': 'the LightState row, then the page that shows it'},
                     'grpc', 'rpc', [], protocol=proto, verification='unverified',
                     und=['the gRPC leg (target %s) and the backend -> page leg (http) are not verified on this link here' % (BR.get('grpc_target') or ':3002'),
                          'the page leg is not a separate row: its medium (http) is named in the notes only'],
                     notes='the data crosses gRPC :3002 as LightState rows; the page reads the row over http', cites=['grpcbridge.mapping_basis.SEED_LIGHT_BRIDGE']))
    return out


def _part(ctx, kind):
    return next((c['name'] for c in ctx.tables.get('CircuitComponentDefinition', []) if c.get('circuit_name') == ctx.circuit and c.get('kind') == kind), '?')


def verdict_of(link):
    return VERIFY.get(link['verification'], 'undetermined')
