"""
@module cmod.custom.generator.context

The graph glue's CONTEXT for the avr templates: exactly what glue.render_files() holds today (the resolved model, the
template project's context, the verbatim atom copies) normalized into plain dicts/lists — statements as FLAT lists with a
depth, every identifier pulled out as its own key so the template filters (c_ident / c_type / c_expr) are the one gate.
Atom bodies stay verbatim text blocks (glue.extract), passed through c_block. Nothing here chooses a pin or an isotope.

Statement kinds (key `k`, indent depth `d`): decl, call, field, rule, frame, tick_open, tick_close, drain_open, drain_close.
"""
from cmod.custom.generator.filters import GenError


def _local_type(ctype):
    t = ctype.replace('const ', '').strip()
    return t[:-1].strip() if t.endswith('*') else t


class _Walk:
    def __init__(self, model):
        self.m, self.nodes, self.edges = model, model['nodes'], model['edges']
        self.indexed = False
        self.drains = {ed['src']: ed for ed in self.edges if ed['kind'] == 'on-rx'}
        self.up = model['cls_up']
        self.cls = model['graph']['class_name']

    def val(self, i, port):
        n = self.nodes[i]
        if port in n.get('bindings', {}):
            return n['bindings'][port]
        for ed in self.edges:
            if ed['dst'] == i and ed['to_port'] == port and ed['kind'] in ('data', 'on-command'):
                if ed['kind'] == 'on-command':
                    return '&%s' % ed['src']
                s = self.nodes[ed['src']]
                expr = ('%s_%s' % (s['instance'], 'wire' if ed['from_port'] == 'wire' else 'length')) if s['kind'] == 'frame' else \
                    '%s_%s' % (ed['src'], ed['from_port'])
                tt = n['ports'][port][1]
                if ed['ctype_from'] != tt and not tt.endswith('*'):
                    expr = '(%s)%s' % (tt, expr)
                return expr
        raise GenError('internal: %s.%s has no source' % (i, port))

    def call(self, i, d):
        n, a = self.nodes[i], self.nodes[i]['atom']
        args, decls = [], []
        for p in a['ports']:
            if p['name'] == 'return':
                continue
            if p['direction'] == 'out':
                decls.append({'k': 'decl', 'd': d, 'type': _local_type(p['ctype']), 'name': '%s_%s' % (i, p['name'])})
                args.append('&%s_%s' % (i, p['name']))
            else:
                args.append(self.val(i, p['name']))
        ret = n['ports'].get('return')
        consumed = any(ed['src'] == i and ed['from_port'] == 'return' for ed in self.edges if ed['kind'] in ('data', 'field'))
        call = {'k': 'call', 'd': d, 'node': i, 'fn': a['function'], 'args': args,
                'ret_type': ret[1] if ret and consumed else None, 'ret_name': '%s_return' % i}
        return decls, call

    def field_write(self, ed, d):
        n = self.nodes[ed['dst']]
        src = '%s_%s' % (ed['src'], ed['from_port'])
        expr = src
        if ed['scale'] or ed['offset']:
            expr = '%s%s%s' % (src, ' * %s' % ed['scale'] if ed['scale'] else '', ' + %s' % ed['offset'] if ed['offset'] else '')
            expr = '(%s)(%s)' % (n['ports'][ed['to_port']][1], expr)
        elif ed['ctype_from'] != n['ports'][ed['to_port']][1]:
            expr = '(%s)%s' % (n['ports'][ed['to_port']][1], src)
        return {'k': 'field', 'd': d, 'dst': ed['dst'], 'port': ed['to_port'], 'expr': expr, 'name': ed['name']}

    def node(self, i, d):
        n, out = self.nodes[i], []
        if n['kind'] == 'c-atom' and i in self.drains:
            ed = self.drains[i]
            parser = ed['dst']
            cmds = [c for _, c in sorted((self.nodes[e['dst']]['order'], e['dst']) for e in self.edges if e['kind'] == 'on-command' and e['src'] == parser)]
            out.append({'k': 'drain_open', 'd': d, 'name': ed['name'], 'up': self.up, 'src': i, 'parser': parser, 'cmds': cmds, 'fn': n['atom']['function'],
                        'port': ed['from_port'], 'type': _local_type(n['ports'][ed['from_port']][1])})
            for c in cmds:
                out += self.node(c, d + 3)
            out.append({'k': 'drain_close', 'd': d})
        elif n['kind'] == 'c-atom':
            decls, c = self.call(i, d)
            out += decls + [c]
        elif n['kind'] == 'rule':
            p = n['params']
            out.append({'k': 'rule', 'd': d, 'name': i, 'cls': p['class'], 'field': p['field'], 'from': p['from'], 'to': p['to'], 'up': self.up,
                        'now': self.val(i, 'now'), 'after_ms': p['after_ms'].rstrip('uU')})
        elif n['kind'] == 'frame':
            out.append({'k': 'frame', 'd': d, 'name': i, 'cls': self.cls, 'inst': n['params']['class'], 'device_id': n['params']['device_id'],
                        'mask': i.upper(), 'indexed': self.indexed})
        elif n['kind'] == 'tick':
            out.append({'k': 'tick_open', 'd': d, 'name': i, 'now': self.val(i, 'now'), 'period_ms': n['params']['period_ms']})
            out += self.stmts('tick:%s' % i, d + 1)
            out.append({'k': 'tick_close', 'd': d})
        return out + [self.field_write(ed, d) for ed in self.edges if ed['kind'] == 'field' and ed['at'] == i]

    def stmts(self, scope, d):
        out = [self.field_write(ed, d) for ed in self.edges if ed['kind'] == 'field' and ed.get('scope') == scope and ed['at'] == 'start']
        for i in self.m['order'].get(scope, []):
            out += self.node(i, d)
        return out


