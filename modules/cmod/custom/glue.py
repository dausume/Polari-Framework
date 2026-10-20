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
#: ucd-0e2b: an 'app' module's OWN extra header(s) (never the atom-matched whole-module copy above, which only
#: triggers for a module an ATOM belongs to — a header with no functions of its own, like button_clock_defs.h, has
#: none) — copied + #included whenever one of the app's OWN atoms is used, same reasoning as board.custom.gen's
#: APP_EXTRA_HEADERS (the hand-written build's own copy of the same rule).
APP_EXTRA_HEADER_MODULES = {'apps/button_clock.c': ('apps/button_clock_defs.h',), 'apps/light.c': ('apps/light_defs.h',)}


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
        # ucd-0e2b: a variant may speak MORE THAN ONE wire class (button_clock: ButtonClockState + ButtonClockEvent)
        # — cmod-1's graph model is single-class (one `class`/`frame`/`parser` node kind), but an app whose copied
        # atoms assemble a SECOND class's frames themselves (never through glue nodes, e.g. events_drain) still
        # needs that class's own generated header on disk to compile. Carried here, always rendered (never gated
        # on an atom "using" it — nothing in `model` names a header file, only a class_name).
        # smp-2: a route the base configuration's knobs pick (sense_route / button_route) is RENDERED by board gen into ONE extra .c file next to hal.c (hal_sense_poll.c, hal_button_pcint.c ...);
        # the graph's project carries it (its hal.c block for that function is switched off by HAL_SENSE_ROUTE / HAL_BUTTON_ROUTE in board_config.h)
        route_files = {fn: open(os.path.join(d, fn)).read() for fn in sorted(os.listdir(d))
                       if fn.startswith(('hal_sense_', 'hal_button_')) and fn.endswith('.c')}
        other_headers = {'%s_packets.h' % c['class'].lower(): open(os.path.join(d, '%s_packets.h' % c['class'].lower())).read()
                          for c in classes if c['class'] != g['class_name'] and os.path.isfile(os.path.join(d, '%s_packets.h' % c['class'].lower()))}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    atoms = {a['name']: a for a in m['atoms']}
    mods = {f['path']: (x['name'], x['role'], [ff['path'] for ff in x['files']]) for x in m['modules'] for f in x['files']}
    headers = [open(os.path.join(spec['root'], f)).read() for f in sorted(mods) if f.endswith('.h') and mods[f][1] != 'config']
    return {'spec': spec, 'manifest': m, 'manifest_sha256': sha(open(mpath, 'rb').read()), 'atoms': atoms, 'modules': mods,
            'base': cfg, 'board_config_h': bc, 'class_header': ch, 'class_header_name': hdr, 'module_headers': headers,
            'other_class_headers': other_headers, 'route_files': route_files, 'class_provenance': next((c for c in classes if c['class'] == g['class_name']), {})}


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
def legacy():
    """POLARI_GLUE_LEGACY=1: emit through the pre-fgm-0 Python string code (glue_legacy) instead of the templates."""
    return os.environ.get('POLARI_GLUE_LEGACY') == '1'


#: the avr templates the glue path renders (their sha256 goes into the glue record: `templates`)
TEMPLATES = ('avr/polari_graph.c.j2', 'avr/polari_graph.h.j2', 'avr/Makefile.j2', 'avr/_lib.j2')


def template_provenance(files):
    """{'templates': {name: sha256}, 'template_generator': 'jinja2 <version>'} for the record — which template files rendered THESE
    bytes ({} + 'legacy' under POLARI_GLUE_LEGACY=1). `generator` keeps naming the cmod generator that stamps every file banner."""
    if legacy():
        return {'templates': {}, 'template_generator': 'legacy python string emitters (POLARI_GLUE_LEGACY=1)'}
    from cmod.custom import pin_config_gen as PG
    from cmod.custom.generator import env as E
    return E.provenance(TEMPLATES + (PG.TEMPLATES if 'pin_config.c' in files else ()))


