"""
@module board.custom.twin_c3_pins

pt-4: THE PADS OF THE LIVE C3 TWIN. `pol board twin c3 up --pins` starts the twin on the pin model (the polari-block QEMU, `polari-c3-run --serve --pins`): every pad is
a modelled level, and the pin channel is a TCP port on this device (127.0.0.1 only). This module is the host end of that port:

  plan(row, pins, wires)   what `up` asks the engine for: None (no pin model asked), or {'layout' (the text of the exported layout), 'wires'}; a chip-HAL light build
                           (PIN_SHIM 0) asks for the pin model by itself - its pins exist nowhere else - with the LED-to-sense jumper as a board wire
  levels(tcp)              every pad's level NOW ({pad: '0' | '1' | 'z'}): the device reports them to a client on connect
  set_pad(tcp, pad, lv)    drive a pad from outside ('0' / '1'), or let it go ('z': the pulls and the chip decide); returns the levels before and the changes seen after

The channel's lines are `@<virtual ns> <pad> 0|1|z` out and `<pad> 0|1|z` in (prf-esp-engines/README.md). One client at a time: each call connects, talks and closes.
Pads are LEVELS, not voltages; a pad the outside drives against the chip is logged by the device, not resolved electrically. A pad driven from outside STAYS driven
after the client closes, until it is let go with z.
"""
import socket
import time

LEVELS = ('0', '1', 'z')


class PinsRefused(RuntimeError):
    pass


def plan(row, pins=None, wires=None):
    from board.custom import light_c3_run as R
    from board.custom import sim_layout as SL
    light = row.get('variant') == R.VARIANT
    chip_hal = light and R.on_pads(row)
    if pins is False or (pins is None and not chip_hal):
        if chip_hal:
            raise PinsRefused('this build is the chip HAL (PIN_SHIM 0): without the pin model its pins go nowhere - leave --no-pins off')
        if wires:
            raise PinsRefused('--wires needs the pin model (--pins)')
        return None
    why = R.pin_model()
    if why:
        raise PinsRefused(why)
    if light and not chip_hal:
        raise PinsRefused('this build pins a RAM shim (PIN_SHIM 1): it never touches a pad - generate it with pin_shim 0 for the pin model')
    if wires is None:
        wires = R.pads_for(row)['wires'] if chip_hal else ''
    for w in [x for x in wires.split(',') if x]:
        if not (len(w.split('-')) == 2 and all(p.isdigit() for p in w.split('-'))):
            raise PinsRefused('--wires wants pad-pad pairs (0-1,4-5), got %s' % wires)
    return {'layout': SL.text(SL.layout(R.SIM_CHIP)), 'wires': wires}


def parse(text):
    """The channel's complete lines -> [(ns, pad, level)]; anything else (a half line, a power-cycle mark) is left out."""
    out = []
    for line in text.split('\n'):
        p = line.split()
        if len(p) == 3 and p[0].startswith('@') and p[0][1:].isdigit() and p[1].isdigit() and p[2] in LEVELS:
            out.append((int(p[0][1:]), int(p[1]), p[2]))
    return out


def _read(sock, quiet_s, limit_s):
    """Read until the port has been quiet for `quiet_s` after its first line (or `limit_s` in all)."""
    got, t0, last = b'', time.time(), None
    sock.settimeout(0.05)
    while time.time() - t0 < limit_s and (last is None or time.time() - last < quiet_s):
        try:
            d = sock.recv(65536)
        except socket.timeout:
            continue
        if not d:
            break
        got, last = got + d, time.time()
    return got.decode('ascii', 'replace')


def _open(tcp, host='127.0.0.1'):
    try:
        return socket.create_connection((host, int(tcp)), timeout=5)
    except OSError as e:
        raise PinsRefused('the twin\'s pin port %s:%s does not answer (%s) - is the twin up with --pins, and is no other client holding the port?' % (host, tcp, e))


def levels(tcp, wait_s=3.0):
    with _open(tcp) as s:
        rows = parse(_read(s, 0.3, wait_s))
    if not rows:
        raise PinsRefused('the pin port %s sent no levels within %.1f s (an engine built before the on-connect report?)' % (tcp, wait_s))
    return {pad: lv for _ns, pad, lv in rows}


def set_pad(tcp, pad, level, settle_s=1.0, wait_s=3.0):
    """-> {'before': {pad: level}, 'changes': [(ns, pad, level)] seen within `settle_s` of the write}."""
    if str(level) not in LEVELS:
        raise PinsRefused('a pad is driven 0 or 1, or let go with z - got %r' % (level,))
    with _open(tcp) as s:
        before = {p: lv for _ns, p, lv in parse(_read(s, 0.3, wait_s))}
        if not before:
            raise PinsRefused('the pin port %s sent no levels within %.1f s (an engine built before the on-connect report?)' % (tcp, wait_s))
        if int(pad) not in before:
            raise PinsRefused('pad %s is not in the layout (pads: %s)' % (pad, ' '.join(str(p) for p in sorted(before))))
        s.sendall(('%d %s\n' % (int(pad), level)).encode())
        changes = parse(_read(s, settle_s, settle_s + 0.5))
    return {'before': before, 'changes': changes}
