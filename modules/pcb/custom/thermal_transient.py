"""
@module pcb.custom.thermal_transient

bob-3g (BENCH_BOARDS_PLAN bob-3; the user's words 2026-10-31: "some components are black boxes and we need the capability to run simulations based on their
data sheets specified thermal behavior over time"): A PCB'S TEMPERATURE OVER TIME, and each black-box part's junction on top of it - two established
models chained, nothing invented:

  the board   the plate of pcb.custom.thermal_spread (the same shape, dielectric, pours, pads, tracks) with its heat capacity, stepped in time by the FEM
              engine (materialsScience.engines.fem_plate_transient: backward Euler on the transient fin equation)
              C = rho c t per area: every dielectric layer at FR-4's (RHO_FR4 x C_FR4, knobs below), copper where it is at copper's (cited) - the
              copper's capacity rides on the same pours / pads / tracks as its conductance (c = k x rho c_Cu / k_Cu, the same thickness and fill)
  the part    its datasheet's Foster network junction -> board (PartThermalModel; materialsScience.engines.thermal_rc), driven by its own power over
              time and referenced to the board's mean temperature under its pads - Tj(t) = T_ambient + board rise under it (t) + Zth part (t)
  powers      pcb.custom.thermal_inputs.power_plan: a power a person gave (always on, one pulse, or a duty cycle) wins over the run's average

  transient(manager, board, run=None, rows=None, h=H_FREE_AIR, t_end=None, refine=10, ambient_c=AMBIENT_C) -> (summary, junctions, chart, why)
      t_end None -> long enough to settle: the larger of 5 x the plate's own time constant C/(2h), 5 x the slowest datasheet stage, 2 x the longest
      pulse, 3 x the longest period (capped at T_END_MAX)
      chart: long form {x: time s, y: rise K, series} for the named graph pcb-thermal-transient, at most CHART_POINTS points per series (stride said)

Copper: Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, Table A.1, pure copper at 300 K: rho 8933 kg/m3, c_p 385 J/(kg K).
FR-4 C_FR4: Kpobie et al., "Experimental and multiscale numerical characterization of the temperature-dependent thermal behavior of FR4 laminates",
J. Materials Research and Technology 40 (2026) 2559-2568: c_p by DSC rises from 760 J/(kg K) at 300 K to 1180 at 430 K - the 300 K value, a KNOB (a
board running hot stores more). RHO_FR4 1850 kg/m3: a typical figure (the FR-4 property table on Wikipedia), a KNOB, not a measurement.
"""
import hashlib
import json

from pcb.custom.thermal import H_FREE_AIR, H_CITE, _rows_of
from pcb.custom.thermal_spread import CLASSES, K_CU, K_FR4_INPLANE, K_FR4_CITE, K_CU_CITE, AMBIENT_C, plate_inputs, place_sources

RHO_CU, C_CU = 8933.0, 385.0
CU_CAP_CITE = 'Incropera & DeWitt Table A.1: copper rho 8933 kg/m3, c_p 385 J/(kg K) at 300 K'
RHO_FR4, C_FR4 = 1850.0, 760.0
FR4_CAP_CITE = ('FR-4 c_p 760 J/(kg K) at 300 K (Kpobie et al., J. Mater. Res. Technol. 40 (2026) 2559-2568, DSC; 1180 at 430 K) and rho 1850 kg/m3 '
                '(typical) - both knobs')
T_END_MAX = 1e5
CHART_POINTS = 400
_CACHE = {}


def _t_end(plate, h, plan, mods):
    tau_plate = RHO_FR4 * C_FR4 * plate['diel'] * 1e-3 / (2.0 * h)
    slow = max([tau for m in mods.values() for _, tau in m['stages']] or [0.0])
    return min(T_END_MAX, max(5 * tau_plate, 5 * slow, 2 * max([p['on_s'] for p in plan] or [0.0]), 3 * max([p['period_s'] for p in plan] or [0.0])))


