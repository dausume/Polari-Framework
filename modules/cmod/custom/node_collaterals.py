"""
@module cmod.custom.node_collaterals

bss-9 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md sections 2b, 6b): THE COLLATERALS A NODE RUN MEASURES BEYOND THE WIRE - small, separated from node_run:

  port_watches(variant, pins, budget)        a pin with no jumper is still read from what the firmware DRIVES: the PORTx and DDRx register words of its port
                                             (data addresses from the chip's register snapshot, board.custom.registers: io address + 0x20), watched like a
                                             struct field; -> (['--watch', ...], {pin: (port_name, ddr_name, bit)}, words)
  driven_level(lines, port, ddr, bit, at)    the level the port drives at a cycle: 'high' / 'low', or None with why (the DDR bit is input; no watch)
  net_current(c, level, step_s)              a net-current collateral: the LED branch (the pin at the rail or at ground, the series R from the collateral's
                                             notes `R=<ohms>`, the generic indicator-LED model electrodevice.custom.spice_run.LED_MODEL - a labelled knob) run
                                             by ngspice in BATCH (the binary; the shared library is not on this host) as a transient with TMAX = the node's
                                             step; -> the words with the current, the bound's verdict, every knob named; a refusal in words when the binary
                                             or the R is missing
  temperature(manager, c, power_w, dt_s)     a temperature collateral: the part's rise over the edge's duration from its PartThermalModel (pcb) Foster
                                             network - rise = sum R_i (1 - exp(-t / tau_i)) x P (the Cauer / Foster forms agree for one pulse); the
                                             refusal names the missing row
"""
import math
import os
import re
import subprocess
import tempfile

from cmod.custom import config_rows as R

VCC_V = 5.0            # KNOB: the UNO's logic rail (the USB 5 V; the pin's output resistance is not modelled, said)
TRAN_STEPS = 20        # KNOB: the transient runs this many node steps so a DC level settles
_REG_IO_OFFSET = 0x20  # avr: an I/O-space address + 0x20 is its data-memory address (the 328P's datasheet, "I/O Memory")


def _registers(mcu='atmega328p'):
    try:
        from board.custom import registers as RG
        d = RG.load(mcu)
        return d.get('registers', d) or {}
    except Exception:  # noqa: BLE001 - board absent: no snapshot
        return {}


def port_watches(variant, pins, budget, mcu='atmega328p'):
    regs = _registers(mcu)
    out, by_pin, words, used = [], {}, [], []
    for pin in sorted(pins):
        m = re.match(r'^P([BCD])(\d)$', pin)
        if not m:
            words.append('%s: not a port pin (PB/PC/PDn): the driven level is not read' % pin)
            continue
        port, bit = m.group(1), int(m.group(2))
        names = ('PORT%s' % port, 'DDR%s' % port)
        if any(n not in regs for n in names):
            words.append('%s: the register snapshot of %s has no %s' % (pin, mcu, ' / '.join(n for n in names if n not in regs)))
            continue
        for n in names:
            if n not in used:
                if len(used) + 1 > budget:
                    words.append('%s: no watch left for %s (the twin watches 8 words per run)' % (pin, n))
                    break
                reg = regs[n]
                addr = int(str(reg['addr']), 0) + (_REG_IO_OFFSET if reg.get('space') == 'io' else 0)
                out += ['--watch', '0x%X/1=%s' % (addr, n)]
                used.append(n)
        if all(n in used for n in names):
            by_pin[pin] = (names[0], names[1], bit)
    return out, by_pin, words


def driven_level(lines, port, ddr, bit, at):
    """-> ('high' | 'low', words) or (None, why)."""
    if port not in lines or ddr not in lines:
        return None, 'no %s / %s watch' % (port, ddr)
    try:
        d = int(float(lines[ddr].at(at) if lines[ddr].at(at) is not None else 0))
        p = int(float(lines[port].at(at) if lines[port].at(at) is not None else 0))
    except (TypeError, ValueError):
        return None, 'the %s / %s words were not numbers' % (port, ddr)
    if not (d >> bit) & 1:
        return None, '%s bit %d is an input (DDR bit 0): the firmware does not drive it' % (ddr, bit)
    return ('high' if (p >> bit) & 1 else 'low'), '%s bit %d' % (port, bit)


