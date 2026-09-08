"""@module cntfet.objects.cnt_power._shared — what the cnt_power row classes share (constants, seeds, helpers); split from cnt_power_basis.py (sap-2c)."""
from cntfet.custom.cnt_metrics import extract_metrics
import itertools
import json
import math
from cntfet.cnt_states_basis import LN10, model_vt, subthreshold_swing_v
import re

FIDELITY = ('F1 (VS_MINIMAL compact model): Ioff, SS, Vt and Cinv '
            'are the model\'s own at the device\'s derived '
            'parameters; leakage is SUBTHRESHOLD ONLY — gate '
            'tunnelling and GIDL are named gaps, not zeros; cell '
            'leakage is a switch-level path sum with the stack '
            'effect as a knob, not a transient')
POWER_CITATIONS = {
    '[NAR01]': {'citation': 'Narendra, Borkar, De, Antoniadis, '
                'Chandrakasan, "Scaling of stack effect and its '
                'application for leakage reduction", ISLPED 2001, '
                'pp. 195-200', 'doi': '10.1145/383082.383132',
                'used_for': 'stack_factor knob (series off devices '
                            'leak less than one)'},
    '[RAB03]': {'citation': 'Rabaey, Chandrakasan, Nikolić, '
                '"Digital Integrated Circuits", 2nd ed., Prentice '
                'Hall 2003, ch. 5 (P = α·f·C·Vdd² + Vdd·Ioff)',
                'doi': '', 'used_for': 'dynamic + static power '
                                        'definitions'},
    '[VS1]': {'citation': 'see cnt_citations [VS1]',
              'used_for': 'thermionic-only model → gate leakage / '
                          'GIDL are gaps'},
}
POWER_KNOBS = {
    'vdd_v': 0.6,
    # activity factor: output transitions per clock cycle (0.1 =
    # the usual random-logic prior)
    'activity': 0.1,
    'f_hz': 1e9,
    # stack effect: leakage multiplier per EXTRA series off device
    # (0.5 = each stacked off device halves the path leakage;
    # [NAR01] measures 2-10x per stack level)
    'stack_factor': 0.5,
    # named gaps — strings, not numbers, so no consumer can add them
    'gate_leakage': 'unmodelled',
    'gidl': 'unmodelled',
    # sensitivity sweeps
    'vt_shifts_v': (-0.05, 0.05),
    'temperatures_k': (300.0, 350.0, 400.0),
    # score-term ranges (log10 W / log10 J) — the min-max spans
    'fet_static_log10w_range': (-12.0, -6.0),
    'cell_static_log10w_range': (-11.0, -6.0),
    'cell_dynamic_log10j_range': (-18.0, -14.0),
}
EQUATIONS = {
    'static': 'P_static = Vdd · Ioff, Ioff = Id(Vgs=0, Vds=Vdd)',
    'ioff_vs_vt': 'Ioff(Vt + ΔVt) = Ioff · 10^(−ΔVt/SS)  '
                  '(SS in V/dec) → dlog10(Ioff)/dVt = −1/SS',
    'ioff_vs_t': 'SS(T) = n_ss·(kT/q)·ln10 = SS(300)·T/300; '
                 'Ioff(T) = Ioff(300)·10^(Vt/SS(300) − Vt/SS(T)) '
                 '(Vt, n_ss and the prefactor held — approximation)',
    'switch_energy': 'E_switch = C_gg · Vdd², C_gg = Cinv·Lg + C_par',
    'dynamic': 'P_dyn = α · f · C_gg · Vdd²',
    'cell_leakage': 'I_leak(state) = Σ_paths(1-net → 0-net through '
                    'k off devices) drive · Ioff_type · '
                    'stack_factor^(k−1)',
    'cell_static': 'P_static(cell) = Vdd · mean_states(I_leak)',
    'cell_dynamic': 'E_dyn = mean_arcs(E_int) + ½·C_L·Vdd² per '
                    'transition (Liberty mid-grid point); '
                    'P_dyn = α · f · E_dyn',
}
def _k(knobs):
    return {**POWER_KNOBS, **(knobs or {})}
def _refuse(error):
    return {'ok': False, 'error': error}
def _c_par_f(manager, device):
    """The CNTParasitics row's c_par_f when a manager can reach it
    (0 with a note otherwise — never a silent assumption)."""
    if manager is None or device is None:
        return 0.0, 'no manager — CNTParasitics row not read (0 F)'
    try:
        from cntfet.custom.cnt_derive import get_row
        row = get_row(manager, 'CNTParasitics',
                      getattr(device, 'parasitics', ''))
    except Exception:
        row = None
    if row is None:
        return 0.0, 'no CNTParasitics row resolved (0 F)'
    return float(getattr(row, 'c_par_f', 0.0) or 0.0), \
        f'CNTParasitics "{row.name}" c_par_f'
