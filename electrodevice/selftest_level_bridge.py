"""
Selftest — ncg-6: the cross-level bridge (digital design -> circuit).

Run from polari-framework/:
    python3 -m electrodevice.selftest_level_bridge

THE DEMO THAT PROVES THE COUPLING: demo-counter2's LSB drives the
breadboard LED branch through a PinBindingDefinition row — stepping
the clock alternates the REAL ngspice current between the proven
2.6123 mA (lit) and ~0 (dark), and an implausible binding vdd yields
the out-of-range verdict + knob suggestion. Honest refusals: no
bindings, non-vsource target, unknown output node.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from electrodevice import device_derive as dd
from electrodevice import level_bridge as lb
from electrodevice.breadboard_basis import (SEED_BREADBOARDS,
                                            SEED_JUMPERS,
                                            SEED_PLACEMENTS)
from electrodevice.spice_run import ngspice_bin
from hwdigital.logic_basis import SEED_LOGIC_DESIGNS, SEED_LOGIC_NODES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    mgr = types.SimpleNamespace(objectTables={
        'BreadboardDefinition': {}, 'ComponentPlacement': {},
        'BoardJumper': {}, 'PinBindingDefinition': {},
        'LogicBlockDesign': {}, 'LogicBlockNode': {},
        'ElectronicDeviceDefinition': {}, 'SpiceModelCard': {},
        'MaterialScaleDefinition': {}}, db=None)
    seeds = (('BreadboardDefinition', SEED_BREADBOARDS),
             ('ComponentPlacement', SEED_PLACEMENTS),
             ('BoardJumper', SEED_JUMPERS),
             ('PinBindingDefinition', lb.SEED_PIN_BINDINGS),
             ('LogicBlockDesign', SEED_LOGIC_DESIGNS),
             ('LogicBlockNode', SEED_LOGIC_NODES))
    for table, rows in seeds:
        for seed in rows:
            mgr.objectTables[table][seed['name']] = (
                types.SimpleNamespace(**seed))
    device = types.SimpleNamespace(
        name='cnt-solgel-led-resistor', device_type='resistor',
        sim_model='cnt-solgel-percolation', length_m=0.002,
        cross_section_m2=1.4e-8, sigma_s_per_m=0.0,
        resistance_ohm=0.0, derived_at='', provenance_json='{}',
        notes='')
    mgr.objectTables['ElectronicDeviceDefinition'][device.name] = (
        device)
    dd.derive_device(mgr, device, executor=lambda m, n: {
        'ok': True, 'engine': 'analytic.percolation-conductivity',
        'inputs': {}, 'result': {'effectiveSigma': 227.267,
                                 'validity': 'idealized'}})
    return mgr


def _refusals():
    print('honest refusals')
    m = _mgr()
    m.objectTables['PinBindingDefinition'] = {}
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'])
    check('no bindings names the PinBindingDefinition knob',
          not result['ok']
          and result['suggestion']['knob'] == 'PinBindingDefinition')

    m = _mgr()
    m.objectTables['PinBindingDefinition'][
        'bind-counter2-bit0-led'].target_name = 'bba-led'
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'])
    check('driving a non-vsource target refuses plainly',
          not result['ok'] and 'vsource' in result['error'])

    m = _mgr()
    m.objectTables['PinBindingDefinition'][
        'bind-counter2-bit0-led'].output_node = 'cnt2-nope'
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'])
    check('unknown output node lists the real outputs',
          not result['ok'] and 'cnt2-q' in result['error'])

    # Review-fix pins.
    m = _mgr()
    m.objectTables['PinBindingDefinition'][
        'bind-counter2-bit0-led'].bit = 5
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'])
    check('a bit beyond the output width refuses naming the width '
          '(never silently drives 0 V forever)',
          not result['ok'] and 'width 2' in result['error'])

    m = _mgr()
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps='abc')
    check('non-integer steps is a plain error',
          not result['ok'] and 'integer' in result['error'])
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=10 ** 9)
    check('an unbounded steps payload is refused (worker-pinning '
          'guard)', not result['ok']
          and str(lb.MAX_DRIVE_STEPS) in result['error'])
    result = lb.drive_boards_from_design(
        m, 'demo-counter2', 'not-a-dict', ['bb-demo-a'])
    check('non-dict inputs is a plain error',
          not result['ok'] and 'dict' in result['error'])


def _blink():
    print('the coupling demo (real ngspice)')
    if ngspice_bin() is None:
        check('ngspice legs', True,
              'skip-honest: ngspice not on this node')
        return
    m = _mgr()
    probes = ['i(vbba_vpin)']
    lit = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=1, probes=probes)
    lit_ma = -lit['measurements'].get('i(vbba_vpin)', 0) * 1e3
    check('count=1: LSB high drives the LED at the proven current',
          lit['ok'] and lit['designOutputs']['cnt2-q'] == 1
          and abs(lit_ma - 2.6123) < 0.01
          and lit['verdict'] == 'all-driven-legs-in-range',
          f'{lit_ma:.4f} mA, {lit["verdict"]}')

    dark = lb.drive_boards_from_design(
        m, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=2, probes=probes)
    dark_ma = abs(dark['measurements'].get('i(vbba_vpin)', 0)) * 1e3
    check('count=2: LSB low leaves it dark',
          dark['ok'] and dark['designOutputs']['cnt2-q'] == 2
          and dark_ma < 0.01
          and dark['verdict'] == 'no-legs-driven',
          f'{dark_ma:.6f} mA, {dark["verdict"]}')

    weak = _mgr()
    weak.objectTables['PinBindingDefinition'][
        'bind-counter2-bit0-led'].vdd = 1.9  # barely above Vf
    result = lb.drive_boards_from_design(
        weak, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=1, probes=probes)
    check('a weak vdd yields the out-of-range verdict + knob '
          'suggestion',
          result['ok'] and result['verdict'] == 'current-out-of-range'
          and 'vdd' in result['suggestion']['knob'],
          result['verdict'])

    # Review-fix pins: the drive is an ACT, not an edit.
    authored = _mgr()
    row = authored.objectTables['ComponentPlacement']['bba-vpin']
    before = row.params_json
    result = lb.drive_boards_from_design(
        authored, 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=2, probes=probes)  # applies 0.0 V during the run
    check('the authored row reads back UNCHANGED after a drive '
          '(transient mutation, restored on every exit path)',
          result['ok'] and row.params_json == before,
          f'params_json={row.params_json}')

    volted = lb.drive_boards_from_design(
        _mgr(), 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=1, probes=['v(bb_demo_a_r1l)', 'i(vbba_vpin)'])
    check('voltage probes are IGNORED by the LED verdict '
          '(a 3.3 V rail is not a 3300 mA leg)',
          volted['ok']
          and volted['verdict'] == 'all-driven-legs-in-range',
          volted['verdict'])

    auto = lb.drive_boards_from_design(
        _mgr(), 'demo-counter2', {'cnt2-en': 1}, ['bb-demo-a'],
        steps=1)  # probes omitted entirely
    auto_ma = -auto['measurements'].get('i(vbba_vpin)', 0) * 1e3
    check('probes omitted -> one auto current probe per bound '
          'source (the act works standalone)',
          auto['ok'] and abs(auto_ma - 2.6123) < 0.01
          and auto['verdict'] == 'all-driven-legs-in-range',
          f'{auto_ma:.4f} mA')


def main():
    _refusals()
    _blink()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
