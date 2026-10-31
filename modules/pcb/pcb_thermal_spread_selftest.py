"""pcb_thermal_spread_selftest - bob-3d (BENCH_BOARDS_PLAN bob-3): WHERE THE HEAT SITS. The thin-plate FEM (materialsScience.engines.fem_plate_thermal,
scikit-fem) checked against the textbook answers it must reproduce, then run on a real board's own rows (kicad-demos 9.0.2 ecc83: a B.Cu GND pour).
Run by pcb_selftest.main().
"""
import json
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
    bare = dict(rows, PcbZone=[], NetGeometry=[], PcbPad=[p for p in rows['PcbPad'] if p['ref'] in given])   # no pour, no tracks, only the heated parts' pads
    s0, _, _, _ = TS.spread(None, 'ecc83', rows=bare, powers=given)
    check('BOARD SPREAD from the board\'s own rows (ecc83: 52.07 x 46.355 mm, 1.51 mm FR-4, a B.Cu GND pour, 33 pads, 59 track segments): R4 (0.5 W) is the hottest spot, above R1 '
          '(0.25 W); the mean rise equals the first-order estimate; the board's copper (pour, tracks, pads) pulls the peak DOWN and leaves the mean where it is (energy balance)',
          not why and [x['ref'] for x in hot] == ['R4', 'R1'] and s['zones'] == 1 and abs(s['mean_rise_c'] - s['lumped_mean_rise_c']) < 1e-9
          and s0['max_rise_c'] > 2 * s['max_rise_c'] and abs(s0['mean_rise_c'] - s['mean_rise_c']) < 1e-9
          and 'Azar & Graebner' in s['basis'] and 'track pieces along themselves' in s['basis'] and field['xs_mm'][-1] > 52,
          (s.get('max_rise_c'), s0.get('max_rise_c'), [x['ref'] for x in hot]))
    conv = plate_mesh_convergence(refines=(8, 12, 16), width=0.05207, height=0.046355, base_k_sheet=0.81 * 1.51e-3, h=10.0,
                                  sources=[{'name': 'R4', 'power_w': 0.5, 'x0': 0.04, 'y0': 0.026, 'x1': 0.042, 'y1': 0.035}])
    check('BOARD SPREAD CONVERGES: the peak moves under 5% between the two finest meshes', conv['converged'], conv)
    none, _, _, why_none = TS.spread(None, 'rectifier', rows=K.read_project(K.read_dir(os.path.join(DEMOS, 'simulation', 'rectifier')), 'rectifier'))
    s2, _, _, _ = TS.spread(None, 'ecc83', rows=rows, powers={'R999': 1.0})
    check('BOARD SPREAD REFUSES in words: a schematic-only project has no board; a part with no pads is listed, never guessed onto the board',
          none is None and 'no PCB outline' in why_none and s2['parts_unplaced'] == 'R999' and s2['max_rise_c'] == -1.0)


OUTLINE_PCB = """(kicad_pcb (version 20240108) (generator "selftest")
  (gr_line (start 0 0) (end 40 0) (layer "Edge.Cuts"))
  (gr_line (start 40 0) (end 40 10) (layer "Edge.Cuts"))
  (gr_arc (start 40 10) (mid 37.0711 17.0711) (end 30 20) (layer "Edge.Cuts"))
  (gr_line (start 30 20) (end 0 20) (layer "Edge.Cuts"))
  (gr_line (start 0 20) (end 0 0) (layer "Edge.Cuts"))
  (gr_circle (center 10 10) (end 13 10) (layer "Edge.Cuts"))
  (gr_line (start 50 50) (end 55 50) (layer "Edge.Cuts"))
  (gr_line (start 1 1) (end 2 2) (layer "F.SilkS")))"""