def fet_power(id_fn, p, device, knobs=None, manager=None,
              metrics=None):
    """The FET power frame: static (subthreshold leakage), the
    named gaps, dynamic (C·Vdd² and α·f·C·Vdd²), and the
    sensitivity of Ioff to Vt and T — every number from ONE model
    with its equation as text."""
    k = _k(knobs)
    vdd = k['vdd_v']
    m = metrics or extract_metrics(id_fn, {'vdd_v': vdd})
    ioff = m['ioff_a']
    ss_v = subthreshold_swing_v(p)            # model SS, V/dec
    ss_meas_mv = m.get('ss_mv_per_dec')
    vt = model_vt(p, vdd)
    t0 = p.get('temperature_k', 300.0)
    c_par, c_par_note = _c_par_f(manager, device)
    c_gg = p['cinv_f_per_m'] * p['lg_m'] + c_par
    e_switch = c_gg * vdd * vdd
    p_dyn = k['activity'] * k['f_hz'] * e_switch
    shifts = {}
    for dv in k['vt_shifts_v']:
        shifts[f'{dv * 1e3:+.0f}mV'] = ioff * 10.0 ** (-dv / ss_v)
    temps = {}
    for t in k['temperatures_k']:
        ss_t = ss_v * t / t0
        temps[f'{t:.0f}K'] = ioff * 10.0 ** (vt / ss_v - vt / ss_t)
    return {
        'ok': True,
        'fidelity': FIDELITY,
        'device': getattr(device, 'name', None),
        'vdd_v': vdd,
        'ioff_a': ioff,
        'ion_a': m['ion_a'],
        'static_w': vdd * ioff,
        'leakage_components': {
            'subthreshold': {'value_w': vdd * ioff,
                             'equation': EQUATIONS['static']},
            'gate': {'refusal': 'no tunnelling model at S1 — named '
                                'gap (plan §2 decision 1)',
                     'knob': k['gate_leakage']},
            'gidl': {'refusal': 'no band-to-band tunnelling model '
                                'at S1 — named gap',
                     'knob': k['gidl']},
        },
        'dynamic': {
            'c_gg_f': c_gg, 'c_intrinsic_f': c_gg - c_par,
            'c_par_f': c_par, 'c_par_source': c_par_note,
            'e_switch_j': e_switch, 'p_dyn_w': p_dyn,
            'activity': k['activity'], 'f_hz': k['f_hz'],
        },
        'sensitivity': {
            'ss_model_v_per_dec': ss_v,
            'ss_measured_mv_per_dec': ss_meas_mv,
            'vt_model_v': vt,
            'dlog10_ioff_dvt_per_v': -1.0 / ss_v,
            'ioff_at_vt_shift_a': shifts,
            'ioff_vs_t_a': temps,
            'approximation': EQUATIONS['ioff_vs_t'],
        },
        'equations': EQUATIONS,
        'citations': POWER_CITATIONS,
        'knobs': k,
    }
def flatten_devices(cell_key, prefix=''):
    """The cell's transistor list with `compose` stages expanded —
    (type, drain, gate, source) on nets named in the top cell's
    namespace (sub-cell internals prefixed so they never collide)."""
    from cntfet.cnt_cell_library_basis import CELL_LIBRARY
    cell = CELL_LIBRARY[cell_key]
    if not cell.get('compose'):
        return [(t, prefix + d if d not in ('vddn', '0') else d,
                 prefix + g, prefix + s if s not in ('vddn', '0')
                 else s) for t, d, g, s in cell['devices']]
    out = []
    for idx, (sub, in_nets, out_net) in enumerate(cell['compose']):
        if isinstance(in_nets, str):
            in_nets = [in_nets]
        sub_cell = CELL_LIBRARY[sub]
        port_map = dict(zip(sub_cell['inputs'], in_nets))
        port_map[sub_cell['output']] = out_net
        sub_prefix = f'{prefix}x{idx}.'
        for t, d, g, s in flatten_devices(sub, sub_prefix):
            def rename(net):
                local = net[len(sub_prefix):] \
                    if net.startswith(sub_prefix) else None
                if local in port_map:
                    return prefix + port_map[local]
                return net
            out.append((t, rename(d), rename(g), rename(s)))
    return out
def _conducts(dtype, gate_value):
    if gate_value is None:
        return None
    return gate_value == 1 if dtype == 'n' else gate_value == 0
