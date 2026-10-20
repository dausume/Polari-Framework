"""
@module board.custom.firmware_state

fst-0..2 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12). His words: "a page dedicated to tracking all state objects in a particular piece of firmware
(Structs, Enums, etc)". EVERY STATE OBJECT OF ONE FIRMWARE CONFIG, DERIVED — NEVER TYPED — from the sources the arc already has:

  * the config's rendered project (cmod.custom.projects.render: the app as main.c, the hal, the sense route, the generated <class>_packets.h,
    board_config.h), parsed with cmod's own preprocessor + pycparser (cmod.custom.atoms.parse_file — structure, never a build);
  * the pinned wire contract of every class the config speaks (board.custom.gen.pinned_contract) + the EnumMapping labels
    (grpcbridge.custom.wire_contract.enum_tables): the wire struct, its tags, proto types, the C types the generator gives them;
  * the generated packets header's own text: the presence bits (<CLASS>_F_<FIELD>), MSG_TYPE / WIRE_VERSION / PAYLOAD_MAX, the enum blocks;
  * the app's defs header and board_config.h: the EEPROM address define, the knobs the pins resolve through (LED_PIN -> D6).

What comes out, per config:
  objects   one per struct instance or struct type, static, local static, enum block or enum-like define group, EEPROM record
  fields    one per struct member / enum value: C type, size, tag + proto type (wire fields), direction (command | telemetry | command+telemetry
            | internal), the pin or task it controls, persistence, WRITERS and READERS (the functions whose bodies touch it, pointer hand-offs
            followed: main hands &rx to polari_rx_feed, which writes rx.have ... -> "written by polari_rx_feed (via main)")
  findings  a field nobody writes beyond zeroing, a field nobody reads, a global nobody reads, an enum value nobody uses

Readers/writers come from the AST (cmod.custom.scan's conservative rules: an lvalue chain's base, `g.f++` = read+write, `&g` handed on = followed
into the callee's pointer-parameter accesses). Enum-like DEFINES are expanded away by the preprocessor, so their users are found in the raw source
text of each function body (a word match) — the two channels are named in every row's `source`.

    derive(config, manager=None, work=None)   -> the document (cached per config + rendered source sha for CACHE_S seconds)
    rows(doc, which)                          -> 'objects' | 'fields' | 'enums' | 'findings' as table rows
    live(manager, config, session='')         -> the wire fields with their live values (the wire class's row on this server; the twin session's status)
    python3 -m board.custom.firmware_state <config> [--json] [--fields|--enums|--findings]     (= pol firmware state <config>)
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time

from pycparser import c_ast

CACHE_S = 60.0
_CACHE = {}
PROVEN_TYPES = {'int64': 'int64_t', 'double': 'double', 'bool': 'uint8_t', 'string': 'char[64]', 'bytes': 'uint8_t[64]'}   # c_twin.C_TYPES
_WIDTH = {'uint8_t': 1, 'int8_t': 1, 'uint16_t': 2, 'int16_t': 2, 'uint32_t': 4, 'int32_t': 4, 'int64_t': 8, 'uint64_t': 8, 'double': 4, 'size_t': 2}


class StateRefused(RuntimeError):
    def __init__(self, msg, status='404 Not Found'):
        super().__init__(msg)
        self.status = status


# ------------------------------------------------------------------ the config's rendered project
def _config(config):
    from cmod.custom import projects as P
    spec = P.resolve('uno')
    cfg = next((c for c in P.configurations(spec) if c['name'] == config), None)
    if cfg is None:
        from board.custom import variants as V
        names = [v['name'] for v in V.SEED_FIRMWARE_VARIANTS]
        raise StateRefused('no firmware config named %r — the UNO configs are %s' % (config, ', '.join(names)))
    return spec, cfg


def _render(config, work):
    from cmod.custom import projects as P
    spec, cfg = _config(config)
    r = P.render(spec, cfg, work)
    return spec, cfg, r


# ------------------------------------------------------------------ one translation unit, walked
class _Walk(object):
    """Every function of one TU: struct-field accesses on globals and on pointer/array parameters, whole-object hand-offs, local statics, calls,
    enum constants used, eeprom calls."""

    def __init__(self, ast, types):
        self.types = types
        self.globals_ = {}
        for ext in ast.ext:
            if isinstance(ext, c_ast.Decl) and ext.name and not isinstance(ext.type, c_ast.FuncDecl):
                d = types.describe(ext.type)
                self.globals_[ext.name] = dict(d, static='static' in (ext.storage or []), file=ext.coord.file if ext.coord else '',
                                               line=ext.coord.line if ext.coord else 0, init=ext.init is not None)
        self.enum_consts = {}
        for ext in ast.ext:
            self._enum_consts(ext)
        self.funcs = {}
        for ext in ast.ext:
            if isinstance(ext, c_ast.FuncDef):
                self._function(ext)

    def _enum_consts(self, node):
        if isinstance(node, c_ast.Enum) and node.values:
            v = -1
            for e in node.values.enumerators:
                from cmod.custom.c_types import const_int
                v = const_int(e.value) if e.value is not None else v + 1
                self.enum_consts[e.name] = v
            return
        for _, ch in node.children():
            self._enum_consts(ch)

    def _function(self, fd):
        name = fd.decl.name
        params = {}
        decl = fd.decl.type
        for p in (getattr(decl, 'args', None) and decl.args.params or []):
            if isinstance(p, c_ast.Decl) and p.name:
                params[p.name] = self.types.describe(p.type)
        f = {'function': name, 'file': fd.coord.file if fd.coord else '', 'line': fd.coord.line if fd.coord else 0,
             'static': 'static' in (fd.decl.storage or []), 'params': params, 'param_order': [p.name for p in (decl.args.params if decl.args else []) if isinstance(p, c_ast.Decl)],
             'fields': {}, 'whole': {}, 'handoffs': [], 'local_statics': {}, 'local_structs': {}, 'calls': [], 'enum_use': {}, 'eeprom': [], 'returns_call': []}
        self.f = f
        self.locals = set(params)
        self._collect_locals(fd.body)
        self._v(fd.body, lhs=False)
        self.funcs[name] = f

    def _collect_locals(self, node):
        if isinstance(node, c_ast.Decl) and node.name:
            self.locals.add(node.name)
            if 'static' in (node.storage or []) and not isinstance(node.type, c_ast.FuncDecl):
                self.f['local_statics'][node.name] = dict(self.types.describe(node.type), line=node.coord.line if node.coord else 0, init=node.init is not None)
            elif not isinstance(node.type, c_ast.FuncDecl):
                d = self.types.describe(node.type)
                if d.get('kind') == 'struct':
                    self.f['local_structs'][node.name] = d.get('name') or ''   # a decoded command lands in a local struct (cmd): its fields read = the command fields
        for _, ch in node.children():
            self._collect_locals(ch)

    # ---- helpers
    def _base(self, node):
        chain = []
        while True:
            if isinstance(node, c_ast.ID):
                return node.name, chain
            if isinstance(node, c_ast.ArrayRef):
                node = node.name
            elif isinstance(node, c_ast.StructRef):
                chain.insert(0, node.field.name)
                node = node.name
            elif isinstance(node, c_ast.UnaryOp) and node.op in ('*', '&'):
                node = node.expr
            elif isinstance(node, c_ast.Cast):
                node = node.expr
            else:
                return None, chain

    def _object(self, base):
        """A struct-typed object the base names: a global ('global') or a pointer/array parameter ('param'), else None."""
        if base in self.f['params']:
            return 'param'
        if base in self.f['local_structs']:
            return 'local'
        if base in self.globals_ and base not in (self.locals - set(self.f['params'])):
            return 'global'
        return None

    def _touch(self, base, chain, w, r):
        kind = self._object(base)
        if kind is None:
            return
        key = (kind, base, chain[0] if chain else '')
        a = self.f['fields'].setdefault(key, {'r': False, 'w': False})
        a['r'] = a['r'] or r
        a['w'] = a['w'] or w

    def _write(self, target, rmw):
        base, chain = self._base(target)
        if base:
            self._touch(base, chain, True, rmw)
        for sub in self._inner_reads(target):
            self._v(sub, lhs=False)

    def _inner_reads(self, node):
        out = []
        while True:
            if isinstance(node, c_ast.ArrayRef):
                out.append(node.subscript)
                node = node.name
            elif isinstance(node, c_ast.StructRef):
                node = node.name
            elif isinstance(node, c_ast.UnaryOp) and node.op == '*':
                node = node.expr
            elif isinstance(node, c_ast.Cast):
                node = node.expr
            else:
                return out

    # ---- the walk
    def _v(self, node, lhs):
        if node is None:
            return
        if isinstance(node, c_ast.Assignment):
            self._write(node.lvalue, rmw=node.op != '=')
            rv = node.rvalue
            while isinstance(rv, c_ast.Cast):
                rv = rv.expr
            if isinstance(rv, c_ast.FuncCall) and isinstance(rv.name, c_ast.ID):
                base, chain = self._base(node.lvalue)
                self.f['returns_call'].append((base, chain[0] if chain else '', rv.name.name))
            self._v(node.rvalue, lhs=False)
            return
        if isinstance(node, c_ast.UnaryOp) and node.op in ('++', '--', 'p++', 'p--'):
            self._write(node.expr, rmw=True)
            return
        if isinstance(node, c_ast.UnaryOp) and node.op == 'sizeof':
            return   # sizeof reads nothing
        if isinstance(node, c_ast.FuncCall):
            callee = node.name.name if isinstance(node.name, c_ast.ID) else '(*indirect)'
            self.f['calls'].append(callee)
            if callee.startswith('eeprom_'):
                self.f['eeprom'].append(callee)
            for i, a in enumerate(node.args.exprs if node.args else []):
                # a whole object handed on: &g, g (an array), g.f (an array member such as state.name) -> the callee's own accesses are followed later
                base, chain = self._base(a)
                ptr_param = isinstance(a, c_ast.ID) and a.name in self.f['params'] and self.f['params'][a.name].get('kind') == 'pointer'
                if base and (isinstance(a, c_ast.UnaryOp) and a.op == '&' or ptr_param or (isinstance(a, (c_ast.ID, c_ast.StructRef)) and self._is_array(a))):
                    if self._object(base):
                        self.f['handoffs'].append({'callee': callee, 'arg': i, 'base': base, 'field': chain[0] if chain else '', 'kind': self._object(base)})
                        continue
                self._v(a, lhs=False)
            return
        if isinstance(node, c_ast.StructRef):
            base, chain = self._base(node)
            if base:
                self._touch(base, chain, False, True)
            for sub in self._inner_reads(node):
                self._v(sub, lhs=False)
            return
        if isinstance(node, c_ast.ID):
            if node.name in self.enum_consts:
                self.f['enum_use'][node.name] = self.f['enum_use'].get(node.name, 0) + 1
            elif self._object(node.name) == 'global':
                self._touch(node.name, [], False, True)
            return
        for _, ch in node.children():
            self._v(ch, lhs=False)

    def _is_array(self, node):
        base, chain = self._base(node)
        if not base:
            return False
        d = self.globals_.get(base) if self._object(base) == 'global' else self.f['params'].get(base)
        if d is None:
            return False
        if not chain:
            return d.get('kind') == 'array'
        m = self._member(d, chain[0])
        return bool(m and m.get('kind') == 'array')

    def _member(self, d, field):
        name = d.get('name') or ''
        t = self.types.typedefs.get(name)
        st = self._struct_of(t) if t is not None else self.types.structs.get(name)
        for decl in (getattr(st, 'decls', None) or []):
            if decl.name == field:
                return self.types.describe(decl.type)
        return None

    def _struct_of(self, t):
        while t is not None and not isinstance(t, (c_ast.Struct, c_ast.Union)):
            t = getattr(t, 'type', None)
        return t

    # ---- struct types
    def members(self, type_name):
        """The members of a typedef'd struct: [(name, described type)]."""
        t = self.types.typedefs.get(type_name)
        st = self._struct_of(t) if t is not None else self.types.structs.get(type_name)
        return [(d.name, self.types.describe(d.type)) for d in (getattr(st, 'decls', None) or []) if d.name]


