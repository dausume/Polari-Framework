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


# ------------------------------------------------------------------ cmod-1: graphs, nodes, edges, glue builds
def _port(n, port, atoms):
    if n.get('kind') == 'c-atom':
        a = atoms.get((n.get('atom') or '').partition(':')[2]) or {}
        return next((p['ctype'] for p in a.get('ports', []) if p['name'] == port), '')
    from cmod.custom.graph import GLUE_PORTS
    return (GLUE_PORTS.get(n.get('kind'), {}).get(port) or ('', ''))[1]


def graph_rows(seed=None):
    """The seeded graphs as rows (+ their committed glue-build record): derived fields come from the atoms' committed manifest and
    the record — nothing is rendered or built at boot. {class: [rows]}."""
    from cmod.custom import graph as GR
    from cmod.custom import glue as GL
    from cmod.custom.graph_seed import SEED_GRAPHS, seed_graph
    out = {'CGraph': [], 'CGraphNode': [], 'CGraphEdge': [], 'CGlueBuild': []}
    for g0 in (seed or SEED_GRAPHS):
        rows = seed_graph(g0['name'])
        g = rows['graph']
        spec = P.resolve(g['project'])
        mpath = P.manifest_path(spec)
        atoms = {a['name']: a for a in json.load(open(mpath))['atoms']} if os.path.isfile(mpath) else {}
        gsha = GR.graph_sha(rows)
        rec = GL.load_record(g['name']) or {}
        fresh = rec.get('graph_sha256') == gsha
        proof, build = (rec.get('proof') or {}) if fresh else {}, (rec.get('build') or {}) if fresh else {}
        status = ('proven' if proof.get('equivalent') else 'built' if build else 'rendered') if fresh else ('stale' if rec else 'seeded')
        inst = {n['instance']: n for n in rows['nodes']}
        out['CGraph'].append(dict(g, status=status, graph_sha256=gsha, node_count=len(rows['nodes']), edge_count=len(rows['edges']),
                                  atom_count=sum(1 for n in rows['nodes'] if n['kind'] == 'c-atom'),
                                  cost_estimate_bytes=int((rec.get('cost_estimate') or {}).get('total_bytes') or 0),
                                  cost_estimate_why=(rec.get('cost_estimate') or {}).get('why', ''), glue_contains='; '.join(rec.get('glue_contains') or [])))
        for n in rows['nodes']:
            a = atoms.get((n.get('atom') or '').partition(':')[2]) or {}
            out['CGraphNode'].append(dict(n, ports_summary=_csv('%s %s:%s' % (p['direction'], p['name'], p['polari_type'] or '-') for p in a.get('ports', [])),
                                          role=(a.get('annotation') or {}).get('role', ''),
                                          cost_bytes=int((a.get('cost') or {}).get('text_bytes_noinline') or 0), isr_safe=a.get('isr_safe', ''),
                                          pure=bool(a.get('pure'))))
        for e in rows['edges']:
            src, dst = inst.get(e['from_node'], {}), inst.get(e['to_node'], {})
            ct = ''
            if dst.get('kind') == 'class' and e.get('to_port'):
                ct = 'field %s' % e['to_port']
            out['CGraphEdge'].append(dict(e, ctype_from=_port(src, e['from_port'], atoms) if e.get('from_port') else '',
                                          ctype_to=ct or (_port(dst, e['to_port'], atoms) if e.get('to_port') else '')))
        if rec:
            ref = proof.get('reference') or {}
            conf = rec.get('conformed') or {}
            out['CGlueBuild'].append({
                'name': '%s@%s' % (g['name'], rec['files_sha256'][:12]), 'graph': g['name'], 'graph_sha256': rec['graph_sha256'],
                'generated_project': rec['generated_project'], 'generator': rec['generator'],
                'files': _csv('%s %s' % (f, s[:12]) for f, s in sorted(rec['files'].items())), 'files_sha256': rec['files_sha256'],
                'rendered_at': rec.get('rendered_at', ''), 'build_ok': bool(build.get('ok')), 'built_by': build.get('built_by', ''),
                'hex_sha256': build.get('hex_sha256', ''), 'size_text': int(build.get('size_text') or 0), 'size_data': int(build.get('size_data') or 0),
                'size_bss': int(build.get('size_bss') or 0), 'reference': '%s (%s)' % (ref.get('variant', ''), ref.get('built_by', '')) if ref else '',
                'ref_hex_sha256': ref.get('hex_sha256', ''), 'ref_size_text': int(ref.get('size_text') or 0), 'ref_size_data': int(ref.get('size_data') or 0),
                'ref_size_bss': int(ref.get('size_bss') or 0), 'cost_estimate_bytes': int((rec.get('cost_estimate') or {}).get('total_bytes') or 0),
                'cost_measured_bytes': int(build.get('cost_measured_attributable_bytes') or 0), 'cost_why': build.get('cost_why', ''),
                'equivalent': bool(proof.get('equivalent')),
                'proof': ('EQUIVALENT: %d frames identical field by field%s%s' % (proof['frames_compared'], '; raw UART identical' if proof.get('raw_uart_identical') else '',
                                                                                   '; the .hex is byte-identical to the hand-written build' if proof.get('hex_identical') else '')
                          if proof.get('equivalent') else ('NOT equivalent: %d differences' % proof.get('n_differences', 0)) if proof else 'not proven'),
                'frames_compared': int(proof.get('frames_compared') or 0), 'fields_compared': _csv(proof.get('fields_compared') or []),
                'differences': '; '.join(proof.get('differences') or []) or ('none' if proof else ''),
                'stimulus': '; '.join(['%s s, seed %s, ADC0 ramp %s mV' % (proof['stimulus']['seconds'], proof['stimulus']['seed'], proof['stimulus']['adc0_ramp_mv'])]
                                      + proof['stimulus']['commands']) if proof else '',
                'cycles': ('total %s / %s; frame tx cycle delta %s..%s; first frame at cycle %s' % (
                    proof['cycles']['total_hand'], proof['cycles']['total_glue'], proof['cycles']['frame_tx_cycle_delta_min'],
                    proof['cycles']['frame_tx_cycle_delta_max'], proof['cycles']['first_frame_cycle_glue'])) if proof else '',
                'engines': '%s; twin %s %s' % (build.get('built_by', ''), (proof.get('twin') or {}).get('how', ''), (proof.get('twin') or {}).get('where', '')) if proof else build.get('built_by', ''),
                'conformed': ('%d atoms (the glue\'s own: %s), %s sha %s' % (conf['atoms'], ', '.join(conf['glue_atoms']), conf['manifest'], conf['manifest_sha256'][:16])) if conf else '',
                'proven_at': proof.get('proven_at', ''), 'notes': '' if fresh else 'STALE: the graph changed since this render (pol cmod render)'})
    return out
