"""
@module cmod.custom.glue_legacy

The PRE-fgm-0 Python emitters of the graph glue (string-joined C), kept verbatim for ONE release behind
`POLARI_GLUE_LEGACY=1` so the template path (cmod.custom.generator + modules/cmod/custom/templates/avr) can be diffed against
them byte for byte (selftest_generator). Not the default; deleted after fgm-0 has soaked.
"""
import os

from cmod.custom import glue as _g
from cmod.custom.glue import GENERATOR, GlueRefused


def _local_type(ctype):
    t = ctype.replace('const ', '').strip()
    return t[:-1].strip() if t.endswith('*') else t


def _render_c(model, ctx, copies, header_comment, pin_config=False):
    g, nodes, edges, cls, up = model['graph'], model['nodes'], model['edges'], model['graph']['class_name'], model['cls_up']
    hdr = ctx['class_header_name']
    indexed = ('#define %s_INDEX_WIDTH' % up) in ctx['class_header']
    # ucd-0e2b: button_clock.c's own atoms use <avr/eeprom.h> (boot_session_mint) and <util/atomic.h> (telemetry_send's
    # ATOMIC_BLOCK snapshot) — the first 'app' atoms to need more than hal.c's own <avr/interrupt.h>. Both are tiny
    # avr-libc headers (macros + static inlines), harmless to include unconditionally even where unused (no
    # -Wunused-function on a macro), so they are added to the FIXED list rather than tracked per atom.
    out = [header_comment, '#include <stdint.h>', '#include <string.h>', '#include <avr/eeprom.h>', '#include <avr/interrupt.h>',
           '#include <util/atomic.h>', '',
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
    if pin_config:
        out.append('    pin_config_init();   /* GENERATED (cmod.custom.pin_config_gen) — runs FIRST, before every other init (his fixed order) */')
    for i in model['order'].get('init', []):
        out.append('    %s   /* %s */' % (call(i)[1], i))
    ordered = sorted(nodes, key=lambda i: (nodes[i]['order'], i))
    out += ['    memset(&%s, 0, sizeof %s);' % (i, i) for i in ordered if nodes[i]['kind'] in ('class', 'parser')]
    # ucd-0e2b: a field edge sourced from an INIT atom (e.g. boot_session_mint's return -> state.boot_session) is
    # scoped 'init' by graph.py's own scope_of() but was never rendered anywhere — the init loop above only calls
    # the atom, it never writes its ports into a class field. Emitted HERE, after the memset block (never before:
    # memset would wipe a field an init atom wrote right after calling it), using the `<node>_<port>` local the
    # init call above already declared (same C statement scope, main()'s own body).
    out += [field_write(ed) for ed in edges if ed['kind'] == 'field' and ed.get('scope') == 'init']
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


def _render_makefile(model, ctx, sources, pin_config=False):
    from cmod.custom import measure as M
    v = M.makefile_vars(os.path.join(ctx['spec']['root'], 'Makefile'))
    g = model['graph']
    cflags = '-mmcu=$(MCU) -DF_CPU=$(F_CPU) %s' % ' '.join(x for x in v['CFLAGS'].split() if not x.startswith(('-mmcu=', '-DF_CPU=')))
    if pin_config:
        cflags += ' -DPOLARI_PIN_CONFIG=1'
    return '\n'.join([
        '# Makefile — GENERATED by %s from the no-code graph %s (sha256 %s).' % (GENERATOR, g['name'], model['sha']),
        '# Regenerate with `pol cmod render %s`. The flags are the %s template Makefile\'s own; SRCS lists the atom' % (g['name'], g['project']),
        '# files + the glue. `make` alone builds firmware.hex (no Polari in the loop).', '#',
        '#   make            # firmware.elf + firmware.hex + the avr-size line', '#   make size',
        'MCU   = %s' % v.get('MCU', 'atmega328p'), 'F_CPU = %s' % v.get('F_CPU', '16000000UL'), 'CC    = %s' % v.get('CC', 'avr-gcc'),
        'CFLAGS = %s' % cflags,
        'LDFLAGS = %s' % v.get('LDFLAGS', ''), 'SRCS = %s' % ' '.join(sources), 'HDRS = %s' % ' '.join(sorted(
            f for f in ctx['files_out'] if f.endswith('.h'))), '',
        'all: firmware.hex size', '', 'firmware.elf: $(SRCS) $(HDRS)', '\t$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(SRCS)', '',
        'firmware.hex: firmware.elf', '\tavr-objcopy -O ihex -R .eeprom $< $@', '', 'size: firmware.elf', '\tavr-size -A firmware.elf', '',
        'clean:', '\trm -f firmware.elf firmware.hex', '', '.PHONY: all size clean', ''])