# ------------------------------------------------------------------ raw text helpers (defines and enum blocks live before the preprocessor)
def _raw_bodies(path):
    """{function name: its body text} by brace matching from each definition line (a structural parse already found the names; this is for word matches)."""
    text = open(path).read()
    out = {}
    # the parameter list carries no parens, quotes or newlines of its own - so a POLARI_NODE(... role("...")) annotation right above a function never
    # swallows the function's header (cst-0 found hal_button_init missing for exactly that reason)
    for m in re.finditer(r'^(?:static\s+)?(?:inline\s+)?[\w\s\*]+?\b(\w+)\s*\([^;{}()"\n]*\)\s*\{', text, re.M):
        name, i, depth = m.group(1), m.end() - 1, 0
        for j in range(i, len(text)):
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0:
                    out[name] = text[i:j + 1]
                    break
    return out


def _defines(path):
    out = []
    for n, line in enumerate(open(path).read().splitlines(), 1):
        m = re.match(r'\s*#define\s+(\w+)(?:\s+(.*?))?\s*(?:/\*(.*?)\*/)?\s*$', line)
        if m and not m.group(1).startswith('_'):
            val = (m.group(2) or '').strip()
            cm = m.group(3)
            if cm is None and '/*' in val:
                val, cm = val.split('/*', 1)[0].strip(), val.split('/*', 1)[1].rsplit('*/', 1)[0]
            out.append({'name': m.group(1), 'value': val, 'comment': (cm or '').strip(), 'line': n})
    return out