def _emit(rows, model, ctx, prov, copies, sources, pin_config):
    """{polari_graph.c, polari_graph.h, Makefile} bytes — templates by default, the legacy emitters behind the flag."""
    if legacy():
        from cmod.custom import glue_legacy as L
        return {'polari_graph.c': L._render_c(model, ctx, copies, L._comment(rows['graph'], model['sha'], 'polari_graph.c: the glue — main() as a '
                                                                            'scheduler over the graph\'s edges, calling the atoms by name'),
                                              pin_config=pin_config).encode(),
                'polari_graph.h': L._render_h(model, ctx, prov).encode(),
                'Makefile': L._render_makefile(model, ctx, sources, pin_config=pin_config).encode()}
    from cmod.custom import measure as M
    from cmod.custom.generator import context as X
    from cmod.custom.generator import env as E
    bn = X.banner(rows['graph']['name'], model['sha'], GENERATOR)
    mk = M.makefile_vars(os.path.join(ctx['spec']['root'], 'Makefile'))
    return {'polari_graph.c': E.render('avr/polari_graph.c.j2', X.glue_c_context(model, ctx, copies, bn, pin_config=pin_config)),
            'polari_graph.h': E.render('avr/polari_graph.h.j2', X.glue_h_context(model, ctx, prov, bn)),
            'Makefile': E.render('avr/Makefile.j2', X.makefile_context(model, ctx, sources, GENERATOR, mk, pin_config=pin_config))}


