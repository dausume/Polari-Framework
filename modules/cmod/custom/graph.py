"""
@module cmod.custom.graph

A CGRAPH'S ROWS → A CHECKED MODEL the glue generator renders (C_MODULARIZATION_PLAN.md §5, cmod-1). Everything the C will
say is decided HERE, from the rows and the atoms' committed manifest — so a graph that cannot become correct C is REFUSED
with the reason, never "fixed up":

  nodes     c-atom (an atom of the graph's project, compiled in its base configuration; not an ISR, not main — the glue
            owns main and an ISR is pulled in by the globals it shares), class, parser, frame, tick, rule
  ports     a c-atom's sockets are its CPort rows; the glue kinds have fixed ports (tick.now, rule.now, frame.wire/length,
            parser.byte/frame); a class node's ports are the fields of the generated <class>_packets.h struct
  edges     data (out → in, Polari types must agree), field (out → class field), tick, on-rx (a byte source returning int
            with one out pointer → parser.byte), on-command (parser.frame → a `const polari_rx_t *` port), calls (the caller
            atom must call the callee itself — read from its derived calls)
  bindings  `port=VALUE`: a C integer literal or a macro the rendered headers define (board_config.h, hal.h, the class
            header) — never free C text
  refused   an unknown atom / node / port, an in port bound twice or not at all, a data cycle, a Polari-type mismatch, a
            node fed from two different ticks, a field written after the frame that sends it, a binding that is not a
            literal or a known macro, a 'called' node no atom calls
  scopes    init (before sei()) · loop (every pass) · tick:<node> (every period) · cmd:<parser> (a complete frame) —
            a node's scope = its tick edge's, else the innermost scope of its data inputs

The graph's sha256 = the canonical rows (volatile fields out), so a render names exactly what it rendered.
"""
import hashlib
import heapq
import json
import re

IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
INT_LIT = re.compile(r'^(-?\d+|0[xX][0-9a-fA-F]+)[uUlL]{0,3}$')
NUM_LIT = re.compile(r'^-?(\d+\.?\d*|\.\d+)([eE]-?\d+)?$')
NODE_KINDS = ('c-atom', 'class', 'parser', 'frame', 'tick', 'rule')
EDGE_KINDS = ('data', 'field', 'tick', 'on-rx', 'on-command', 'calls')
STAGES = ('init', 'loop', 'called')
#: the fixed ports of the glue-owned node kinds: (direction, C type, Polari type)
GLUE_PORTS = {'tick': {'now': ('in', 'uint32_t', 'int64')},
              'rule': {'now': ('in', 'uint32_t', 'int64')},
              'frame': {'wire': ('out', 'const uint8_t *', 'bytes'), 'length': ('out', 'size_t', 'int64')},
              'parser': {'byte': ('in', 'uint8_t', 'int64'), 'frame': ('out', 'const polari_rx_t *', 'ref:polari_rx_t')}}
GRAPH_KEYS = ('name', 'project', 'board', 'base_configuration', 'class_name', 'replaces', 'generated_project')
NODE_KEYS = ('instance', 'kind', 'atom', 'stage', 'order', 'bindings', 'params')
EDGE_KEYS = ('kind', 'from_node', 'from_port', 'to_node', 'to_port', 'order', 'scale', 'offset')


class GraphRefused(ValueError):
    pass


def kv(text, where):
    """'a=1; b=X,Y' → {'a': '1', 'b': 'X,Y'} (no JSON on a row a person edits)."""
    out = {}
    for part in [p.strip() for p in (text or '').split(';') if p.strip()]:
        if '=' not in part:
            raise GraphRefused('%s: %r is not key=value' % (where, part))
        k, v = [x.strip() for x in part.split('=', 1)]
        if not IDENT.match(k) or k in out:
            raise GraphRefused('%s: key %r is not a name or appears twice' % (where, k))
        out[k] = v
    return out


