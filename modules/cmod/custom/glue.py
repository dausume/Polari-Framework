"""
@module cmod.custom.glue

GRAPH → PLAIN-C GLUE (C_MODULARIZATION_PLAN.md §5, cmod-1): a checked `CGraph` (custom/graph.py) renders to a REAL C project —
always one, committed into the graph's `generated_project` (D-cmod-4) — that `make` alone builds. No Python at run time, no
interpreter, no table walked at run time: the generator decides everything and writes ordinary statements.

The rendered project holds:
  polari_graph.c    GENERATED. The glue: the class instance + parser + frame buffers (file-scope statics), the app atoms the
                    graph uses COPIED VERBATIM from their app file (with their POLARI_NODE line and enclosing #if — an app
                    file also holds a main(), so it cannot be compiled whole), and main(): the init atoms in graph order,
                    the class's identity + initial status, sei(), then the loop — the on-rx drain (byte source → parser →
                    msg_type gate → the on-command atoms), every loop-scope atom, and per tick an `if` on the ms clock with
                    its statements (field writes, atoms, rules, the frame + send) in topological order
  polari_graph.h    GENERATED. The graph's name + sha, the frame masks, the provenance of every file (path + sha256)
  Makefile          GENERATED. The template Makefile's own flags; SRCS = the atom files + the glue (listed, not globbed)
  hal.c / hal.h     the atom modules, copied VERBATIM (sha recorded; --gc-sections drops what the graph does not reach)
  board_config.h    the base configuration's knobs, rendered by board's own gen (the same bytes the hand-written build has)
  <class>_packets.h the generated header (c_twin target=avr, from the pinned contract — never a server's live exposure)

Every generated file opens with a comment naming the graph, its sha and `pol cmod render <graph>`. A hand edit is allowed:
`pol cmod diff` shows it and a render refuses to overwrite it without --force (a person's C wins; the graph is told).
The render record (files + shas, the cost estimate, later the build + proof) is cmod/custom/glue_builds/<graph>.json.
"""
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import tempfile

from cmod.custom import graph as GR
from cmod.custom import projects as P

GENERATOR = 'cmod.custom.glue 1'
HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, 'glue_builds')
GENERATED = ('polari_graph.c', 'polari_graph.h', 'Makefile')


class GlueRefused(ValueError):
    pass


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


# ------------------------------------------------------------------ rows
def graph_rows(name, manager=None):
    """The graph's rows from a running server's tables (when given) else the seeds → {'graph', 'nodes', 'edges'}."""
    if manager is not None:
        t = manager.objectTables or {}
        gs = [r for r in (t.get('CGraph') or {}).values() if r.name == name]
        if gs:
            import inspect

            def d(r):
                return {k: getattr(r, k, '') for k in inspect.signature(type(r).__init__).parameters if k not in ('self', 'manager')}
            return {'graph': d(gs[0]), 'nodes': [d(r) for r in (t.get('CGraphNode') or {}).values() if r.graph == name],
                    'edges': [d(r) for r in (t.get('CGraphEdge') or {}).values() if r.graph == name]}
    from cmod.custom.graph_seed import seed_graph
    rows = seed_graph(name)
    if rows is None:
        from cmod.custom.graph_seed import SEED_GRAPHS
        raise GlueRefused('no graph %r (seeded: %s)' % (name, ', '.join(g['name'] for g in SEED_GRAPHS)))
    return rows