def _enum_blocks(path):
    """[{'comment', 'values': [(name, value, comment)]}] for every `enum { ... };` block in a header."""
    text = open(path).read()
    out = []
    for m in re.finditer(r'(?:/\*(.*?)\*/\s*)?enum\s*\{(.*?)\};', text, re.S):
        vals = []
        for line in m.group(2).splitlines():
            mm = re.match(r'\s*(\w+)\s*=\s*(\d+)\s*,?\s*(?:/\*(.*?)\*/)?', line)
            if mm:
                vals.append((mm.group(1), int(mm.group(2)), (mm.group(3) or '').strip()))
        if vals:
            out.append({'comment': (m.group(1) or '').strip(), 'values': vals})
    return out


# ------------------------------------------------------------------ the derivation
def _parse_tu(path, include_dirs):
    from cmod.custom import atoms as T
    from cmod.custom.c_types import TypeTable
    ast, problems = T.parse_file(path, include_dirs)
    types = TypeTable(ast)
    return _Walk(ast, types), problems


def _follow(walks, fn, base, seen, depth=0):
    """What `fn` does to the object handed to it as parameter `base`: its own field accesses on that parameter + what it hands on. -> {field: {'r','w','via'}}"""
    out = {}
    if depth > 4 or (fn, base) in seen:
        return out
    seen = seen | {(fn, base)}
    f = next((w.funcs[fn] for w in walks if fn in w.funcs), None)
    if f is None:
        return out
    for (kind, b, fld), a in f['fields'].items():
        if kind == 'param' and b == base:
            o = out.setdefault(fld, {'r': False, 'w': False})
            o['r'], o['w'] = o['r'] or a['r'], o['w'] or a['w']
    for h in f['handoffs']:
        if h['kind'] == 'param' and h['base'] == base:
            callee = next((w.funcs[h['callee']] for w in walks if h['callee'] in w.funcs), None)
            if callee is None:
                # a library call (memset / strcpy / memcpy): the first argument is written, the rest read
                o = out.setdefault(h['field'], {'r': False, 'w': False})
                if h['arg'] == 0:
                    o['w'] = True
                else:
                    o['r'] = True
                continue
            pname = callee['param_order'][h['arg']] if h['arg'] < len(callee['param_order']) else ''
            for fld, a in _follow(walks, h['callee'], pname, seen, depth + 1).items():
                key = fld if not h['field'] else h['field']
                o = out.setdefault(key, {'r': False, 'w': False})
                o['r'], o['w'] = o['r'] or a['r'], o['w'] or a['w']
    return out


