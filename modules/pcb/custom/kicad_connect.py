"""
@module pcb.custom.kicad_connect

kxc-2 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): THE ELECTRICAL GRAPH OF A SCHEMATIC, read from the file itself (no KiCad). Polari is the source of truth
(his ruling 2026-10-30), so the nets are OURS - KiCad's own netlist is the cross-check, never the input.

  connect(instances, lib_symbols, symbols)  → (nets, problems): every sheet instance's connection points joined:
      symbol pins   the library pin's tip, transformed into the sheet (library y-up → sheet y-down, the symbol's mirror then its rotation, plus its at)
      wires         a wire joins its two ends and anything lying on it (a T needs no junction dot; crossing wires without an end on each other do not join)
      junctions     a point on two wires joins them
      labels        local labels join by name WITHIN one sheet instance; global labels and power symbols join by name everywhere
      hierarchy     a child sheet's hierarchical label joins the parent's sheet pin of the same name on that sheet instance
      no_connect    marks a pin as deliberately unconnected (kept on the endpoint)
  compare(nets, kicad_netlist_rows)        node sets equal? (net names are compared separately: KiCad's naming has its own priorities)

A net = {name, scope, endpoints: [{ref, pin, pin_name, pintype, instance_path, x, y}], labels, power}. Names follow KiCad's visible rules where they
are unambiguous: a power symbol's or global label's name; a local or hierarchical label prefixed by its sheet path; else unnamed-<ref>-<pin>.
Buses are not expanded yet (counted in KiCadCoverage, next slice).
"""
import math

from pcb.custom import sexpr as S

Q = 10000   # 0.1 µm grid for point identity (KiCad writes mm with at most 4 decimals)


def _k(x, y):
    return (round(x * Q), round(y * Q))


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _lib_pins(lsym, unit, body_style):
    """[(number, name, type, x, y)] of one library symbol's pins for this unit (unit 0 sub-symbols are shared by every unit)."""
    out = []
    for sub in S.find(lsym, 'symbol'):
        parts = str(sub[1]).rsplit('_', 2)
        if len(parts) < 3:
            continue
        u, b = int(S.num(parts[1], 0)), int(S.num(parts[2], 0))
        if u not in (0, unit) or b not in (0, body_style):
            continue
        for p in S.find(sub, 'pin'):
            x, y, _ = S.xy(p)
            out.append((S.value(p, 'number'), S.value(p, 'name'), str(p[1]) if len(p) > 1 else '', x, y))
    return out


def place(x, y, at, rot, mirror):
    """Library point → sheet point: flip y (library y-up), mirror, rotate (counter-clockwise on screen, y down), translate."""
    x, y = x, -y
    if mirror == 'x':
        y = -y
    elif mirror == 'y':
        x = -x
    a = math.radians(rot)
    return at[0] + x * math.cos(a) + y * math.sin(a), at[1] - x * math.sin(a) + y * math.cos(a)


def _on_segment(pt, a, b, eps=1.0):
    """pt on the segment a-b (integer grid units; eps = 1 unit)."""
    (px, py), (ax, ay), (bx, by) = pt, a, b
    if min(ax, bx) - eps > px or px > max(ax, bx) + eps or min(ay, by) - eps > py or py > max(ay, by) + eps:
        return False
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    length = math.hypot(bx - ax, by - ay) or 1.0
    return abs(cross) / length <= eps