def glue_c_context(model, ctx, copies, banner, pin_config=False):
    """The context of avr/polari_graph.c.j2."""
    w = _Walk(model)
    nodes = model['nodes']
    w.indexed = ('#define %s_INDEX_WIDTH' % w.up) in ctx['class_header']
    hdr = ctx['class_header_name']
    ordered = sorted(nodes, key=lambda i: (nodes[i]['order'], i))
    statics = []
    for i in ordered:
        n = nodes[i]
        if n['kind'] in ('class', 'parser', 'frame'):
            statics.append({'kind': n['kind'], 'name': i})
    init = []
    for i in model['order'].get('init', []):
        init.append(w.call(i, 1)[1])          # init decls are never emitted (legacy: call(i)[1] only)
    return {'banner': banner, 'cls': w.cls, 'up': w.up, 'class_header': hdr,
            'extra_headers': [h for h in ctx['files_out'] if h.endswith('.h') and h not in ('board_config.h', hdr, 'polari_graph.h')],
            'statics': statics, 'copies': copies,
            'main_locals': [{'name': i, 'kind': nodes[i]['kind']} for i in sorted(nodes) if nodes[i]['kind'] in ('tick', 'frame')],
            'pin_config': pin_config, 'init_calls': init,
            'zeroed': [i for i in ordered if nodes[i]['kind'] in ('class', 'parser')],
            # legacy quirk kept byte-for-byte: an init-scope field write is emitted at column 0
            'init_fields': [w.field_write(ed, 0) for ed in w.edges if ed['kind'] == 'field' and ed.get('scope') == 'init'],
            'identity': [{'name': i, 'cls_name': nodes[i]['params'].get('name'), 'status': nodes[i]['params'].get('status')}
                         for i in ordered if nodes[i]['kind'] == 'class'],
            'loop_stmts': w.stmts('loop', 2)}


def banner(graph_name, gsha, generator):
    return {'generator': generator, 'graph': graph_name, 'sha': gsha}


def glue_h_context(model, ctx, provenance, bn):
    g, nodes, up = model['graph'], model['nodes'], model['cls_up']
    frames = [{'name': i, 'upper': i.upper(), 'fields': list(nodes[i]['fields'])} for i in sorted(nodes) if nodes[i]['kind'] == 'frame']
    return {'banner': bn, 'class_header': ctx['class_header_name'], 'graph': g['name'], 'sha': model['sha'], 'cls': g['class_name'], 'up': up,
            'frames': frames, 'provenance': [{'file': f, 'sha16': s[:16], 'src': src} for f, s, src in provenance]}


def makefile_context(model, ctx, sources, generator, mk, pin_config=False):
    """mk: measure.makefile_vars() of the template project's Makefile."""
    g = model['graph']
    cflags = '-mmcu=$(MCU) -DF_CPU=$(F_CPU) %s' % ' '.join(x for x in mk['CFLAGS'].split() if not x.startswith(('-mmcu=', '-DF_CPU=')))
    if pin_config:
        cflags += ' -DPOLARI_PIN_CONFIG=1'
    return {'generator': generator, 'graph': g['name'], 'sha': model['sha'], 'project': g['project'],
            'mcu': mk.get('MCU', 'atmega328p'), 'f_cpu': mk.get('F_CPU', '16000000UL'), 'cc': mk.get('CC', 'avr-gcc'), 'cflags': cflags,
            'ldflags': mk.get('LDFLAGS', ''), 'srcs': ' '.join(sources),
            'hdrs': ' '.join(sorted(f for f in ctx['files_out'] if f.endswith('.h')))}
