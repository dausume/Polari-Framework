"""
@module cntfet.cnt_fo4

The bridge from "this FET switches nicely" to "this CPU can run at X"
(Dustin / 2026-08-30): the FO4 inverter delay from the characterized
cell library of a device, then the clock a pipeline of N FO4 per cycle
would run at.

  t_delay ≈ C_load · Vdd / I_drive       (why FO4, not Ion, decides)
  FO4     = INV delay driving 4 inverter inputs, with the INV's OWN
            output slew as its input slew (fixed point over the grid)
  T_cycle = N · FO4  (N ≈ 10–25 FO4 of logic per cycle: knob bands)
  f_max   = 1 / T_cycle

HONESTY (every payload): the library is INTRINSIC-grade — the S1 /
sifet compact model, labelled stand-in parasitics, NO wires, NO
layout-backed area. FO4 here is therefore an UPPER BOUND on speed:
a 5 fF vs 50 fF wiring load is a 10× swing on the same transistor.
The grade-up (cell-3 junction/parasitic capacitances, layout area)
is named on the payload, not hidden.

@consumers cnt_api (GET /api/cntfet/device/{name}/fo4), fet-overview
"""

from cntfet.cnt_cell_scoring import _latest_library_row, parse_liberty

FO4_KNOBS = {
    'fanout': 4,
    # logic depth bands per cycle (FO4 units) — the classic
    # microarchitecture rule of thumb; knobs, stated on the payload
    'fo4_per_cycle_bands': {'aggressive': 12, 'moderate': 15,
                            'relaxed': 20, 'conservative': 30},
    'slew_iterations': 3,
}
FIDELITY = ('INTRINSIC-grade cell timing (compact model + labelled '
            'stand-in parasitics) → FO4 and the clock bands are UPPER '
            'BOUNDS: they EXCLUDE extracted interconnect, clock tree, '
            'SRAM, IR drop and package effects; a 5 fF vs 50 fF wiring '
            'load is a 10× swing on the same transistor')
OWNER = ('the CELL layer owns FO4 and transition energy (characterized '
         'switching events over the FET model); the FET page only '
         'exposes the primitives that feed them')


def _nearest_index(values, target):
    return min(range(len(values)), key=lambda i: abs(values[i] - target))


def fo4_from_liberty(text, cell='INVX1', knobs=None):
    """{fo4_ps, rise_ps, fall_ps, transition_ps, load_ff, slew_ps,
    energy_aJ, iterations} from OUR Liberty (parse_liberty format)."""
    k = {**FO4_KNOBS, **(knobs or {})}
    parsed = parse_liberty(text)
    c = parsed['cells'].get(cell)
    if c is None:
        return {'ok': False,
                'error': f'{cell} not in this library run — '
                         f'characterized cells: {sorted(parsed["cells"])}'}
    loads, slews = parsed['index_2_ff'], parsed['index_1_ps']
    cin = c.get('inputCap_ff') or (loads[0] if loads else None)
    if not loads or not slews or cin is None:
        return {'ok': False, 'error': 'library grid unreadable'}
    target_load = k['fanout'] * cin
    li = _nearest_index(loads, target_load)
    arcs = c['arcs']
    arc = arcs.get('A') or next(iter(arcs.values()))
    need = ('cell_rise', 'cell_fall', 'rise_transition', 'fall_transition')
    if not all(n in arc for n in need):
        return {'ok': False, 'error': f'{cell} arc lacks {need}'}
    si = len(slews) // 2
    history = []
    for _ in range(k['slew_iterations']):
        tr = 0.5 * (arc['rise_transition'][si][li]
                    + arc['fall_transition'][si][li])
        history.append({'slew_ps': slews[si], 'transition_ps': tr})
        nsi = _nearest_index(slews, tr)
        if nsi == si:
            break
        si = nsi
    rise, fall = arc['cell_rise'][si][li], arc['cell_fall'][si][li]
    energy = arc.get('rise_power', [[None]])[si][li] if 'rise_power' in arc else None
    return {'ok': True, 'cell': cell,
            'fo4_ps': 0.5 * (rise + fall), 'rise_ps': rise, 'fall_ps': fall,
            'transition_ps': history[-1]['transition_ps'],
            'load_ff': loads[li], 'load_target_ff': target_load,
            'input_cap_ff': cin, 'slew_ps': slews[si],
            'energy_internal_aJ': energy,
            'slewFixedPoint': history,
            'gridNote': (f'load grid {loads} fF (index {li} ≈ '
                         f'{k["fanout"]}×Cin {target_load:.3g} fF); '
                         f'slew grid {slews} ps')}


def clock_bands(fo4_ps, bands):
    out = []
    for label, n in bands.items():
        t_ps = n * fo4_ps
        out.append({'band': label, 'fo4_per_cycle': n,
                    'cycle_ps': t_ps, 'f_ghz': 1e3 / t_ps if t_ps > 0 else None})
    return out