def graph_sha(rows):
    """sha256 over the canonical rows: the graph's identity fields, nodes by instance, edges by (order, endpoints)."""
    g = {k: rows['graph'].get(k, '') for k in GRAPH_KEYS}
    nodes = sorted(({k: n.get(k, '') for k in NODE_KEYS} for n in rows['nodes']), key=lambda n: n['instance'])
    edges = sorted(({k: e.get(k, '') for k in EDGE_KEYS} for e in rows['edges']),
                   key=lambda e: (int(e['order'] or 0), e['from_node'], e['from_port'], e['to_node'], e['to_port']))
    return hashlib.sha256(json.dumps({'graph': g, 'nodes': nodes, 'edges': edges}, sort_keys=True).encode()).hexdigest()


def header_struct(text, cls):
    """The generated header's `<cls>_t` fields → {field: C type} (array fields keep their element type + [n])."""
    m = re.search(r'typedef struct\s*\{(.*?)\}\s*%s_t;' % re.escape(cls), text, re.S)
    if not m:
        raise GraphRefused('the class header has no %s_t struct' % cls)
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r'\s*(.+?)\s+(\w+)(\[\d+\])?;', line.split('/*')[0])
        if mm:
            out[mm.group(2)] = mm.group(1) + (mm.group(3) or '')
    return out


def macros(*texts):
    """Every #define name and enum constant the rendered headers declare (what a binding may name)."""
    out = set()
    for t in texts:
        out |= set(re.findall(r'(?m)^\s*#\s*define\s+([A-Za-z_]\w*)', t))
        for body in re.findall(r'enum\s*\{(.*?)\}', t, re.S):
            out |= set(re.findall(r'([A-Za-z_]\w*)\s*(?:=|,|$)', body))
    return out


def _isr_writers(atoms, base):
    """global name → [ISR atom keys writing it] among the atoms compiled in the base configuration."""
    out = {}
    for k, a in atoms.items():
        if a['kind'] == 'isr' and base in a['configs']:
            for r in a['resources']:
                if r['kind'] == 'global' and 'w' in r['access']:
                    out.setdefault(r['name'], []).append(k)
    return out


def _closure_calls(atoms, key, seen=None):
    """Every atom function reachable from one atom through its derived calls (by function name)."""
    by_fn = {a['function']: k for k, a in atoms.items() if a['kind'] != 'isr'}
    seen = set() if seen is None else seen
    for c in atoms[key]['calls']:
        k = by_fn.get(c)
        if k and k not in seen:
            seen.add(k)
            _closure_calls(atoms, k, seen)
    return seen


