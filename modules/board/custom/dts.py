"""
@module board.custom.dts

A SMALL devicetree source reader (brd-bo) — enough of the DTS grammar to ingest a Zephyr board directory (`.dts`, `.dtsi`,
pinctrl) and our own rendered overlays: comments, preprocessor lines (skipped, #include recorded), `/ { }`, `&label { }`,
`label: name@unit { }`, `prop = <cells>, "strings", &ref;`, `prop;`. Not a dtc: no macro expansion (a macro stays a token,
e.g. `<UART0_TX_GPIO21>` — exactly what the ingest wants), no /delete-node/, no merging across files (the caller merges by
label). Every node and property carries its source LINE, so an ingested row can cite file:line.

    parse(text) -> {'includes': [..], 'roots': [node]}   node = {'name', 'label', 'ref', 'line', 'props': {k: (value, line)}, 'children': []}
"""
import re

_NAME = re.compile(r'[A-Za-z0-9,._+@#?\-/]+')


class DtsError(ValueError):
    pass


def _strip(text):
    """Remove comments, keep newlines (so line numbers survive); return (text, includes)."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(''.join('\n' if c == '\n' else ' ' for c in text[i:j]))
            i = j
        elif text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    lines, includes = [], []
    for ln in ''.join(out).split('\n'):
        s = ln.strip()
        if s.startswith('#'):
            m = re.match(r'#\s*include\s*[<"]([^>"]+)[>"]', s)
            if m:
                includes.append(m.group(1))
            lines.append('')
        else:
            lines.append(ln)
    return '\n'.join(lines), includes


def _tokens(text):
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == '\n':
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif c in '{};=:,':
            yield (c, c, line)
            i += 1
        elif c in '<[':
            close = '>' if c == '<' else ']'
            j = text.find(close, i)
            if j < 0:
                raise DtsError('line %d: unterminated %s' % (line, c))
            raw = text[i:j + 1]
            yield ('cells', raw, line)
            line += raw.count('\n')
            i = j + 1
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            yield ('string', text[i:j + 1], line)
            i = j + 1
        elif c == '&':
            m = _NAME.match(text, i + 1)
            if not m:
                raise DtsError('line %d: & without a label' % line)
            yield ('ref', m.group(0), line)
            i = m.end()
        else:
            m = _NAME.match(text, i)
            if not m:
                raise DtsError('line %d: unexpected %r' % (line, c))
            yield ('name', m.group(0), line)
            i = m.end()


def parse(text):
    body, includes = _strip(text)
    toks = list(_tokens(body))
    pos = [0]

    def peek(k=0):
        return toks[pos[0] + k] if pos[0] + k < len(toks) else (None, None, 0)

    def take(kind=None):
        t = peek()
        if kind and t[0] != kind:
            raise DtsError('line %d: expected %s, got %r' % (t[2], kind, t[1]))
        pos[0] += 1
        return t

    def value():
        parts = []
        while peek()[0] not in (';', None):
            t = take()
            if t[0] != ',':
                parts.append(t[1] if t[0] != 'ref' else '&' + t[1])
        return ', '.join(parts)

    def node_body(node):
        take('{')
        while peek()[0] != '}':
            if peek()[0] is None:
                raise DtsError('unterminated node %s' % node['name'])
            label = ''
            if peek()[0] == 'name' and peek(1)[0] == ':':
                label = take()[1]
                take(':')
            t = take()
            if t[0] == 'name' and peek()[0] == '{':
                child = {'name': t[1], 'label': label, 'ref': '', 'line': t[2], 'props': {}, 'children': []}
                node_body(child)
                node['children'].append(child)
            elif t[0] == 'name' and peek()[0] == '=':
                take('=')
                node['props'][t[1]] = (value(), t[2])
                take(';')
            elif t[0] == 'name' and peek()[0] == ';':
                node['props'][t[1]] = ('', t[2])
                take(';')
            else:
                raise DtsError('line %d: unexpected %r in %s' % (t[2], t[1], node['name']))
        take('}')
        take(';')

    roots = []
    while peek()[0] is not None:
        t = peek()
        if t[0] == 'name' and t[1] == '/dts-v1/':
            take()
            take(';')
            continue
        label = ''
        if t[0] == 'name' and peek(1)[0] == ':':
            label = take()[1]
            take(':')
            t = peek()
        if t[0] == 'ref':
            take()
            node = {'name': '&' + t[1], 'label': label, 'ref': t[1], 'line': t[2], 'props': {}, 'children': []}
        elif t[0] == 'name':
            take()
            node = {'name': t[1], 'label': label, 'ref': '', 'line': t[2], 'props': {}, 'children': []}
        else:
            raise DtsError('line %d: unexpected %r at top level' % (t[2], t[1]))
        node_body(node)
        roots.append(node)
    return {'includes': includes, 'roots': roots}


def walk(nodes, path=''):
    """Every node with its path (depth-first)."""
    for n in nodes:
        p = '%s/%s' % (path, n['name']) if path else n['name']
        yield p, n
        yield from walk(n['children'], p)


def cells(value):
    """'<A B (C | D)>' → ['A', 'B', '(C | D)'] (a parenthesised expression stays one token)."""
    v = value.strip()
    if v.startswith('<') and v.endswith('>'):
        v = v[1:-1]
    out, depth, cur = [], 0, ''
    for ch in v:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def string(value):
    v = value.strip()
    return v[1:-1] if v.startswith('"') and v.endswith('"') else v
