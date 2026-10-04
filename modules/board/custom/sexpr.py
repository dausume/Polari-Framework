"""
@module board.custom.sexpr

A tiny S-EXPRESSION reader/writer (brd-bo; D-pcb-1 ruled "write directly"): KiCad's netlist (`.net`, `(export (version "E") …)`)
and schematic files are s-expressions. Quoted strings stay distinguishable from bare atoms (`Q`), so a written file parses back
to the same tree. `check_netlist` is the stand-in for KiCad's own reader until a pcb worker exists (no kicad-cli here): balanced,
the top-level shape of a KiCad 6+ netlist (as kicad-cli `sch export netlist --format kicadsexpr` writes it — compared against
KiCad 9's own qa/data/eeschema/netlists/bus_entries/bus_entries.net), unique refs and net codes, every node naming a component.
"""


class Q(str):
    """A quoted string atom."""


class SexprError(ValueError):
    pass


def parse(text):
    i, n = 0, len(text)
    stack, cur = [], []
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == '(':
            stack.append(cur)
            cur = []
            i += 1
        elif c == ')':
            if not stack:
                raise SexprError('unbalanced ) at %d' % i)
            done, cur = cur, stack.pop()
            cur.append(done)
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == '\\' and j + 1 < n:
                    buf.append({'n': '\n', 't': '\t'}.get(text[j + 1], text[j + 1]))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            if j >= n:
                raise SexprError('unterminated string at %d' % i)
            cur.append(Q(''.join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            cur.append(text[i:j])
            i = j
    if stack:
        raise SexprError('%d unclosed (' % len(stack))
    if len(cur) != 1:
        raise SexprError('expected one top-level expression, got %d' % len(cur))
    return cur[0]


def q(s):
    return '"%s"' % str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def _depth(x):
    return 1 + max((_depth(y) for y in x if isinstance(y, list)), default=0) if isinstance(x, list) else 0


def write(tree, indent=0):
    """KiCad-like layout: a short expression of depth <= 2 on one line, anything bigger one child per line (deterministic)."""
    if not isinstance(tree, list):
        return q(tree) if isinstance(tree, Q) else str(tree)
    one = '(' + ' '.join(write(x) for x in tree) + ')'
    if _depth(tree) <= 2 and len(one) + 2 * indent <= 110:
        return one
    head = [write(x) for x in tree if not isinstance(x, list)]
    return '(' + ' '.join(head) + ''.join('\n' + '  ' * (indent + 1) + write(x, indent + 1) for x in tree if isinstance(x, list)) + ')'


def find(tree, head):
    return [x for x in tree if isinstance(x, list) and x and x[0] == head]


def value(tree, head, default=''):
    f = find(tree, head)
    return str(f[0][1]) if f and len(f[0]) > 1 else default


def check_netlist(tree):
    """Problems with a parsed KiCad netlist tree (empty = it has the shape KiCad writes)."""
    why = []
    if not (isinstance(tree, list) and tree and tree[0] == 'export'):
        return ['not a KiCad netlist: the top-level expression is not (export …)']
    if value(tree, 'version') != 'E':
        why.append('(version "E") missing — KiCad 6+ netlists say version E')
    for sec in ('design', 'components', 'nets'):
        if not find(tree, sec):
            why.append('(%s …) missing' % sec)
    refs = []
    for comp in (find(find(tree, 'components')[0], 'comp') if find(tree, 'components') else []):
        r, v = value(comp, 'ref'), value(comp, 'value')
        if not r or not v:
            why.append('a comp without ref/value: %s' % write(comp)[:80])
        refs.append(r)
    if len(refs) != len(set(refs)):
        why.append('duplicate component refs: %s' % sorted({r for r in refs if refs.count(r) > 1}))
    codes = []
    for net in (find(find(tree, 'nets')[0], 'net') if find(tree, 'nets') else []):
        codes.append(value(net, 'code'))
        if not value(net, 'name'):
            why.append('a net without a name (code %s)' % value(net, 'code'))
        for node in find(net, 'node'):
            if value(node, 'ref') not in refs:
                why.append('net %s: node ref %s is not a component' % (value(net, 'name'), value(node, 'ref')))
            if not value(node, 'pin'):
                why.append('net %s: a node without a pin' % value(net, 'name'))
    if len(codes) != len(set(codes)):
        why.append('duplicate net codes')
    return why