def _thin(n):
    return max(1, -(-n // CHART_POINTS))


def transient(manager, board, run=None, rows=None, h=H_FREE_AIR, t_end=None, refine=10, ambient_c=AMBIENT_C):
    from materialsScience.engines.fem_plate_transient import solve_plate_transient_2d
    from materialsScience.engines.thermal_rc import junction_trajectory
    from pcb.custom.thermal_inputs import models, power_plan
    rows = rows if rows is not None else _rows_of(manager, board, CLASSES)
    plate, why = plate_inputs(board, rows)
    if why:
        return None, [], [], why
    plan, source_words, unaccounted, why = power_plan(manager, board, run, rows)
    if why:
        return None, [], [], why
    mods = models(manager, board, rows)
    sources, unplaced = place_sources(plate, [p for p in plan if p['avg_w'] > 0])
    if not sources:
        return None, [], [], 'no part with power has pads on %s - give a part a power on the Thermal over time tab, or keep a run%s' % (board, unaccounted)
    t_end = float(t_end) if t_end else _t_end(plate, h, plan, mods)
    key = hashlib.sha256(json.dumps([board, h, t_end, refine, ambient_c, plan, mods, plate['shape_words'], plate['n_pads'], len(plate['lines']),
                                     plate['zones']], sort_keys=True, default=str).encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]

    cap = RHO_CU * C_CU / K_CU   # copper's heat capacity per unit of its conductance: the same thickness and fill carry both
    regions = [dict(r, add_c_sheet=r['add_k_sheet'] * cap) for r in plate['regions']]
    lines = [dict(ln, c_line=ln['k_line'] * cap) for ln in plate['lines']]
    out = solve_plate_transient_2d(plate['w'] * 1e-3, plate['ht'] * 1e-3, K_FR4_INPLANE * plate['diel'] * 1e-3, RHO_FR4 * C_FR4 * plate['diel'] * 1e-3, h,
                                   t_end, sources=sources, regions=regions, lines=lines, outline=plate['outline'] or None, holes=plate['holes'], refine=refine)
    if not out.get('ok'):
        return None, [], [], 'the transient FEM solve refused: %s' % out.get('error')

    times, stride = out['times'], _thin(len(out['times']))
    by_from = {p['ref']: p['from'] for p in plan}
    chart = [{'x': times[i], 'y': out['maxRise'][i], 'series': 'board, hottest point'} for i in range(0, len(times), stride)]
    junctions = []
    for s in out['sources']:
        ref, m = s['name'], mods.get(s['name'])
        board_rise = s['meanRise']
        chart += [{'x': times[i], 'y': board_rise[i], 'series': '%s: board under it' % ref} for i in range(0, len(times), stride)]
        row = {'ref': ref, 'power_w': s['power_w'], 'on_s': s['on_s'], 'period_s': s['period_s'], 'from': by_from.get(ref, ''),
               'board_peak_rise_c': s['peakMeanRise'], 'board_peak_at_s': s['peakAt'], 'junction_peak_rise_c': -1.0, 'junction_peak_at_s': -1.0,
               'tj_peak_c': -1.0, 'tj_max_c': -1.0, 'margin_c': -1.0, 'datasheet_ja_rise_c': -1.0, 'model': '',
               'basis': 'no datasheet thermal model: only the board under it (give its Foster stages on the Thermal over time tab)'}
        if m and m['stages']:
            z = junction_trajectory(m['stages'], times, out['powers'][ref])
            tj = [b + zz for b, zz in zip(board_rise, z)]
            k = max(range(len(tj)), key=tj.__getitem__)
            row.update(junction_peak_rise_c=tj[k], junction_peak_at_s=times[k], tj_peak_c=ambient_c + tj[k], model=m['name'],
                       basis=('Tj = ambient %g C (a knob) + the board\'s mean rise under its pads (plate FEM) + its datasheet Zth j-%s (%d Foster stages, '
                              'Rth %.4g K/W; %s) driven by its own power over time' % (ambient_c, m['reference'], len(m['stages']), m['rth'], m['words'])))
            if m['tj_max_c']:
                row.update(tj_max_c=m['tj_max_c'], margin_c=m['tj_max_c'] - row['tj_peak_c'])
            chart += [{'x': times[i], 'y': tj[i], 'series': '%s: junction' % ref} for i in range(0, len(times), stride)]
        elif m and m['bad']:
            row['basis'] = 'datasheet model %s not used: %s' % (m['name'], m['bad'])
        if m and m['rth_ja_k_w']:
            row['datasheet_ja_rise_c'] = s['power_w'] * m['rth_ja_k_w']
        junctions.append(row)

    summary = {'board': board, 'source': source_words, 'h_w_m2k': h, 'ambient_c': ambient_c, 't_end_s': t_end, 'steps': out['steps'],
               'factorisations': out['factorisations'], 'dt0_s': out['dt0'], 'plate_time_constant_s': out['plateTimeConstant'],
               'peak_rise_c': out['peakRise'], 'peak_at_s': out['peakAt'], 'steady_max_rise_c': out['steadyMaxRise'], 'final_max_rise_c': out['maxRise'][-1],
               'input_j': out['inputJ'], 'balance_error': out['balanceError'], 'parts_placed': len(sources), 'parts_unplaced': ', '.join(unplaced),
               'dofs': out['dofs'], 'chart_stride': stride,
               'basis': ('transient thin-plate FEM (scikit-fem, backward Euler): C dT/dt - div(K grad T) + 2h T = q(t); plate = %s; K = FR-4 %s (%s) + '
                         'copper (%s); C = FR-4 (%s) + copper (%s) where the copper is; h a knob (%s); powers = %s; each part with a datasheet model adds '
                         'its Foster Zth on top of the board under it (one way: the board sets its reference)%s%s'
                         % (plate['shape_words'], plate['stack_words'], K_FR4_CITE, K_CU_CITE, FR4_CAP_CITE, CU_CAP_CITE, H_CITE, source_words,
                            ('; no pads, not placed: %s' % ', '.join(unplaced)) if unplaced else '', unaccounted))}
    result = (summary, sorted(junctions, key=lambda r: -max(r['junction_peak_rise_c'], r['board_peak_rise_c'])), chart, '')
    if len(_CACHE) >= 8:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = result
    return result