def _access_table(walks):
    """-> {(global, field): {'writers': {fn: how}, 'readers': {fn: how}}} across every TU, with hand-offs followed (`via` names the chain)."""
    acc = {}

    def mark(g, fld, fn, r, w, via=''):
        e = acc.setdefault((g, fld), {'writers': {}, 'readers': {}})
        how = 'via %s' % via if via else 'direct'
        if w:
            e['writers'].setdefault(fn, how)
        if r:
            e['readers'].setdefault(fn, how)
    for w in walks:
        for fn, f in w.funcs.items():
            for (kind, b, fld), a in f['fields'].items():
                if kind == 'global':
                    mark(b, fld, fn, a['r'], a['w'])
            for h in f['handoffs']:
                if h['kind'] != 'global':
                    continue
                callee = next((x.funcs[h['callee']] for x in walks if h['callee'] in x.funcs), None)
                if callee is None:
                    lib_w = h['arg'] == 0 and h['callee'] in ('memset', 'strcpy', 'strncpy', 'memcpy', 'sprintf', 'snprintf')
                    mark(h['base'], h['field'], fn, not lib_w, lib_w, via=h['callee'])
                    if lib_w and not h['field']:
                        mark(h['base'], '*', fn, False, True, via=h['callee'])
                    continue
                pname = callee['param_order'][h['arg']] if h['arg'] < len(callee['param_order']) else ''
                followed = _follow(walks, h['callee'], pname, frozenset())
                if not followed:
                    mark(h['base'], h['field'], fn, True, False, via='%s (handed, not touched there)' % h['callee'])
                for fld, a in followed.items():
                    mark(h['base'], h['field'] or fld, h['callee'], a['r'], a['w'], via='%s hands it over' % fn)
    return acc


def _pin_names(defines):
    """board_config.h knobs that name pins: LED_PIN 6 -> {'LED_PIN': 'D6'}, BUTTON_PIN 2 -> D2, ADC channels -> A<n>."""
    out = {}
    for d in defines:
        if d['name'].endswith('_PIN') and re.fullmatch(r'\d+u?', d['value'] or ''):
            n = int(d['value'].rstrip('u'))
            out[d['name']] = ('A%d' % (n - 14)) if n >= 14 else 'D%d' % n
        if d['name'].endswith('_ADC') and re.fullmatch(r'\d+u?', d['value'] or ''):
            out[d['name']] = 'A%s' % d['value'].rstrip('u')
    return out


def _annotations(root, modules):
    """{function: {'role', 'uses'}} from the POLARI_NODE annotations of the project's own sources (cmod.custom.annotation)."""
    from cmod.custom import annotation as A
    out = {}
    for fn in modules:
        p = os.path.join(root, fn)
        if fn.endswith('.c') and os.path.isfile(p):
            for a in A.find(open(p).read(), fn):
                out[a['name']] = {'role': a.get('role', ''), 'uses': list(a.get('uses') or [])}
    return out


def _csv(d):
    return ', '.join('%s%s' % (k, '' if v == 'direct' else ' (%s)' % v) for k, v in sorted(d.items()))


def derive(config, manager=None, work=None, cache=True):
    """The document for one config. Cached per (config, rendered source sha) for CACHE_S seconds — the page's four tables share one derivation."""
    key = config
    hit = _CACHE.get(key) if cache else None
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    own = work is None
    work = work or tempfile.mkdtemp(prefix='fst-%s-' % config)
    try:
        doc = _derive(config, manager, work)
    finally:
        if own:
            shutil.rmtree(work, ignore_errors=True)
    if cache:
        _CACHE[key] = (time.time(), doc)
    if manager is not None:
        try:
            persist(manager, doc)
        except Exception as e:   # noqa: BLE001 — the document stands on its own; the rows are a convenience
            doc['persist_note'] = 'rows not stored: %s' % e
    return doc


