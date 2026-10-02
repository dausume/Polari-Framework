"""
@module cmod.custom.atoms

C PROJECT → ATOMS (C_MODULARIZATION_PLAN.md §2/§4, cmod-0). An ATOM is a C function defined in one of the project's own
.c files; its facts are DERIVED by parsing (pycparser, preprocess.py) — never hand-maintained:

  signature   return type + parameters (C type, AVR width, the Polari type a port carries — c_types.py)
  ports       a by-value parameter = in; a pointer = in (const) / out (only written through) / inout (read and written,
              or handed to a callee); a non-void return = out(return). A POLARI_NODE annotation adds the unit and
              meaning and may settle a pointer's direction (annotation.py); it may not contradict the C (an out() on a
              const pointer is refused)
  resources   registers (avr-libc's own names → peripheral), file-scope globals (read/write, volatile, width, shared with
              an ISR), library resources (EEPROM, the watchdog, SREG.I by sei/cli), the ISR vector it IS
  calls       what it calls; pure = touches no global, register or resource and calls only pure functions
  isr_safe    for a main-context atom: every global it shares with an ISR is read/written inside an ATOMIC_BLOCK when it
              is wider than one byte (the torn read) or modified read-modify-write; `isr` for an ISR itself;
              `undetermined` when it opens a manual sei()/cli() region (not tracked)

Functions defined in headers (the generated <class>_packets.h) are not atoms of the project — they are read for the
purity/ISR closure and listed as `library`.
"""
import os

from pycparser import c_ast, c_parser

from cmod.custom import annotation as A
from cmod.custom import registers as R
from cmod.custom.c_types import TypeTable, polari_type
from cmod.custom.preprocess import ISR_PREFIX, preprocess
from cmod.custom.scan import BodyScan

#: avr-libc / libc calls that touch a resource (by name; prefix match on a trailing '*')
LIB_RESOURCES = {'sei': 'SREG.I (interrupts on)', 'cli': 'SREG.I (interrupts off)', 'eeprom_*': 'EEPROM', 'wdt_*': 'WDT',
                 '_delay_*': 'busy-wait', 'sleep_*': 'SLEEP'}
#: library calls that touch only the memory their arguments point at (no global, no register)
LIB_MEMORY = ('memcpy', 'memset', 'memmove', 'memcmp', 'strcpy', 'strncpy', 'strlen', 'strcmp', 'strncmp')


class CModRefused(ValueError):
    pass


def lib_resource(name):
    for k, v in LIB_RESOURCES.items():
        if name == k or (k.endswith('*') and name.startswith(k[:-1])):
            return v
    return ''


def parse_file(path, include_dirs, defines=()):
    text, problems = preprocess(path, include_dirs, defines)
    try:
        return c_parser.CParser().parse(text, os.path.basename(path)), problems
    except Exception as e:   # pycparser's ParseError carries file:line:col
        raise CModRefused('pycparser cannot parse %s: %s' % (os.path.basename(path), e))


def _globals(ast, types):
    out = {}
    for ext in ast.ext:
        if isinstance(ext, c_ast.Decl) and ext.name and not isinstance(ext.type, c_ast.FuncDecl):
            d = types.describe(ext.type)
            d['static'] = 'static' in (ext.storage or [])
            d['extern'] = 'extern' in (ext.storage or [])
            d['file'] = ext.coord.file if ext.coord else ''
            out[ext.name] = d
    return out


def tu_facts(path, include_dirs, defines=(), mcu='atmega328p'):
    """One translation unit → {function name: facts} for EVERY function defined in it (headers included; `file` says where)."""
    ast, problems = parse_file(path, include_dirs, defines)
    types = TypeTable(ast)
    gl = _globals(ast, types)
    regs = R.load(mcu)['registers']
    out = {}
    for ext in ast.ext:
        if not isinstance(ext, c_ast.FuncDef):
            continue
        fname = ext.decl.name
        isr = fname[len(ISR_PREFIX):] if fname.startswith(ISR_PREFIX) else ''
        ftype = ext.decl.type
        ret = types.describe(ftype.type)
        params = []
        for p in (ftype.args.params if ftype.args else []):
            if isinstance(p, c_ast.Decl) and p.name:
                params.append((p.name, types.describe(p.type)))
        s = BodyScan(ext, gl, regs, types)
        out[isr or fname] = {
            'function': fname, 'isr': isr, 'file': ext.coord.file, 'line': ext.coord.line, 'static': 'static' in (ext.decl.storage or []),
            'returns': ret, 'params': params, 'globals': {k: dict(v, decl=gl[k]) for k, v in s.g.items()}, 'registers': s.reg,
            'calls': s.calls, 'pointers': s.ptr, 'atomic': s.atomic}
    return out, problems