def evaluate_netlist(devices, inputs):
    """Net values (1 / 0 / None = floating) for one input vector:
    a net takes the value of any rail or input it reaches through
    conducting devices; contention (a net reached from both rails)
    is reported, never hidden."""
    values = {'vddn': 1, '0': 0, **inputs}
    contention = set()
    changed = True
    while changed:
        changed = False
        for dtype, d, g, s in devices:
            on = _conducts(dtype, values.get(g))
            if not on:
                continue
            vd, vs = values.get(d), values.get(s)
            if vd is None and vs is not None:
                values[d] = vs
                changed = True
            elif vs is None and vd is not None:
                values[s] = vd
                changed = True
            elif vd is not None and vs is not None and vd != vs:
                contention.add((d, s))
    return values, contention
def _off_paths(devices, values):
    """Every simple path from a 1-valued net to a 0-valued net whose
    devices are all OFF and whose intermediate nets are floating —
    each returned as its list of device indices."""
    adj = {}
    for idx, (dtype, d, g, s) in enumerate(devices):
        on = bool(_conducts(dtype, values.get(g)))
        # an ON device between two FLOATING nets is a short inside
        # the off stack (NAND3 with only the middle input high):
        # traversed at no cost, never counted as an off device
        adj.setdefault(d, []).append((s, idx, on))
        adj.setdefault(s, []).append((d, idx, on))
    paths = []
    ones = [n for n, v in values.items() if v == 1]

    def walk(net, used_devices, off_devices, used_nets):
        for nxt, idx, on in adj.get(net, []):
            if idx in used_devices or nxt in used_nets:
                continue
            v = values.get(nxt)
            if on and v is not None:
                continue                  # on devices join valued
                                          # nets to their own value
            off = off_devices if on else off_devices + [idx]
            if v == 0 and off:
                paths.append(off)
            elif v is None:
                walk(nxt, used_devices + [idx], off,
                     used_nets | {nxt})
            # v == 1: same-valued net — no potential drop, no path
    for start in ones:
        walk(start, [], [], {start})
    return paths
def _when(inputs, order):
    """Liberty state condition: A=0,B=1 → "!A*B"."""
    return '*'.join(('' if inputs[i] else '!') + i for i in order)
def cell_leakage_states(cell_key, drive, ioff_n_a, ioff_p_a,
                        knobs=None):
    """Per-input-state leakage of one cell variant: the off network
    per vector, its paths (with the stack effect applied per
    series off device), current and power."""
    from cntfet.cnt_cell_library_basis import CELL_LIBRARY
    k = _k(knobs)
    cell = CELL_LIBRARY[cell_key]
    devices = flatten_devices(cell_key)
    sf = k['stack_factor']
    states = []
    for vector in itertools.product((0, 1), repeat=len(cell['inputs'])):
        inputs = dict(zip(cell['inputs'], vector))
        values, contention = evaluate_netlist(devices, inputs)
        paths = _off_paths(devices, values)
        i_leak, path_rows = 0.0, []
        for path in paths:
            types = [devices[i][0] for i in path]
            n_off = len(path)
            ioff = ioff_n_a if types[0] == 'n' else ioff_p_a
            i_path = drive * ioff * sf ** (n_off - 1)
            i_leak += i_path
            path_rows.append({
                'devices': [f'{devices[i][0]}({devices[i][2]})'
                            for i in path],
                'network': 'pull-down (n)' if types[0] == 'n'
                else 'pull-up (p)',
                'off_in_series': n_off,
                'stack_multiplier': sf ** (n_off - 1),
                'i_a': i_path})
        y = values.get(cell['output'])
        states.append({
            'inputs': inputs,
            'when': _when(inputs, cell['inputs']),
            'output': y,
            # cells-2: multi-output cells (HA/FA) report every pin
            'outputs': {o: values.get(o)
                        for o in cell.get('outputs', [cell['output']])},
            'off_network': ('pull-down (n) off — leaks to 0'
                            if y == 1 else
                            'pull-up (p) off — leaks from VDD'
                            if y == 0 else 'output floating'),
            'paths': path_rows,
            'i_leak_a': i_leak,
            'p_static_w': k['vdd_v'] * i_leak,
            'contention': sorted(contention),
        })
    currents = [s['i_leak_a'] for s in states]
    mean_i = sum(currents) / len(currents)
    return {
        'ok': True, 'cell': cell_key, 'drive': drive,
        'fet_count': len(devices) * drive,
        'states': states,
        'mean_i_leak_a': mean_i,
        'mean_static_w': k['vdd_v'] * mean_i,
        'max_static_w': k['vdd_v'] * max(currents),
        'min_static_w': k['vdd_v'] * min(currents),
        'equation': EQUATIONS['cell_leakage'],
        'stack_effect': f'series off devices multiply by '
                        f'stack_factor^(k−1) = {sf}^(k−1) [NAR01]; '
                        f'the path sum is an upper bound when '
                        f'paths share a device',
        'knobs': k,
    }
