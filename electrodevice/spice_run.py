"""
@module electrodevice.spice_run

ngspice circuit tests (capability-honest: absence of the binary is a
named refusal, never a fake result). The first circuit is the one the
FPGA actually drives: each lit pixel of the 4x4 grid is an FPGA pin
at VDD pushing current through the material-derived resistor into an
LED — 16 branches, currents and verdicts per pin.

The pixels input can come STRAIGHT from the live LedMatrix4x4State
row, so the circuit test evaluates the grid's CURRENT commanded
state: object -> FPGA pins -> (simulated) silicon -> SPICE currents.

@consumers
  - electrodevice.device_api (circuit-test knob act)
  - electrodevice.selftest_electrodevice
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from electrodevice.device_derive import render_card, subckt_name

#: Generic indicator-LED compact model (~2 V forward at mA currents).
LED_MODEL = '.model polari_led D(Is=1e-18 N=1.8 Rs=2)'

#: Honest current window for a small indicator LED.
LED_MIN_A, LED_MAX_A = 1e-3, 20e-3


def ngspice_bin():
    env = os.environ.get('NGSPICE_BIN')
    if env and os.path.exists(env):
        return env
    found = shutil.which('ngspice')
    if found:
        return found
    home = os.path.expanduser('~/tools/ngspice/bin/ngspice')
    return home if os.path.exists(home) else None


def capability():
    binary = ngspice_bin()
    return {'ok': True, 'engine': 'ngspice',
            'available': binary is not None,
            'binary': binary or '',
            'suggestion': None if binary else {
                'knob': 'NGSPICE_BIN env var',
                'how': 'build ngspice --with-x=no into ~/tools/'
                       'ngspice (no sudo needed) or point '
                       'NGSPICE_BIN at an existing binary'}}


def render_led_grid_netlist(device, pixels, vdd=3.3, pins=16):
    """One branch per pin: Vpin -> device subckt -> LED -> gnd."""
    card = render_card(device)
    if card is None:
        return None
    sub = subckt_name(device)
    lines = [f'* Polari fpga-pin-led grid test — {device.name}, '
             f'pixels=0x{pixels:04X}, vdd={vdd}',
             card, LED_MODEL]
    for pin in range(pins):
        lit = (pixels >> pin) & 1
        volts = vdd if lit else 0.0
        lines += [
            f'Vpin{pin} pin{pin} 0 DC {volts}',
            f'X{pin} pin{pin} mid{pin} {sub}',
            f'D{pin} mid{pin} 0 polari_led',
        ]
    lines += ['.control', 'op']
    # One print per line: multi-variable print emits a table the
    # name=value parser can't read.
    lines += [f'print i(vpin{pin})' for pin in range(pins)]
    lines += ['quit', '.endc', '.end', '']
    return '\n'.join(lines)


def _parse_currents(stdout, pins):
    """ngspice op output: lines like 'i(vpin3) = -5.23e-03' (source
    convention: current INTO the branch is negative at the source)."""
    currents = {}
    for match in re.finditer(
            r'i\(vpin(\d+)\)\s*=\s*([-+0-9.eE]+)', stdout):
        currents[int(match.group(1))] = -float(match.group(2))
    return [currents.get(pin, 0.0) for pin in range(pins)]


def run_led_grid(manager, device, pixels, vdd=3.3,
                 result_factory=None):
    binary = ngspice_bin()
    if binary is None:
        return {'ok': False,
                'error': 'ngspice not available on this node',
                'capability': capability()}
    netlist = render_led_grid_netlist(device, pixels, vdd)
    if netlist is None:
        return {'ok': False,
                'error': f'device "{device.name}" has never been '
                         'derived — POST {"action": "derive"} first'}
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'grid.cir')
        with open(path, 'w') as f:
            f.write(netlist)
        proc = subprocess.run([binary, '-b', path],
                              capture_output=True, text=True,
                              timeout=120)
    currents = _parse_currents(proc.stdout, 16)
    lit = [(pixels >> pin) & 1 for pin in range(16)]
    per_pin = []
    ok_count = 0
    for pin in range(16):
        amps = currents[pin]
        if lit[pin]:
            in_range = LED_MIN_A <= amps <= LED_MAX_A
            ok_count += in_range
            per_pin.append({'pin': pin, 'lit': True,
                            'current_mA': round(amps * 1e3, 4),
                            'inRange': in_range})
        else:
            per_pin.append({'pin': pin, 'lit': False,
                            'current_mA': round(amps * 1e3, 6)})
    lit_count = sum(lit)
    verdict = ('no-pixels-lit' if lit_count == 0 else
               'all-leds-in-range' if ok_count == lit_count else
               'current-out-of-range')
    suggestion = None
    if verdict == 'current-out-of-range' and lit_count:
        sample = next(p for p in per_pin if p['lit'])
        direction = ('raise' if sample['current_mA'] < LED_MIN_A * 1e3
                     else 'lower')
        suggestion = {
            'knob': f'/api/electrodevice/devices/{device.name} '
                    'geometry (length_m / cross_section_m2) or the '
                    'sim model volumeFraction',
            'why': f'lit-pin current {sample["current_mA"]} mA is '
                   f'outside {LED_MIN_A * 1e3:.0f}-'
                   f'{LED_MAX_A * 1e3:.0f} mA',
            'how': f'{direction} conductance: adjust geometry and '
                   'POST {"action": "derive"} again',
        }
    outputs = {'perPin': per_pin, 'litCount': lit_count,
               'inRangeCount': ok_count,
               'totalCurrent_mA': round(sum(
                   c for c, l in zip(currents, lit) if l) * 1e3, 3)}
    if result_factory is None:
        from electrodevice.device_basis import CircuitRunResult
        result_factory = CircuitRunResult
    stamp = datetime.now(timezone.utc).isoformat()
    row = result_factory(
        name=f'{device.name}-run-{stamp[11:19].replace(":", "")}',
        device_name=device.name, circuit='fpga-pin-led',
        inputs_json=json.dumps({'pixels': pixels, 'vdd': vdd,
                                'resistance_ohm':
                                    device.resistance_ohm}),
        outputs_json=json.dumps(outputs), verdict=verdict,
        engine=f'ngspice ({os.path.basename(binary)})',
        ran_at=stamp, notes='', manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report = {'ok': True, 'device': device.name, 'verdict': verdict,
              'outputs': outputs, 'resultRow': row.name}
    if suggestion:
        report['suggestion'] = suggestion
    return report
