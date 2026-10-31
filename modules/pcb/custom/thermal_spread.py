"""
@module pcb.custom.thermal_spread

bob-3d (BENCH_BOARDS_PLAN bob-3, his words 2026-10-30: "finite element model simulations are already well defined"): WHERE THE HEAT SITS on a PCB - the
board as a thin plate solved by the existing FEM engine (materialsScience.engines.fem_plate_thermal, scikit-fem), fed only by the board's own rows and
a kept run. Nothing here is a new model: it maps rows onto the textbook plate problem and reads the answer back.

  spread(manager, board, run=None, rows=None, h=H_FREE_AIR, refine=12, powers=None) -> (summary, hotspots, field, why)
    plate        the Edge.Cuts bounding box (PcbBoard width x height); a non-rectangular outline is solved as its box (said)
    sheet K      layers in parallel, sum k_i t_i: every dielectric layer of the stackup at the FR-4 in-plane conductivity (a cited knob); copper ONLY
                 where it is - each copper pour / teardrop (PcbZone) adds k_Cu x its layer's thickness x (filled / outline area); tracks and pads are
                 not counted (said: that leaves the board less conductive than it is, so peaks read HIGH, never low)
    sources      each part's average power from the run (pcb.custom.thermal.dissipation; sources themselves excluded) spread over the box of its own
                 pads (PcbPad); a part with no pads, and the power the run cannot place (unaccounted), are listed, never guessed onto the board
    powers       {ref: W} given by a person instead of a run (said as 'given' on every row)
  The engine's built-in checks ride on every summary: the energy balance, and the mean rise = the first-order P / (h 2A) of pcb.custom.thermal.

K_CU: Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, Table A.1, pure copper at 300 K: 401 W/(m K).
K_FR4_INPLANE: Azar & Graebner, "Experimental Determination of Thermal Conductivity of Printed Wiring Boards", Proc. 12th IEEE SEMI-THERM (1996)
169-182, doi:10.1109/STHERM.1996.545107: FR-4 in-plane 0.81 W/(m K) (through-plane about a third of that). A KNOB: used for every dielectric layer,
whatever its material string, and said.
"""
import json
import math

from pcb.custom.thermal import H_FREE_AIR, H_CITE, dissipation, _rows_of

K_CU = 401.0
K_CU_CITE = 'Incropera & DeWitt Table A.1: pure copper 401 W/(m K) at 300 K'
K_FR4_INPLANE = 0.81
K_FR4_CITE = 'Azar & Graebner, IEEE SEMI-THERM 1996, doi:10.1109/STHERM.1996.545107: FR-4 in-plane 0.81 W/(m K)'
CLASSES = ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact', 'PcbBoard', 'PcbPad', 'PcbZone')
_COPPER_ZONES = ('copper', 'teardrop')


def _stack(pcb):
    """(dielectric thickness mm, {copper layer: thickness mm}, words) from the board's own stackup; the board thickness when it has none."""
    stack = json.loads(pcb.get('stackup_json') or '[]')
    diel = sum(float(s.get('thickness') or 0) for s in stack if s.get('type') in ('core', 'prepreg'))
    copper = {s['layer']: float(s.get('thickness') or 0) for s in stack if s.get('type') == 'copper'}
    if diel > 0:
        mats = sorted({s.get('material') or '?' for s in stack if s.get('type') in ('core', 'prepreg')})
        return diel, copper, 'dielectric %g mm (%s) from the stackup' % (diel, ', '.join(mats))
    t = float(pcb.get('thickness_mm') or 0)
    return t, copper, ('no stackup: the board thickness %g mm taken as all dielectric' % t) if t > 0 else ''


def _zone_layers(zone, copper):
    layers = json.loads(zone.get('layers_json') or '[]')
    return [c for c in copper if c in layers or '*.Cu' in layers]


def _pad_box(pads):
    """The box around a part's pads (mm), each pad's extent turned by its angle."""
    xs, ys = [], []
    for p in pads:
        a = math.radians(float(p.get('angle') or 0))
        w, ht = float(p.get('size_w_mm') or 0), float(p.get('size_h_mm') or 0)
        hw = (abs(w * math.cos(a)) + abs(ht * math.sin(a))) / 2
        hh = (abs(w * math.sin(a)) + abs(ht * math.cos(a))) / 2
        xs += [p['x_mm'] - hw, p['x_mm'] + hw]
        ys += [p['y_mm'] - hh, p['y_mm'] + hh]
    return min(xs), min(ys), max(xs), max(ys)


