"""
Selftest for fp-1 (FET_CELL_POWER_SILICON_PLAN §1): FET + cell
power — static/leakage, sensitivity, per-state cell leakage with
the stack effect, dynamic from the Liberty energy tables, budgets,
Liberty leakage_power emission, score-term + graph seeds.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_power

Pure model + synthetic Liberty — no ngspice needed.
"""

import json
import sys

from cntfet import cnt_derive as cd
from cntfet import cnt_power as cp
from cntfet import selftest_cntfet as st
from cntfet.cnt_cell_library import _liberty_library
from cntfet.cnt_cell_scoring import parse_liberty
from cntfet.cnt_device_viz import device_model

_results = []
DEV = 'cnt-aligned-s1'


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _close(a, b, rel=1e-6):
    return a is not None and b is not None and \
        abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


def _state(report, when):
    return next(s for s in report['states'] if s['when'] == when)


def main():
    mgr = st._mgr()
    st._seed_all(mgr)
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    mgr.objectTables.setdefault('PowerBudget', {})
    dev = cd.get_row(mgr, 'AlignedCNTFETDevice', DEV)
    res = cd.derive_device(
        mgr, dev, parameter_factory=st._row_factory(mgr, 'CNTFETParameterRow'))
    check('fp-1: S1 device derives', res.get('ok'), str(res.get('error')))
    id_fn, p, device, refusal = device_model(mgr, DEV)
    check('fp-1: device_model resolves the S1 frame', refusal is None)

    # ---- 1. FET static power -----------------------------------------
    k = dict(cp.POWER_KNOBS)
    fet = cp.fet_power(id_fn, p, device, k, manager=mgr)
    ioff = id_fn(0.0, k['vdd_v'])
    print(f'   S1: Ioff = {ioff:.4g} A, P_static = Vdd·Ioff = '
          f'{fet["static_w"]:.4g} W, SS(model) = '
          f'{fet["sensitivity"]["ss_model_v_per_dec"] * 1e3:.2f} mV/dec, '
          f'Vt = {fet["sensitivity"]["vt_model_v"]:.3f} V, C_gg = '
          f'{fet["dynamic"]["c_gg_f"]:.3g} F, E_switch = '
          f'{fet["dynamic"]["e_switch_j"]:.3g} J, P_dyn(α=0.1, 1 GHz) = '
          f'{fet["dynamic"]["p_dyn_w"]:.3g} W')
    check('fp-1 FET: static power = Vdd·Ioff from the model, knobs '
          'echoed, gate/GIDL are named refusals (not zeros)',
          _close(fet['static_w'], 0.6 * ioff)
          and fet['knobs']['stack_factor'] == 0.5
          and fet['knobs']['gate_leakage'] == 'unmodelled'
          and 'refusal' in fet['leakage_components']['gate']
          and 'refusal' in fet['leakage_components']['gidl']
          and 'value_w' not in fet['leakage_components']['gate'])
    dyn = fet['dynamic']
    check('fp-1 FET: E_switch = C_gg·Vdd² and P_dyn = α·f·E with '
          'C_gg = Cinv·Lg + C_par (S1 parasitics row = 0 F, named)',
          _close(dyn['e_switch_j'], dyn['c_gg_f'] * 0.36)
          and _close(dyn['p_dyn_w'], 0.1 * 1e9 * dyn['e_switch_j'])
          and _close(dyn['c_gg_f'], p['cinv_f_per_m'] * p['lg_m'])
          and 'CNTParasitics' in dyn['c_par_source'])

    # ---- 2. sensitivity ----------------------------------------------
    sens = fet['sensitivity']
    ss = sens['ss_model_v_per_dec']
    check('fp-1 FET: −50 mV Vt shift multiplies Ioff by 10^(0.05/SS); '
          'dlog10(Ioff)/dVt = −1/SS; +50 mV divides by the same',
          _close(sens['ioff_at_vt_shift_a']['-50mV'],
                 ioff * 10 ** (0.05 / ss))
          and _close(sens['ioff_at_vt_shift_a']['+50mV'],
                     ioff * 10 ** (-0.05 / ss))
          and _close(sens['dlog10_ioff_dvt_per_v'], -1.0 / ss))
    t = sens['ioff_vs_t_a']
    check('fp-1 FET: Ioff rises monotonically with T (300 → 350 → '
          '400 K via φt-scaled SS) and the approximation is stated',
          _close(t['300K'], ioff) and t['300K'] < t['350K'] < t['400K']
          and 'approximation' in sens['approximation'])

    # ---- 3. cell leakage states --------------------------------------
    ioff_n, ioff_p = cp._twin_ioffs(id_fn, p, 0.6)
    inv = cp.cell_leakage_states('cinv', 1, ioff_n, ioff_p, k)
    s0, s1 = _state(inv, '!A'), _state(inv, 'A')
    check('fp-1 cell: inverter input 0 → Y=1, n off, leaks Ioff_n '
          'through the pull-down; input 1 → Y=0, p off, leaks Ioff_p',
          s0['output'] == 1 and 'pull-down' in s0['off_network']
          and s0['paths'][0]['network'].startswith('pull-down')
          and _close(s0['i_leak_a'], ioff_n)
          and s1['output'] == 0 and 'pull-up' in s1['off_network']
          and _close(s1['i_leak_a'], ioff_p))
    nand = cp.cell_leakage_states('cnand2', 1, ioff_n, ioff_p, k)
    n00, n01, n10, n11 = (_state(nand, w) for w in
                          ('!A*!B', '!A*B', 'A*!B', 'A*B'))
    check('fp-1 cell: NAND2 state 00 has TWO series off n devices → '
          'stack factor 0.5 applied, leakage LOWER than 01/10 (one '
          'off device = Ioff); 11 = two parallel off p = 2·Ioff_p',
          n00['paths'][0]['off_in_series'] == 2
          and _close(n00['i_leak_a'], 0.5 * ioff_n)
          and _close(n01['i_leak_a'], ioff_n)
          and _close(n10['i_leak_a'], ioff_n)
          and n00['i_leak_a'] < n01['i_leak_a']
          and _close(n11['i_leak_a'], 2 * ioff_p))
    check('fp-1 cell: mean static over states = Vdd · mean(I_leak); '
          'x2 drive doubles it; stack_factor knob honoured (0.25 → '
          'state 00 = 0.25·Ioff)',
          _close(nand['mean_static_w'],
                 0.6 * (0.5 + 1 + 1 + 2) / 4 * ioff_n)
          and _close(cp.cell_leakage_states(
              'cnand2', 2, ioff_n, ioff_p, k)['mean_static_w'],
              2 * nand['mean_static_w'])
          and _close(_state(cp.cell_leakage_states(
              'cnand2', 1, ioff_n, ioff_p,
              {**k, 'stack_factor': 0.25}), '!A*!B')['i_leak_a'],
              0.25 * ioff_n))
    nand3 = cp.cell_leakage_states('cnand3', 1, ioff_n, ioff_p, k)
    xor = cp.cell_leakage_states('cxor2', 1, ioff_n, ioff_p, k)
    check('fp-1 cell: NAND3 000 = 3 series off → 0.25·Ioff; 010 (on '
          'device inside the off stack) = 0.5·Ioff; composed XOR2 '
          'flattens (10 FETs) and every state has an output value',
          _close(_state(nand3, '!A*!B*!C')['i_leak_a'], 0.25 * ioff_n)
          and _close(_state(nand3, '!A*B*!C')['i_leak_a'], 0.5 * ioff_n)
          and xor['fet_count'] == 10
          and all(s['output'] in (0, 1) and not s['contention']
                  for s in xor['states']))

    # ---- 4. cell_power: dynamic refuses by name, then resolves ------
    no_lib = cp.cell_power(mgr, DEV, 'cnand2', 1, k)
    check('fp-1 cell_power: no library run → dynamic refuses BY NAME '
          '(characterize-cells), static still reported',
          no_lib['ok'] and no_lib['dynamic'] is None
          and no_lib['dynamic_w'] is None
          and 'characterize-cells' in no_lib['dynamic_refusal']
          and _close(no_lib['static_w'], nand['mean_static_w']))

    def _pt(scale):
        return {'cell_rise_s': 5e-13 * scale, 'cell_fall_s': 5e-13 * scale,
                'rise_transition_s': 6e-13 * scale,
                'fall_transition_s': 6e-13 * scale,
                'energy_rise_j': 2e-18 * scale, 'energy_fall_j': 1e-18}
    blocks = [{'libertyName': 'INVX1', 'function': '(!A)',
               'inputs': ['A'], 'inputCap_f': 1e-17,
               'leakage': cp.leakage_blocks_for('cinv', 1, ioff_n,
                                                ioff_p, k),
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(1)] * 3] * 3}}},
              {'libertyName': 'NAND2X1', 'function': '(!(A*B))',
               'inputs': ['A', 'B'], 'inputCap_f': 1e-17,
               'leakage': cp.leakage_blocks_for('cnand2', 1, ioff_n,
                                                ioff_p, k),
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(2)] * 3] * 3},
                        'B': {'pin': 'B', 'sense': 'negative',
                              'tables': [[_pt(2)] * 3] * 3}}},
              {'libertyName': 'NOR2X1', 'function': '(!(A+B))',
               'inputs': ['A', 'B'], 'inputCap_f': 1e-17,
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(1)] * 3] * 3}}}]
    lib_text = _liberty_library(0.6, [1e-12, 2e-12, 4e-12],
                                [1e-17, 2e-17, 4e-17], blocks)
    st._row_factory(mgr, 'CellCharacterizationRun')(
        name='s1-lib-test', device=DEV, cell='library:INVX1,NAND2X1',
        liberty_text=lib_text, ran_at='2026-08-27T00:00:00', vdd_v=0.6)
    with_lib = cp.cell_power(mgr, DEV, 'cnand2', 1, k)
    # mid grid: load 0.02 fF → ½·C·V² = 3.6 aJ; E_int = (4 + 1)/2 = 2.5 aJ
    check('fp-1 cell_power: with a library row the dynamic energy '
          'resolves at the mid-grid point (E_int 2.5 aJ + ½C_L·Vdd² '
          '3.6 aJ), P_dyn = α·f·E, total = static + dynamic',
          with_lib['run'] == 's1-lib-test'
          and with_lib['dynamic'] is not None
          and _close(with_lib['dynamic']['e_dyn_j'], 6.1e-18, 1e-3)
          and _close(with_lib['dynamic_w'], 0.1 * 1e9 * 6.1e-18, 1e-3)
          and _close(with_lib['total_w'],
                     with_lib['static_w'] + with_lib['dynamic_w']))
    lib = cp.library_power(mgr, DEV, k)
    check('fp-1 library_power: every cell of the run (INVX1, NAND2X1, '
          'NOR2X1), totals summed, none refused',
          [c['libertyName'] for c in lib['cells']]
          == ['INVX1', 'NAND2X1', 'NOR2X1']
          and lib['dynamic_refused'] == []
          and _close(lib['total_static_w'],
                     sum(c['static_w'] for c in lib['cells'])))

    # ---- 5. budgets ----------------------------------------------------
    b_pass = dict(cp.SEED_POWER_BUDGETS[1])
    b_fail = {**b_pass, 'name': 'tight', 'max_static_w': 1e-12}
    r_pass = cp.check_budget(with_lib, b_pass)
    r_fail = cp.check_budget(with_lib, b_fail)
    check('fp-1 budget: check_budget passes the 1 nW / 1 µW prior with '
          'margins, FAILS a 1 pW limit naming max_static_w, and marks '
          'an absent quantity unevaluated (not passed)',
          r_pass['pass'] and r_pass['failed'] == []
          and all(c['margin'] > 0 for c in r_pass['checks'])
          and not r_fail['pass'] and r_fail['failed'] == ['max_static_w']
          and next(c for c in r_fail['checks']
                   if c['limit'] == 'max_static_w')['margin'] < 0
          and cp.check_budget({'static_w': 1e-10},
                              cp.SEED_POWER_BUDGETS[2])['checks'][0]['pass']
          is None)
    for seed in cp.SEED_POWER_BUDGETS:
        st._row_factory(mgr, 'PowerBudget')(**seed)
    br = cp.budget_report(mgr, DEV, k)
    mapped = [t for t in br['targets'] if t['mapped']]
    other = [t for t in br['targets'] if not t['mapped']]
    check('fp-1 budget_report is TARGET-scoped: S1 is engineered for '
          'low-power-logic (its FET + cell checks are pass/fail there); '
          'every other target is informational (would / would not meet, '
          'never a failure); density stays unevaluated until a layout '
          'area exists',
          br['ok'] and br['engineeredFor']['targets'] == ['low-power-logic']
          and len(mapped) == 1 and mapped[0]['status'] in ('meets', 'misses')
          and any(r['scope'] == 'fet' and r['pass'] for r in br['results'])
          and sum(r['scope'] == 'cell' for r in br['results']) == 3
          and all(t['status'] == 'not-a-target' for t in other)
          and any(t['target'] == 'high-performance-logic'
                  and any(c['limit'] == 'max_density_w_per_cm2'
                          and c['pass'] is None
                          for r in t['checks'] for c in r['checks'])
                  for t in other)
          and len(cp.PowerBudget.__init__.__code__.co_varnames) > 5)

    # ---- 6. Liberty emission ------------------------------------------
    parsed = parse_liberty(lib_text)
    leak = cp.parse_leakage(lib_text)
    check('fp-1 Liberty: leakage_power () { when : "!A"; value : uW; } '
          'blocks + cell_leakage_power emitted per input state, '
          'parse_liberty STILL reads the timing/energy tables, and a '
          'block without `leakage` emits nothing new',
          'leakage_power () {\n      when : "!A";\n      value : '
          in lib_text
          and set(parsed['cells']) == {'INVX1', 'NAND2X1', 'NOR2X1'}
          and len(parsed['cells']['NAND2X1']['arcs']['B']) == 6
          and set(leak['NAND2X1']['states'])
          == {'!A*!B', '!A*B', 'A*!B', 'A*B'}
          and _close(leak['NAND2X1']['states']['!A*!B'],
                     n00['p_static_w'] * 1e6, 1e-4)
          and _close(leak['NAND2X1']['cell_leakage_uW'],
                     nand['mean_static_w'] * 1e6, 1e-4)
          and 'NOR2X1' not in leak
          and lib_text.count('leakage_power ()') == 6)
    # grammar: every leakage_power group is balanced and holds exactly
    # a when + a value attribute (what OpenSTA's Liberty reader expects)
    import re
    groups = re.findall(r'leakage_power \(\) \{(.*?)\}', lib_text, re.S)
    check('fp-1 Liberty grammar: each group = `when : "<expr>";` + '
          '`value : <num>;` with the header\'s leakage_power_unit 1uW',
          len(groups) == 6
          and all(re.fullmatch(r'\s*when : "[!A-Z*]+";\s*value : '
                               r'[-+0-9.eE]+;\s*', g) for g in groups)
          and 'leakage_power_unit : "1uW";' in lib_text)

    # ---- 7. score terms + frame ---------------------------------------
    frame = cp.power_frame(fet, with_lib)
    check('fp-1 score: three seed terms (lower better, min-max on the '
          'log10 range knobs) and power_frame supplies every raw key '
          'they cite',
          [t['name'] for t in cp.SEED_POWER_SCORE_TERMS]
          == ['fet-static-power', 'cell-static-power',
              'cell-dynamic-energy']
          and all(not t['is_positive'] for t in cp.SEED_POWER_SCORE_TERMS)
          and json.loads(cp.SEED_POWER_SCORE_TERMS[0]
                         ['normalization_json'])
          == {'method': 'min-max', 'min': -12.0, 'max': -6.0}
          and all(frame.get(v['raw']) is not None
                  for v in cp.POWER_TERMS.values())
          and _close(frame['log10_static_w'],
                     __import__('math').log10(fet['static_w'])))

    # ---- 8. graphs + rows --------------------------------------------
    names = [g['name'] for g in cp.SEED_CNT_POWER_GRAPHS]
    check('fp-1 graphs: three seeds round-trip (graphConfig JSON, log y '
          'on the leakage graphs) and CURVE_BUILDERS names them',
          names == ['cnt-device-leakage-vs-vt',
                    'cnt-device-cell-leakage-states',
                    'cnt-device-power-breakdown']
          and all(json.loads(g['definition'])['graphConfig']['options']
                  ['yType'] == 'log' for g in cp.SEED_CNT_POWER_GRAPHS)
          and set(cp.CURVE_BUILDERS) == {'leakage-vs-vt',
                                         'cell-leakage-states',
                                         'power-breakdown'})
    rows_vt = cp.CURVE_BUILDERS['leakage-vs-vt'](id_fn, p, device, mgr, k)
    rows_st = cp.CURVE_BUILDERS['cell-leakage-states'](
        id_fn, p, device, mgr, k)
    rows_pb, pb_ref = cp.CURVE_BUILDERS['power-breakdown'](
        id_fn, p, device, mgr, k)
    line = [r for r in rows_vt if r['style'] == 'line']
    check('fp-1 rows: leakage-vs-vt = 31 line points (decreasing in '
          'ΔVt) + budget hguide + Vt vguide; cell-leakage-states = one '
          'dot per (cell, state); power-breakdown = static + dynamic '
          'per characterized cell, no refusal',
          len(line) == 31
          and all(a['y'] > b['y'] for a, b in zip(line, line[1:]))
          and any(r['style'] == 'hguide' and 'fet-leakage-1nw'
                  in r['series'] for r in rows_vt)
          and any(r['style'] == 'vguide' for r in rows_vt)
          and sum(1 for r in rows_st if r['series'] == 'NAND2X1') == 4
          and sum(1 for r in rows_st if r['series'] == 'MUX2X1') == 8
          and pb_ref is None
          and {(r['series'], r['x']) for r in rows_pb}
          >= {('INVX1', 'static'), ('INVX1', 'dynamic'),
              ('NAND2X1', 'dynamic')})

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return passed == len(_results)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