def _derive(config, manager, work):
    from board.custom import gen
    from grpcbridge.custom import wire_contract as WC
    spec, cfg, r = _render(config, work)
    d = r['dir']
    walks, problems = [], []
    for src in r['sources']:
        w, probs = _parse_tu(os.path.join(d, src), r['include_dirs'])
        w.src, w.module = src, r['map'].get(src, src)
        walks.append(w)
        problems += probs
    acc = _access_table(walks)
    ann = _annotations(spec['root'], [f for _m, fs, _r in spec['modules'] for f in fs])
    cfg_defs = _defines(os.path.join(d, 'board_config.h'))
    pins = _pin_names(cfg_defs)
    app_src = next((w for w in walks if w.src == 'main.c'), walks[0])
    raw = {}
    for w in walks:
        raw.update(_raw_bodies(os.path.join(d, w.src)))
    for h in os.listdir(d):
        if h.endswith('.h'):
            raw.update({k: v for k, v in _raw_bodies(os.path.join(d, h)).items() if k not in raw})
    classes = json.loads(cfg['variant'].get('classes_json') or '[]')
    objects, fields, enums, findings = [], [], [], []

    def fn_words(fn):
        a = ann.get(fn)
        return '%s — %s' % (fn, a['role']) if a and a.get('role') else fn

    def controls(readers):
        """The pin a field controls: a reader atom whose annotation `uses` a pin knob, or that calls a hal pin writer."""
        out = []
        for fn in readers:
            a = ann.get(fn) or {}
            for u in a.get('uses', []):
                out.append('%s (%s) via %s' % (pins.get(u, u), u, fn))
            f = next((w.funcs[fn] for w in walks if fn in w.funcs), None)
            if f and not a.get('uses') and fn != 'main':   # main does everything; only a dedicated reader atom is said to control the pin
                for c in f['calls']:
                    if c in ('hal_led', 'hal_pwm_apply'):
                        out.append('%s via %s -> %s' % (pins.get('LED_PIN', 'LED_PIN'), fn, c))
        return '; '.join(sorted(set(out)))

    def add_field(obj, name, ctype, width, **kw):
        fields.append(dict({'name': '%s.%s' % (obj, name), 'config': config, 'object': obj, 'field': name, 'c_type': ctype, 'size_bytes': width,
                            'tag': '', 'proto_type': '', 'direction': 'internal', 'controls': '', 'persisted': '', 'writers': '', 'readers': '',
                            'enum': '', 'finding': '', 'source': ''}, **kw))

    # ---- 1. the wire struct(s): the pinned contract + the generated packet struct + presence bits
    hdr_defs = {}
    for cls in classes:
        c = gen.pinned_contract(cls)[0]
        fmap = c['field_map']['fields']
        upper = cls.upper()
        hdr = os.path.join(d, '%s_packets.h' % cls.lower())
        defs = _defines(hdr) if os.path.isfile(hdr) else []
        hdr_defs[cls] = defs
        enum_tables = WC.enum_tables(manager, cls) or {}
        inst = [g for w in walks for g, gd in w.globals_.items() if (gd.get('name') or '') == '%s_t' % cls]
        obj = 'wire:%s' % cls
        tele_mask = next((x['value'] for x in _defines(os.path.join(d, h)) for h in [] ), '')
        send_decl = next((x for w in walks for x in w.funcs.values() if 'hal_usart_send' in x['calls'] and any(h['base'] in inst for h in x['handoffs'])), None)
        decoders = [fn for w in walks for fn, f in w.funcs.items() if any(c.endswith('_decode_rx') for c in f['calls']) and fn not in ('polari_rx_feed',)]
        members = dict(app_src.members('%s_t' % cls))
        for fname, fm in sorted(fmap.items(), key=lambda kv: kv[1]['tag']):
            m = members.get(fname) or {}
            ctype = m.get('c') or PROVEN_TYPES.get(fm['proto_type'], '?')
            width = m.get('width') or _WIDTH.get(ctype, 0)
            wr = {}
            rd = {}
            for g in inst:
                e = acc.get((g, fname), {'writers': {}, 'readers': {}})
                wr.update(e['writers'])
                rd.update(e['readers'])
                whole = acc.get((g, ''), {'writers': {}, 'readers': {}})
                for fn, how in whole['readers'].items():
                    rd.setdefault(fn, how if how != 'direct' else 'the whole struct')
                for fn, how in whole['writers'].items():
                    if 'memset' in how:
                        continue   # a memset of the struct is the zeroing below, not a write of this field
                    wr.setdefault(fn, how if how != 'direct' else 'the whole struct')
                z = acc.get((g, '*'), {'writers': {}})
                for fn, how in z['writers'].items():
                    wr.setdefault(fn, 'zeroed at init, %s' % how)
            # command: a decoder atom writes this field AND reads the same field off its decoded LOCAL struct (cmd.<f>) — the host set it
            is_cmd = False
            for fn in wr:
                f_ = next((w.funcs[fn] for w in walks if fn in w.funcs), None)
                if fn in decoders and f_ and any(k[0] == 'local' and k[2] == fname and f_['local_structs'].get(k[1]) == '%s_t' % cls and a['r'] for k, a in f_['fields'].items()):
                    is_cmd = True
            telem = send_decl is not None
            omitted = ''
            for h in os.listdir(d):
                if h.endswith('_defs.h'):
                    for x in _defines(os.path.join(d, h)):
                        if x['name'] == 'TELEMETRY_MASK' and ('~%s_F_%s' % (upper, fname.upper())) in x['value']:
                            knob = re.search(r'\((\w+)\s*\?', x['value'])
                            omitted = ' (omitted when %s is 0)' % (knob.group(1) if knob else 'the knob')
            direction = ('command+telemetry' if is_cmd and telem else 'command' if is_cmd else 'telemetry' if telem else 'internal') + omitted
            persisted = ''
            for w in walks:
                for fn, f in w.funcs.items():
                    for (b, fld, callee) in f['returns_call']:
                        if b in inst and fld == fname:
                            cf = next((x.funcs[callee] for x in walks if callee in x.funcs), None)
                            if cf and cf['eeprom']:
                                addr = next((x for h2 in os.listdir(d) if h2.endswith('.h') for x in _defines(os.path.join(d, h2)) if 'EEPROM' in x['name']), None)
                                persisted = 'EEPROM%s via %s (%s)' % (' %s = %s' % (addr['name'], addr['value']) if addr else '', callee, ', '.join(sorted(set(cf['eeprom']))))
            real_writers = {fn: how for fn, how in wr.items() if not how.startswith('zeroed')}
            finding = ''
            if not real_writers:
                finding = 'nobody writes %s beyond zeroing it at init — the report always carries 0 / empty for it' % fname
            elif not rd:
                finding = 'nobody reads %s' % fname
            enum_name = '%s_%s_*' % (upper, fname.upper()) if fname in enum_tables else ''
            add_field(obj, fname, ctype, width, tag=fm['tag'], proto_type=fm['proto_type'], direction=direction, controls=controls(rd),
                      persisted=persisted, writers=_csv(wr), readers=_csv(rd), enum=enum_name, finding=finding,
                      source='pinned contract v%s (%s) + %s_packets.h + the parsed atoms' % (c['contract_version'], c['contract_hash'], cls.lower()))
            if fname in enum_tables:
                t = enum_tables[fname]
                vals = [(0, t.get('unknown', 'unknown'))] + [(i + 1, lab) for i, lab in enumerate(t.get('labels', []))]
                eobj = 'enum:%s_%s' % (upper, fname.upper())
                users = {}
                for i, lab in vals:
                    const = '%s_%s_%s' % (upper, fname.upper(), re.sub(r'\W', '_', lab).upper())
                    wrs = sorted(fn for w in walks for fn, f in w.funcs.items() if const in f['enum_use'] and any(k[2] == fname and a['w'] for k, a in f['fields'].items()))
                    rds = sorted(fn for w in walks for fn, f in w.funcs.items() if const in f['enum_use'] and fn not in wrs)
                    users[const] = (wrs, rds)
                    enums.append({'name': const, 'config': config, 'enum': eobj, 'field': '%s.%s' % (cls, fname), 'value': i,
                                  'meaning': '%s = %s' % (fname, lab) + (' (the wire value nobody has set yet)' if i == 0 else ''),
                                  'set_by': ', '.join(wrs), 'compared_by': ', '.join(rds),
                                  'finding': '' if (wrs or rds or i == 0) else 'no atom sets or compares %s' % const,
                                  'source': 'EnumMapping %s.%s (1 byte on the wire) + the generated enum block + the parsed atoms' % (cls, fname)})
                objects.append({'name': eobj, 'config': config, 'kind': 'enum', 'c_type': 'enum (uint8_t on the wire)', 'size_bytes': 1, 'declared_in': '%s_packets.h' % cls.lower(),
                                'fields_count': len(vals), 'writers': ', '.join(sorted({fn for v in users.values() for fn in v[0]})),
                                'readers': ', '.join(sorted({fn for v in users.values() for fn in v[1]})),
                                'words': 'the values of %s.%s on the wire (EnumMapping): %s' % (cls, fname, ', '.join('%d = %s' % v for v in vals)), 'source': 'EnumMapping + generated header'})
        for g in inst:
            gd = next(w.globals_[g] for w in walks if g in w.globals_)
            objects.append({'name': obj, 'config': config, 'kind': 'wire-struct', 'c_type': '%s_t %s' % (cls, g), 'size_bytes': gd.get('width', 0),
                            'declared_in': '%s (%s_t from %s_packets.h, contract v%s %s)' % (os.path.basename(gd.get('file') or ''), cls, cls.lower(), c['contract_version'], c['contract_hash']),
                            'fields_count': len(fmap), 'writers': _csv({fn: how for (gg, fld), e in acc.items() if gg == g for fn, how in e['writers'].items()}),
                            'readers': _csv({fn: how for (gg, fld), e in acc.items() if gg == g for fn, how in e['readers'].items()}),
                            'words': 'THE wire struct of class %s: the report the board sends (telemetry) and the command it takes; the struct controls the hardware (the pin follows it)' % cls,
                            'source': 'pinned contract + generated header + the parsed atoms'})
        # presence bits + the header's own constants = enum-like define groups
        bits = [x for x in defs if x['name'].startswith('%s_F_' % upper)]
        if bits:
            eobj = 'defines:%s_F_*' % upper
            for x in bits:
                users = sorted(fn for fn, body in raw.items() if re.search(r'\b%s\b' % re.escape(x['name']), body))
                enums.append({'name': x['name'], 'config': config, 'enum': eobj, 'field': '%s presence bits' % cls, 'value': x['value'], 'meaning': x['comment'] or 'presence bit',
                              'set_by': '', 'compared_by': ', '.join(users), 'finding': '', 'source': 'generated header text (word match in function bodies)'})
            objects.append({'name': eobj, 'config': config, 'kind': 'enum-defines', 'c_type': '%s_mask_t' % cls, 'size_bytes': _WIDTH.get(next((x['value'].split()[-1].rstrip(';') for x in defs if False), ''), 0) or 1,
                            'declared_in': '%s_packets.h' % cls.lower(), 'fields_count': len(bits), 'writers': '', 'readers': ', '.join(sorted({fn for x in bits for fn, body in raw.items() if re.search(r'\b%s\b' % re.escape(x['name']), body)})),
                            'words': 'which fields a frame carries: one bit per field in tag order; %s_F_ALL = every field' % upper, 'source': 'generated header text'})
        consts = [x for x in defs if x['name'] in ('%s_MSG_TYPE' % upper, '%s_WIRE_VERSION' % upper, '%s_PAYLOAD_MAX' % upper, '%s_PRELUDE_BYTES' % upper, '%s_HASH_V2' % upper)]
        if consts:
            eobj = 'defines:%s_wire' % upper
            for x in consts:
                users = sorted(fn for fn, body in raw.items() if re.search(r'\b%s\b' % re.escape(x['name']), body))
                enums.append({'name': x['name'], 'config': config, 'enum': eobj, 'field': '%s framing' % cls, 'value': x['value'], 'meaning': {'MSG_TYPE': 'the frame type byte that names this class', 'WIRE_VERSION': 'the wire format version', 'PAYLOAD_MAX': 'the largest payload this class can need', 'PRELUDE_BYTES': 'bytes before the fields (index + presence bits)', 'HASH_V2': 'the wire contract hash the compat check compares'}.get(x['name'].split('_', 1)[1], ''),
                              'set_by': '', 'compared_by': ', '.join(users), 'finding': '', 'source': 'generated header text'})
            objects.append({'name': eobj, 'config': config, 'kind': 'enum-defines', 'c_type': 'constants', 'size_bytes': 0, 'declared_in': '%s_packets.h' % cls.lower(), 'fields_count': len(consts),
                            'writers': '', 'readers': ', '.join(sorted({fn for x in consts for fn, body in raw.items() if re.search(r'\b%s\b' % re.escape(x['name']), body)})),
                            'words': 'the framing constants of class %s' % cls, 'source': 'generated header text'})

    # ---- 2. the firmware's other struct globals (the rx parser state) + every static of the app, its defs header and the hal
    wire_inst = {g for w in walks for g, gd in w.globals_.items() if (gd.get('name') or '').endswith('_t') and (gd.get('name') or '')[:-2] in classes}
    seen = set()
    for w in walks:
        for g, gd in sorted(w.globals_.items()):
            if g in wire_inst or g in seen or gd.get('kind') == 'function':
                continue
            seen.add(g)
            where = os.path.basename(gd.get('file') or w.src)
            kind = 'struct' if gd.get('kind') == 'struct' else 'static'
            e_all = {fn: how for (gg, fld), e in acc.items() if gg == g for fn, how in e['writers'].items()}
            r_all = {fn: how for (gg, fld), e in acc.items() if gg == g for fn, how in e['readers'].items()}
            name = '%s:%s' % ('struct' if kind == 'struct' else 'static', g)
            group = 'generated header' if where.endswith('_packets.h') else 'hal' if where.startswith('hal') else 'the app' if where == 'main.c' else 'defs header'
            finding = '' if (e_all or r_all) else 'nobody touches %s' % g
            if e_all and not r_all:
                finding = 'nobody reads %s' % g
            if r_all and not e_all and not gd.get('init'):
                finding = 'nobody writes %s' % g
            objects.append({'name': name, 'config': config, 'kind': kind, 'c_type': gd.get('c', '?'), 'size_bytes': gd.get('width', 0), 'declared_in': '%s (%s)' % (where, group),
                            'fields_count': len(w.members(gd.get('name') or '')) if kind == 'struct' else 0, 'writers': _csv(e_all), 'readers': _csv(r_all),
                            'words': ('file-scope %s%s' % ('static ' if gd.get('static') else '', gd.get('c', ''))) + (' — %s' % fn_words(next(iter(e_all))) if len(e_all) == 1 else ''),
                            'source': 'parsed TU (%s)' % w.src, 'finding': finding})
            if finding:
                findings.append({'config': config, 'about': name, 'finding': finding, 'kind': 'global'})
            if kind == 'struct':
                for fname, m in w.members(gd.get('name') or ''):
                    e = acc.get((g, fname), {'writers': {}, 'readers': {}})
                    ff = ''
                    if not e['writers'] and not acc.get((g, '*'), {}).get('writers'):
                        ff = 'nobody writes %s.%s' % (g, fname)
                    elif not e['readers']:
                        ff = 'nobody reads %s.%s' % (g, fname)
                    add_field(name, fname, m.get('c', '?'), m.get('width', 0), writers=_csv(e['writers']), readers=_csv(e['readers']), finding=ff, source='parsed TU (%s)' % w.src)
        for fn, f in w.funcs.items():
            for ln, ld in f['local_statics'].items():
                name = 'local-static:%s.%s' % (fn, ln)
                objects.append({'name': name, 'config': config, 'kind': 'local-static', 'c_type': ld.get('c', '?'), 'size_bytes': ld.get('width', 0), 'declared_in': '%s (inside %s)' % (w.src, fn),
                                'fields_count': 0, 'writers': fn, 'readers': fn, 'words': 'a value %s keeps between calls — %s' % (fn, (ann.get(fn) or {}).get('role', 'state of its own')),
                                'source': 'parsed TU (%s)' % w.src, 'finding': ''})
    # ---- 3. EEPROM record(s): the address defines + the atoms that read/write them
    for h in sorted(os.listdir(d)):
        if h.endswith('.h'):
            for x in _defines(os.path.join(d, h)):
                if 'EEPROM' in x['name'] and 'ADDR' in x['name']:
                    users = sorted(fn for fn, body in raw.items() if re.search(r'\b%s\b' % re.escape(x['name']), body))
                    rw = {fn: ', '.join(sorted(set(next((xx.funcs[fn]['eeprom'] for xx in walks if fn in xx.funcs), [])))) for fn in users}
                    objects.append({'name': 'eeprom:%s' % x['name'], 'config': config, 'kind': 'eeprom', 'c_type': 'uint32_t at %s' % x['value'], 'size_bytes': 4, 'declared_in': h,
                                    'fields_count': 1, 'writers': ', '.join(fn for fn, c in rw.items() if 'write' in c), 'readers': ', '.join(fn for fn, c in rw.items() if 'read' in c),
                                    'words': 'persisted across resets: %s' % (x['comment'] or 'an EEPROM record'), 'source': 'header text + the parsed atoms (%s)' % ', '.join('%s: %s' % kv for kv in rw.items()), 'finding': ''})
    for f in fields:
        if f['finding']:
            findings.append({'config': config, 'about': f['name'], 'finding': f['finding'], 'kind': 'field'})
    for e in enums:
        if e['finding']:
            findings.append({'config': config, 'about': e['name'], 'finding': e['finding'], 'kind': 'enum'})
    atoms = sorted({fn for w in walks for fn in w.funcs if w.src == 'main.c' or fn in ann})
    return {'ok': True, 'config': config, 'app': cfg.get('app', ''), 'classes': classes, 'board': spec['board'], 'mcu': spec['mcu'], 'source_sha': r.get('source_sha', ''),
            'sources': r['sources'], 'generated': r['generated'], 'objects': objects, 'fields': fields, 'enums': enums, 'findings': findings, 'problems': problems,
            'atoms': atoms, 'pins': pins, 'derived_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'counts': {'objects': len(objects), 'fields': len(fields), 'enums': len(enums), 'findings': len(findings)},
            'derived_by': 'board.custom.firmware_state — parsed from the rendered config (cmod preprocessor + pycparser), the pinned wire contract, the generated header text; never typed'}