def _twin_ioffs(id_fn, p, vdd):
    """n Ioff from the model; the p twin is the mirrored device
    ({**p, 'ptype': 1}, cnt_cells convention) — symmetric by
    construction at S1, so |Ioff_p| = Ioff_n (stated)."""
    from cntfet.custom.cnt_vs_model import vs_terminal_current
    ioff_n = id_fn(0.0, vdd)
    p_p = {**p, 'ptype': 1}
    ioff_p = abs(vs_terminal_current(0.0, -vdd, p_p)['id_a'])
    return ioff_n, ioff_p
def _dynamic_from_library(parsed, liberty_name, vdd):
    """E per transition for one cell at the mid-grid point from the
    OWN Liberty (cnt_cell_scoring.parse_liberty output)."""
    cell = parsed['cells'].get(liberty_name)
    if cell is None:
        return None, f'{liberty_name} not in the library run'
    i1 = len(parsed['index_1_ps']) // 2
    i2 = len(parsed['index_2_ff']) // 2
    load_f = parsed['index_2_ff'][i2] * 1e-15 \
        if parsed['index_2_ff'] else 0.0
    internals = []
    for pin, tables in cell['arcs'].items():
        try:
            internals.append(0.5 * (tables['rise_power'][i1][i2]
                                    + tables['fall_power'][i1][i2]))
        except (KeyError, IndexError):
            continue
    if not internals:
        return None, f'{liberty_name}: no complete energy table'
    e_int = sum(internals) / len(internals) * 1e-18
    e_load = 0.5 * load_f * vdd * vdd
    return {'e_internal_j': e_int, 'e_load_j': e_load,
            'e_dyn_j': e_int + e_load,
            'gridPoint': {'slew_ps': parsed['index_1_ps'][i1],
                          'load_ff': parsed['index_2_ff'][i2]}}, None
def cell_power(manager, device_name, cell_key, drive=1, knobs=None,
               liberty_text=None):
    """One cell variant's power: the per-state leakage table, the
    mean static power, the dynamic energy from the latest library
    row (refuses BY NAME without a run — static still reports),
    and the total at the activity/f knobs."""
    from cntfet.cnt_cell_library_basis import liberty_cell_name
    from cntfet.cnt_cell_scoring_seed import (
        _latest_library_row, parse_liberty,
    )
    from cntfet.cnt_device_viz_seed import device_model
    k = _k(knobs)
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return refusal
    vdd = k['vdd_v']
    ioff_n, ioff_p = _twin_ioffs(id_fn, p, vdd)
    static = cell_leakage_states(cell_key, drive, ioff_n, ioff_p, k)
    lib_name = liberty_cell_name(cell_key, drive)
    run_name = None
    if liberty_text is None:
        row = _latest_library_row(manager, device_name)
        if row is not None:
            liberty_text, run_name = row.liberty_text, row.name
    dynamic = None
    if liberty_text is None:
        dyn_refusal = (f'no cell-library characterization run for '
                       f'"{device_name}" — POST {{"action": '
                       f'"characterize-cells"}} to /api/cntfet/'
                       f'devices/{device_name} first (dynamic '
                       f'energy needs the cell-2 energy tables)')
    else:
        dynamic, dyn_refusal = _dynamic_from_library(
            parse_liberty(liberty_text), lib_name, vdd)
    p_dyn = (k['activity'] * k['f_hz'] * dynamic['e_dyn_j']
             if dynamic else None)
    return {
        'ok': True, 'fidelity': FIDELITY,
        'device': device_name, 'cell': cell_key, 'drive': drive,
        'libertyName': lib_name, 'run': run_name, 'vdd_v': vdd,
        'ioff_n_a': ioff_n, 'ioff_p_a': ioff_p,
        'states': static['states'],
        'static_w': static['mean_static_w'],
        'static_max_w': static['max_static_w'],
        'stack_effect': static['stack_effect'],
        'dynamic': dynamic,
        'dynamic_refusal': dyn_refusal,
        'dynamic_w': p_dyn,
        'total_w': (static['mean_static_w'] + p_dyn
                    if p_dyn is not None else None),
        'equations': {'static': EQUATIONS['cell_static'],
                      'leakage': EQUATIONS['cell_leakage'],
                      'dynamic': EQUATIONS['cell_dynamic']},
        'knobs': k,
    }