def connect(instances, lib_symbols, symbols):
    """instances: kicad_cover.sheet_instances(); lib_symbols {lib_id: tree}; symbols: SchematicSymbol rows (one per placed instance)."""
    uf, problems = _UF(), []
    endpoints, labels, power_names, no_connects = {}, {}, {}, set()
    by_inst = {}
    for s in symbols:
        by_inst.setdefault((s['instance_path'], s['uuid']), s)
    for inst in instances:
        ipath = '/' + '/'.join(inst['uuids'])
        tag = lambda k: (ipath, k)   # noqa: E731 - a point belongs to its sheet INSTANCE
        points = set()
        wires = []
        for w in S.find(inst['tree'], 'wire'):
            pts = [_k(S.num(xy[1]), S.num(xy[2])) for xy in S.find_all(w, 'xy')]
            for a, b in zip(pts, pts[1:]):
                wires.append((a, b))
                uf.union(tag(a), tag(b))
                points |= {a, b}
        for j in S.find(inst['tree'], 'junction'):
            x, y, _ = S.xy(j)
            points.add(_k(x, y))
        for nc in S.find(inst['tree'], 'no_connect'):
            x, y, _ = S.xy(nc)
            no_connects.add(tag(_k(x, y)))
        for head, scope in (('label', 'local'), ('global_label', 'global'), ('hierarchical_label', 'hierarchical')):
            for lb in S.find(inst['tree'], head):
                x, y, _ = S.xy(lb)
                k = _k(x, y)
                points.add(k)
                labels.setdefault((scope, ipath if scope == 'local' else '', str(lb[1])), []).append(tag(k))
                if scope == 'hierarchical':
                    labels.setdefault(('hier-child', ipath, str(lb[1])), []).append(tag(k))
        for sh in S.find(inst['tree'], 'sheet'):   # this instance's sheet pins: they meet the child instance's hierarchical labels
            child = ipath + '/' + S.value(sh, 'uuid')
            for p in S.find(sh, 'pin'):
                x, y, _ = S.xy(p)
                k = _k(x, y)
                points.add(k)
                labels.setdefault(('hier-child', child, str(p[1])), []).append(tag(k))
        for s in S.find(inst['tree'], 'symbol'):
            row = by_inst.get((ipath, S.value(s, 'uuid')))
            lsym = lib_symbols.get(S.value(s, 'lib_id'))
            if row is None or lsym is None:
                problems.append('%s: symbol %s (%s) not placed or no library symbol' % (inst['path'], S.value(s, 'uuid'), S.value(s, 'lib_id')))
                continue
            at = S.xy(s)
            pins = _lib_pins(lsym, row['unit'], int(S.num(S.value(s, 'body_style') or S.value(s, 'convert') or 1, 1)))
            # a GLOBAL power symbol = a (power) symbol whose pin is power_in: its net is named by its value everywhere. A (power) symbol with a power_out
            # pin (PWR_FLAG) only marks its own net as driven - it joins nothing by name
            is_power = bool(S.find(lsym, 'power'))
            global_power = is_power and all(p[2] == 'power_in' for p in pins)
            units = len({int(S.num(str(sub[1]).rsplit('_', 2)[1], 0)) for sub in S.find(lsym, 'symbol') if len(str(sub[1]).rsplit('_', 2)) == 3} - {0})
            for num, name, ptype, lx, ly in pins:
                k = _k(*place(lx, ly, at[:2], at[2], row['mirror']))
                points.add(k)
                key = tag(k)
                if global_power:
                    power_names.setdefault(row['value'], []).append(key)
                elif is_power:
                    continue
                else:
                    endpoints.setdefault(key, []).append({'ref': row['ref'], 'pin': num, 'pin_name': name, 'pintype': ptype, 'instance_path': ipath,
                                                         'x': k[0] / Q, 'y': k[1] / Q, 'unit_letter': chr(64 + row['unit']) if units > 1 else ''})
        for pt in points:   # a point on a wire joins it (wire ends already joined their own wire)
            for a, b in wires:
                if pt != a and pt != b and _on_segment(pt, a, b):
                    uf.union(tag(pt), tag(a))
            uf.find(tag(pt))
    named = {}
    for (scope, where, name), keys in labels.items():
        for k in keys[1:]:
            uf.union(keys[0], k)
        named.setdefault(uf.find(keys[0]), []).append((scope, where, name))
    for name, keys in power_names.items():
        for k in keys[1:]:
            uf.union(keys[0], k)
    # a global label and a power symbol of one name are one net
    globals_ = {}
    for (scope, where, name), keys in labels.items():
        if scope == 'global':
            globals_.setdefault(name, []).extend(keys)
    for name, keys in power_names.items():
        globals_.setdefault(name, []).extend(keys)
    for name, keys in globals_.items():
        for k in keys[1:]:
            uf.union(keys[0], k)
    groups, seen = {}, set()
    for key, eps in sorted(endpoints.items()):
        for e in eps:   # a pin shared by every unit (a dual op-amp's supply pins) is ONE pin of the part, whichever unit draws it
            if (e['ref'], e['pin']) in seen:
                continue
            seen.add((e['ref'], e['pin']))
            groups.setdefault(uf.find(key), []).append(dict(e, no_connect=key in no_connects))
    root_names = {}
    for name, keys in globals_.items():
        root_names.setdefault(uf.find(keys[0]), set()).add(('global', '', name))
    for (scope, where, name), keys in labels.items():
        if scope in ('local', 'hierarchical'):
            root_names.setdefault(uf.find(keys[0]), set()).add((scope, where, name))
    inst_name = {'/' + '/'.join(i['uuids']): i['path'] for i in instances}
    nets = []
    for root, eps in groups.items():
        names = root_names.get(root, set())
        glob = sorted(n for s, _, n in names if s == 'global')
        loc = sorted((inst_name.get(w, '/') + n) for s, w, n in names if s in ('local', 'hierarchical'))
        eps = sorted(eps, key=lambda e: (e['ref'], e['pin']))
        name = glob[0] if glob else loc[0] if loc else _driver_name(eps)
        nets.append({'name': name, 'scope': 'global' if glob else 'sheet' if loc else 'unnamed', 'aliases': glob[1:] + (loc[1:] if not glob else loc),
                     'endpoints': eps})
    return sorted(nets, key=lambda n: n['name']), problems