# ------------------------------------------------------------------ context: the atoms + the rendered base configuration
def context(g):
    spec = P.resolve(g['project'])
    if spec['kind'] != 'template':
        raise GlueRefused('cmod-1 renders graphs over a TEMPLATE project (uno); %s is %s' % (g['project'], spec['kind']))
    mpath = P.manifest_path(spec)
    if not os.path.isfile(mpath):
        raise GlueRefused('%s has no polari-firmware.json — run `pol cmod conform %s` first' % (g['project'], g['project']))
    m = json.load(open(mpath))
    cfg = next((c for c in m['configurations'] if c['name'] == g['base_configuration']), None)
    if cfg is None:
        raise GlueRefused('base configuration %r is not one of %s\'s (%s)' % (g['base_configuration'], g['project'],
                                                                           ', '.join(c['name'] for c in m['configurations'])))
    from board.custom import gen
    from board.custom import variants as V
    work = tempfile.mkdtemp(prefix='cmod-glue-')
    try:
        row = gen.gen('uno', work=work, variant=g['base_configuration'], variant_rows=[V.find(g['base_configuration'])])
        d = row['project_dir']
        hdr = '%s_packets.h' % g['class_name'].lower()
        if not os.path.isfile(os.path.join(d, hdr)):
            raise GlueRefused('the base configuration %s does not speak %s' % (g['base_configuration'], g['class_name']))
        bc, ch = open(os.path.join(d, 'board_config.h')).read(), open(os.path.join(d, hdr)).read()
        classes = json.loads(row['classes_json'])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    atoms = {a['name']: a for a in m['atoms']}
    mods = {f['path']: (x['name'], x['role'], [ff['path'] for ff in x['files']]) for x in m['modules'] for f in x['files']}
    headers = [open(os.path.join(spec['root'], f)).read() for f in sorted(mods) if f.endswith('.h') and mods[f][1] != 'config']
    return {'spec': spec, 'manifest': m, 'manifest_sha256': sha(open(mpath, 'rb').read()), 'atoms': atoms, 'modules': mods,
            'base': cfg, 'board_config_h': bc, 'class_header': ch, 'class_header_name': hdr, 'module_headers': headers,
            'class_provenance': next((c for c in classes if c['class'] == g['class_name']), {})}


