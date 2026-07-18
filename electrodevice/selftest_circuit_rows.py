"""
Selftest — ncg-4: circuits promoted to data.

Run from polari-framework/:
    python3 -m electrodevice.selftest_circuit_rows

THE REGRESSION BAR: the row-expressed single LED branch must
reproduce the hand-coded fpga-pin-led renderer's leg current
EXACTLY (same ngspice, same models — proven 2.6123 mA at 3.3 V).
Plus the capacitor promotion (RC t63 lands on tau=RC), the compiler
seam (netlist artifact through the registered row), and the honest
refusals (unknown kind, underived device, undeclared-net
suggestion). ngspice legs skip honestly when the binary is absent.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from electrodevice import circuit_netlist as cn
from electrodevice import device_derive as dd
from electrodevice import spice_run as sr
from electrodevice.circuit_basis import (SEED_CIRCUIT_COMPONENTS,
                                         SEED_CIRCUIT_NETS,
                                         SEED_CIRCUITS)
from polariNoCode.graph_compilers import compile_with

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _device():
    return types.SimpleNamespace(
        name='cnt-solgel-led-resistor', device_type='resistor',
        sim_model='cnt-solgel-percolation', length_m=0.002,
        cross_section_m2=1.4e-8, sigma_s_per_m=0.0,
        resistance_ohm=0.0, derived_at='',
        provenance_json='{}', notes='')


def _executor(sigma):
    return lambda m, n: {
        'ok': True, 'engine': 'analytic.percolation-conductivity',
        'inputs': {}, 'result': {'effectiveSigma': sigma,
                                 'validity': 'idealized'}}


def _mgr():
    mgr = types.SimpleNamespace(objectTables={
        'CircuitDefinition': {}, 'CircuitNetDefinition': {},
        'CircuitComponentDefinition': {},
        'ElectronicDeviceDefinition': {}, 'SpiceModelCard': {},
        'MaterialScaleDefinition': {}}, db=None)
    for seed in SEED_CIRCUITS:
        mgr.objectTables['CircuitDefinition'][seed['name']] = (
            types.SimpleNamespace(**seed))
    for seed in SEED_CIRCUIT_NETS:
        mgr.objectTables['CircuitNetDefinition'][seed['name']] = (
            types.SimpleNamespace(**seed))
    for seed in SEED_CIRCUIT_COMPONENTS:
        mgr.objectTables['CircuitComponentDefinition'][
            seed['name']] = types.SimpleNamespace(**seed)
    device = _device()
    mgr.objectTables['ElectronicDeviceDefinition'][
        device.name] = device
    dd.derive_device(mgr, device, executor=_executor(227.267))
    return mgr


def _generation():
    print('row-driven netlist generation')
    m = _mgr()
    rendered = cn.render_circuit(m, 'led-branch-row')
    net = rendered['netlist']
    check('derived subckt card rides the netlist with provenance',
          '.subckt polari_cnt_solgel_led_resistor' in net
          and 'DERIVED from simulated material data' in net)
    check('element lines from rows (V, X, D + led model)',
          'Vvpin0 pin0 0 DC 3.3' in net
          and 'Xrlimit0 pin0 mid0 polari_cnt_solgel_led_resistor'
          in net and 'Ddled0 mid0 0 polari_led' in net
          and cn.LED_MODEL in net)
    check('declared nets carry no suggestion',
          rendered['suggestions'] == [])

    stray = _mgr()
    stray.objectTables['CircuitComponentDefinition'][
        'rlimit0'].pins_json = '["pin0", "midX"]'
    suggestion = cn.render_circuit(
        stray, 'led-branch-row')['suggestions']
    check('undeclared net is a suggestion naming the row knob',
          suggestion and suggestion[0]['knob']
          == 'CircuitNetDefinition' and 'midX'
          in suggestion[0]['action'])

    bad = _mgr()
    bad.objectTables['CircuitComponentDefinition'][
        'dled0'].kind = 'flux-capacitor'
    try:
        cn.render_circuit(bad, 'led-branch-row')
        refused = False
    except ValueError as exc:
        refused = 'unknown kind' in str(exc)
    check('unknown component kind is a plain error', refused)

    underived = _mgr()
    underived.objectTables['ElectronicDeviceDefinition'][
        'cnt-solgel-led-resistor'].derived_at = ''
    underived.objectTables['ElectronicDeviceDefinition'][
        'cnt-solgel-led-resistor'].derived_resistance_ohm = 0.0
    try:
        cn.render_circuit(underived, 'led-branch-row')
        refused = False
    except ValueError as exc:
        refused = 'derive' in str(exc)
    check('underived device names the derive act', refused)

    # Review-fix pins: missing electrical values are plain errors
    # naming row + param — never silent defaults or raw KeyErrors.
    nodc = _mgr()
    nodc.objectTables['CircuitComponentDefinition'][
        'vpin0'].params_json = '{}'
    try:
        cn.render_circuit(nodc, 'led-branch-row')
        refused = False
    except ValueError as exc:
        refused = "'dc'" in str(exc) and 'vpin0' in str(exc)
    check("a vsource without 'dc' refuses naming row + param "
          '(a defaulted 0 V source is a dead circuit that "works")',
          refused)

    noval = _mgr()
    noval.objectTables['CircuitComponentDefinition'][
        'r1'].params_json = '{}'
    result = cn.run_circuit(noval, 'rc-lowpass-demo')
    check("a resistor without 'ohms' is an honest ok:false "
          '(not a raw KeyError crash)',
          not result['ok'] and "'ohms'" in result['error'])

    badanalysis = _mgr()
    badanalysis.objectTables['CircuitDefinition'][
        'led-branch-row'].analyses_json = '[{"args": "1u 1m"}]'
    try:
        cn.render_circuit(badanalysis, 'led-branch-row')
        refused = False
    except ValueError as exc:
        refused = '"type"' in str(exc)
    check('an analysis entry without "type" is a plain error',
          refused)


def _compiler_seam():
    print('the registered compiler (circuit-netlist)')
    m = _mgr()
    row = types.SimpleNamespace(
        name='circuit-netlist', domain='circuit',
        compiler_ref='electrodevice.circuit_netlist:compile_circuit',
        enabled=True)
    result = compile_with(row, {'manager': m,
                                'circuit_name': 'led-branch-row'})
    check('netlist artifact through the seam',
          result['definition'] is None
          and result['artifacts'][0]['kind'] == 'spice-netlist'
          and 'Generated by Polari'
          in result['artifacts'][0]['text'])


def _regression_and_promotion():
    print('ngspice: hand-renderer regression + capacitor promotion')
    if sr.ngspice_bin() is None:
        check('ngspice legs', True,
              'skip-honest: ngspice not on this node')
        return
    m = _mgr()
    device = m.objectTables['ElectronicDeviceDefinition'][
        'cnt-solgel-led-resistor']

    # The proven hand renderer, one lit pin (pin0 of 0x0001).
    legacy = sr.run_led_grid(
        m, device, 0x0001,
        result_factory=lambda **f: types.SimpleNamespace(
            **{k: v for k, v in f.items() if k != 'manager'}))
    legacy_ma = next(p['current_mA']
                     for p in legacy['outputs']['perPin']
                     if p['pin'] == 0)
    rows = cn.run_circuit(m, 'led-branch-row')
    row_ma = -rows['measurements'].get('i(vvpin0)', 0.0) * 1e3
    check('row circuit reproduces the hand renderer leg current',
          rows['ok'] and abs(row_ma - legacy_ma) < 1e-3,
          f'rows={row_ma:.4f} mA vs legacy={legacy_ma:.4f} mA')
    check('and it is the PROVEN 2.6123 mA figure',
          abs(row_ma - 2.6123) < 0.01, f'{row_ma:.4f} mA')

    rc = cn.run_circuit(m, 'rc-lowpass-demo')
    t63 = rc['measurements'].get('t63', 0.0)
    check('capacitor promotion: RC t63 lands on tau = 10 ms',
          rc['ok'] and abs(t63 - 0.010) < 0.001,
          f't63={t63 * 1e3:.3f} ms')


def main():
    _generation()
    _compiler_seam()
    _regression_and_promotion()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
