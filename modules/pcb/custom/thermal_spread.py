"""
@module pcb.custom.thermal_spread

bob-3d (BENCH_BOARDS_PLAN bob-3, his words 2026-10-30: "finite element model simulations are already well defined"): WHERE THE HEAT SITS on a PCB - the
board as a thin plate solved by the existing FEM engine (materialsScience.engines.fem_plate_thermal, scikit-fem), fed only by the board's own rows and
a kept run. Nothing here is a new model: it maps rows onto the textbook plate problem and reads the answer back.

  spread(manager, board, run=None, rows=None, h=H_FREE_AIR, refine=12, powers=None) -> (summary, hotspots, field, why)
    plate        the board's own Edge.Cuts shape (bob-3e: PcbBoard outline_json polygon_mm + holes_mm, pcb.custom.kicad_outline); a board ingested
                 before that has only its bounding box, and says so
    sheet K      layers in parallel, sum k_i t_i: every dielectric layer of the stackup at the FR-4 in-plane conductivity (a cited knob); copper ONLY
                 where it is - each copper pour / teardrop (PcbZone) adds k_Cu x its layer's thickness x (filled / outline area); each PAD adds
                 k_Cu x the thickness of the copper layers it is on over its own rectangle; each TRACK (NetGeometry segments + arcs as chords) is an
                 embedded conductor k_Cu x width x thickness along itself only. Vias are not counted: in a plate at one temperature through its
                 thickness they carry heat between layers, not along the board (said)
    sources      each part's average power from the run (pcb.custom.thermal.dissipation; sources themselves excluded) spread over the box of its own
                 pads (PcbPad); a part with no pads, and the power the run cannot place (unaccounted), are listed, never guessed onto the board
    powers       {ref: W} given by a person instead of a run (said as 'given' on every row); with none, pcb.custom.thermal_inputs.power_plan: a
                 PartPowerInput a person gave wins over the run for that part, a duty-cycled one counts at its average (power x on / period)
    junction     bob-3g: a part with a datasheet model (PartThermalModel) gets its junction's rise = the board's mean rise under it + P x Rth j-board
                 (sum of its Foster R), beside the datasheet's own P x Rth j-a (its test board, for comparison) and its Tj max at AMBIENT_C (a knob)
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
AMBIENT_C = 25.0   # a KNOB: room temperature for reading a junction rise against a datasheet Tj max - never measured, always said
CLASSES = ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact', 'PcbBoard', 'PcbPad', 'PcbZone', 'NetGeometry')
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


def _pad_copper(pads, copper, ox, oy):
    """Each pad as a copper region over its own rectangle (turned by its angle; a round / oval pad by its bounding rectangle, said)."""
    out = []
    for p in pads:
        layers = json.loads(p.get('layers_json') or '[]')
        t = sum(copper[c] for c in copper if c in layers or '*.Cu' in layers)
        w, ht = float(p.get('size_w_mm') or 0), float(p.get('size_h_mm') or 0)
        if t <= 0 or w <= 0 or ht <= 0:
            continue
        a = math.radians(float(p.get('angle') or 0))
        ca, sa = math.cos(a), math.sin(a)
        corners = [((p['x_mm'] - ox + dx * ca - dy * sa) * 1e-3, (p['y_mm'] - oy + dx * sa + dy * ca) * 1e-3)
                   for dx, dy in ((-w / 2, -ht / 2), (w / 2, -ht / 2), (w / 2, ht / 2), (-w / 2, ht / 2))]
        region = {'name': p['name'], 'add_k_sheet': K_CU * t * 1e-3}
        if abs(round(math.degrees(a) / 90) * 90 - math.degrees(a)) < 1e-6:
            xs, ys = [c[0] for c in corners], [c[1] for c in corners]
            region.update(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys))
        else:
            region['polygon'] = [list(c) for c in corners]
        out.append(region)
    return out


def _tracks(geoms, copper, ox, oy):
    """Each track segment (and each arc, as chords) as an embedded conductor k_Cu x width x thickness."""
    from pcb.custom.kicad_outline import arc_points
    lines = []
    for g in geoms:
        pieces = [((x1, y1), (x2, y2), wd, lay) for x1, y1, x2, y2, wd, lay in json.loads(g.get('segments_json') or '[]')]
        for sx, sy, mx, my, ex, ey, wd, lay in json.loads(g.get('arcs_json') or '[]'):
            pts = arc_points((sx, sy), (mx, my), (ex, ey))
            pieces += [(a, b, wd, lay) for a, b in zip(pts, pts[1:])]
        for (x1, y1), (x2, y2), wd, lay in pieces:
            if copper.get(lay, 0) > 0 and wd > 0:
                lines.append({'name': g.get('net', ''), 'x0': (x1 - ox) * 1e-3, 'y0': (y1 - oy) * 1e-3, 'x1': (x2 - ox) * 1e-3, 'y1': (y2 - oy) * 1e-3,
                              'k_line': K_CU * wd * 1e-3 * copper[lay] * 1e-3})
    return lines


def steady_w(plan_row):
    """The power a part puts in on average over a long time: always on -> its power; duty-cycled -> power x on / period; one pulse -> 0."""
    p, on, period = plan_row['avg_w'], plan_row.get('on_s', 0.0), plan_row.get('period_s', 0.0)
    if on <= 0:
        return p
    return p * min(1.0, on / period) if period > 0 else 0.0


def plate_inputs(board, rows):
    """(plate, why): the board as the plate solvers take it - its shape, the dielectric sheet, copper where it is (pours, pads, tracks), its pads by ref."""
    pcb = next(iter(rows.get('PcbBoard') or []), None)
    if pcb is None or not float(pcb.get('width_mm') or 0) or not float(pcb.get('height_mm') or 0):
        return None, 'no PCB outline for %s (a schematic-only project has no board to spread heat in)' % board
    shape = json.loads(pcb.get('outline_json') or '{}')
    bbox = shape.get('bbox_mm') or [0.0, 0.0, pcb['width_mm'], pcb['height_mm']]
    ox, oy, w, ht = bbox[0], bbox[1], float(pcb['width_mm']), float(pcb['height_mm'])
    diel, copper, stack_words = _stack(pcb)
    if diel <= 0:
        return None, 'undetermined: %s has neither a stackup nor a thickness - the plate\'s conductance is unknown' % board
    regions = []
    for z in rows.get('PcbZone') or []:
        layers = _zone_layers(z, copper)
        outline = json.loads(z.get('outline_json') or '[]')
        if z.get('kind') not in _COPPER_ZONES or not layers or len(outline) < 3 or not float(z.get('outline_area_mm2') or 0):
            continue
        fill = float(z.get('filled_area_mm2') or 0) / float(z['outline_area_mm2'])
        regions.append({'name': z['name'], 'add_k_sheet': K_CU * sum(copper[c] for c in layers) * 1e-3 * fill,
                        'polygon': [[(x - ox) * 1e-3, (y - oy) * 1e-3] for x, y in outline]})
    zones = len(regions)
    regions += _pad_copper(rows.get('PcbPad') or [], copper, ox, oy)
    to_m = lambda loop: [[(x - ox) * 1e-3, (y - oy) * 1e-3] for x, y in loop]   # noqa: E731
    outline, holes = to_m(shape.get('polygon_mm') or []), [to_m(hl) for hl in shape.get('holes_mm') or []]
    pads = {}
    for p in rows.get('PcbPad') or []:
        pads.setdefault(p['ref'], []).append(p)
    return {'ox': ox, 'oy': oy, 'w': w, 'ht': ht, 'diel': diel, 'stack_words': stack_words, 'regions': regions, 'zones': zones,
            'lines': _tracks(rows.get('NetGeometry') or [], copper, ox, oy), 'outline': outline, 'holes': holes, 'pads': pads,
            'n_pads': len(rows.get('PcbPad') or []),
            'shape_words': (('the board\'s own Edge.Cuts shape (%d vertices, %d cut-outs)' % (len(outline), len(holes))) if outline
                            else 'the %g x %g mm Edge.Cuts box (ingested before the shape was kept - re-ingest for the outline itself)' % (w, ht))}, ''


def place_sources(plate, given):
    """(sources, unplaced): each powered part spread over the box of its own pads (m, board frame); a part with no pads is listed, never guessed."""
    sources, unplaced = [], []
    ox, oy, w, ht = plate['ox'], plate['oy'], plate['w'], plate['ht']
    for p in given:
        if not plate['pads'].get(p['ref']):
            unplaced.append(p['ref'])
            continue
        x0, y0, x1, y1 = _pad_box(plate['pads'][p['ref']])
        sources.append(dict({k: p[k] for k in ('on_s', 'period_s') if k in p}, name=p['ref'], power_w=p['avg_w'], x0=max(0.0, (x0 - ox) * 1e-3),
                            y0=max(0.0, (y0 - oy) * 1e-3), x1=min(w, x1 - ox) * 1e-3, y1=min(ht, y1 - oy) * 1e-3, box_mm=(x0, y0, x1, y1)))
    return sources, unplaced


def spread(manager, board, run=None, rows=None, h=H_FREE_AIR, refine=12, powers=None):
    from materialsScience.engines.fem_plate_thermal import solve_plate_conduction_2d
    rows = rows if rows is not None else _rows_of(manager, board, CLASSES)
    plate, why = plate_inputs(board, rows)
    if why:
        return None, [], None, why

    if powers is not None:
        given = [{'ref': r, 'avg_w': float(p), 'kind': 'given'} for r, p in powers.items()]
        source_words, unaccounted = 'given by a person', ''
    else:   # bob-3g: a power a person gave (PartPowerInput) wins over the run's average for that part
        from pcb.custom.thermal_inputs import power_plan
        plan, source_words, unaccounted, why = power_plan(manager, board, run, rows)
        if why:
            return None, [], None, why
        given = [{'ref': p['ref'], 'avg_w': steady_w(p), 'kind': p['from']} for p in plan if steady_w(p) > 0]
        pulsed = [p['ref'] for p in plan if p['on_s'] > 0 and p['period_s'] <= 0]
        if pulsed:
            unaccounted += '; a single pulse leaves nothing in steady state - see Thermal over time: %s' % ', '.join(pulsed)

    sources, unplaced = place_sources(plate, given)
    ox, oy, w, ht, diel, lines = plate['ox'], plate['oy'], plate['w'], plate['ht'], plate['diel'], plate['lines']
    regions, outline, holes, zones = plate['regions'], plate['outline'], plate['holes'], plate['zones']
    shape_words, stack_words = plate['shape_words'], plate['stack_words']

    base = {'board': board, 'source': source_words, 'h_w_m2k': h, 'max_rise_c': -1.0, 'mean_rise_c': -1.0, 'lumped_mean_rise_c': -1.0,
            'placed_w': sum(s['power_w'] for s in sources), 'parts_placed': len(sources), 'parts_unplaced': ', '.join(unplaced),
            'zones': zones, 'pads': len(rows.get('PcbPad') or []), 'tracks': len(lines)}
    if not sources:
        return dict(base, basis='no part with power has pads on the board - nothing to spread%s' % unaccounted), [], None, ''
    out = solve_plate_conduction_2d(w * 1e-3, ht * 1e-3, K_FR4_INPLANE * diel * 1e-3, h, sources=sources, regions=regions, lines=lines,
                                     outline=outline or None, holes=holes, refine=refine)
    if not out.get('ok'):
        return dict(base, basis='the FEM solve refused: %s' % out.get('error')), [], None, ''

    summary = dict(base, max_rise_c=out['maxRise'], mean_rise_c=out['meanRise'], lumped_mean_rise_c=out['lumpedMeanRise'],
                   balance_error=out['balanceError'], spreading_length_mm=out['spreadingLength'] * 1e3, dofs=out['dofs'], area_mm2=out['plateArea'] * 1e6,
                   basis=('steady thin-plate FEM (scikit-fem): -div(K grad T) + 2h T = q, edges insulated; plate = %s; K = FR-4 %s (%s) + copper where it '
                          'is, at k_Cu (%s): %d pours x layer thickness x fill, %d pads over their rectangles, %d track pieces along themselves (vias not '
                          'counted: they carry heat through the board, not along it); h a knob (%s); sources = %s over each part\'s pad box%s%s'
                          % (shape_words, stack_words, K_FR4_CITE, K_CU_CITE, base['zones'], base['pads'], len(lines), H_CITE, source_words,
                             ('; no pads, not placed: %s' % ', '.join(unplaced)) if unplaced else '', unaccounted)))
    by = {s['name']: s for s in sources}
    from pcb.custom.thermal_inputs import models
    mods = models(manager, board, rows)
    hotspots = []
    for s in sorted(out['sources'], key=lambda s: -s['peakRise']):
        box = by[s['name']]['box_mm']
        row = {'ref': s['name'], 'power_w': s['power_w'], 'peak_rise_c': s['peakRise'], 'mean_rise_c': s['meanRise'],
               'x_mm': (box[0] + box[2]) / 2, 'y_mm': (box[1] + box[3]) / 2, 'junction_rise_c': -1.0, 'tj_c': -1.0, 'tj_max_c': -1.0,
               'datasheet_ja_rise_c': -1.0, 'basis': 'spread over its pads\' box %.2f x %.2f mm; %s' % (box[2] - box[0], box[3] - box[1], source_words)}
        m = mods.get(s['name'])
        if m and m['stages']:
            row.update(junction_rise_c=s['meanRise'] + s['power_w'] * m['rth'], tj_max_c=m['tj_max_c'] or -1.0)
            row['tj_c'] = AMBIENT_C + row['junction_rise_c']
            row['basis'] += ('; junction = board mean under it + P x Rth j-%s %.4g K/W (datasheet model %s: %s); Tj at ambient %g C, a knob'
                             % (m['reference'], m['rth'], m['name'], m['words'], AMBIENT_C))
        elif m and m['bad']:
            row['basis'] += '; datasheet model %s not used: %s' % (m['name'], m['bad'])
        if m and m['rth_ja_k_w']:
            row['datasheet_ja_rise_c'] = s['power_w'] * m['rth_ja_k_w']
        hotspots.append(row)
    field = {'origin_mm': [ox, oy], 'xs_mm': [x * 1e3 for x in out['map']['xs']], 'ys_mm': [y * 1e3 for y in out['map']['ys']], 'rise_c': out['map']['rise']}
    return summary, hotspots, field, ''