def library_power(manager, device_name, knobs=None,
                  liberty_text=None):
    """Every characterized cell of the latest library run (or, with
    no run, every library cell at x1 with dynamic refused)."""
    from cntfet.cnt_cell_library_basis import CELL_LIBRARY
    from cntfet.cnt_cell_scoring_seed import (
        _latest_library_row, _liberty_to_cell, parse_liberty,
    )
    from cntfet.cnt_device_viz_seed import device_model
    k = _k(knobs)
    _fn, _p, _d, refusal = device_model(manager, device_name)
    if refusal is not None:
        return refusal
    run_name = None
    if liberty_text is None:
        row = _latest_library_row(manager, device_name)
        if row is not None:
            liberty_text, run_name = row.liberty_text, row.name
    variants = []
    if liberty_text is not None:
        for name in sorted(parse_liberty(liberty_text)['cells']):
            key, drive = _liberty_to_cell(name)
            if key:
                variants.append((key, drive))
    if not variants:
        variants = [(key, 1) for key in CELL_LIBRARY]
    cells = [cell_power(manager, device_name, key, drive, k,
                        liberty_text) for key, drive in variants]
    static = [c['static_w'] for c in cells]
    dyn = [c['dynamic_w'] for c in cells if c['dynamic_w'] is not None]
    return {
        'ok': True, 'fidelity': FIDELITY, 'device': device_name,
        'run': run_name, 'cells': cells,
        'total_static_w': sum(static),
        'total_dynamic_w': sum(dyn) if dyn else None,
        'dynamic_refused': [c['libertyName'] for c in cells
                            if c['dynamic_w'] is None],
        'knobs': k,
    }
SEED_POWER_BUDGETS = [
    {'name': 'fet-leakage-1nw', 'scope': 'fet',
     'max_static_w': 1e-9, 'max_dynamic_w': None,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: one FET may leak at most 1 nW at Vdd '
              '(≈ 1.7 nA at 0.6 V — the S3 yield off-criterion '
              'in power units)', 'is_prior': True},
    {'name': 'cell-leakage-1nw', 'scope': 'cell',
     'max_static_w': 1e-9, 'max_dynamic_w': 1e-6,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: per-cell mean leakage ≤ 1 nW, dynamic ≤ 1 µW '
              'at the activity/f knobs', 'is_prior': True},
    {'name': 'block-density-100w-cm2', 'scope': 'block',
     'max_static_w': None, 'max_dynamic_w': None,
     'max_density_w_per_cm2': 100.0, 'max_temperature_k': 358.0,
     'notes': 'PRIOR: the air/heat-sink-cooled density ceiling '
              '(~100 W/cm²) and an 85 °C junction limit', 'is_prior': True},
]
_LIMITS = (('max_static_w', 'static_w', 'W'),
           ('max_dynamic_w', 'dynamic_w', 'W'),
           ('max_density_w_per_cm2', 'density_w_per_cm2', 'W/cm²'),
           ('max_temperature_k', 'temperature_k', 'K'))
def _get(obj, key):
    return obj.get(key) if isinstance(obj, dict) \
        else getattr(obj, key, None)
def check_budget(power_report, budget):
    """Pass/fail PER LIMIT with the margin (limit − value, and the
    ratio); a limit the report cannot evaluate is 'unevaluated'
    with the missing key named, never a silent pass."""
    checks, failed = [], []
    for limit_key, value_key, unit in _LIMITS:
        limit = _get(budget, limit_key)
        if limit is None or limit == '':
            continue
        try:
            # live rows come back with string-typed numbers (persistence)
            limit = float(limit)
        except (TypeError, ValueError):
            checks.append({'limit': limit_key, 'max': limit, 'unit': unit,
                           'value': None, 'pass': None,
                           'why': f'limit "{limit}" is not numeric'})
            continue
        if limit <= 0:
            continue   # 0 / negative = "no limit declared" on the row
        value = _get(power_report, value_key)
        if value is None:
            checks.append({'limit': limit_key, 'max': limit,
                           'unit': unit, 'value': None,
                           'pass': None,
                           'why': f'report has no {value_key} '
                                  f'(unevaluated)'})
            continue
        ok = value <= limit
        if not ok:
            failed.append(limit_key)
        checks.append({'limit': limit_key, 'max': limit,
                       'unit': unit, 'value': value, 'pass': ok,
                       'margin': limit - value,
                       'ratio': value / limit if limit else None})
    return {'budget': _get(budget, 'name'),
            'scope': _get(budget, 'scope'),
            'pass': not failed and any(c['pass'] is not None
                                       for c in checks),
            'failed': failed, 'checks': checks}