def _bound_verdict(bound, value):
    """bound: 'lo..hi' | '<=x' | '>=x' (amperes), -> ' (bound ...: met|UNMET)' or ''."""
    b = (bound or '').strip()
    if not b:
        return ''
    try:
        if '..' in b:
            lo, hi = (float(x) for x in b.split('..', 1))
            ok = lo <= value <= hi
        elif b.startswith('<='):
            ok = value <= float(b[2:])
        elif b.startswith('>='):
            ok = value >= float(b[2:])
        else:
            return ' (bound %r: not understood - use lo..hi, <=x or >=x in amperes)' % b
    except ValueError:
        return ' (bound %r: not a number)' % b
    return ' (bound %s A: %s)' % (b, 'met' if ok else 'UNMET')


def _ngspice():
    try:
        from electrodevice.custom import spice_run as SR
        return SR.ngspice_bin(), SR.LED_MODEL
    except Exception:  # noqa: BLE001
        return None, ''


def net_current(c, level, step_s):
    """level: 'high' | 'low' | None (the pin's level at the met cycle)."""
    m = re.search(r'\bR\s*=\s*([0-9.]+)\s*(k?)', c.get('notes') or '')
    if not m:
        return 'net-current %s: unmeasured - the collateral names no series resistance (write R=<ohms> in its notes; the kit\'s LED resistor is 220 ohm, board.custom.kit_parts)' % c['signal']
    r_ohm = float(m.group(1)) * (1000.0 if m.group(2) else 1.0)
    if level is None:
        return 'net-current %s: unmeasured - the pin\'s level at the node is not known (no jumper and no driven level)' % c['signal']
    binary, led_model = _ngspice()
    if not binary:
        return 'net-current %s: unmeasured - no ngspice binary on this host (electrodevice.custom.spice_run.capability names the knob NGSPICE_BIN)' % c['signal']
    step = step_s if step_s and step_s > 0 else 1e-6
    v = VCC_V if level == 'high' else 0.0
    deck = ('* bss-9 the LED branch at node level %s\nVpin n1 0 DC %g\nR1 n1 n2 %g\nD1 n2 0 polari_led\n%s\n.tran %g %g\n.control\nrun\nprint i(vpin)\n.endc\n.end\n'
            % (level, v, r_ohm, led_model, step, TRAN_STEPS * step))
    with tempfile.TemporaryDirectory(prefix='node-net-') as d:
        path = os.path.join(d, 'branch.cir')
        open(path, 'w').write(deck)
        try:
            p = subprocess.run([binary, '-b', path], capture_output=True, text=True, timeout=60, cwd=d)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 'net-current %s: unmeasured - ngspice did not run: %s' % (c['signal'], e)
    vals = re.findall(r'^\s*\d+\s+[-+0-9.eE]+\s+([-+0-9.eE]+)\s*$', p.stdout, re.M)
    if not vals:
        return 'net-current %s: unmeasured - ngspice printed no i(vpin) (exit %s): %s' % (c['signal'], p.returncode, (p.stderr or p.stdout)[-160:].strip())
    amps = -float(vals[-1])   # the source convention: current out of the pin into the branch is negative at the source
    return ('net-current %s: %.2f mA through R %g ohm + the LED at the pin %s (%s V) - ngspice batch .tran step %.3g us x %d, settled%s; knobs: VCC %g V, the generic '
            'indicator-LED model (electrodevice.custom.spice_run.LED_MODEL, ~2 V forward: measure the kit LED\'s Vf to replace it)'
            % (c['signal'], amps * 1e3, r_ohm, level, v, step * 1e6, TRAN_STEPS, _bound_verdict(c.get('bound'), amps), VCC_V))


def temperature(manager, c, power_w, dt_s):
    rows = [r for r in R.rows(manager, 'PartThermalModel') if c['signal'] in (r.get('name'), r.get('ref'), r.get('part_key'))] if getattr(manager, 'objectTables', None) is not None else []
    if not rows:
        return 'temperature %s: unmeasured - no PartThermalModel row for it (pcb: a datasheet Foster network R / tau per stage; give one)' % c['signal']
    import json
    try:
        foster = json.loads(rows[0].get('foster_json') or '[]')
    except ValueError:
        foster = []
    if not foster:
        return 'temperature %s: unmeasured - its PartThermalModel %s has no Foster stages' % (c['signal'], rows[0]['name'])
    if power_w is None:
        return 'temperature %s: unmeasured - no power on the part (a net-current collateral on the same node gives it)' % c['signal']
    rise = sum(float(r_) * (1 - math.exp(-dt_s / float(tau))) * power_w for r_, tau in foster if float(tau) > 0)
    return 'temperature %s: +%.4f K over the edge\'s %.3g ms at %.3g mW (Foster %s, %s%s)' % (c['signal'], rise, dt_s * 1e3, power_w * 1e3, rows[0]['name'],
                                                                                          rows[0].get('origin', ''), _bound_verdict(c.get('bound'), rise).replace(' A:', ' K:'))