def rows(doc, which):
    return {'objects': doc['objects'], 'fields': doc['fields'], 'enums': doc['enums'], 'findings': doc['findings']}[which]


# ------------------------------------------------------------------ rows on a server
def persist(manager, doc):
    from board.board_basis import FirmwareStateObject, FirmwareStateField
    from board.custom.installer import upsert
    for o in doc['objects']:
        upsert(manager, FirmwareStateObject, dict(o, name='%s:%s' % (doc['config'], o['name']), object=o['name']))
    for f in doc['fields']:
        upsert(manager, FirmwareStateField, dict(f, name='%s:%s' % (doc['config'], f['name']), field_name=f['field']))


# ------------------------------------------------------------------ live
def live(manager, config, session=''):
    """The wire fields with their live values: the wire class's row this config reports into (its rig name), the twin session's status line (cycle, adc), the hosted
    bridge that feeds the row. Nothing is simulated here: a value is shown only when a row holds it."""
    doc = derive(config, manager)
    rig = json.loads(_config(config)[1]['variant'].get('knobs_json') or '{}').get('rig_name', config)
    out = []
    for cls in doc['classes']:
        table = ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}) if manager is not None else {}
        row = next((r for r in (table.values() if isinstance(table, dict) else table) if getattr(r, 'name', '') == rig), None)
        for f in [x for x in doc['fields'] if x['object'] == 'wire:%s' % cls]:
            val = getattr(row, f['field'], None) if row is not None else None
            out.append({'name': f['name'], 'config': config, 'class': cls, 'row': rig if row is not None else '', 'field': f['field'], 'direction': f['direction'],
                        'live': '' if val is None else str(val), 'live_note': ('from row %s %s' % (cls, rig)) if row is not None else 'no %s row named %s on this server yet (attach a bridge; the first report makes it)' % (cls, rig),
                        'controls': f['controls'], 'writers': f['writers'], 'readers': f['readers']})
    status, bridges = {}, []
    if session and manager is not None:
        from board.custom import twin_sessions as TS
        try:
            s = TS.one(manager, session)
            status = dict(s.get('status') or {}, session=session, state=s.get('state'), hex_sha256=s.get('hex_sha256'), config=s.get('config'))
        except Exception as e:   # noqa: BLE001
            status = {'session': session, 'error': str(e)}
        try:
            from grpcbridge.custom import hosted_bridges as HB
            bridges = [b for b in HB.listing(manager) if b.get('session') == session]
        except Exception:   # noqa: BLE001
            bridges = []
    for k, v in sorted(status.items()):
        out.append({'name': 'twin.%s' % k, 'config': config, 'class': 'twin session', 'row': session, 'field': k, 'direction': 'twin status', 'live': str(v), 'live_note': 'the twin\'s latest status line', 'controls': '', 'writers': '', 'readers': ''})
    for b in bridges:
        out.append({'name': 'bridge.%s' % b['name'], 'config': config, 'class': 'hosted bridge', 'row': b['name'], 'field': 'state', 'direction': 'bridge', 'live': b.get('state', ''), 'live_note': 'feeds the %s row from the session\'s serial report' % ', '.join(doc['classes']), 'controls': '', 'writers': '', 'readers': ''})
    return {'ok': True, 'config': config, 'rig': rig, 'session': session, 'rows': out, 'count': len(out)}