def _budget_rows(manager):
    rows = []
    if manager is not None:
        table = (getattr(manager, 'objectTables', {}) or {}).get(
            'PowerBudget') or {}
        rows = list(table.values() if isinstance(table, dict)
                    else table)
    if rows:
        return rows
    try:
        from cntfet.cnt_targets_basis import SEED_TARGET_POWER_BUDGETS
    except ImportError:
        SEED_TARGET_POWER_BUDGETS = []
    return [dict(b) for b in SEED_POWER_BUDGETS + SEED_TARGET_POWER_BUDGETS]
def budget_report(manager, device_name, knobs=None):
    """Budgets are TARGET-scoped (Dustin 2026-08-29): a check is
    pass / fail only against a DesignTarget the device is mapped to;
    against every other target it is INFORMATIONAL — a device is
    never "failing" a budget it was not engineered for."""
    from cntfet.cnt_device_viz_seed import device_model
    from cntfet.cnt_targets_basis import targets_for_device
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return refusal
    k = _k(knobs)
    fet = fet_power(id_fn, p, device, k, manager=manager)
    fet_report = {'static_w': fet['static_w'],
                  'dynamic_w': fet['dynamic']['p_dyn_w'],
                  'temperature_k': p.get('temperature_k')}
    lib = library_power(manager, device_name, k)
    budgets = {_get(b, 'name'): b for b in _budget_rows(manager)}
    mapped, mapping, all_targets = targets_for_device(manager, device_name)
    mapped_names = {t['name'] for t in mapped}

    def _checks_for(target):
        out = []
        for bname in json.loads(target.get('budgets_json') or '[]'):
            b = budgets.get(bname)
            if b is None:
                out.append({'subject': device_name, 'budget': bname,
                            'scope': '?', 'pass': None, 'failed': [],
                            'checks': [], 'why': 'no PowerBudget row'})
                continue
            scope = _get(b, 'scope')
            if scope == 'fet':
                out.append({'subject': device_name,
                            **check_budget(fet_report, b)})
            elif scope == 'cell':
                for c in lib.get('cells', []):
                    out.append({'subject': c['libertyName'],
                                **check_budget(c, b)})
            else:
                out.append({'subject': f'{device_name}-block',
                            **check_budget(
                                {'temperature_k': p.get('temperature_k'),
                                 'density_w_per_cm2': None}, b)})
        return out

    def _verdict(checks):
        evaluated = [c for c in checks if c.get('pass') is not None]
        if not evaluated:
            return 'unevaluated'
        return 'misses' if any(c['failed'] for c in evaluated) else 'meets'

    targets_out = []
    for name, t in all_targets.items():
        checks = _checks_for(t)
        is_mapped = name in mapped_names
        verdict = _verdict(checks)
        targets_out.append({
            'target': name, 'display_name': t.get('display_name', name),
            'description': t.get('description', ''),
            'optimization': t.get('optimization', ''),
            'mapped': is_mapped,
            'status': (verdict if is_mapped else 'not-a-target'),
            'informational': (None if is_mapped else verdict),
            'statement': (
                f"engineered for {t.get('display_name', name)}: "
                f"{verdict.upper()} its budgets" if is_mapped else
                f"not a target for this device — would "
                f"{'meet' if verdict == 'meets' else 'not meet' if verdict == 'misses' else 'be unevaluated against'} "
                f"{t.get('display_name', name)} (informational only)"),
            'checks': checks,
            'failingSubjects': sorted({c['subject'] for c in checks
                                       if c.get('failed')}),
        })
    targets_out.sort(key=lambda t: (not t['mapped'], t['target']))
    mapped_results = [c for t in targets_out if t['mapped']
                      for c in t['checks']]
    return {'ok': True, 'device': device_name, 'fidelity': FIDELITY,
            'fet': fet_report,
            'engineeredFor': mapping,
            'targets': targets_out,
            # the mapped-target checks only (what "fail" may mean)
            'results': mapped_results,
            'failing': [r for r in mapped_results if r.get('failed')],
            'rule': 'pass / fail exists only against a target the FET '
                    'is engineered for (FETTargetMapping); every other '
                    'target is informational, never a failure',
            'honesty': 'density W/cm² needs a layout-backed area — '
                       'unevaluated until one exists',
            'knobs': k}
