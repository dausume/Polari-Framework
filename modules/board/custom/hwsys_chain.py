"""
@module board.custom.hwsys_chain

hsp-1 (L7): the hop SEGMENTS the signal paths are built from — each segment asks the code that owns the check and writes the hop:
  pin_in / pin_out   one board pin walked header <-> chip: header pin (ladder rungs 3 + 5) · E2 crossing (rung 3) · package leg (rung 2) · SocPin (rung 1) · PinFunction (rungs 6-9: multiplexing,
                     electrical limits, lifecycle, existing claims; all ten rungs ride along). A function that IS the transport (USART0 on D0/D1) is ok at rung 8 when the path's own link is that transport.
  serial_chain       the 16U2 side (u2_hops) and the host side (host_hops) both directions share; contract_hop checks the wire contract.
  contract_hop       the pinned wire contract (board.custom.compat) checked against the LightState class: drift = blocked, no live hash to compare = conditional, equal live hash = ok.
Verdict vocabulary: ok | blocked | conditional | unchecked | not-yet | undetermined.
"""
import json

from board.custom import exposure_view as V
from board.custom import hwsys_links as HL
from board.custom.hwsys_context import VERIFY, worst

LIGHT_FW = 'FirmwareSolution:uno-light'


def pin_chain(ctx, canon, fn, purpose=False):
    """-> dict of the five hops of one board pin (header, crossing, leg, socpin, function), un-numbered, in header -> chip order."""
    cs, sp = HL._leg_crossings(ctx, canon)
    c = cs[0] if cs else None
    lad = ctx.ladder(canon, fn, purpose=purpose)
    soc = HL._mcu(ctx).get('soc', '')
    hdr = V.header_pins(c['outer_ref'], ctx.tables)[0] if c else ''
    out = {}
    v, d, x = ctx.rungs_hop(lad, (3, 5), 'header')
    out['header'] = ctx.hop('pin', 'ConnectorPin:%s' % hdr if hdr else '', 'header pin %s (%s)' % (canon, hdr), 'ladder rung 3 + 5', v, d, **x)
    v, d, x = ctx.rungs_hop(lad, (3,), 'crossing')
    out['crossing'] = ctx.hop('enclosure-crossing', 'EnclosureContact:%s' % c['name'] if c else '', 'E2 crossing: %s' % (V.short(c) if c else 'none for ' + canon), 'ladder rung 3', v, d, **x)
    leg = c['inner_ref'] if c else ''
    v, d, x = ctx.rungs_hop(lad, (2,), 'leg')
    out['leg'] = ctx.hop('pin', leg, 'package leg of %s' % canon, 'ladder rung 2', v, d, **x)
    v, d, x = ctx.rungs_hop(lad, (1,), 'socpin')
    out['socpin'] = ctx.hop('pin', 'SocPin:%s' % sp['name'] if sp else '', 'SoC pad %s' % (sp['pin'] if sp else canon), 'ladder rung 1', v, d, **x)
    v, d, x = ctx.rungs_hop(lad, (6, 7, 8, 9), 'function')
    out['function'] = ctx.hop('pin', 'PinFunction:%s:%s' % (sp['name'], fn) if sp else '', '%s as %s' % (sp['pin'] if sp else canon, fn),
                              'ladder rungs 6-9 (multiplexing, electrical limits, lifecycle, existing claims)', v, d, **x)
    out['soc'] = soc
    return out


def pin_in(ctx, canon, fn):
    c = pin_chain(ctx, canon, fn)
    return [c[k] for k in ('header', 'crossing', 'leg', 'socpin', 'function')]


def pin_out(ctx, canon, fn):
    c = pin_chain(ctx, canon, fn)
    return [c[k] for k in ('function', 'socpin', 'leg', 'crossing', 'header')]