def resolve(rows, ctx):
    """rows {'graph', 'nodes', 'edges'} + ctx (glue.context: manifest atoms, base config, rendered headers) → the model."""
    g = rows['graph']
    gname = g['name']
    atoms, base = ctx['atoms'], g['base_configuration']
    struct = header_struct(ctx['class_header'], g['class_name'])
    known = macros(ctx['board_config_h'], ctx['class_header'], *ctx['module_headers'])
    cls_up = g['class_name'].upper()

    def literal_or_macro(v, where):
        if INT_LIT.match(v) or (IDENT.match(v) and v in known):
            return v
        raise GraphRefused('%s: %r is neither a C integer literal nor a macro the project\'s headers define (board_config.h, '
                           'hal.h, %s) — a binding never carries free C' % (where, v, ctx['class_header_name']))

    nodes = {}
    for n in sorted(rows['nodes'], key=lambda n: n['instance']):
        inst, where = n['instance'], '%s node %s' % (gname, n.get('instance'))
        if not IDENT.match(inst or '') or inst in nodes:
            raise GraphRefused('%s: the instance name must be a unique C identifier' % where)
        if n['kind'] not in NODE_KINDS:
            raise GraphRefused('%s: kind %r (known: %s)' % (where, n['kind'], ', '.join(NODE_KINDS)))
        node = {'instance': inst, 'kind': n['kind'], 'order': int(n.get('order') or 0), 'row': n, 'ports': {},
                'params': kv(n.get('params', ''), where), 'bindings': {}}
        if n['kind'] == 'c-atom':
            proj, _, key = (n.get('atom') or '').partition(':')
            if proj != g['project'] or key not in atoms:
                raise GraphRefused('%s: no atom %r in project %s (pol cmod atoms %s lists them)' % (where, n.get('atom'), g['project'], g['project']))
            a = atoms[key]
            if a['kind'] in ('isr', 'entry'):
                raise GraphRefused('%s: %s is %s — the glue owns main(), and an ISR comes with the globals it shares, never as a node'
                                   % (where, key, 'an ISR' if a['kind'] == 'isr' else 'the entry point'))
            if base not in a['configs']:
                raise GraphRefused('%s: %s is not compiled in the base configuration %s (only in %s)' % (where, key, base, ', '.join(a['configs'])))
            if n.get('stage') not in STAGES:
                raise GraphRefused('%s: stage %r (init | loop | called)' % (where, n.get('stage')))
            node.update(atom=a, key=key, stage=n['stage'],
                        ports={p['name']: (p['direction'], p['ctype'], p['polari_type']) for p in a['ports']})
            for port, v in kv(n.get('bindings', ''), where).items():
                if port not in node['ports'] or node['ports'][port][0] not in ('in', 'inout') or port == 'return':
                    raise GraphRefused('%s: binding %s= names no in port of %s' % (where, port, a['function']))
                node['bindings'][port] = literal_or_macro(v, where + ' binding ' + port)
        else:
            if n.get('atom') or n.get('bindings'):
                raise GraphRefused('%s: only a c-atom names an atom or carries bindings' % where)
            node['ports'] = dict(GLUE_PORTS.get(n['kind'], {}))
            p = node['params']
            if n['kind'] == 'class':
                if p.get('class') != g['class_name']:
                    raise GraphRefused('%s: class=%s, but the graph speaks %s' % (where, p.get('class'), g['class_name']))
                if p.get('name'):
                    literal_or_macro(p['name'], where + ' name') if not p['name'].startswith('"') else None
                if p.get('status') and '%s_STATUS_%s' % (cls_up, p['status']) not in known:
                    raise GraphRefused('%s: status=%s is not a %s_STATUS_* value of the class header' % (where, p['status'], cls_up))
                node['ports'] = {f: ('in', t, '') for f, t in struct.items()}
            elif n['kind'] == 'parser':
                if p.get('class') != g['class_name']:
                    raise GraphRefused('%s: the parser speaks %s, the graph %s' % (where, p.get('class'), g['class_name']))
            elif n['kind'] == 'tick':
                literal_or_macro(p.get('period_ms', ''), where + ' period_ms')
            elif n['kind'] == 'rule':
                if p.get('rule') != 'after-ms':
                    raise GraphRefused('%s: rule %r (cmod-1 knows after-ms: field from → to once the clock passes after_ms)' % (where, p.get('rule')))
                for k in ('class', 'field', 'from', 'to', 'after_ms'):
                    if not p.get(k):
                        raise GraphRefused('%s: rule after-ms needs %s=' % (where, k))
                if not INT_LIT.match(p['after_ms']):
                    raise GraphRefused('%s: after_ms must be an integer literal' % where)
                for k in ('from', 'to'):
                    if '%s_STATUS_%s' % (cls_up, p[k]) not in known:
                        raise GraphRefused('%s: %s=%s is not a %s_STATUS_* value' % (where, k, p[k], cls_up))
            elif n['kind'] == 'frame':
                literal_or_macro(p.get('device_id', ''), where + ' device_id')
                fields = [f.strip() for f in p.get('fields', '').split(',') if f.strip()]
                bad = [f for f in fields if f not in struct]
                if not fields or bad:
                    raise GraphRefused('%s: fields=%s — every field must be one of %s_t\'s (%s)' % (where, p.get('fields'), g['class_name'], ', '.join(struct)))
                node['fields'] = fields
        nodes[inst] = node
    for n in nodes.values():
        if n['kind'] in ('rule', 'frame'):
            c = nodes.get(n['params'].get('class', ''))
            if not c or c['kind'] != 'class':
                raise GraphRefused('%s node %s: class=%s names no class node' % (gname, n['instance'], n['params'].get('class')))
            if n['kind'] == 'rule' and n['params']['field'] not in struct:
                raise GraphRefused('%s node %s: field %s is not in %s_t' % (gname, n['instance'], n['params']['field'], g['class_name']))

    # ---------------------------------------------------------------- edges
    edges, bound = [], {}
    for e in sorted(rows['edges'], key=lambda e: (int(e.get('order') or 0), e['name'])):
        where = '%s edge %s (%s %s.%s → %s.%s)' % (gname, e['name'], e['kind'], e['from_node'], e.get('from_port', ''), e['to_node'], e.get('to_port', ''))
        if e['kind'] not in EDGE_KINDS:
            raise GraphRefused('%s: kind %r (known: %s)' % (where, e['kind'], ', '.join(EDGE_KINDS)))
        src, dst = nodes.get(e['from_node']), nodes.get(e['to_node'])
        if not src or not dst:
            raise GraphRefused('%s: names a node the graph does not have' % where)
        fp, tp = e.get('from_port', ''), e.get('to_port', '')
        ed = {'name': e['name'], 'kind': e['kind'], 'src': src['instance'], 'dst': dst['instance'], 'from_port': fp, 'to_port': tp,
              'order': int(e.get('order') or 0), 'scale': e.get('scale', ''), 'offset': e.get('offset', ''), 'row': e}
        k = e['kind']
        if k in ('data', 'field'):
            if fp not in src['ports'] or src['ports'][fp][0] not in ('out', 'inout'):
                raise GraphRefused('%s: %s has no out port %r' % (where, src['instance'], fp))
            if k == 'data':
                if dst['kind'] == 'class':
                    raise GraphRefused('%s: a value into a class field is a `field` edge' % where)
                if tp not in dst['ports'] or dst['ports'][tp][0] not in ('in', 'inout'):
                    raise GraphRefused('%s: %s has no in port %r' % (where, dst['instance'], tp))
                if src['ports'][fp][2] != dst['ports'][tp][2]:
                    raise GraphRefused('%s: Polari types differ (%s → %s)' % (where, src['ports'][fp][2], dst['ports'][tp][2]))
            else:
                if dst['kind'] != 'class' or tp not in dst['ports']:
                    raise GraphRefused('%s: a field edge ends on a field of the class node (%s)' % (where, ', '.join(struct)))
                for x in ('scale', 'offset'):
                    if ed[x] and not NUM_LIT.match(ed[x]):
                        raise GraphRefused('%s: %s must be a numeric literal' % (where, x))
            ed['ctype_from'], ed['ctype_to'] = src['ports'][fp][1], dst['ports'][tp][1]
            slot = (dst['instance'], tp)
            if slot in bound:
                raise GraphRefused('%s: %s.%s is already bound by %s' % (where, dst['instance'], tp, bound[slot]))
            bound[slot] = e['name']
        elif k == 'tick':
            if src['kind'] != 'tick':
                raise GraphRefused('%s: a tick edge starts at a tick node' % where)
            if dst['kind'] == 'class' and tp not in dst['ports']:
                raise GraphRefused('%s: %s is not a field of the class' % (where, tp))
            if dst['kind'] in ('tick', 'parser') or (dst['kind'] == 'c-atom' and dst['stage'] != 'loop'):
                raise GraphRefused('%s: only a loop c-atom, a rule, a frame or a class field can run on a tick' % where)
        elif k == 'on-rx':
            a = src.get('atom')
            outs = [p for p in (a or {}).get('ports', []) if p['direction'] == 'out' and p['name'] != 'return']
            if not a or src['stage'] != 'loop' or dst['kind'] != 'parser' or tp != 'byte' or [p['name'] for p in outs] != [fp] \
                    or not outs[0]['ctype'].endswith('*') or not a['signature'].startswith('int '):
                raise GraphRefused('%s: on-rx drains a loop atom shaped `int f(uint8_t *b)` (returns 1 per byte) into parser.byte' % where)
            bound[(dst['instance'], 'byte')] = e['name']
        elif k == 'on-command':
            if src['kind'] != 'parser' or fp != 'frame' or dst['kind'] != 'c-atom' or dst['stage'] != 'loop' \
                    or dst['ports'].get(tp, ('', '', ''))[2] != 'ref:polari_rx_t' or dst['ports'][tp][0] != 'in':
                raise GraphRefused('%s: on-command joins parser.frame to a loop atom\'s `const polari_rx_t *` in port' % where)
            slot = (dst['instance'], tp)
            if slot in bound:
                raise GraphRefused('%s: %s.%s is already bound by %s' % (where, dst['instance'], tp, bound[slot]))
            bound[slot] = e['name']
        elif k == 'calls':
            if src['kind'] != 'c-atom' or dst['kind'] != 'c-atom' or dst['stage'] != 'called':
                raise GraphRefused('%s: calls joins a c-atom to a c-atom of stage called' % where)
            if dst['atom']['function'] not in src['atom']['calls']:
                raise GraphRefused('%s: %s does not call %s (its derived calls: %s) — a calls edge records what the C does, it adds '
                                   'nothing' % (where, src['atom']['function'], dst['atom']['function'], ', '.join(src['atom']['calls']) or '-'))
            if tp and tp not in dst['ports']:
                raise GraphRefused('%s: %s has no port %r' % (where, dst['atom']['function'], tp))
        edges.append(ed)

    # ---------------------------------------------------------------- every in port bound, called nodes called
    callers = {}
    for ed in edges:
        if ed['kind'] == 'calls':
            callers.setdefault(ed['dst'], []).append(ed['src'])
    for n in nodes.values():
        if n['kind'] == 'c-atom' and n['stage'] == 'called':
            if n['instance'] not in callers:
                raise GraphRefused('%s node %s: stage called, but no `calls` edge says which atom calls it' % (gname, n['instance']))
            continue
        need = [p for p, d in n['ports'].items() if d[0] in ('in', 'inout') and p != 'return'] if n['kind'] != 'class' else []
        for p in need:
            if (n['instance'], p) not in bound and p not in n['bindings']:
                raise GraphRefused('%s node %s: in port %r is unbound — wire it (data / on-command edge) or bind it (%s=…)'
                                   % (gname, n['instance'], p, p))
            if (n['instance'], p) in bound and p in n['bindings']:
                raise GraphRefused('%s node %s: in port %r is both wired (%s) and bound' % (gname, n['instance'], p, bound[(n['instance'], p)]))
    for ed in edges:
        if ed['kind'] == 'data' and nodes[ed['dst']]['kind'] in ('tick', 'rule') and ed['ctype_from'] != 'uint32_t':
            raise GraphRefused('%s edge %s: a %s\'s clock must be a uint32_t millisecond count (got %s)'
                               % (gname, ed['name'], nodes[ed['dst']]['kind'], ed['ctype_from']))

    # ---------------------------------------------------------------- no cycle through data / field edges
    succ = {i: [] for i in nodes}
    for ed in edges:
        if ed['kind'] in ('data', 'field'):
            succ[ed['src']].append(ed['dst'])
    color = {}

    def visit(u, path):
        color[u] = 1
        for v in succ[u]:
            if color.get(v) == 1:
                raise GraphRefused('%s: the data edges form a cycle: %s — a value cannot depend on itself within one pass (keep it in '
                                   'a class field instead)' % (gname, ' → '.join(path[path.index(v):] + [v]) if v in path else u + ' → ' + v))
            if not color.get(v):
                visit(v, path + [v])
        color[u] = 2
    for u in sorted(nodes):
        if not color.get(u):
            visit(u, [u])

    # ---------------------------------------------------------------- scopes
    scope = {}
    ticked = {ed['dst']: ed['src'] for ed in edges if ed['kind'] == 'tick' and nodes[ed['dst']]['kind'] != 'class'}
    cmd = {ed['dst']: ed['src'] for ed in edges if ed['kind'] == 'on-command'}
    preds = {}
    for ed in edges:
        if ed['kind'] == 'data':
            preds.setdefault(ed['dst'], []).append(ed['src'])

    def scope_of(i, stack=()):
        if i in scope:
            return scope[i]
        n = nodes[i]
        if n['kind'] in ('class', 'parser'):
            s = 'global'
        elif n['kind'] == 'c-atom' and n['stage'] in ('init', 'called'):
            s = n['stage']
        elif i in cmd:
            s = 'cmd:%s' % cmd[i]
        else:
            ins = {scope_of(p, stack + (i,)) for p in preds.get(i, [])} - {'loop', 'global'}
            if i in ticked:
                ins.add('tick:%s' % ticked[i])
            if n['kind'] == 'tick':
                ins = set()
            if len(ins) > 1:
                raise GraphRefused('%s node %s: fed from different scopes (%s) — a value crossing ticks belongs in a class field'
                                   % (gname, i, ', '.join(sorted(ins))))
            s = ins.pop() if ins else 'loop'
        scope[i] = s
        return s
    for i in sorted(nodes):
        scope_of(i)
    for i, s in scope.items():
        if s.startswith('cmd:') and preds.get(i):
            raise GraphRefused('%s node %s: an on-command atom takes only the frame (data inputs: %s)' % (gname, i, ', '.join(preds[i])))
        if nodes[i]['kind'] in ('frame', 'rule') and not s.startswith('tick:'):
            raise GraphRefused('%s node %s: a %s runs on a tick (add a tick edge)' % (gname, i, nodes[i]['kind']))

    # ---------------------------------------------------------------- statement order per scope (topological, order as tie-break)
    order = {}
    for s in sorted(set(scope.values())):
        members = [i for i in nodes if scope[i] == s]
        indeg = {i: 0 for i in members}
        for ed in edges:
            if ed['kind'] == 'data' and ed['src'] in indeg and ed['dst'] in indeg:
                indeg[ed['dst']] += 1
        heap = [(nodes[i]['order'], i) for i in members if indeg[i] == 0]
        heapq.heapify(heap)
        out = []
        while heap:
            _, u = heapq.heappop(heap)
            out.append(u)
            for ed in edges:
                if ed['kind'] == 'data' and ed['src'] == u and ed['dst'] in indeg:
                    indeg[ed['dst']] -= 1
                    if indeg[ed['dst']] == 0:
                        heapq.heappush(heap, (nodes[ed['dst']]['order'], ed['dst']))
        order[s] = out

    # field writes: where they happen (a tick edge on the field samples it on that tick; else right after the source)
    tick_fields = {(ed['dst'], ed['to_port']): ed['src'] for ed in edges if ed['kind'] == 'tick' and nodes[ed['dst']]['kind'] == 'class'}
    for ed in edges:
        if ed['kind'] != 'field':
            continue
        t = tick_fields.get((ed['dst'], ed['to_port']))
        ss = scope[ed['src']]
        if t and ss != 'tick:%s' % t:
            if ss not in ('loop',):
                raise GraphRefused('%s edge %s: sampled on tick %s, but its source runs in %s' % (gname, ed['name'], t, ss))
            ed['scope'], ed['at'] = 'tick:%s' % t, 'start'
        else:
            ed['scope'], ed['at'] = ss, ed['src']
    for i, n in nodes.items():
        if n['kind'] == 'frame':
            s = scope[i]
            pos = order[s].index(i)
            late = [ed['name'] for ed in edges if ed['kind'] == 'field' and ed.get('scope') == s and ed['at'] != 'start'
                    and ed['dst'] == n['params']['class'] and ed['to_port'] in n['fields'] and order[s].index(ed['at']) > pos]
            if late:
                raise GraphRefused('%s node %s: field edge(s) %s write after the frame that sends them (the frame would carry the '
                                   'previous value) — give the frame a later order' % (gname, i, ', '.join(late)))

    # ISRs the atoms depend on (they write a global an atom reads), the modules to carry
    writers = _isr_writers(atoms, base)
    used = sorted({n['key'] for n in nodes.values() if n['kind'] == 'c-atom'})
    isrs = sorted({w for k in used for r in atoms[k]['resources'] if r['kind'] == 'global' for w in writers.get(r['name'], [])})
    advice = _advice(nodes, atoms, edges)
    return {'graph': g, 'sha': graph_sha(rows), 'nodes': nodes, 'edges': edges, 'scope': scope, 'order': order, 'struct': struct,
            'atoms_used': used, 'isrs': isrs, 'advice': advice, 'cls_up': cls_up}