# ------------------------------------------------------------------ CLI
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='pol firmware state')
    ap.add_argument('config')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fields', action='store_true')
    ap.add_argument('--enums', action='store_true')
    ap.add_argument('--findings', action='store_true')
    a = ap.parse_args(argv)
    try:
        doc = derive(a.config, cache=False)
    except StateRefused as e:
        print('[REFUSED] %s' % e)
        return 3
    if a.json:
        print(json.dumps(doc, indent=1, default=str))
        return 0
    print('[ OK ] %s (%s on %s): %d state objects, %d fields, %d enum values, %d findings' % (doc['config'], doc['app'], doc['board'], *doc['counts'].values()))
    if not (a.fields or a.enums or a.findings):
        for o in doc['objects']:
            print('  %-14s %-34s %-22s %4s B  %s' % (o['kind'], o['name'], o['c_type'][:22], o['size_bytes'], o['declared_in']))
            if o['writers'] or o['readers']:
                print('  %14s written by: %s' % ('', o['writers'] or '-'))
                print('  %14s read by:    %s' % ('', o['readers'] or '-'))
    if a.fields:
        for f in doc['fields']:
            print('  %-40s %-12s tag %-2s %-22s %s' % (f['name'], f['c_type'][:12], f['tag'] or '-', f['direction'], f['controls'] or ''))
            print('  %40s written by: %s' % ('', f['writers'] or '-'))
            print('  %40s read by:    %s%s' % ('', f['readers'] or '-', ('   PERSISTED ' + f['persisted']) if f['persisted'] else ''))
    if a.enums:
        for e in doc['enums']:
            print('  %-40s = %-8s %-40s set by: %s  compared by: %s' % (e['name'], e['value'], e['meaning'][:40], e['set_by'] or '-', e['compared_by'] or '-'))
    if a.findings or not (a.fields or a.enums):
        for f in doc['findings']:
            print('  [FINDING] %s: %s' % (f['about'], f['finding']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
