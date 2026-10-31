"""pcb_thermal_spread_selftest - bob-3d (BENCH_BOARDS_PLAN bob-3): WHERE THE HEAT SITS. The thin-plate FEM (materialsScience.engines.fem_plate_thermal,
scikit-fem) checked against the textbook answers it must reproduce, then run on a real board's own rows (kicad-demos 9.0.2 ecc83: a B.Cu GND pour).
Run by pcb_selftest.main().
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2')


def run_plate_engine(check):
    import numpy as np
    from scipy.special import k0
    from materialsScience.engines.fem_plate_thermal import solve_plate_conduction_2d as S
    K, h, W, s, P = 0.81 * 1.51e-3 + 401 * 35e-6, 10.0, 0.4, 0.002, 0.5
    L = np.sqrt(K / (2 * h))
    o = S(W, W, K, h, sources=[{'name': 'U1', 'power_w': P, 'x0': W / 2 - s / 2, 'y0': W / 2 - s / 2, 'x1': W / 2 + s / 2, 'y1': W / 2 + s / 2}],
          refine=40, grid=(401, 401))
    xs, row = np.array(o['map']['xs']), np.array(o['map']['rise'])[200]
    errs = []
    for r in (0.01, 0.02, 0.04):
        i = int(np.argmin(abs(xs - (W / 2 + r))))
        errs.append(abs(row[i] / (P / (2 * np.pi * K) * k0((xs[i] - W / 2) / L)) - 1))
    check('PLATE FEM = THE ANALYTIC PLATE: a small source on a wide plate falls off as P / (2 pi K) K0(r / L), L = sqrt(K / 2h) (the fin solution) - '
          'within 2% at 10, 20 and 40 mm', max(errs) < 0.02, errs)
    check('PLATE FEM CONSERVES ENERGY: all the power put in leaves through the two faces (balance to 1e-9), so the mean rise IS the lumped P / (h 2A)',
          o['balanceError'] < 1e-9 and abs(o['meanRise'] - o['lumpedMeanRise']) < 1e-9 * o['lumpedMeanRise'], (o['balanceError'], o['meanRise'], o['lumpedMeanRise']))
    u = S(0.05, 0.04, K, h, sources=[{'name': 'all', 'power_w': 1.0, 'x0': 0, 'y0': 0, 'x1': 0.05, 'y1': 0.04}])
    check('PLATE FEM, heat put in everywhere: no gradient, the rise is q / 2h exactly (1 W over 50 x 40 mm at h = 10: 25 K)',
          abs(u['maxRise'] - 25.0) < 1e-9 and abs(u['minRise'] - 25.0) < 1e-9, (u['maxRise'], u['minRise']))
    check('PLATE FEM REFUSES in words: no area, a non-positive h, a source off the plate',
          'width' in S(0, 1, K, h)['error'] and 'h' in S(1, 1, K, 0)['error']
          and 'off the plate' in S(0.01, 0.01, K, h, sources=[{'name': 'X', 'power_w': 1, 'x0': 0.02, 'y0': 0.02, 'x1': 0.03, 'y1': 0.03}])['error'])


def run_board_spread(check):
    from pcb.custom import kicad_read as K
    from pcb.custom import thermal_spread as TS
    from materialsScience.engines.fem_plate_thermal import plate_mesh_convergence
    rows = K.read_project(K.read_dir(os.path.join(DEMOS, 'ecc83')), 'ecc83')
    given = {'R1': 0.25, 'R4': 0.5}
    s, hot, field, why = TS.spread(None, 'ecc83', rows=rows, powers=given)
    bare = dict(rows, PcbZone=[])
    s0, _, _, _ = TS.spread(None, 'ecc83', rows=bare, powers=given)
    check('BOARD SPREAD from the board\'s own rows (ecc83: 52.07 x 46.355 mm, 1.51 mm FR-4, a B.Cu GND pour): R4 (0.5 W) is the hottest spot, above R1 '
          '(0.25 W); the mean rise equals the first-order estimate; the pour pulls the peak DOWN and leaves the mean where it is (energy balance)',
          not why and [x['ref'] for x in hot] == ['R4', 'R1'] and s['zones'] == 1 and abs(s['mean_rise_c'] - s['lumped_mean_rise_c']) < 1e-9
          and s0['max_rise_c'] > 2 * s['max_rise_c'] and abs(s0['mean_rise_c'] - s['mean_rise_c']) < 1e-9
          and 'Azar & Graebner' in s['basis'] and 'peaks read high' in s['basis'] and field['xs_mm'][-1] > 52,
          (s.get('max_rise_c'), s0.get('max_rise_c'), [x['ref'] for x in hot]))
    conv = plate_mesh_convergence(refines=(8, 12, 16), width=0.05207, height=0.046355, base_k_sheet=0.81 * 1.51e-3, h=10.0,
                                  sources=[{'name': 'R4', 'power_w': 0.5, 'x0': 0.04, 'y0': 0.026, 'x1': 0.042, 'y1': 0.035}])
    check('BOARD SPREAD CONVERGES: the peak moves under 5% between the two finest meshes', conv['converged'], conv)
    none, _, _, why_none = TS.spread(None, 'rectifier', rows=K.read_project(K.read_dir(os.path.join(DEMOS, 'simulation', 'rectifier')), 'rectifier'))
    s2, _, _, _ = TS.spread(None, 'ecc83', rows=rows, powers={'R999': 1.0})
    check('BOARD SPREAD REFUSES in words: a schematic-only project has no board; a part with no pads is listed, never guessed onto the board',
          none is None and 'no PCB outline' in why_none and s2['parts_unplaced'] == 'R999' and s2['max_rise_c'] == -1.0)
