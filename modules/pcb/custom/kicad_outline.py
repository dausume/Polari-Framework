"""
@module pcb.custom.kicad_outline

bob-3e: THE BOARD'S SHAPE from its Edge.Cuts drawing - not only its bounding box. KiCad draws an outline as loose items (gr_line, gr_arc, gr_rect,
gr_circle, gr_poly) whose ends meet; this chains them into closed loops:

  loops(tree) -> {'polygon_mm': outer loop [[x, y], ...], 'holes_mm': [loop, ...], 'open_ends': n, 'arc_step_deg': ARC_STEP_DEG}
    outer = the loop of largest area, holes = every other closed loop (cut-outs, mounting slots); arcs and circles become chords every ARC_STEP_DEG
    (a stated discretisation: the chord error is r (1 - cos(step / 2)), 0.1% of r at 5 degrees); items whose ends do not meet within END_TOL_MM are
    counted in open_ends and left out - an outline KiCad's own DRC would also flag, never closed by guessing.
"""
import math

from pcb.custom import sexpr as S

ARC_STEP_DEG = 5.0
END_TOL_MM = 1e-3


def _pt(e, head):
    x, y, _ = S.xy(e, head)
    return (x, y)


def _circle_through(a, m, b):
    """Centre and radius of the circle through three points (None when they are in a line)."""
    ax, ay = a
    bx, by = m
    cx, cy = b
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None, 0.0
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.dist((ux, uy), a)


def arc_points(start, mid, end, step_deg=ARC_STEP_DEG):
    """The arc start -> mid -> end as points (start and end exact), one chord per step_deg at most."""
    c, r = _circle_through(start, mid, end)
    if c is None:
        return [start, end]
    a0, am, a1 = (math.atan2(p[1] - c[1], p[0] - c[0]) for p in (start, mid, end))
    sweep = (a1 - a0) % (2 * math.pi)
    if (am - a0) % (2 * math.pi) > sweep:  # the mid point is on the other way round
        sweep -= 2 * math.pi
    n = max(2, int(math.ceil(abs(math.degrees(sweep)) / step_deg)))
    return [start] + [(c[0] + r * math.cos(a0 + sweep * i / n), c[1] + r * math.sin(a0 + sweep * i / n)) for i in range(1, n)] + [end]


def _area(loop):
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]))


def _pieces(tree):
    """(open chains [[pt, ...]], closed loops) from the Edge.Cuts items."""
    chains, closed = [], []
    for g in S.find(tree, 'gr_line'):
        if S.value(g, 'layer') == 'Edge.Cuts':
            chains.append([_pt(g, 'start'), _pt(g, 'end')])
    for g in S.find(tree, 'gr_arc'):
        if S.value(g, 'layer') == 'Edge.Cuts':
            chains.append(arc_points(_pt(g, 'start'), _pt(g, 'mid'), _pt(g, 'end')))
    for g in S.find(tree, 'gr_rect'):
        if S.value(g, 'layer') == 'Edge.Cuts':
            (x0, y0), (x1, y1) = _pt(g, 'start'), _pt(g, 'end')
            closed.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    for g in S.find(tree, 'gr_circle'):
        if S.value(g, 'layer') == 'Edge.Cuts':
            c, e = _pt(g, 'center'), _pt(g, 'end')
            r = math.dist(c, e)
            n = int(math.ceil(360.0 / ARC_STEP_DEG))
            closed.append([(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)])
    for g in S.find(tree, 'gr_poly'):
        if S.value(g, 'layer') == 'Edge.Cuts':
            pts = [(S.num(p[1]), S.num(p[2])) for p in S.find_all(g, 'xy')]
            if len(pts) >= 3:
                closed.append(pts)
    return chains, closed


def loops(tree):
    chains, closed = _pieces(tree)
    near = lambda a, b: math.dist(a, b) <= END_TOL_MM
    open_ends = 0
    while chains:
        loop = chains.pop(0)
        grown = True
        while grown and not (len(loop) > 2 and near(loop[0], loop[-1])):
            grown = False
            for i, c in enumerate(chains):
                if near(loop[-1], c[0]):
                    loop += c[1:]
                elif near(loop[-1], c[-1]):
                    loop += c[::-1][1:]
                else:
                    continue
                chains.pop(i)
                grown = True
                break
        if len(loop) > 2 and near(loop[0], loop[-1]):
            closed.append(loop[:-1])
        else:
            open_ends += 1
    closed.sort(key=lambda lp: -abs(_area(lp)))
    rnd = lambda lp: [[round(x, 4), round(y, 4)] for x, y in lp]
    return {'polygon_mm': rnd(closed[0]) if closed else [], 'holes_mm': [rnd(lp) for lp in closed[1:]], 'open_ends': open_ends,
            'arc_step_deg': ARC_STEP_DEG}
