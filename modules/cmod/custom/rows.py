"""
@module cmod.custom.rows

`polari-firmware.json` → ROWS (CProject, CModule, CFunctionAtom, CPort). The manifest is the derived truth; the rows are
its projection, so the page shows configured tables (no raw JSON — every list becomes a text column or its own row) and
the seeds need no parse and no engine at boot. Row names: `<project>` / `<project>:<module>` / `<project>:<atom>` /
`<project>:<atom>#<port>`.
"""
import hashlib
import json
import os

from cmod.custom import projects as P


def _csv(xs):
    return ', '.join(str(x) for x in xs)


def project_rows(m, path=''):
    p = m['project']
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest() if path and os.path.isfile(path) else ''
    b = m.get('build') or {}
    c = m.get('counts') or {}
    proj = {'name': p, 'title': m.get('title', ''), 'kind': m.get('kind', ''), 'root': m.get('root', ''), 'board': m.get('board', ''),
            'mcu': m.get('mcu', ''), 'manifest_path': os.path.join(m.get('root', ''), P.MANIFEST_NAME), 'manifest_sha256': sha,
            'parser': m['parser']['engine'], 'parser_version': m['parser']['version'], 'atoms': c.get('atoms', 0),
            'annotated': c.get('annotated', 0), 'isr_atoms': c.get('isr', 0), 'pure_atoms': c.get('pure', 0),
            'not_isr_safe': c.get('not_isr_safe', 0), 'modules': len(m.get('modules', [])),
            'configurations': _csv(x['name'] for x in m.get('configurations', [])), 'cc': b.get('cc', ''), 'cc_version': b.get('cc_version', ''),
            'cflags': ' '.join(b.get('cflags', [])),
            'make_alone': '; '.join('%s %s %s' % (x['name'], 'ok' if x['make_alone']['ok'] else 'FAILED', x['make_alone']['hex_sha256'][:16])
                                    for x in m.get('configurations', []) if x.get('make_alone')),
            'conformed_at': m.get('conformed_at', ''), 'notes': m.get('notes', '')}
    mods = [{'name': '%s:%s' % (p, x['name']), 'project': p, 'module': x['name'], 'role': x['role'], 'files': _csv(f['path'] for f in x['files']),
             'sha256': hashlib.sha256(''.join(f['sha256'] for f in x['files']).encode()).hexdigest(), 'atoms': len(x['atoms']), 'notes': ''}
            for x in m.get('modules', [])]
    atoms, ports = [], []
    for a in m.get('atoms', []):
        cost = a.get('cost') or {}
        regs = [r for r in a['resources'] if r['kind'] == 'register']
        atoms.append({
            'name': '%s:%s' % (p, a['name']), 'project': p, 'module': a['module'], 'function': a['function'], 'kind': a['kind'],
            'signature': a['signature'], 'line': a['line'], 'is_static': bool(a['static']), 'isr_vector': a['isr_vector'],
            'port_count': len(a['ports']),
            'ports_summary': _csv('%s %s:%s%s' % (x['direction'], x['name'], x['polari_type'] or '-', ' [%s]' % x['unit'] if x['unit'] else '')
                                  for x in a['ports']),
            'resources_summary': _csv('%s %s%s' % (r['kind'], r['name'], ' (%s)' % r['access'] if r['access'] else '') for r in a['resources']),
            'registers': _csv(r['name'] for r in regs), 'peripherals': _csv(sorted({r['peripheral'] for r in regs if r['peripheral']})),
            'globals_touched': _csv(r['name'] for r in a['resources'] if r['kind'] == 'global'), 'calls': _csv(a['calls']),
            'pure': bool(a['pure']), 'pure_why': a['pure_why'], 'isr_safe': a['isr_safe'], 'isr_safe_why': a['isr_safe_why'],
            'atomic_block': bool(a['atomic_block']), 'annotated': bool(a['annotation']),
            'annotation_form': (a['annotation'] or {}).get('form', ''), 'role': (a['annotation'] or {}).get('role', ''), 'configs': _csv(a['configs']),
            'text_bytes': int(cost.get('text_bytes') or 0), 'in_shipped_build': bool(cost.get('in_shipped_build')), 'inlined': bool(cost.get('inlined')),
            'text_bytes_noinline': int(cost.get('text_bytes_noinline') or 0),
            'stack_bytes': cost['stack_bytes'] if cost.get('stack_bytes') is not None else -1, 'stack_kind': cost.get('stack_kind', ''),
            'measured_in': cost.get('measured_in', ''), 'cost_why': cost.get('why', ''), 'title': a.get('title', ''), 'notes': a.get('notes', '')})
        for i, x in enumerate(a['ports']):
            ports.append({'name': '%s:%s#%s' % (p, a['name'], x['name']), 'project': p, 'atom': '%s:%s' % (p, a['name']), 'port': x['name'],
                          'position': i, 'direction': x['direction'], 'ctype': x['ctype'], 'width_bytes': int(x['width_bytes'] or 0),
                          'polari_type': x['polari_type'], 'unit': x['unit'], 'meaning': x['meaning'], 'source': x['source']})
    return {'CProject': [proj], 'CModule': mods, 'CFunctionAtom': atoms, 'CPort': ports}


def template_rows():
    """Rows of every TEMPLATE project whose manifest is committed (the seeds) — {class: [rows]}."""
    out = {'CProject': [], 'CModule': [], 'CFunctionAtom': [], 'CPort': []}
    for name in sorted(P.TEMPLATES):
        spec = P.resolve(name)
        path = P.manifest_path(spec)
        if not os.path.isfile(path):
            continue
        for k, v in project_rows(json.load(open(path)), path).items():
            out[k] += v
    return out