def uart_pin(ctx, canon, fn, link):
    """USART0 on D0 / D1: ok at the lifecycle rung when the reservation's reason IS the transport and this path's own link carries it. -> (function hop, crossing hop)."""
    cs, sp = HL._leg_crossings(ctx, canon)
    leg = cs[0]['inner_ref'] if cs else ''
    via = [c for c in HL._e2(ctx.tables, ctx.board) if c['inner_ref'] == leg and c['via'] == 'series-resistor'] or [None]
    lad = ctx.ladder(canon, fn, purpose=True)
    plain = ctx.ladder(canon, 'GPIO', purpose=False)
    r8 = plain['rungs'][7]
    own = (1, 2, 6, 7, 8, 9)
    v, d, x = ctx.rungs_hop(lad, own, 'function')
    note = ''
    if link is not None and r8['verdict'] == 'blocked':
        note = 'reserved for the transport, used as the transport: %s is reserved at rung 8 (%s) and this path IS that transport (link %s, %s); a plain GPIO claim here would still be blocked' \
               % (canon, r8['detail'][:120], link['name'], link['medium'])
        x['transport_satisfied'] = True
    elif r8['verdict'] != 'blocked':
        note = 'no lifecycle reservation was found for %s (rung 8 of a plain claim: %s)' % (canon, r8['verdict'])
    fn_hop = ctx.hop('pin', 'PinFunction:%s:%s' % (sp['name'], fn) if sp else '', '%s as %s (USART0)' % (sp['pin'] if sp else canon, fn),
                     'ladder rungs 1-2 + 6-9 (lifecycle rung 8: transport reservation)', v, (note + ('; ' if note and d else '') + d) if v != 'ok' or note else d, **x)
    cx = via[0]
    r3, r4, r5 = lad['rungs'][2], lad['rungs'][3], lad['rungs'][4]
    v4, note4 = r4['verdict'], ''
    if cx and link is not None and v4 == 'conditional':   # rung 4 names the consumer on the line; here the consumer IS this path's link, so rung 4 is satisfied (rungs 3 and 5 still count)
        v4, note4 = 'ok', 'rung 4: the part on the line is this path\'s link %s (%s %s %s): %s' % (link['name'], cx['via'], cx['via_part'], cx['via_value'], r4['detail'][:140])
    parts = [(3, r3['verdict'], r3['detail']), (4, v4, note4 or r4['detail']), (5, r5['verdict'], r5['detail'])]
    d4 = '; '.join(('rung %d [%s] %s' % (n, v, d[:170])) for n, v, d in parts if v != 'ok' or n == 4)
    cross = ctx.hop('enclosure-crossing', 'EnclosureContact:%s' % cx['name'] if cx else '', 'E2 crossing: %s' % (V.short(cx) if cx else 'none'),
                    'ladder rung 3 + 4 + 5 (rung 4: the consumer is the link)', worst([v for _n, v, _d in parts]), d4,
                    rungs=[{'rung': r['rung'], 'name': r['name'], 'verdict': r['verdict']} for r in lad['rungs']])
    return fn_hop, cross


def contract_check(ctx, need=()):
    """(verdict, detail, extra) — the pinned LightState contract against the class now; `need` = field names the question needs."""
    from board.custom import board_object as BO
    from board.custom import compat
    c = ctx.contract()
    if c is None:
        return 'unchecked', 'no pinned LightState contract on this node', {}
    pinned = set(c['field_map']['fields'])
    now = set(BO._fields('LightState'))
    h = c['contract_hash']
    if pinned != now:
        return 'blocked', 'the pinned contract v%s fields %s differ from the LightState class %s — the wire has drifted' % (c['contract_version'], sorted(pinned ^ now), sorted(now)), {'contract_hash': h}
    live = compat._live(ctx.manager, 'LightState')
    gaps = ['%s has no field %s' % ('LightState v%s' % c['contract_version'], n) for n in need if n not in pinned]
    if live is not None and live[2] and live[2] != h:
        return 'blocked', 'the live exposure hash %s differs from the pinned %s' % (live[2], h), {'contract_hash': h}
    if live is not None and live[2] == h and not gaps:
        return 'ok', 'LightState v%s: the live exposure hash equals the pinned %s and the pinned fields equal the class' % (c['contract_version'], h), {'contract_hash': h}
    base = 'LightState v%s hash %s: the pinned fields equal the class (%d); %s' % (c['contract_version'], h, len(now), 'the live hash was not compared (no live exposure here)' if live is None else 'the live hash equals')
    return ('conditional' if gaps or live is None else 'ok'), base + ('; ' + '; '.join(gaps) if gaps else ''), {'contract_hash': h}