def _named(e):
    """A pin has a NAME when it is neither empty, '~' nor just its own number (KiCad's own reading)."""
    return bool(e['pin_name']) and e['pin_name'] not in ('~', e['pin'])


def _driver_name(eps):
    """An unlabelled net's name the way KiCad writes it: Net-(<ref><unit>-<pin name | Pad<n>>), a NAMED pin preferred, ties by reference + unit then
    pin; a lone pin is unconnected-(<ref>-<name>-Pad<n>) or unconnected-(<ref>-Pad<n>)."""
    named = [e for e in eps if _named(e)]
    e = sorted(named or eps, key=lambda e: (e['ref'] + e.get('unit_letter', ''), e['pin']))[0]
    if len(eps) == 1:
        return 'unconnected-(%s-%sPad%s)' % (e['ref'], (e['pin_name'] + '-') if _named(e) else '', e['pin'])
    return 'Net-(%s%s-%s)' % (e['ref'], e.get('unit_letter', ''), e['pin_name'] if _named(e) else 'Pad%s' % e['pin'])


def rows(nets, board):
    """{'SchematicNet': [...], 'NetEndpoint': [...]} - the rows of one schematic's nets."""
    import json
    out = {'SchematicNet': [], 'NetEndpoint': []}
    for n in nets:
        types = {}
        for e in n['endpoints']:
            types[e['pintype']] = types.get(e['pintype'], 0) + 1
        out['SchematicNet'].append({'name': '%s:%s' % (board, n['name']), 'board': board, 'net': n['name'], 'scope': n['scope'], 'endpoints': len(n['endpoints']),
                                    'aliases_json': json.dumps(n['aliases']), 'pintypes_json': json.dumps(types, sort_keys=True), 'kicad_check': '', 'notes': ''})
        for e in n['endpoints']:
            out['NetEndpoint'].append({'name': '%s:%s:%s' % (board, e['ref'], e['pin']), 'board': board, 'net': n['name'], 'ref': e['ref'],
                                       'unit': e.get('unit_letter', ''), 'pin': e['pin'], 'pin_name': e['pin_name'], 'pintype': e['pintype'],
                                       'instance_path': e['instance_path'], 'x_mm': e['x'], 'y_mm': e['y'], 'no_connect': bool(e.get('no_connect')), 'notes': ''})
    return out


def kicad_netlist_rows(tree):
    """[(net, ref, pin, pintype)] from KiCad's own exported netlist (kicadsexpr)."""
    out = []
    for net in S.find(S.find(tree, 'nets')[0], 'net'):
        for nd in S.find(net, 'node'):
            out.append((S.value(net, 'name'), S.value(nd, 'ref'), S.value(nd, 'pin'), S.value(nd, 'pintype')))
    return out


def compare(nets, kicad_rows):
    """{'same_groups', 'ours_only', 'kicad_only', 'names_equal', 'name_differences'} - node SETS compared (each net a frozenset of (ref, pin))."""
    ours = {frozenset((e['ref'], e['pin']) for e in n['endpoints']): n['name'] for n in nets}
    theirs = {}
    for name, ref, pin, _ in kicad_rows:
        theirs.setdefault(name, set()).add((ref, pin))
    theirs = {frozenset(v): k for k, v in theirs.items()}
    same = set(ours) & set(theirs)
    diffs = sorted((ours[g], theirs[g]) for g in same if ours[g] != theirs[g])
    return {'same_groups': len(same), 'ours_only': sorted(sorted(g) for g in set(ours) - set(theirs)),
            'kicad_only': sorted(sorted(g) for g in set(theirs) - set(ours)), 'names_equal': len(same) - len(diffs), 'name_differences': diffs}