def spread(manager, board, run=None, rows=None, h=H_FREE_AIR, refine=12, powers=None):
    from materialsScience.engines.fem_plate_thermal import solve_plate_conduction_2d
    rows = rows if rows is not None else _rows_of(manager, board, CLASSES)
    pcb = next(iter(rows.get('PcbBoard') or []), None)
    if pcb is None or not float(pcb.get('width_mm') or 0) or not float(pcb.get('height_mm') or 0):
        return None, [], None, 'no PCB outline for %s (a schematic-only project has no board to spread heat in)' % board
    bbox = json.loads(pcb.get('outline_json') or '{}').get('bbox_mm') or [0.0, 0.0, pcb['width_mm'], pcb['height_mm']]
    ox, oy, w, ht = bbox[0], bbox[1], float(pcb['width_mm']), float(pcb['height_mm'])
    diel, copper, stack_words = _stack(pcb)
    if diel <= 0:
        return None, [], None, 'undetermined: %s has neither a stackup nor a thickness - the plate\'s conductance is unknown' % board

    if powers is not None:
        given = [{'ref': r, 'avg_w': float(p), 'kind': 'given'} for r, p in powers.items()]
        source_words, unaccounted = 'given by a person', ''
    else:
        parts, why = dissipation(manager, board, run, rows)
        if why:
            return None, [], None, why
        given = [p for p in parts if p['kind'] != 'V' and p['avg_w'] > 0]
        undetermined = [p['ref'] for p in parts if p['avg_w'] == -1.0]
        source_words = 'run %s' % (parts[0]['run'] if parts else '')
        unaccounted = ('; power NOT placed (its parts\' current is not in the run): %s' % ', '.join(undetermined)) if undetermined else ''

    pads = {}
    for p in rows.get('PcbPad') or []:
        pads.setdefault(p['ref'], []).append(p)
    sources, unplaced = [], []
    for p in given:
        if not pads.get(p['ref']):
            unplaced.append(p['ref'])
            continue
        x0, y0, x1, y1 = _pad_box(pads[p['ref']])
        sources.append({'name': p['ref'], 'power_w': p['avg_w'], 'x0': max(0.0, (x0 - ox) * 1e-3), 'y0': max(0.0, (y0 - oy) * 1e-3),
                        'x1': min(w, x1 - ox) * 1e-3, 'y1': min(ht, y1 - oy) * 1e-3, 'box_mm': (x0, y0, x1, y1)})

    regions = []
    for z in rows.get('PcbZone') or []:
        layers = _zone_layers(z, copper)
        outline = json.loads(z.get('outline_json') or '[]')
        if z.get('kind') not in _COPPER_ZONES or not layers or len(outline) < 3 or not float(z.get('outline_area_mm2') or 0):
            continue
        fill = float(z.get('filled_area_mm2') or 0) / float(z['outline_area_mm2'])
        regions.append({'name': z['name'], 'add_k_sheet': K_CU * sum(copper[c] for c in layers) * 1e-3 * fill,
                        'polygon': [[(x - ox) * 1e-3, (y - oy) * 1e-3] for x, y in outline]})

    base = {'board': board, 'source': source_words, 'h_w_m2k': h, 'max_rise_c': -1.0, 'mean_rise_c': -1.0, 'lumped_mean_rise_c': -1.0,
            'placed_w': sum(s['power_w'] for s in sources), 'parts_placed': len(sources), 'parts_unplaced': ', '.join(unplaced), 'zones': len(regions)}
    if not sources:
        return dict(base, basis='no part with power has pads on the board - nothing to spread%s' % unaccounted), [], None, ''
    out = solve_plate_conduction_2d(w * 1e-3, ht * 1e-3, K_FR4_INPLANE * diel * 1e-3, h, sources=sources, regions=regions, refine=refine)
    if not out.get('ok'):
        return dict(base, basis='the FEM solve refused: %s' % out.get('error')), [], None, ''

    summary = dict(base, max_rise_c=out['maxRise'], mean_rise_c=out['meanRise'], lumped_mean_rise_c=out['lumpedMeanRise'],
                   balance_error=out['balanceError'], spreading_length_mm=out['spreadingLength'] * 1e3, dofs=out['dofs'],
                   basis=('steady thin-plate FEM (scikit-fem): -div(K grad T) + 2h T = q, edges insulated; plate = the %g x %g mm Edge.Cuts box; K = FR-4 %s '
                          '(%s) + %d copper pours at k_Cu (%s) x layer thickness x fill; tracks and pads NOT counted (peaks read high); h a knob (%s); '
                          'sources = %s over each part\'s pad box%s%s' % (w, ht, stack_words, K_FR4_CITE, len(regions), K_CU_CITE, H_CITE, source_words,
                                                                          ('; no pads, not placed: %s' % ', '.join(unplaced)) if unplaced else '', unaccounted)))
    by = {s['name']: s for s in sources}
    hotspots = [{'ref': s['name'], 'power_w': s['power_w'], 'peak_rise_c': s['peakRise'], 'mean_rise_c': s['meanRise'],
                 'x_mm': (by[s['name']]['box_mm'][0] + by[s['name']]['box_mm'][2]) / 2, 'y_mm': (by[s['name']]['box_mm'][1] + by[s['name']]['box_mm'][3]) / 2,
                 'basis': 'spread over its pads\' box %.2f x %.2f mm; %s' % (by[s['name']]['box_mm'][2] - by[s['name']]['box_mm'][0],
                                                                         by[s['name']]['box_mm'][3] - by[s['name']]['box_mm'][1], source_words)}
                for s in sorted(out['sources'], key=lambda s: -s['peakRise'])]
    field = {'origin_mm': [ox, oy], 'xs_mm': [x * 1e3 for x in out['map']['xs']], 'ys_mm': [y * 1e3 for y in out['map']['ys']], 'rise_c': out['map']['rise']}
    return summary, hotspots, field, ''