def contract_hop(ctx, what, need=(), gap=''):
    v, d, x = contract_check(ctx, need)
    if gap and v in ('ok', 'conditional'):
        v, d = 'conditional', d + '; ' + gap
    return ctx.hop('contract', 'WireContract:LightState@uno-light', what, 'contract hash', v, d, **x)


def link_hop(ctx, links, key, what):
    lk = links.get(key)
    name = 'SystemLink:%s' % (lk['name'] if lk else '%s:%s' % (ctx.system_name, key))
    return ctx.hop('link', name, what, 'link verification (the row\'s cited verification)', VERIFY.get(lk['verification'], 'undetermined') if lk else 'unchecked',
                   ('%s: %s' % (lk['verification'], lk['undetermined'][:200])) if lk else '', missing_blocks=True)


def firmware_hop(ctx, what, purpose):
    v, d = ctx.purpose_proof(purpose)
    return ctx.hop('firmware', LIGHT_FW, what, 'twin proof (cmod Purpose %s)' % purpose, v, d)


def u2_hops(ctx, links, pad, fn):
    """The 16U2's side: its pad (rungs 1-2 of the ladder on U2) + its USB (UsbInterfaceDefinition verification) + the USB connector crossing."""
    lad = ctx.ladder(pad, fn, chip='atmega16u2')
    v, d, x = ctx.rungs_hop(lad, (1, 2), 'u2 pad')
    sp = lad['soc_pin']
    pad_hop = ctx.hop('pin', 'SocPin:%s' % sp if sp else '', 'U2 pad %s (%s)' % (pad, fn), 'ladder rung 1 + 2 (on U2)', v, d, **x)
    usb = links.get('u2-usb-host')
    uv = VERIFY.get(usb['verification'], 'undetermined') if usb else 'unchecked'
    usb_hop = ctx.hop('pin', 'PackageContact:atmega16u2-32-qfn:29', 'U2 USB D+/D- (legs 29, 30) and its USB interface', 'UsbInterfaceDefinition verification (16U2 verified, CH340 unverified; the bench interface is pending)', uv,
                      usb['undetermined'][:300] if usb else 'link u2-usb-host is not in this system')
    cx = next((c for c in HL._e2(ctx.tables, ctx.board) if c['via_part'] == 'RN3D'), None)
    cross = ctx.hop('enclosure-crossing', 'EnclosureContact:%s' % cx['name'] if cx else '', 'E2 crossing: %s (the USB connector)' % (V.short(cx) if cx else 'none'),
                    'exposure map verification (E2 crossing row)', VERIFY.get(cx['verification'], 'undetermined') if cx else 'unchecked', (cx['verification'] + ': ' + cx['undetermined'][:160]) if cx else '')
    return pad_hop, usb_hop, cross


def host_hops(ctx, links):
    """The host side both directions share: serial port, Java bridge, gRPC link."""
    port = ctx.hop('participant', 'HardwareBridgeDefinition:uno-light-bridge', 'the host serial port the bridge opens', 'none', 'unchecked',
                   'no host-side detection or open of the port has run here (Detect is the bridge panel\'s step)')
    jb = ctx.hop('participant', 'Runtime:java-bridge', 'the Java bridge (decodes frames up, routes the command down)', 'none', 'unchecked', 'the Runtime row is cited; nothing here proves the bridge runs')
    grpc = link_hop(ctx, links, 'bridge-backend-grpc', 'gRPC :3002 between the bridge and the backend')
    return port, jb, grpc