def run_outline_and_tracks(check):
    import math
    import numpy as np
    from scipy.special import k0
    from pcb.custom import kicad_outline as KO
    from pcb.custom import sexpr as S
    from materialsScience.engines.fem_plate_thermal import solve_plate_conduction_2d as SOLVE
    shape = KO.loops(S.parse(OUTLINE_PCB))
    poly, holes = shape['polygon_mm'], shape['holes_mm']
    area = abs(0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])))
    exact = 40 * 20 - 100 + math.pi * 100 / 4   # the rectangle less the 10 x 10 corner, plus the quarter disc of r = 10
    check('BOARD SHAPE from Edge.Cuts (bob-3e): lines + an arc chain into ONE outer loop (its area = the drawn shape to the chord error of 5-degree steps), '
          'a circle is a hole, a line whose ends meet nothing is counted open, never closed by guessing; other layers ignored',
          abs(area - exact) / exact < 1e-3 and len(holes) == 1 and len(holes[0]) == 72 and shape['open_ends'] == 1, (area, exact, len(holes), shape['open_ends']))
    L = [[0, 0], [0.05, 0], [0.05, 0.02], [0.02, 0.02], [0.02, 0.04], [0, 0.04]]
    u = SOLVE(0.05, 0.04, 0.81 * 1.51e-3, 10.0, sources=[{'name': 'a', 'power_w': 1.0, 'x0': 0, 'y0': 0, 'x1': 0.01, 'y1': 0.01}], outline=L,
              holes=[[[0.03, 0.005], [0.04, 0.005], [0.04, 0.015], [0.03, 0.015]]])
    check('PLATE FEM ON THE BOARD\'S OWN SHAPE: an L-shaped plate with a cut-out meshes to exactly its area (rectilinear edges become grid lines), the mean '
          'rise is P / (h 2A) of THAT area, and a map point off the board is empty',
          abs(u['plateArea'] - 0.0013) < 1e-12 and abs(u['meanRise'] - u['lumpedMeanRise']) < 1e-9 * u['meanRise'] and u['map']['rise'][-1][-1] is None, u['plateArea'])
    K, h, W, s, P, c, dy = 0.81 * 1.51e-3, 10.0, 0.4, 0.002, 0.5, 4 * 0.81 * 1.51e-3, 0.002
    lines = [{'name': 't', 'x0': 0, 'y0': y, 'x1': W, 'y1': y, 'k_line': c * dy} for y in np.arange(dy / 2, W, dy)]
    o = SOLVE(W, W, K, h, sources=[{'name': 'U', 'power_w': P, 'x0': W / 2 - s / 2, 'y0': W / 2 - s / 2, 'x1': W / 2 + s / 2, 'y1': W / 2 + s / 2}],
              lines=lines, refine=50, grid=(401, 401))
    kx = K + c
    R, xs, errs = np.array(o['map']['rise'], dtype=float), np.array(o['map']['xs']), []
    for r in (0.02, 0.04):
        i = int(np.argmin(abs(xs - (W / 2 + r))))
        d, amp = xs[i] - W / 2, P / (2 * np.pi * np.sqrt(kx * K))
        errs += [abs(R[200][i] / (amp * k0(d / np.sqrt(kx / (2 * h)))) - 1), abs(R[i][200] / (amp * k0(d / np.sqrt(K / (2 * h)))) - 1)]
    check('TRACKS conduct ALONG themselves only (embedded 1-D conductors): a plate ruled with parallel tracks every 2 mm behaves as the orthotropic plate '
          'of the textbook - P / (2 pi sqrt(Kx Ky)) K0(sqrt(x2/Lx2 + y2/Ly2)) - along AND across the tracks within 3% at 20 and 40 mm; energy still balances',
          max(errs) < 0.03 and o['balanceError'] < 1e-9 and abs(o['lineLengthOnPlate'] / W - len(lines)) < 1e-6, errs)


def run_pcb_scene(check):
    from pcb.custom import kicad_read as K
    from board.custom import pcb_scene as PSC
    from board.custom import pin_view as PV
    from board.board_details_page import BOARD_DETAILS_PAGES
    rows = K.read_project(K.read_dir(os.path.join(DEMOS, 'ecc83')), 'ecc83')
    st, r = PSC.build('ecc83', rows=rows, powers={'R1': 0.25, 'R4': 0.5})
    t = r['thermal']
    on = [v for row in t['rise'] for v in row if v is not None]
    r4 = [p for p in r['pins'] if p['label'].startswith('R4.')]
    check('THE PCB DRAWN WITH ITS HEAT (bob-3f, the pin view\'s own payload): one surface in the board\'s Edge.Cuts shape, every pad a mark (33), the plate '
          'FEM\'s field on the same frame with its peak; each pad carries the rise where it sits (R4\'s pads hotter than the board\'s mean)',
          st == 200 and len(r['surfaces']) == 1 and len(r['pins']) == 33 and not t['why'] and abs(max(on) - t['max']) < 0.05 * t['max']
          and all(p['rise_c'] > t['mean'] for p in r4) and 'peak +' in r['stage']['notes'][0], (t.get('max'), [p['rise_c'] for p in r4]))
    st2, r2 = PSC.build('ecc83', rows=rows)
    check('THE PCB DRAWN WITHOUT A FIELD says why (no run kept) and still draws the board; the door routes pcb:<board> and a board that is not there is a 404',
          st2 == 200 and 'no finished run' in r2['thermal']['why'] and 'rise' not in r2['thermal'] and len(r2['pins']) == 33
          and PV.door(None, 'pcb:nope', {})[0] == 404)
    page = json.dumps(BOARD_DETAILS_PAGES)   # the page's rows are kept as a JSON string inside the row, hence the escaped quotes
    check('BOARD DETAILS THERMAL TAB mounts the drawing: hardware-pin-view with board = pcb:{scope:board}',
          'bd-thermal-map' in page and '\\"board\\": \\"pcb:{scope:board}\\"' in page)