def _peripherals(a):
    return {r['peripheral'] for r in a['resources'] if r['kind'] == 'register' and r['peripheral']}


def _advice(nodes, atoms, edges):
    """Suggestions, never refusals: a peripheral a loop atom touches that no init atom sets up; an init order where an init
    atom calls a clock reader before the timer's init."""
    out = []
    init = sorted((n for n in nodes.values() if n['kind'] == 'c-atom' and n['stage'] == 'init'), key=lambda n: n['order'])
    covered = set().union(*[_peripherals(n['atom']) for n in init]) if init else set()
    for n in sorted(nodes.values(), key=lambda n: n['instance']):
        if n['kind'] == 'c-atom' and n['stage'] != 'init':
            miss = sorted(_peripherals(n['atom']) - covered)
            if miss:
                out.append('%s (%s) touches %s, which no init node sets up' % (n['instance'], n['atom']['function'], ', '.join(miss)))
    for i, n in enumerate(init):
        reach = _closure_calls(atoms, n['key'])
        readers = [k for k in reach if any(r['kind'] == 'global' and 'shared with ISR' in r['detail'] for r in atoms[k]['resources'])]
        if readers and not any('TIMER' in p for m in init[:i] for p in _peripherals(m['atom'])):
            out.append('init %s calls %s (a clock reader) before any timer init' % (n['instance'], ', '.join(readers)))
    return out