CATEGORY = 'fet-figures-of-merit'
POWER_TERMS = {
    'fet-static-power': {
        'raw': 'log10_static_w', 'ideal': 'computed', 'unit': 'log10 W',
        'equation': 'log10(Vdd · Ioff)',
        'ideal_why': 'the range floor (1 pW): the S1 model\'s '
                     'thermionic tail cannot reach zero leakage'},
    'cell-static-power': {
        'raw': 'log10_cell_static_w', 'ideal': 'computed',
        'unit': 'log10 W',
        'equation': 'log10(Vdd · mean_states(I_leak))',
        'ideal_why': 'the range floor: no off path leaks'},
    'cell-dynamic-energy': {
        'raw': 'log10_cell_dynamic_j', 'ideal': 'computed',
        'unit': 'log10 J',
        'equation': 'log10(mean_arcs(E_int) + ½·C_L·Vdd²)',
        'ideal_why': 'the range floor: the unavoidable load-charging '
                     'energy alone'},
}
def _term(name, display, description, unit, positive, lo, hi,
          tags=()):
    """cnt_scoring._term, copied so this file stands alone."""
    return {
        'name': name, 'display_name': display,
        'description': description,
        'category': CATEGORY, 'value_type': 'custom', 'unit': unit,
        'is_positive': positive,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': lo, 'max': hi}),
        'temporal_json': json.dumps({'nature': 'stock',
                                     'resample': 'nearest'}),
        'abstract_tags_json': json.dumps(
            ['fet', 'power', 'device-figures-of-merit', *tags]),
        'source': 'cntfet.cnt_power_basis (fp-1)',
        'provenance_id': 'FET_CELL_POWER_SILICON_PLAN §fp-1',
    }
def _describe(key, lo, hi):
    t = POWER_TERMS[key]
    return (f"{t['equation']}. Lower is better; ideal = the range "
            f"floor ({t['ideal_why']}). Range {lo} → {hi} {t['unit']} "
            f"(knob). Raw frame key: {t['raw']}.")
def _seed_terms(k=None):
    k = _k(k)
    lo, hi = k['fet_static_log10w_range']
    cs_lo, cs_hi = k['cell_static_log10w_range']
    cd_lo, cd_hi = k['cell_dynamic_log10j_range']
    return [
        _term('fet-static-power', 'Static power (log10 W)',
              _describe('fet-static-power', lo, hi), 'log10 W',
              False, lo, hi, ('leakage',)),
        _term('cell-static-power', 'Cell static power (log10 W)',
              _describe('cell-static-power', cs_lo, cs_hi),
              'log10 W', False, cs_lo, cs_hi, ('cell', 'leakage')),
        _term('cell-dynamic-energy', 'Cell dynamic energy (log10 J)',
              _describe('cell-dynamic-energy', cd_lo, cd_hi),
              'log10 J', False, cd_lo, cd_hi, ('cell', 'energy')),
    ]
SEED_POWER_SCORE_TERMS = _seed_terms()
def _log10(x):
    return math.log10(x) if x is not None and x > 0 else None
def power_frame(fet_report=None, cell_report=None):
    """The keys the power terms cite (merge into a score frame)."""
    return {
        'log10_static_w': _log10(_get(fet_report or {}, 'static_w')),
        'static_w': _get(fet_report or {}, 'static_w'),
        'log10_cell_static_w': _log10(
            _get(cell_report or {}, 'static_w')),
        'log10_cell_dynamic_j': _log10(
            (_get(cell_report or {}, 'dynamic') or {}).get('e_dyn_j')
            if cell_report else None),
        'cell_dynamic_w': _get(cell_report or {}, 'dynamic_w'),
    }
def leakage_blocks_for(cell_key, drive, ioff_n, ioff_p, knobs=None):
    """{when → W} for a cell block's optional `leakage` entry
    (cnt_cell_library._liberty_library emits them in uW)."""
    st = cell_leakage_states(cell_key, drive, ioff_n, ioff_p, knobs)
    return {s['when']: s['p_static_w'] for s in st['states']}
_LEAK_RE = re.compile(
    r'leakage_power \(\) \{\s*when : "([^"]*)";\s*value : '
    r'([-+0-9.eE]+);\s*\}', re.S)
def parse_leakage(text):
    """{cellName: {'states': {when: uW}, 'cell_leakage_uW': x}} read
    back from our emitter (round-trip check)."""
    out = {}
    for m in re.finditer(r'\n  cell \(([^)]+)\) \{\n(.*?)\n  \}(?=\n)',
                         text, re.S):
        name, body = m.group(1), m.group(2)
        states = {w: float(v) for w, v in _LEAK_RE.findall(body)}
        cl = re.search(r'cell_leakage_power : ([-+0-9.eE]+);', body)
        if states or cl:
            out[name] = {'states': states,
                         'cell_leakage_uW': float(cl.group(1))
                         if cl else None}
    return out
