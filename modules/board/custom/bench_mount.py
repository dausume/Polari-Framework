"""
@module board.custom.bench_mount

drv-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; the user's words 2026-10-31: "enable placing boards with footprints onto other boards"): ONE BOARD MOUNTED ON
ANOTHER, BY POSITION. The child Board (a DIP driver, a breakout module, a shield) is put at (x_mm, y_mm) on the parent Board (a breadboard, a PCB, a dev
board) turned by `rotation` degrees; every child foothold lands on the parent foothold under it - both positions are each board's own (cited or
derived) foothold geometry, so a pin that lands nowhere, or two pins the parent joins, is a fact of the geometry, not a guess:

  landings(child_feet, parent_feet, x_mm, y_mm, rotation=0, tolerance_mm=0.5) -> {'pairs': [(child foothold, parent foothold, miss_mm)],
                       'unlanded': [child footholds with no parent foothold within tolerance], 'shared': [parent footholds hit twice],
                       'joined': [(child a, child b, parent node)] - two child pins the parent joins inside (a DIP not straddling a breadboard's
                       trench puts opposite pins on one strip: a short through the parent)}
  placements(child_feet, parent_feet, rotations=(0, 90, 180, 270), tolerance_mm=0.5, limit=60) -> [{x_mm, y_mm, rotation, first_on, pins}]
                       drv-2: every position where the child mounts cleanly - all pins land, none share a hole, none joined - found by putting the
                       child's first pin on each parent foothold at each rotation (a spatial index, so a 16-pin DIP over a 400-hole breadboard is quick)
  options(manager, bench, child, limit=60) -> (status, body)   the clean placements of one Board on every other Board of the bench (the page's
                       "Mount here" rows)
  mount(manager, bench, body) -> (status, body)   {child, parent, x_mm, y_mm, rotation?, tolerance_mm?, allow_joined?}: stores one BenchConnection
                       (kind mounted) per landed pin - all pins must land and none may share a hole; joined pins are refused unless allow_joined
                       (a part whose pins are meant to be joined, said by the person)
Transform: the child's own frame (y down) turned counter-clockwise on screen by `rotation` about its origin, then moved to (x_mm, y_mm) in the
parent's frame - the same convention as KiCad's footprint placement (board.pcb kicad_footholds.pad_positions).
"""
import math


def _place(f, x, y, rot):
    a = math.radians(rot)
    fx, fy = float(f.get('x_mm') or 0.0), float(f.get('y_mm') or 0.0)
    return x + fx * math.cos(a) + fy * math.sin(a), y - fx * math.sin(a) + fy * math.cos(a)


def landings(child_feet, parent_feet, x_mm, y_mm, rotation=0.0, tolerance_mm=0.5):
    pairs, unlanded, hit = [], [], {}
    for f in sorted(child_feet, key=lambda f: f['foothold']):
        px, py = _place(f, x_mm, y_mm, rotation)
        best = min(parent_feet, key=lambda p: math.hypot(p['x_mm'] - px, p['y_mm'] - py), default=None)
        miss = math.hypot(best['x_mm'] - px, best['y_mm'] - py) if best else float('inf')
        if best is None or miss > tolerance_mm:
            unlanded.append(f['foothold'])
            continue
        pairs.append((f['foothold'], best['foothold'], round(miss, 4)))
        hit.setdefault(best['foothold'], []).append(f['foothold'])
    node = {p['foothold']: p['node'] for p in parent_feet}
    by_node = {}
    for c, p, _ in pairs:
        by_node.setdefault(node[p], []).append(c)
    joined = [(cs[i], cs[j], n) for n, cs in sorted(by_node.items()) for i in range(len(cs)) for j in range(i + 1, len(cs))]
    return {'pairs': pairs, 'unlanded': unlanded, 'shared': sorted(p for p, cs in hit.items() if len(cs) > 1), 'joined': joined}