def cost(model, atoms, base_app_main=None):
    """THE COST BEFORE BUILDING (the cost rule as a suggestion): the atoms as nodes (-fno-inline text, cmod-0's measurement),
    the ISRs they pull in, and the glue + library reference = the shipped main() of the app the graph replaces (the same
    scheduling, parser and frame assembly). An upper bound: an atom the hand-written build inlined is counted as a node AND
    inside that main; the C runtime (vectors, crt, libgcc) is in neither — it is what the measured .text adds."""
    parts = []
    for k in model['atoms_used']:
        parts.append((k, int((atoms[k].get('cost') or {}).get('text_bytes_noinline') or 0), 'atom as a node'))
    for k in model['isrs']:
        parts.append((k, int((atoms[k].get('cost') or {}).get('text_bytes_noinline') or 0), 'ISR it shares a global with'))
    ref = 0
    if base_app_main and base_app_main in atoms:
        ref = int((atoms[base_app_main].get('cost') or {}).get('text_bytes') or 0)
        parts.append((base_app_main, ref, 'glue + library reference: the replaced main() as shipped'))
    total = sum(p[1] for p in parts)
    why = ('atoms as nodes %d B + ISRs %d B + glue/library reference %d B (%s shipped) = %d B — an upper bound for the attributable '
           'code (inlined atoms counted twice); the C runtime (vectors, crt, libgcc float) is not in it'
           % (sum(p[1] for p in parts if p[2] == 'atom as a node'), sum(p[1] for p in parts if p[2].startswith('ISR')), ref,
              base_app_main or '-', total))
    return {'total_bytes': total, 'parts': parts, 'why': why}