# ------------------------------------------------------------------ copying an app atom out of its file, verbatim
def _code_mask(text):
    """text with comments, strings and char literals blanked (same length) — for brace / directive scanning."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                out[k] = ' ' if text[k] != '\n' else '\n'
            i = j
        elif text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif c in '"\'':
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            for k in range(i + 1, min(j, n)):
                out[k] = ' '
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def extract(text, atom, filename):
    """The atom's definition, verbatim: from its POLARI_NODE line (or its own line) to its closing brace, wrapped in the #if
    lines that enclose it. → (text, first_line, last_line). Refused: an atom inside an #else/#elif branch, or one using a
    macro its app file defines (the copy would not compile without the rest of the file)."""
    lines = text.split('\n')
    masked = _code_mask(text).split('\n')
    start = (atom['annotation'] or {}).get('line') or atom['line']
    fl = atom['line']
    if atom['function'] not in lines[fl - 1]:
        raise GlueRefused('%s:%d does not hold %s (the manifest is stale — pol cmod conform)' % (filename, fl, atom['function']))
    depth, end, opened = 0, None, False
    for i in range(fl - 1, len(lines)):
        for ch in masked[i]:
            if ch == '{':
                depth, opened = depth + 1, True
            elif ch == '}':
                depth -= 1
        if opened and depth == 0:
            end = i + 1
            break
    if end is None:
        raise GlueRefused('%s: no closing brace for %s' % (filename, atom['function']))
    stack = []
    for i in range(start - 1):
        s = masked[i].strip()
        if re.match(r'#\s*(if|ifdef|ifndef)\b', s):
            stack.append([lines[i].strip(), 'if'])
        elif re.match(r'#\s*(elif|else)\b', s) and stack:
            stack[-1][1] = 'else'
        elif re.match(r'#\s*endif\b', s) and stack:
            stack.pop()
    if any(b == 'else' for _, b in stack):
        raise GlueRefused('%s: %s sits in an #else/#elif branch — cmod-1 copies only a function under plain #if lines' % (filename, atom['function']))
    body = '\n'.join(lines[start - 1:end])
    local = set(re.findall(r'(?m)^\s*#\s*define\s+([A-Za-z_]\w*)', text)) - {'POLARI_NODE'}
    used = sorted(m for m in local if re.search(r'\b%s\b' % re.escape(m), _code_mask(body)))
    if used:
        raise GlueRefused('%s: %s uses %s, defined in its app file — move the macro into a header the atom includes'
                          % (filename, atom['function'], ', '.join(used)))
    return '\n'.join([o for o, _ in stack] + [body] + ['#endif'] * len(stack)), start, end


# ------------------------------------------------------------------ the C
def _local_type(ctype):
    t = ctype.replace('const ', '').strip()
    return t[:-1].strip() if t.endswith('*') else t


def _render_c(model, ctx, copies, header_comment):
    g, nodes, edges, cls, up = model['graph'], model['nodes'], model['edges'], model['graph']['class_name'], model['cls_up']
    hdr = ctx['class_header_name']
    indexed = ('#define %s_INDEX_WIDTH' % up) in ctx['class_header']
    out = [header_comment, '#include <stdint.h>', '#include <string.h>', '#include <avr/interrupt.h>', '',
           '#include "board_config.h"']
    out += ['#include "%s"' % h for h in ctx['files_out'] if h.endswith('.h') and h not in ('board_config.h', hdr, 'polari_graph.h')]
    out += ['#include "%s"   /* GENERATED (c_twin target=avr) */' % hdr, '#include "polari_graph.h"', '']
    out.append('/* the glue\'s state (file-scope statics, so avr-size counts them): */')
    for i in sorted(nodes, key=lambda i: (nodes[i]['order'], i)):
        n = nodes[i]
        if n['kind'] == 'class':
            out.append('static %s_t %s;   /* class node %s: the %s instance the frames carry */' % (cls, i, i, cls))
        elif n['kind'] == 'parser':
            out.append('static polari_rx_t %s;   /* parser node %s: the generated header\'s receiver */' % (i, i))
        elif n['kind'] == 'frame':
            out.append('static uint8_t %s_payload[%s_PAYLOAD_MAX];   /* frame node %s */' % (i, up, i))
            out.append('static uint8_t %s_wire[POLARI_HEADER_LEN + %s_PAYLOAD_MAX + 4u];' % (i, up))
    for c in copies:
        out += ['', '/* atom %s — copied VERBATIM from %s lines %d-%d (sha256 %s) */' % (c['atom'], c['file'], c['first'], c['last'], c['sha256'][:16]),
                c['text']]

    def val(i, port):
        """The C expression feeding in port (i, port)."""
        n = nodes[i]
        if port in n.get('bindings', {}):
            return n['bindings'][port]
        for ed in edges:
            if ed['dst'] == i and ed['to_port'] == port and ed['kind'] in ('data', 'on-command'):
                if ed['kind'] == 'on-command':
                    return '&%s' % ed['src']
                s = nodes[ed['src']]
                expr = ('%s_%s' % (s['instance'], 'wire' if ed['from_port'] == 'wire' else 'length')) if s['kind'] == 'frame' else \
                    '%s_%s' % (ed['src'], ed['from_port'])
                tt = n['ports'][port][1]
                if ed['ctype_from'] != tt and not tt.endswith('*'):
                    expr = '(%s)%s' % (tt, expr)
                return expr
        raise GlueRefused('internal: %s.%s has no source' % (i, port))

    def call(i):
        n, a = nodes[i], nodes[i]['atom']
        args, decls = [], []
        for p in a['ports']:
            if p['name'] == 'return':
                continue
            if p['direction'] == 'out':
                decls.append('%s %s_%s;' % (_local_type(p['ctype']), i, p['name']))
                args.append('&%s_%s' % (i, p['name']))
            else:
                args.append(val(i, p['name']))
        c = '%s(%s)' % (a['function'], ', '.join(args))
        ret = n['ports'].get('return')
        consumed = any(ed['src'] == i and ed['from_port'] == 'return' for ed in edges if ed['kind'] in ('data', 'field'))
        return decls, ('const %s %s_return = %s;' % (ret[1], i, c) if ret and consumed else c + ';')

    def field_write(ed):
        n = nodes[ed['dst']]
        src = '%s_%s' % (ed['src'], ed['from_port'])
        expr = src
        if ed['scale'] or ed['offset']:
            expr = '%s%s%s' % (src, ' * %s' % ed['scale'] if ed['scale'] else '', ' + %s' % ed['offset'] if ed['offset'] else '')
            expr = '(%s)(%s)' % (n['ports'][ed['to_port']][1], expr)
        elif ed['ctype_from'] != n['ports'][ed['to_port']][1]:
            expr = '(%s)%s' % (n['ports'][ed['to_port']][1], src)
        return '%s.%s = %s;   /* field %s */' % (ed['dst'], ed['to_port'], expr, ed['name'])

    drains = {ed['src']: ed for ed in edges if ed['kind'] == 'on-rx'}

    def node_stmts(i, ind):
        n, body = nodes[i], []
        if n['kind'] == 'c-atom' and i in drains:
            ed = drains[i]
            parser = ed['dst']
            cmds = [c for _, c in sorted((nodes[e['dst']]['order'], e['dst']) for e in edges if e['kind'] == 'on-command' and e['src'] == parser)]
            body += [ind + '{   /* on-rx %s: %s → %s; on-command (msg_type %s_MSG_TYPE): %s */' % (ed['name'], i, parser, up, ', '.join(cmds) or '-'),
                     ind + '    %s %s_%s;' % (_local_type(n['ports'][ed['from_port']][1]), i, ed['from_port']),
                     ind + '    while (%s(&%s_%s))' % (n['atom']['function'], i, ed['from_port']),
                     ind + '        if (polari_rx_feed(&%s, %s_%s) && %s.msg_type == %s_MSG_TYPE) {' % (parser, i, ed['from_port'], parser, up)]
            for c in cmds:
                body += node_stmts(c, ind + '            ')
            body += [ind + '        }', ind + '}']
        elif n['kind'] == 'c-atom':
            decls, c = call(i)
            body += [ind + x for x in decls] + [ind + c + '   /* %s */' % i]
        elif n['kind'] == 'rule':
            p = n['params']
            body.append(ind + 'if (%s.%s == %s_STATUS_%s && %s > %su) %s.%s = %s_STATUS_%s;   /* rule %s */'
                        % (p['class'], p['field'], up, p['from'], val(i, 'now'), p['after_ms'].rstrip('uU'), p['class'], p['field'], up, p['to'], i))
        elif n['kind'] == 'frame':
            enc = '%s_encode(&%s, %s_payload, %s%s_MASK)' % (cls, n['params']['class'], i, 'INSTANCE_INDEX, ' if indexed else '', i.upper())
            body.append(ind + 'const size_t %s_length = %s_frame(%s_wire, %s, %s_seq++, %s_payload, %s);   /* frame %s */'
                        % (i, cls, i, n['params']['device_id'], i, i, enc, i))
        elif n['kind'] == 'tick':
            body += [ind + 'if ((int32_t)(%s - %s_next_ms) >= 0) {   /* tick %s: every %s ms */' % (val(i, 'now'), i, i, n['params']['period_ms']),
                     ind + '    %s_next_ms += %s;' % (i, n['params']['period_ms'])] + stmts('tick:%s' % i, ind + '    ') + [ind + '}']
        body += [ind + field_write(ed) for ed in edges if ed['kind'] == 'field' and ed['at'] == i]
        return body

    def stmts(scope, ind):
        body = [ind + field_write(ed) for ed in edges if ed['kind'] == 'field' and ed.get('scope') == scope and ed['at'] == 'start']
        for i in model['order'].get(scope, []):
            body += node_stmts(i, ind)
        return body

    out += ['', 'int main(void)', '{']
    for i in sorted(nodes):
        if nodes[i]['kind'] == 'tick':
            out.append('    uint32_t %s_next_ms = 0u;' % i)
        elif nodes[i]['kind'] == 'frame':
            out.append('    uint32_t %s_seq = 0u;' % i)
    out += ['', '    /* init: the init atoms in graph order, the class identity, then interrupts on */']
    for i in model['order'].get('init', []):
        out.append('    %s   /* %s */' % (call(i)[1], i))
    ordered = sorted(nodes, key=lambda i: (nodes[i]['order'], i))
    out += ['    memset(&%s, 0, sizeof %s);' % (i, i) for i in ordered if nodes[i]['kind'] in ('class', 'parser')]
    for i in ordered:
        n = nodes[i]
        if n['kind'] == 'class':
            if n['params'].get('name'):
                out.append('    strcpy(%s.name, %s);' % (i, n['params']['name']))
            if n['params'].get('status'):
                out.append('    %s.status = %s_STATUS_%s;' % (i, up, n['params']['status']))
    out += ['    sei();', '', '    for (;;) {'] + stmts('loop', '        ') + ['    }', '}', '']
    return '\n'.join(out)


def _comment(g, gsha, what):
    return ('/*\n * %s — GENERATED by %s from the no-code graph %s (sha256 %s).\n * Regenerate with `pol cmod render %s`. Editing by hand is '
            'allowed: `pol cmod diff %s` shows it, and a render\n * never overwrites a hand edit silently. Plain C on avr-libc (RULE 2); '
            'no Python at run time.\n */' % (what, GENERATOR, g['name'], gsha, g['name'], g['name']))


def _render_h(model, ctx, provenance):
    g, nodes, up = model['graph'], model['nodes'], model['cls_up']
    out = [_comment(g, model['sha'], 'polari_graph.h: the graph\'s identity, the frame masks, where every file came from'),
           '#ifndef POLARI_GRAPH_H', '#define POLARI_GRAPH_H', '', '#include "%s"' % ctx['class_header_name'], '',
           '#define POLARI_GRAPH_NAME   "%s"' % g['name'], '#define POLARI_GRAPH_SHA256 "%s"' % model['sha'], '']
    for i in sorted(nodes):
        n = nodes[i]
        if n['kind'] == 'frame':
            out.append('/* frame node %s: the fields its telemetry carries */' % i)
            out.append('#define %s_MASK ((%s_mask_t)(%s))' % (i.upper(), g['class_name'], ' | '.join('%s_F_%s' % (up, f.upper()) for f in n['fields'])))
    out += ['', '/* the files of this project (sha256 of the bytes written):']
    out += [' *   %-24s %s  %s' % (f, s[:16], src) for f, s, src in provenance]
    out += [' */', '', '#endif /* POLARI_GRAPH_H */', '']
    return '\n'.join(out)


def _render_makefile(model, ctx, sources):
    from cmod.custom import measure as M
    v = M.makefile_vars(os.path.join(ctx['spec']['root'], 'Makefile'))
    g = model['graph']
    return '\n'.join([
        '# Makefile — GENERATED by %s from the no-code graph %s (sha256 %s).' % (GENERATOR, g['name'], model['sha']),
        '# Regenerate with `pol cmod render %s`. The flags are the %s template Makefile\'s own; SRCS lists the atom' % (g['name'], g['project']),
        '# files + the glue. `make` alone builds firmware.hex (no Polari in the loop).', '#',
        '#   make            # firmware.elf + firmware.hex + the avr-size line', '#   make size',
        'MCU   = %s' % v.get('MCU', 'atmega328p'), 'F_CPU = %s' % v.get('F_CPU', '16000000UL'), 'CC    = %s' % v.get('CC', 'avr-gcc'),
        'CFLAGS = -mmcu=$(MCU) -DF_CPU=$(F_CPU) %s' % ' '.join(x for x in v['CFLAGS'].split() if not x.startswith(('-mmcu=', '-DF_CPU='))),
        'LDFLAGS = %s' % v.get('LDFLAGS', ''), 'SRCS = %s' % ' '.join(sources), 'HDRS = %s' % ' '.join(sorted(
            f for f in ctx['files_out'] if f.endswith('.h'))), '',
        'all: firmware.hex size', '', 'firmware.elf: $(SRCS) $(HDRS)', '\t$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(SRCS)', '',
        'firmware.hex: firmware.elf', '\tavr-objcopy -O ihex -R .eeprom $< $@', '', 'size: firmware.elf', '\tavr-size -A firmware.elf', '',
        'clean:', '\trm -f firmware.elf firmware.hex', '', '.PHONY: all size clean', ''])


def render_files(rows, ctx=None):
    """rows → (model, {file: bytes}, provenance, copies) — nothing written."""
    ctx = ctx or context(rows['graph'])
    model = GR.resolve(rows, ctx)
    root = ctx['spec']['root']
    whole, copies = {}, []
    for k in model['atoms_used'] + model['isrs']:
        a = ctx['atoms'][k]
        name, role, files = ctx['modules'][a['module']]
        if role in ('hal', 'source', 'header'):
            for f in files:
                whole[f] = '%s/%s' % (ctx['manifest']['root'], f)
        elif role == 'app' and k in model['atoms_used']:
            text = open(os.path.join(root, a['module'])).read()
            body, first, last = extract(text, a, a['module'])
            copies.append({'atom': k, 'file': '%s/%s' % (ctx['manifest']['root'], a['module']), 'first': first, 'last': last,
                           'sha256': sha(text), 'text': body})
        else:
            raise GlueRefused('%s: module role %s cannot be carried' % (k, role))
    copies.sort(key=lambda c: (c['file'], c['first']))
    files = {f: open(os.path.join(root, f), 'rb').read() for f in whole}
    files['board_config.h'] = ctx['board_config_h'].encode()
    files[ctx['class_header_name']] = ctx['class_header'].encode()
    sources = sorted(f for f in files if f.endswith('.c')) + ['polari_graph.c']
    ctx['files_out'] = sorted(files) + ['polari_graph.h']
    cp = ctx['class_provenance']
    prov = [(f, sha(files[f]), 'copied verbatim from %s' % whole[f]) for f in sorted(whole)]
    prov += [('board_config.h', sha(files['board_config.h']), 'board gen: the %s knobs' % rows['graph']['base_configuration']),
             (ctx['class_header_name'], sha(files[ctx['class_header_name']]),
              'c_twin target=avr, contract v%s %s (%s %s)' % (cp.get('contract_version', '?'), cp.get('contract_hash', ''), cp.get('source', ''), cp.get('path', '')))]
    prov += [('polari_graph.c', '-' * 16, 'GENERATED (+ %s copied verbatim)' % ', '.join(c['atom'] for c in copies) if copies else 'GENERATED')]
    files['polari_graph.c'] = _render_c(model, ctx, copies, _comment(rows['graph'], model['sha'], 'polari_graph.c: the glue — main() as a '
                                                                       'scheduler over the graph\'s edges, calling the atoms by name')).encode()
    files['polari_graph.h'] = _render_h(model, ctx, prov).encode()
    files['Makefile'] = _render_makefile(model, ctx, sources).encode()
    from board.custom import gen as G
    bad = [f for f in files if not (f.endswith(G.RULE2_EXT) or f in G.RULE2_NAMES)]
    if bad:
        raise GlueRefused('RULE 2: a generated project holds only .c/.h + Makefile — %s' % bad)
    return model, files, prov, copies


def glue_contains(model, copies):
    """What the generator OWNS (the logic of the hand-written app that is not an atom), in words — for the CGraph row."""
    n = model['nodes']
    out = ['main() and its loop (the scheduler)']
    out += ['init: %s, then sei()' % ' → '.join(n[i]['atom']['function'] for i in model['order'].get('init', []))]
    out += ['the class instance `%s` (%s_t): zeroed, name = %s, status = %s' % (i, model['graph']['class_name'], n[i]['params'].get('name', '-'),
                                                                              n[i]['params'].get('status', '-')) for i in sorted(n) if n[i]['kind'] == 'class']
    out += ['the parser `%s` (polari_rx_t) fed by the on-rx drain, msg_type gate → on-command atoms' % i for i in sorted(n) if n[i]['kind'] == 'parser']
    out += ['tick `%s`: every %s ms on the uint32_t clock, wrap-safe ((int32_t)(now - next) >= 0)' % (i, n[i]['params']['period_ms'])
            for i in sorted(n) if n[i]['kind'] == 'tick']
    out += ['%d field write(s) into the class instance' % sum(1 for e in model['edges'] if e['kind'] == 'field')]
    out += ['rule `%s`: %s %s → %s once the clock passes %s ms' % (i, n[i]['params']['field'], n[i]['params']['from'], n[i]['params']['to'],
                                                                 n[i]['params']['after_ms']) for i in sorted(n) if n[i]['kind'] == 'rule']
    out += ['frame `%s`: the sequence counter, %s_encode (mask: %s) + %s_frame into static buffers' % (
        i, model['graph']['class_name'], ', '.join(n[i]['fields']), model['graph']['class_name']) for i in sorted(n) if n[i]['kind'] == 'frame']
    out += ['the app atoms copied verbatim: %s' % ', '.join(c['atom'] for c in copies)] if copies else []
    return out


# ------------------------------------------------------------------ the record + writing into the project
def record_path(name):
    return os.path.join(RECORDS, '%s.json' % name)


def load_record(name):
    p = record_path(name)
    return json.load(open(p)) if os.path.isfile(p) else None


def save_record(name, rec):
    os.makedirs(RECORDS, exist_ok=True)
    with open(record_path(name), 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, indent=1, ensure_ascii=False)
        fh.write('\n')


def project_dir(g):
    return os.path.join(P.MODULES, g['generated_project'])


def _base_main(ctx, g):
    app = ctx['base'].get('app') or ''
    return 'apps/%s.main' % app if app else None


def render(name, manager=None, write=True, force=False, out_dir=None, rows=None):
    """Render the graph; write ONLY what changed; refuse to overwrite a hand edit (disk ≠ the last render) without force.
    out_dir: render elsewhere (no record touched); rows: render these rows instead of the stored graph (a what-if)."""
    rows = rows or graph_rows(name, manager)
    g = rows['graph']
    ctx = context(g)
    model, files, prov, copies = render_files(rows, ctx)
    d = out_dir or project_dir(g)
    rec = load_record(name) if out_dir is None else None
    last = (rec or {}).get('files', {})
    disk = {f: sha(open(os.path.join(d, f), 'rb').read()) for f in sorted(os.listdir(d)) if f != P.MANIFEST_NAME} if os.path.isdir(d) else {}
    hand = sorted(f for f in disk if f in last and disk[f] != last[f])
    stray = sorted(f for f in disk if f not in files)
    fresh = {f: sha(b) for f, b in files.items()}
    changed = sorted(f for f in files if disk.get(f) != fresh[f])
    if write and hand and not force and any(f in changed for f in hand):
        raise GlueRefused('%s: hand-edited since the last render: %s — a person\'s C wins (pol cmod diff %s shows it); render --force '
                          'replaces it' % (d, ', '.join(hand), name))
    est = GR.cost(model, ctx['atoms'], _base_main(ctx, g))
    if write and (changed or stray):
        os.makedirs(d, exist_ok=True)
        for f in changed:
            open(os.path.join(d, f), 'wb').write(files[f])
        for f in stray:
            os.remove(os.path.join(d, f))
    files_sha = sha(''.join('%s %s\n' % (f, fresh[f]) for f in sorted(fresh)))
    if write and out_dir is None and ((rec or {}).get('files_sha256') != files_sha or (rec or {}).get('graph_sha256') != model['sha']):
        keep = rec if rec and rec.get('files_sha256') == files_sha else None
        rec = {'graph': name, 'graph_sha256': model['sha'], 'generator': GENERATOR, 'generated_project': g['generated_project'],
               'files': fresh, 'files_sha256': files_sha, 'rendered_at': datetime.datetime.now().isoformat(timespec='seconds'),
               'inputs': [{'label': lab, 'file': f, 'sha256': s} for f, s, lab in prov if not s.startswith('-')]
               + [{'label': 'atoms manifest', 'file': '%s/%s' % (ctx['manifest']['root'], P.MANIFEST_NAME), 'sha256': ctx['manifest_sha256']}],
               'cost_estimate': {'total_bytes': est['total_bytes'], 'why': est['why'], 'parts': [{'atom': a, 'bytes': b, 'as': w} for a, b, w in est['parts']]},
               'glue_contains': glue_contains(model, copies), 'advice': model['advice'],
               'build': (keep or {}).get('build'), 'proof': (keep or {}).get('proof'), 'conformed': (keep or {}).get('conformed')}
        save_record(name, rec)
    return {'graph': name, 'dir': d, 'sha': model['sha'], 'written': sorted(changed) if write else [], 'removed': stray if write else [],
            'unchanged': not changed and not stray, 'hand_edited': hand, 'files': fresh, 'files_sha256': files_sha, 'cost': est,
            'advice': model['advice'], 'glue_contains': glue_contains(model, copies), 'model': model, 'texts': files}


def diff(name, manager=None, rows=None):
    """What changed vs the last render: the graph (fresh render ≠ the record), hand edits (disk ≠ the record), stale files
    (disk ≠ a fresh render) with a unified diff of each. Nothing written."""
    rows = rows or graph_rows(name, manager)
    g = rows['graph']
    _model, files, _prov, _c = render_files(rows)
    d = project_dir(g)
    rec = load_record(name) or {}
    last = rec.get('files', {})
    disk = {f: open(os.path.join(d, f), 'rb').read() for f in sorted(os.listdir(d)) if f != P.MANIFEST_NAME} if os.path.isdir(d) else {}
    out = {'graph': name, 'dir': d, 'graph_sha256': GR.graph_sha(rows), 'recorded_graph_sha256': rec.get('graph_sha256', ''),
           'graph_changed': GR.graph_sha(rows) != rec.get('graph_sha256'), 'hand_edited': sorted(f for f in disk if f in last and sha(disk[f]) != last[f]),
           'added': sorted(f for f in files if f not in disk), 'removed': sorted(f for f in disk if f not in files),
           'stale': sorted(f for f in files if f in disk and disk[f] != files[f]), 'diffs': {}}
    for f in out['stale'] + out['added']:
        a = disk.get(f, b'').decode(errors='replace').splitlines(keepends=True)
        b = files[f].decode(errors='replace').splitlines(keepends=True)
        out['diffs'][f] = ''.join(difflib.unified_diff(a, b, 'on disk/%s' % f, 'render/%s' % f))
    out['clean'] = not (out['stale'] or out['added'] or out['removed'] or out['hand_edited'])
    return out


def compile_graph(domain_rows):
    """The GraphCompilerDefinition seam (polariNoCode.graph_compilers, row `cmod-glue`): {'CGraph': [row], 'CGraphNode': [...],
    'CGraphEdge': [...]} → artifacts only (no solution graph: a C graph never runs in the engine — RULE 2)."""
    g = (domain_rows.get('CGraph') or [None])[0]
    if not g:
        raise GlueRefused('compile_graph needs one CGraph row')
    rows = {'graph': dict(g), 'nodes': [dict(n) for n in domain_rows.get('CGraphNode', [])], 'edges': [dict(e) for e in domain_rows.get('CGraphEdge', [])]}
    model, files, _p, _c = render_files(rows)
    return {'definition': None, 'artifacts': [{'path': f, 'sha256': sha(b), 'text': b.decode()} for f, b in sorted(files.items())],
            'provenance': {'compiler': 'cmod-glue', 'graph': g['name'], 'graph_sha256': model['sha'], 'generator': GENERATOR}}