def fo4_report(manager, device_name, knobs=None):
    """The per-device speed estimate — FO4 from the latest library
    run, clock bands, energy per transition, PDP — all labelled
    intrinsic-grade."""
    k = {**FO4_KNOBS, **(knobs or {})}
    row = _latest_library_row(manager, device_name)
    if row is None:
        return {'ok': False,
                'error': f'no cell-library characterization run for '
                         f'"{device_name}" — POST {{"action": '
                         f'"characterize-cells"}} to /api/cntfet/devices/'
                         f'{device_name} first', 'fidelity': FIDELITY}
    vdd = float(getattr(row, 'vdd_v', 0.6) or 0.6)
    # the Liberty header is the ground truth for the run's Vdd (rows
    # written before 2026-08-30 carry the class default instead)
    import re
    m = re.search(r'nom_voltage\s*:\s*([0-9.]+)', row.liberty_text or '')
    if m:
        vdd = float(m.group(1))
    # device-relative honesty: the run must be at the device's OWN Vdd
    from cntfet.cnt_derive import get_row
    dev = (get_row(manager, 'AlignedCNTFETDevice', device_name)
           or get_row(manager, 'SiliconMOSFET', device_name))
    dev_vdd = float(getattr(dev, 'vdd_v', 0) or 0) if dev is not None else 0.0
    vdd_note = ''
    if dev_vdd and abs(dev_vdd - vdd) > 1e-9:
        vdd_note = (f'library run {row.name} was characterized at {vdd:g} V '
                    f'but this device\'s own Vdd is {dev_vdd:g} V — '
                    f're-characterize (POST characterize-cells) for an '
                    f'own-Vdd FO4')
    fo4 = fo4_from_liberty(row.liberty_text, knobs=k)
    if not fo4.get('ok'):
        return {**fo4, 'run': row.name, 'fidelity': FIDELITY}
    e_load_aJ = fo4['load_ff'] * 1e-15 * vdd * vdd * 1e18
    e_total = (fo4['energy_internal_aJ'] or 0.0) + e_load_aJ
    bands = clock_bands(fo4['fo4_ps'], k['fo4_per_cycle_bands'])
    fast = max(bands, key=lambda b: b['f_ghz'] or 0)
    slow = min(bands, key=lambda b: b['f_ghz'] or 0)
    return {
        'ok': True, 'device': device_name, 'run': row.name, 'vdd_v': vdd,
        'device_vdd_v': dev_vdd or vdd, 'vddMismatch': vdd_note,
        'fidelity': FIDELITY, 'knobs': k,
        'fo4': fo4,
        'energy': {'internal_aJ': fo4['energy_internal_aJ'],
                   'load_cv2_aJ': e_load_aJ, 'per_transition_aJ': e_total,
                   'pdp_aJ_ps': e_total * fo4['fo4_ps'],
                   'equation': 'E = E_internal (∫Vdd·Idd dt over the edge, '
                               'leakage baseline subtracted, load CV² '
                               'removed — cnt_cell_library) + C_load·Vdd²; '
                               'PDP = E·FO4',
                   'measured': True},
        'clock': bands,
        'owner': OWNER,
        'headline': (f"FO4 ≈ {fo4['fo4_ps']:.3g} ps at {vdd:g} V; INV "
                     f"transition energy {e_total:.3g} aJ (measured from "
                     f"the switching transient: ∫Vdd·Idd dt, leakage "
                     f"subtracted, + C_load·Vdd²); estimated clock "
                     f"{slow['f_ghz']:.3g}–{fast['f_ghz']:.3g} GHz for "
                     f"{slow['fo4_per_cycle']}–{fast['fo4_per_cycle']} "
                     f"FO4/cycle — intrinsic-grade estimate; excludes "
                     f"extracted interconnect, clock tree, SRAM, IR drop "
                     f"and package effects"),
        'clockRange': {'f_ghz_min': slow['f_ghz'], 'f_ghz_max': fast['f_ghz'],
                       'fo4_per_cycle': [slow['fo4_per_cycle'],
                                         fast['fo4_per_cycle']]},
        'equations': {'fo4': 'INV delay driving 4 inverter inputs at its '
                             'own output slew (fixed point on the grid)',
                      'cycle': 'T = N·FO4, N = logic depth per cycle',
                      'why': 't_delay ≈ C_load·Vdd/I_drive'},
        'gradeUp': ['cell-3: junction / fringe / wiring capacitance '
                    'replaces the labelled stand-ins', 'layout-backed '
                    'area → wire load per net', 'then FO4 becomes a '
                    'design number instead of an upper bound'],
    }


def fo4_rows(report):
    """Long-form rows: clock band vs FO4 multiple (dot), for the
    `fet-device-fo4-clock` graph."""
    if not report.get('ok'):
        return None, report
    rows = [{'series': 'f (GHz)', 'style': 'dot', 'dash': False,
             'x': b['band'], 'y': b['f_ghz']} for b in report['clock']]
    return rows, None