def _fet_ioffs(id_fn, p, knobs):
    k = _k(knobs)
    return _twin_ioffs(id_fn, p, k['vdd_v'])
def leakage_vs_vt_rows(id_fn, p, device, manager=None, knobs=None,
                       span_v=0.15, step_v=0.01):
    """Ioff vs Vt shift (log y) with the budget as a guide."""
    k = _k(knobs)
    fet = fet_power(id_fn, p, device, k, manager=manager)
    ss_v = fet['sensitivity']['ss_model_v_per_dec']
    rows = []
    n = int(round(2 * span_v / step_v))
    for i in range(n + 1):
        dv = -span_v + i * step_v
        rows.append({'series': 'Ioff', 'style': 'line', 'dash': False,
                     'x': dv * 1e3,
                     'y': fet['ioff_a'] * 10.0 ** (-dv / ss_v)})
    rows.append({'series': 'nominal Vt', 'style': 'vguide',
                 'dash': True, 'x': 0.0, 'y': None,
                 'label': f"Vt = {fet['sensitivity']['vt_model_v']:.3f} V"})
    for b in _budget_rows(manager):
        if _get(b, 'scope') == 'fet' and _get(b, 'max_static_w'):
            i_max = _get(b, 'max_static_w') / k['vdd_v']
            rows.append({'series': _get(b, 'name'), 'style': 'hguide',
                         'dash': True, 'x': None, 'y': i_max,
                         'label': f"{_get(b, 'name')}: "
                                  f"{_get(b, 'max_static_w'):.2g} W "
                                  f"/ Vdd = {i_max:.2g} A"})
    return rows
def cell_leakage_state_rows(id_fn, p, device, manager=None,
                            knobs=None, cells=None, drive=1):
    """x = input state (categorical), one dot per cell."""
    from cntfet.cnt_cell_library_basis import CELL_LIBRARY, liberty_cell_name
    ioff_n, ioff_p = _fet_ioffs(id_fn, p, knobs)
    rows = []
    for key in (cells or list(CELL_LIBRARY)):
        st = cell_leakage_states(key, drive, ioff_n, ioff_p, knobs)
        for s in st['states']:
            rows.append({'series': liberty_cell_name(key, drive),
                         'style': 'dot', 'dash': False,
                         'x': s['when'], 'y': s['p_static_w']})
    return rows
def power_breakdown_rows(id_fn, p, device, manager=None, knobs=None):
    """x = static | dynamic (categorical), one series per cell;
    dynamic missing → the refusal rides along."""
    name = getattr(device, 'name', '')
    lib = library_power(manager, name, knobs)
    if not lib.get('ok'):
        return [], lib
    rows = []
    for c in lib['cells']:
        rows.append({'series': c['libertyName'], 'style': 'dot',
                     'dash': False, 'x': 'static', 'y': c['static_w']})
        if c['dynamic_w'] is not None:
            rows.append({'series': c['libertyName'], 'style': 'dot',
                         'dash': False, 'x': 'dynamic',
                         'y': c['dynamic_w']})
    refusal = (None if lib['total_dynamic_w'] is not None
               else {'ok': False,
                     'error': lib['cells'][0]['dynamic_refusal']})
    return rows, refusal
CURVE_BUILDERS = {
    'leakage-vs-vt': leakage_vs_vt_rows,
    'cell-leakage-states': cell_leakage_state_rows,
    'power-breakdown': power_breakdown_rows,
}
def _graph(kind, description, x_label, y_label, y_type='linear'):
    return {
        'name': f'cnt-device-{kind}',
        'description': description + ' — data: /api/cntfet/'
                       'device/{name}/points?curve=' + kind,
        'source_class': 'AlignedCNTFETDevice',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'yType': y_type},
            'aggregation': None,
        }}),
    }
SEED_CNT_POWER_GRAPHS = [
    _graph('leakage-vs-vt',
           'Off-current vs threshold shift: Ioff·10^(−ΔVt/SS) on a '
           'log axis (one decade per SS of Vt), with the FET '
           'leakage budget as a guide',
           'ΔVt (mV)', 'Ioff (A)', y_type='log'),
    _graph('cell-leakage-states',
           'Cell leakage per INPUT STATE from the off network '
           '(stack effect applied to series off devices) — one '
           'dot per cell per state',
           'input state', 'P_static (W)', y_type='log'),
    _graph('power-breakdown',
           'Static (mean over states) vs dynamic (α·f·E from the '
           'characterized energy tables) power per cell',
           'component', 'P (W)', y_type='log'),
]