def mount(manager, bench_name, body):
    from board.custom import bench_nets as BN
    feet, by_id = BN._boards(bench_name, manager)
    if feet is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    body = body or {}
    child, parent = body.get('child', ''), body.get('parent', '')
    for who in (child, parent):
        if who not in by_id:
            return 422, {'ok': False, 'error': 'no Board %r on this bench (ids: %s)' % (who, ', '.join(sorted(by_id)))}
        if who not in feet:
            return 422, {'ok': False, 'error': 'Board %r has no footholds (%s)' % (who, by_id[who]['footholds_note'])}
    if child == parent:
        return 422, {'ok': False, 'error': 'a Board cannot be mounted on itself'}
    try:
        x, y, rot = float(body['x_mm']), float(body['y_mm']), float(body.get('rotation', 0.0))
        tol = float(body.get('tolerance_mm', 0.5))
    except (KeyError, TypeError, ValueError):
        return 400, {'ok': False, 'error': 'body needs x_mm and y_mm (numbers; rotation and tolerance_mm optional)'}
    got = landings(feet[child], feet[parent], x, y, rot, tol)
    why = []
    if got['unlanded']:
        why.append('%d pin(s) of %s land on nothing of %s within %g mm: %s' % (len(got['unlanded']), child, parent, tol, ', '.join(got['unlanded'])))
    if got['shared']:
        why.append('two pins land in one place: %s' % ', '.join(got['shared']))
    if got['joined'] and not body.get('allow_joined'):
        why.append('%s joins pins of %s inside itself (a short through the parent): %s' % (
            parent, child, '; '.join('%s + %s on %s' % j for j in got['joined'][:6])))
    if why:
        return 422, dict({'ok': False, 'error': '; '.join(why)}, **got)
    conns = [{'from_board': child, 'from_foothold': c, 'to_board': parent, 'to_foothold': p, 'kind': 'mounted',
              'label': 'mounted at %g, %g mm, %g deg' % (x, y, rot)} for c, p, _ in got['pairs']]
    status, out = BN.add_connections(manager, bench_name, conns)
    return status, dict(out, landings=got['pairs'])


def _grid(parent_feet, tol):
    cell, g = max(tol, 1e-6), {}
    for p in parent_feet:
        g.setdefault((round(p['x_mm'] / cell), round(p['y_mm'] / cell)), []).append(p)
    return cell, g


def _near(grid, x, y, tol):
    cell, g = grid
    i, j = round(x / cell), round(y / cell)
    best, miss = None, float('inf')
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for p in g.get((i + di, j + dj), ()):
                d = math.hypot(p['x_mm'] - x, p['y_mm'] - y)
                if d < miss:
                    best, miss = p, d
    return (best, miss) if miss <= tol else (None, miss)


def placements(child_feet, parent_feet, rotations=(0, 90, 180, 270), tolerance_mm=0.5, limit=60):
    if not child_feet or not parent_feet:
        return []
    grid = _grid(parent_feet, tolerance_mm)
    first = sorted(child_feet, key=lambda f: (len(str(f['foothold'])), str(f['foothold'])))[0]
    out, seen = [], set()
    for rot in rotations:
        ox, oy = _place(first, 0.0, 0.0, rot)
        for p in sorted(parent_feet, key=lambda p: (p['y_mm'], p['x_mm'])):
            x, y = p['x_mm'] - ox, p['y_mm'] - oy
            key = (round(x, 3), round(y, 3), rot)
            if key in seen:
                continue
            seen.add(key)
            hit, nodes, ok = set(), {}, True
            for f in child_feet:
                q, _ = _near(grid, *_place(f, x, y, rot), tolerance_mm)
                if q is None or q['foothold'] in hit or q['node'] in nodes:
                    ok = False
                    break
                hit.add(q['foothold'])
                nodes[q['node']] = f['foothold']
            if ok:
                out.append({'x_mm': round(x, 3), 'y_mm': round(y, 3), 'rotation': rot, 'first_on': p['foothold'], 'pins': len(child_feet)})
                if len(out) >= limit:
                    return out
    return out


def options(manager, bench_name, child, limit=60):
    from board.custom import bench_nets as BN
    feet, by_id = BN._boards(bench_name, manager)
    if feet is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    if child not in feet:
        return 422, {'ok': False, 'error': 'no Board %r with footholds on this bench (ids: %s)' % (child, ', '.join(sorted(feet)))}
    rows = []
    for parent in sorted(feet):
        if parent == child:
            continue
        for r in placements(feet[child], feet[parent], limit=limit):
            rows.append(dict(r, child=child, parent=parent, parent_label=by_id[parent]['label'],
                             where='pin %s on %s, turned %g deg' % (sorted(feet[child], key=lambda f: (len(str(f['foothold'])), str(f['foothold'])))[0]['foothold'],
                                                                     r['first_on'], r['rotation'])))
    return 200, {'ok': True, 'bench': bench_name, 'child': child, 'rows': rows,
                 'note': '' if rows else 'no clean placement: on no other Board do all of %s\'s pins land, each in its own place, without two of them joined' % child}
