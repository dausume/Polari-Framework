"""
Selftest — ncg-5: breadboard placements + multi-board composition.

Run from polari-framework/:
    python3 -m electrodevice.selftest_breadboard

THE ACCEPTANCE BAR: the LED branch rebuilt as PLACEMENTS on one
board, the same branch SPLIT ACROSS TWO JUMPERED BOARDS, and the LED
board RE-WRAPPED AS A .subckt COMPONENT must all conduct the same
proven 2.6123 mA — tie-point connectivity, net unioning, and
board-as-component are pure wiring, never electrical drift. Plus the
honest refusals (bad tie grammar, off-board rows, unknown boards).
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from electrodevice import breadboard_netlist as bn
from electrodevice import circuit_netlist as cn
from electrodevice import device_derive as dd
from electrodevice.breadboard_basis import (SEED_BREADBOARDS,
                                            SEED_JUMPERS,
                                            SEED_PLACEMENTS)
from electrodevice.spice_run import ngspice_bin
from polariNoCode.graph_compilers import compile_with

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    mgr = types.SimpleNamespace(objectTables={
        'BreadboardDefinition': {}, 'ComponentPlacement': {},
        'BoardJumper': {}, 'ElectronicDeviceDefinition': {},
        'SpiceModelCard': {}, 'MaterialScaleDefinition': {}},
        db=None)
    for seed in SEED_BREADBOARDS:
        mgr.objectTables['BreadboardDefinition'][seed['name']] = (
            types.SimpleNamespace(**seed))
    for seed in SEED_PLACEMENTS:
        mgr.objectTables['ComponentPlacement'][seed['name']] = (
            types.SimpleNamespace(**seed))
    for seed in SEED_JUMPERS:
        mgr.objectTables['BoardJumper'][seed['name']] = (
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


def _connectivity():
    print('tie-point grammar + connectivity compiler')
    board = types.SimpleNamespace(name='bb-demo-a', rows=30)
    check('tie nets: strips split at the trench, gnd is ground 0',
          bn.tie_net(board, 'r5L') == 'bb_demo_a_r5l'
          and bn.tie_net(board, 'r5R') == 'bb_demo_a_r5r'
          and bn.tie_net(board, 'gnd') == '0')
    try:
        bn.tie_net(board, 'q9X')
        bad = False
    except ValueError as exc:
        bad = 'tie point' in str(exc)
    check('bad tie grammar is a plain error', bad)

    m = _mgr()
    rendered = bn.render_breadboards(m, ['bb-demo-a'])
    net = rendered['netlist']
    check('same tie row = same net (resistor meets source at r1L)',
          'Vbba_vpin bb_demo_a_r1l 0 DC 3.3' in net
          and 'Xbba_rlimit bb_demo_a_r1l bb_demo_a_r5l' in net)
    check('derived card + LED model ride along',
          '.subckt polari_cnt_solgel_led_resistor' in net
          and '.model polari_led' in net)

    off = _mgr()
    off.objectTables['ComponentPlacement'][
        'bba-led'].tiepoints_json = '["r99L", "gnd"]'
    try:
        bn.render_breadboards(off, ['bb-demo-a'])
        refused = False
    except ValueError as exc:
        refused = 'rows 1..30' in str(exc)
    check('a tie beyond the board rows names the placement', refused)

    try:
        bn.render_breadboards(_mgr(), ['bb-nope'])
        refused = False
    except ValueError as exc:
        refused = 'unknown breadboard' in str(exc)
    check('unknown board lists the known ones', refused)


def _jumper_union():
    print('multi-board: jumpers union nets')
    m = _mgr()
    rendered = bn.render_breadboards(m, ['bb-split-1', 'bb-split-2'])
    pins = rendered['netByPlacement']
    check('the jumper makes resistor-out and LED-anode ONE net',
          pins['bb1-rlimit'][1] == pins['bb2-led'][0],
          f"{pins['bb1-rlimit'][1]} vs {pins['bb2-led'][0]}")
    check('a fully-in-set run carries no suggestions',
          rendered['suggestions'] == [])

    half = bn.render_breadboards(m, ['bb-split-1'])
    check('a jumper reaching OUTSIDE the run set is a suggestion '
          'naming jumper + missing board',
          len(half['suggestions']) == 1
          and 'jmp-split-signal' in half['suggestions'][0]['action']
          and 'bb-split-2' in half['suggestions'][0]['action'])

    ranged = _mgr()
    ranged.objectTables['BoardJumper'][
        'jmp-split-signal'].tie_a = 'r99L'
    try:
        bn.render_breadboards(ranged, ['bb-split-1', 'bb-split-2'])
        refused = False
    except ValueError as exc:
        refused = ('jumper' in str(exc)
                   and 'rows 1..30' in str(exc))
    check('a jumper tie beyond the board rows names the jumper',
          refused)


def _control_parity():
    print('control block: parity with the circuit renderer')
    m = _mgr()
    try:
        bn.render_breadboards(m, ['bb-demo-a'],
                              analyses=[{'type': 'ac'}])
        refused = False
    except ValueError as exc:
        refused = 'unknown analysis type' in str(exc)
    check('unknown analysis type raises (never silently dropped)',
          refused)

    capm = _mgr()
    capm.objectTables['ComponentPlacement']['bba-cap'] = (
        types.SimpleNamespace(
            name='bba-cap', board_name='bb-demo-a',
            kind='capacitor',
            params_json='{"farads": 1e-6, "ic": 0}',
            tiepoints_json='["r5L", "gnd"]', description=''))
    rendered = bn.render_breadboards(
        capm, ['bb-demo-a'],
        analyses=[{'type': 'tran', 'args': '0.1m 1m'}])
    check('tran carries uic when a placement declares ic=',
          'tran 0.1m 1m uic' in rendered['netlist'])

    nodc = _mgr()
    nodc.objectTables['ComponentPlacement'][
        'bba-vpin'].params_json = '{}'
    result = bn.run_breadboards(nodc, ['bb-demo-a'])
    check("a vsource without 'dc' refuses naming row + param "
          '(no silent dead source)',
          not result['ok'] and "'dc'" in result['error']
          and 'bba-vpin' in result['error'])


def _compiler_seam():
    print('the registered compiler (breadboard-netlist)')
    m = _mgr()
    row = types.SimpleNamespace(
        name='breadboard-netlist', domain='circuit',
        compiler_ref='electrodevice.breadboard_netlist'
                     ':compile_breadboard',
        enabled=True)
    result = compile_with(row, {'manager': m,
                                'board_names': ['bb-demo-a']})
    check('netlist artifact through the seam',
          result['definition'] is None
          and result['artifacts'][0]['kind'] == 'spice-netlist')


def _currents():
    print('ngspice: placements == rows == split boards == subckt')
    if ngspice_bin() is None:
        check('ngspice legs', True,
              'skip-honest: ngspice not on this node')
        return
    m = _mgr()
    single = bn.run_breadboards(m, ['bb-demo-a'],
                                probes=['i(vbba_vpin)'])
    single_ma = -single['measurements'].get('i(vbba_vpin)', 0) * 1e3
    check('single board conducts the proven 2.6123 mA',
          single['ok'] and abs(single_ma - 2.6123) < 0.01,
          f'{single_ma:.4f} mA')

    split = bn.run_breadboards(m, ['bb-split-1', 'bb-split-2'],
                               probes=['i(vbb1_vpin)'])
    split_ma = -split['measurements'].get('i(vbb1_vpin)', 0) * 1e3
    check('two jumpered boards conduct IDENTICALLY',
          split['ok'] and abs(split_ma - single_ma) < 1e-6,
          f'{split_ma:.4f} mA vs {single_ma:.4f} mA')

    sub = bn.render_board_subckt(m, 'bb-split-2',
                                 {'anode': 'r2L'})
    check('board re-wraps as .subckt with the named port',
          '.subckt bb_split_2 anode' in sub
          and 'anode 0 polari_led' in sub)
    from electrodevice.device_derive import render_card
    device = m.objectTables['ElectronicDeviceDefinition'][
        'cnt-solgel-led-resistor']
    composed = '\n'.join([
        '* board-as-component composition test',
        render_card(device), sub,
        'Vpin pin 0 DC 3.3',
        'Xr pin mid polari_cnt_solgel_led_resistor',
        'Xledboard mid bb_split_2',
        '.control', 'op', 'print i(vpin)', 'quit', '.endc',
        '.end', ''])
    wrapped = cn.run_netlist(composed, label='board-as-component')
    wrapped_ma = -wrapped['measurements'].get('i(vpin)', 0) * 1e3
    check('the wrapped board conducts the same current as a '
          'component', wrapped['ok']
          and abs(wrapped_ma - single_ma) < 1e-6,
          f'{wrapped_ma:.4f} mA')


def _subckt_regressions():
    """Review-fix pins: the three configurations the old string-
    surgery renderer corrupted must now be exact."""
    print('subckt regressions (device card, DC 0 + gnd port, '
          'jumped port)')
    m = _mgr()

    # (1) A board CONTAINING a device placement: the card keeps its
    # own .ends OUTSIDE the board subckt, and the composition
    # conducts the proven current end-to-end.
    sub1 = bn.render_board_subckt(m, 'bb-split-1', {'out': 'r9R'})
    check('device card rides GLOBALLY with its .ends intact',
          sub1.count('.ends') == 2
          and '.ends bb_split_1' in sub1
          and sub1.index('.ends') < sub1.index('.subckt bb_split_1'))
    if ngspice_bin() is not None:
        from electrodevice.spice_run import LED_MODEL
        composed = '\n'.join([
            '* device board as a component', sub1, LED_MODEL,
            'Xboard anode bb_split_1',
            'Dled anode 0 polari_led',
            '.control', 'op', 'print i(v.xboard.vbb1_vpin)',
            'quit', '.endc', '.end', ''])
        run = cn.run_netlist(composed, label='device-board-wrap')
        ma = -run['measurements'].get('i(v.xboard.vbb1_vpin)',
                                      0) * 1e3
        check('a wrapped DEVICE board conducts the proven current',
              run['ok'] and abs(ma - 2.6123) < 0.01, f'{ma:.4f} mA')

    # (2) DC 0 with gnd as an external pin: the value must survive
    # (the old renderer rewrote 'DC 0' into 'DC <port>').
    zero = _mgr()
    zero.objectTables['ComponentPlacement'] = {
        'z-src': types.SimpleNamespace(
            name='z-src', board_name='bb-demo-a', kind='vsource',
            params_json='{"dc": 0}',
            tiepoints_json='["r1L", "gnd"]', description='')}
    zero.objectTables['BoardJumper'] = {}
    sub_zero = bn.render_board_subckt(zero, 'bb-demo-a',
                                      {'g': 'gnd'})
    check("a 0-valued element keeps 'DC 0' when gnd is a port",
          'Vz_src bb_demo_a_r1l g DC 0' in sub_zero)

    # (3) A port tie jumped to another strip lands on the CANONICAL
    # net (the old renderer left it floating).
    jumped = _mgr()
    jumped.objectTables['ComponentPlacement'] = {
        'j-res': types.SimpleNamespace(
            name='j-res', board_name='bb-demo-a', kind='resistor',
            params_json='{"ohms": 100}',
            tiepoints_json='["r2L", "gnd"]', description='')}
    jumped.objectTables['BoardJumper'] = {
        'j-strap': types.SimpleNamespace(
            name='j-strap', board_a='bb-demo-a', tie_a='r1L',
            board_b='bb-demo-a', tie_b='r2L', description='')}
    sub_jumped = bn.render_board_subckt(jumped, 'bb-demo-a',
                                        {'out': 'r2L'})
    check('a jumped port tie resolves to the canonical net '
          '(never floats)', 'Rj_res out 0 100' in sub_jumped)

    try:
        bn.render_board_subckt(jumped, 'bb-demo-a',
                               {'a': 'r1L', 'b': 'r2L'})
        refused = False
    except ValueError as exc:
        refused = 'same net' in str(exc)
    check('two ports landing on one net (via the jumper) refuse '
          'plainly', refused)


def main():
    _connectivity()
    _jumper_union()
    _control_parity()
    _compiler_seam()
    _currents()
    _subckt_regressions()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