def _ports(f, ann):
    ports = []
    for name, d in f['params']:
        if d['kind'] in ('pointer', 'array'):
            tgt = d.get('target') or {}
            use = f['pointers'].get(name, {})
            if tgt.get('const'):
                direction, how = 'in', 'const pointer'
            elif use.get('w') and not use.get('r') and not use.get('passed'):
                direction, how = 'out', 'only written through'
            elif use.get('w') or use.get('passed'):
                direction, how = 'inout', 'read and written' if use.get('w') else 'handed to %s' % ', '.join(sorted(set(use['passed'])))
            else:
                direction, how = 'in', 'only read through'
        else:
            direction, how = 'in', 'by value'
        ports.append({'name': name, 'direction': direction, 'ctype': d['c'], 'width_bytes': d.get('width', 0) if d['kind'] not in ('pointer', 'array')
                      else (d.get('target') or {}).get('width', 0), 'polari_type': polari_type(d), 'unit': '', 'meaning': '', 'source': 'derived: ' + how})
    if f['returns'].get('kind') != 'void':
        r = f['returns']
        ports.append({'name': 'return', 'direction': 'out', 'ctype': r['c'], 'width_bytes': r.get('width', 0), 'polari_type': polari_type(r),
                      'unit': '', 'meaning': '', 'source': 'derived: return value'})
    if ann:
        where = '%s:%d' % (f['file'], ann['line'])
        by = {p['name']: p for p in ports}
        for ap in ann['ports']:
            p = by.get(ap['name'])
            if p is None:
                raise A.AnnotationRefused('%s: POLARI_NODE(%s) names port %r — the function has %s' % (
                    where, ann['name'], ap['name'], ', '.join(by) or 'no parameters and returns void'))
            if ap['direction'] != p['direction']:
                if p['source'].endswith('const pointer') and ap['direction'] != 'in':
                    raise A.AnnotationRefused('%s: %s(%s) contradicts the C: %s is a const pointer' % (where, ap['direction'], ap['name'], ap['name']))
                if p['source'] == 'derived: by value' and ap['direction'] != 'in':
                    raise A.AnnotationRefused('%s: %s(%s) contradicts the C: %s is passed by value' % (where, ap['direction'], ap['name'], ap['name']))
                p['direction'] = ap['direction']
            p.update(unit=ap['unit'], meaning=ap['meaning'], source=p['source'] + ' + annotation')
    return ports


def attach_annotations(source_path, rel, functions_here):
    """Annotations of one source file → {function: annotation}; refuses one that names no function defined after it."""
    text = open(source_path).read()
    anns = A.find(text, rel)
    out = {}
    import re
    for a in anns:
        tail = text.split('\n')[a['end_line']:]
        nxt = None
        for line in tail[:12]:
            line = re.sub(r'__attribute__\s*\(\(.*?\)\)', '', line)
            m = re.match(r'^\s*(?:[A-Za-z_][\w\s\*]*?\b)?(?:ISR\s*\(\s*(\w+)|(\w+)\s*\()', line)
            if m and not line.lstrip().startswith(('#', '/*', '*', '//')):
                nxt = m.group(1) or m.group(2)
                break
        if nxt != a['name']:
            raise A.AnnotationRefused('%s:%d: POLARI_NODE(%s) must sit right above %s — the next function is %s' % (
                rel, a['line'], a['name'], a['name'], nxt or 'none'))
        out[a['name']] = a
    return out