def render_files(rows, ctx=None, manager=None):
    """rows → (model, {file: bytes}, provenance, copies) — nothing written."""
    ctx = ctx or context(rows['graph'])
    model = GR.resolve(rows, ctx)
    root = ctx['spec']['root']
    # ucd-0e2b: `whole` maps the project-side (FLAT — this generated project has no subdirectories) name to
    # (provenance label, path to read relative to `root`); every existing module (hal.c/hal.h/board_config.h) was
    # already flat, so basename(f) == f for them — only a header living under apps/ (button_clock_defs.h) needs
    # the two to differ.
    whole, copies = {}, []
    for k in model['atoms_used'] + model['isrs']:
        a = ctx['atoms'][k]
        if a['module'] not in ctx['modules'] and a['module'] in ctx.get('route_files', {}):
            continue   # smp-2: a route-rendered module (hal_sense_poll.c) is carried whole from the base configuration's render (route_files), never copied from the template root
        name, role, files = ctx['modules'][a['module']]
        if role in ('hal', 'source', 'header'):
            for f in files:
                whole[os.path.basename(f)] = ('%s/%s' % (ctx['manifest']['root'], f), f)
        elif role == 'app' and k in model['atoms_used']:
            for h in APP_EXTRA_HEADER_MODULES.get(a['module'], ()):
                whole[os.path.basename(h)] = ('%s/%s' % (ctx['manifest']['root'], h), h)
            text = open(os.path.join(root, a['module'])).read()
            body, first, last = extract(text, a, a['module'])
            copies.append({'atom': k, 'file': '%s/%s' % (ctx['manifest']['root'], a['module']), 'first': first, 'last': last,
                           'sha256': sha(text), 'text': body})
        else:
            raise GlueRefused('%s: module role %s cannot be carried' % (k, role))
    copies.sort(key=lambda c: (c['file'], c['first']))
    files = {dest: open(os.path.join(root, src), 'rb').read() for dest, (_prov, src) in whole.items()}
    files['board_config.h'] = ctx['board_config_h'].encode()
    files[ctx['class_header_name']] = ctx['class_header'].encode()
    for hfn, text in ctx.get('other_class_headers', {}).items():
        files[hfn] = text.encode()
    for rfn, text in ctx.get('route_files', {}).items():
        files[rfn] = text.encode()
    # ucd-0b: a graph with a FirmwareSolution over it gains the GENERATED pin_config.h/.c (claims -> bits, in the
    # fixed init order) — ridden along below like any other file (SRCS/HDRS/#include derive from `files`, never a
    # second list to keep in sync).
    from cmod.custom import firmware as FW
    sol = FW.solution_for_graph(rows['graph']['name'], manager=manager)
    pin_config = sol is not None
    if pin_config:
        from cmod.custom import pin_config_gen as PG
        pcg = PG.render(sol['name'], rows['graph']['name'], manager=manager)
        files['pin_config.h'] = pcg['pin_config.h']
        files['pin_config.c'] = pcg['pin_config.c']
    sources = sorted(f for f in files if f.endswith('.c')) + ['polari_graph.c']
    ctx['files_out'] = sorted(files) + ['polari_graph.h']
    cp = ctx['class_provenance']
    prov = [(f, sha(files[f]), 'copied verbatim from %s' % whole[f][0]) for f in sorted(whole)]
    prov += [('board_config.h', sha(files['board_config.h']), 'board gen: the %s knobs' % rows['graph']['base_configuration']),
             (ctx['class_header_name'], sha(files[ctx['class_header_name']]),
              'c_twin target=avr, contract v%s %s (%s %s)' % (cp.get('contract_version', '?'), cp.get('contract_hash', ''), cp.get('source', ''), cp.get('path', '')))]
    prov += [(rfn, sha(files[rfn]), 'board gen: the %s knobs\' route file (rendered from its catom template)' % rows['graph']['base_configuration']) for rfn in sorted(ctx.get('route_files', {}))]
    prov += [(hfn, sha(files[hfn]), 'c_twin target=avr: a second wire class %s\'s own atoms assemble (never a glue class/frame node)' % hfn)
             for hfn in sorted(ctx.get('other_class_headers', {}))]
    if pin_config:
        prov += [('pin_config.h', sha(files['pin_config.h']), 'GENERATED (cmod.custom.pin_config_gen) from %s\'s pin claims' % sol['name']),
                 ('pin_config.c', '-' * 16, 'GENERATED (cmod.custom.pin_config_gen) from %s\'s pin claims' % sol['name'])]
    prov += [('polari_graph.c', '-' * 16, 'GENERATED (+ %s copied verbatim)' % ', '.join(c['atom'] for c in copies) if copies else 'GENERATED')]
    files.update(_emit(rows, model, ctx, prov, copies, sources, pin_config))
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
    model, files, prov, copies = render_files(rows, ctx, manager=manager)
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
    tprov = template_provenance(files)
    if write and out_dir is None and ((rec or {}).get('files_sha256') != files_sha or (rec or {}).get('graph_sha256') != model['sha']
                                      or any((rec or {}).get(k) != v for k, v in tprov.items())):
        keep = rec if rec and rec.get('files_sha256') == files_sha else None
        rec = {'graph': name, 'graph_sha256': model['sha'], 'generator': GENERATOR, 'generated_project': g['generated_project'],
               'files': fresh, 'files_sha256': files_sha, 'rendered_at': datetime.datetime.now().isoformat(timespec='seconds'),
               'inputs': [{'label': lab, 'file': f, 'sha256': s} for f, s, lab in prov if not s.startswith('-')]
               + [{'label': 'atoms manifest', 'file': '%s/%s' % (ctx['manifest']['root'], P.MANIFEST_NAME), 'sha256': ctx['manifest_sha256']}],
               'cost_estimate': {'total_bytes': est['total_bytes'], 'why': est['why'], 'parts': [{'atom': a, 'bytes': b, 'as': w} for a, b, w in est['parts']]},
               'glue_contains': glue_contains(model, copies), 'advice': model['advice'],
               **tprov, 'build': (keep or {}).get('build'), 'proof': (keep or {}).get('proof'), 'conformed': (keep or {}).get('conformed')}
        save_record(name, rec)
    return {'graph': name, 'dir': d, 'sha': model['sha'], 'written': sorted(changed) if write else [], 'removed': stray if write else [],
            'unchanged': not changed and not stray, 'hand_edited': hand, 'files': fresh, 'files_sha256': files_sha, 'cost': est,
            'advice': model['advice'], 'glue_contains': glue_contains(model, copies), 'model': model, 'texts': files}


def diff(name, manager=None, rows=None):
    """What changed vs the last render: the graph (fresh render ≠ the record), hand edits (disk ≠ the record), stale files
    (disk ≠ a fresh render) with a unified diff of each. Nothing written."""
    rows = rows or graph_rows(name, manager)
    g = rows['graph']
    _model, files, _prov, _c = render_files(rows, manager=manager)
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
