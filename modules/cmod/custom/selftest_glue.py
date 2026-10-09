"""
@module cmod.custom.selftest_glue

The cmod-1 half of cmod_selftest (C_MODULARIZATION_PLAN.md §10 cmod-1): the seeded graph → a deterministic render equal to the
committed project; what the glue contains; the REFUSALS (a data cycle, an unbound in port, a Polari-type mismatch, free C in a
binding, an unknown atom, an ISR as a node, a calls edge the C does not have, a field written after its frame); render
idempotence and the hand-edit guard; the Makefile building with a FAKE avr-gcc (no engine); the compiler seam; the committed
glue-build record (the twin proof) and its rows; the cost estimate. The real twin equivalence is the probe's
(tests/cmod_liveboot_probe.py --engines).
"""
import copy
import os
import shutil
import stat
import subprocess
import tempfile

G = 'uno-sim-rig-graph'


def _rows():
    from cmod.custom.graph_seed import seed_graph
    return copy.deepcopy(seed_graph(G))


def _node(rows, inst):
    return next(n for n in rows['nodes'] if n['instance'] == inst)


def graph_parts(check):

    def render_deterministic():
        from cmod.custom import glue as GL
        from cmod.custom import graph as GR
        a = GL.render(G, write=False)
        b = GL.render(G, write=False)
        check('the seeded graph resolves and renders deterministically: two renders → the same bytes (files sha %s)' % a['files_sha256'][:12],
              a['texts'] == b['texts'] and a['files_sha256'] == b['files_sha256'])
        rec = GL.load_record(G)
        check('the graph\'s sha = the canonical rows; the committed record names the same graph sha and the same files',
              rec and rec['graph_sha256'] == GR.graph_sha(_rows()) == a['sha'] and rec['files'] == a['files'], (rec or {}).get('graph_sha256'))
        d = GL.diff(G)
        check('the committed project (cmod/custom/graphs/uno-sim-rig-graph) IS the render: pol cmod diff is clean (no stale, hand-edited, '
              'added or removed file)', d['clean'], {k: d[k] for k in ('stale', 'hand_edited', 'added', 'removed')})
        files = sorted(a['files'])
        check('the rendered project = polari_graph.c/.h + Makefile + the atom files (hal.c/hal.h verbatim) + board_config.h + the class header '
              '+ the GENERATED pin_config.h/.c (ucd-0b, uno-sim-rig-graph has a FirmwareSolution) — only .c/.h + Makefile (RULE 2)',
              files == ['Makefile', 'board_config.h', 'hal.c', 'hal.h', 'pin_config.c', 'pin_config.h', 'polari_graph.c', 'polari_graph.h',
                        'simrigstate_packets.h'], files)
        from cmod.custom import projects as P
        root = P.resolve('uno')['root']
        check('hal.c / hal.h are copied VERBATIM (byte-identical to the template)',
              all(a['texts'][f] == open(os.path.join(root, f), 'rb').read() for f in ('hal.c', 'hal.h')))
        c = a['texts']['polari_graph.c'].decode()
        check('every generated file names the graph, its sha and `pol cmod render` in its header comment',
              all(G in a['texts'][f].decode()[:600] and a['sha'] in a['texts'][f].decode()[:600] and 'pol cmod render %s' % G in a['texts'][f].decode()[:600]
                  for f in ('polari_graph.c', 'polari_graph.h', 'Makefile')))
        calls = ['hal_usart_init();', 'hal_tick_init();', 'hal_led_init();', 'hal_pwm_init();', 'hal_adc_init();', 'while (hal_rx_pop(&rx_pop_b))',
                 'apply_command(&rx);', 'hal_millis();', 'hal_adc_read(ADC_CHANNEL);', 'sensor_value(adc_return);', 'hal_usart_send(frame_wire, frame_length);']
        check('polari_graph.c calls the atoms BY NAME in graph order (init → sei → on-rx drain → on-command → clock → tick: adc → temp → '
              'rule → frame → send)', all(x in c for x in calls) and [c.index(x) for x in calls] == sorted(c.index(x) for x in calls)
              and c.index('sei();') < c.index('for (;;)'), [x for x in calls if x not in c])
        check('the tick is a wrap-safe compare on the uint32_t clock; uptime_ms is sampled ON the tick (inside its block), the status rule '
              'and the frame follow the field writes', '(int32_t)(clock_return - telemetry_next_ms) >= 0' in c
              and c.index('telemetry_next_ms += TELEMETRY_MS') < c.index('state.uptime_ms = (int64_t)clock_return') < c.index('state.temp_c = temp_return')
              < c.index('rule boot_ok') < c.index('SimRigState_frame('))
        check('the app atoms sensor_value + apply_command are copied VERBATIM from apps/sim_rig.c with their POLARI_NODE line and enclosing '
              '#if FEATURE_ADC (an app file holds a main(), so it is never compiled whole)',
              '#if FEATURE_ADC\nPOLARI_NODE(sensor_value' in c and 'static void apply_command(const polari_rx_t *r)' in c
              and open(os.path.join(root, 'apps', 'sim_rig.c')).read().count('state.status = SIMRIGSTATE_STATUS_COMMANDED;') == 1)
        check('no runtime walks a table: no Python, no interpreter — main() is plain statements (no function pointers, no graph data in C)',
              'python' not in c.split('int main(void)')[1].lower() and '(*' not in c.split('int main(void)')[1])
        gc = a['glue_contains']
        check('what the glue OWNS is listed (main + scheduler, init order + sei, the class instance, the parser, the tick, field writes, '
              'the status rule, the frame, the copied app atoms) — %d items' % len(gc),
              len(gc) == 9 and gc[0].startswith('main()') and any('rule `boot_ok`' in x for x in gc) and any('copied verbatim' in x for x in gc), gc)

    def refusals():
        from cmod.custom import glue as GL
        from cmod.custom.graph import GraphRefused
        ctx = GL.context(_rows()['graph'])

        def refused(label, mutate, needle):
            rows = _rows()
            mutate(rows)
            try:
                GL.render_files(rows, ctx)
                check('refused: %s' % label, False, 'rendered without complaint')
            except (GraphRefused, GL.GlueRefused) as e:
                check('refused: %s — "%s"' % (label, str(e)[:110]), needle in str(e), str(e))

        def cycle(r):
            _node(r, 'adc')['bindings'] = ''
            r['nodes'].append(dict(_node(r, 'adc'), name='%s:adc2' % G, instance='adc2', order=22))
            r['edges'] += [dict(r['edges'][8], name='%s#20' % G, kind='data', from_node='adc', from_port='return', to_node='adc2', to_port='channel', order=20),
                           dict(r['edges'][8], name='%s#21' % G, kind='data', from_node='adc2', from_port='return', to_node='adc', to_port='channel', order=21)]
        refused('a cycle in the data edges (adc → adc2 → adc)', cycle, 'cycle')
        refused('an unbound in port (hal_adc_read.channel with its binding removed)', lambda r: _node(r, 'adc').update(bindings=''), 'unbound')

        def mismatch(r):
            _node(r, 'adc')['bindings'] = ''
            r['edges'].append(dict(r['edges'][8], name='%s#22' % G, from_node='temp', from_port='return', to_node='adc', to_port='channel', order=30))
        refused('a Polari-type mismatch (sensor_value → double into hal_adc_read.channel → int64)', mismatch, 'Polari types differ')
        refused('free C in a binding (channel=ADC_CHANNEL+1)', lambda r: _node(r, 'adc').update(bindings='channel=ADC_CHANNEL+1'), 'never carries free C')
        refused('an unknown atom', lambda r: _node(r, 'adc').update(atom='uno:hal.hal_adc_reed'), 'no atom')
        refused('an ISR as a node', lambda r: _node(r, 'clock').update(atom='uno:hal.TIMER2_COMPA_vect'), 'ISR')
        refused('an atom not compiled in the base configuration (hal_presses: HAL_INT0 only)',
                lambda r: _node(r, 'clock').update(atom='uno:hal.hal_presses'), 'not compiled in the base configuration')
        refused('a calls edge the C does not have (apply_command never calls hal_adc_read)',
                lambda r: (_node(r, 'pwm').update(atom='uno:hal.hal_adc_read'), r['edges'][3].update(to_port='channel')), 'does not call')
        refused('a field written after the frame that sends it (frame ordered before temp)', lambda r: _node(r, 'frame').update(order=22),
                'write after the frame')
        refused('an in port wired twice (send.n from the frame AND from the clock)',
                lambda r: r['edges'].append(dict(r['edges'][14], name='%s#23' % G, from_node='clock', from_port='return', order=40)), 'already bound')
        rows = _rows()
        rows['nodes'] = [n for n in rows['nodes'] if n['instance'] != 'adc_init']
        m = GL.render_files(rows, ctx)[0]
        check('ADVICE, not a refusal: without adc_init the generator says hal_adc_read touches the ADC no init node sets up',
              any('adc (hal_adc_read) touches ADC' in x for x in m['advice']), m['advice'])

    def idempotent_and_hand_edit():
        from cmod.custom import glue as GL
        tmp = tempfile.mkdtemp(prefix='cmod-glue-st-')
        saved = GL.RECORDS
        try:
            GL.RECORDS = os.path.join(tmp, 'records')
            rows = _rows()
            rows['graph']['generated_project'] = os.path.join(tmp, 'proj')   # an absolute path: project_dir joins it as is
            r1 = GL.render(G, rows=rows)
            r2 = GL.render(G, rows=rows)
            check('render writes the 9 files INTO the project (incl. the GENERATED pin_config.h/.c, ucd-0b); a second render writes nothing (idempotent)',
                  len(r1['written']) == 9 and r2['unchanged'] and not r2['written'], (r1['written'], r2['written']))
            p = os.path.join(tmp, 'proj', 'polari_graph.c')
            open(p, 'a').write('/* a person\'s edit */\n')
            d = GL.diff(G, rows=rows)
            check('a hand edit shows in pol cmod diff (hand_edited + a unified diff), the graph itself unchanged',
                  d['hand_edited'] == ['polari_graph.c'] and not d['graph_changed'] and 'a person' in d['diffs']['polari_graph.c'], d['hand_edited'])
            try:
                GL.render(G, rows=rows)
                check('a render refuses to overwrite the hand edit (a person\'s C wins)', False)
            except GL.GlueRefused as e:
                check('a render refuses to overwrite the hand edit (a person\'s C wins) — "%s"' % str(e)[:80], 'hand-edited' in str(e))
            r3 = GL.render(G, rows=rows, force=True)
            check('…and --force restores the render (the one file rewritten)', r3['written'] == ['polari_graph.c'] and GL.diff(G, rows=rows)['clean'])
            _make_with_fake_avr_gcc(check, os.path.join(tmp, 'proj'), tmp)
        finally:
            GL.RECORDS = saved
            shutil.rmtree(tmp, ignore_errors=True)

    def compiler_seam():
        from types import SimpleNamespace
        from polariNoCode.graph_compilers import SEED_GRAPH_COMPILERS, compile_with
        from cmod.custom import glue as GL
        row = [r for r in SEED_GRAPH_COMPILERS if r['name'] == 'cmod-glue']
        check('a GraphCompilerDefinition row `cmod-glue` (domain cmod) registers the generator on the existing compiler seam',
              len(row) == 1 and row[0]['compiler_ref'] == 'cmod.custom.glue:compile_graph')
        rows = _rows()
        res = compile_with(SimpleNamespace(name='cmod-glue', enabled=True, compiler_ref=row[0]['compiler_ref']),
                           {'CGraph': [rows['graph']], 'CGraphNode': rows['nodes'], 'CGraphEdge': rows['edges']})
        r = GL.render(G, write=False)
        check('compile_with(cmod-glue) → artifacts only (definition None: a C graph never runs in the engine), the same files and shas as '
              'pol cmod render', res['definition'] is None and {a['path']: a['sha256'] for a in res['artifacts']} == r['files'])

    def record_and_rows():
        from cmod.custom import glue as GL
        rec = GL.load_record(G)
        p, b = rec.get('proof') or {}, rec.get('build') or {}
        check('the committed glue-build record: make alone built it (%s), .text %s .data %s .bss %s' % (
            b.get('built_by'), b.get('size_text'), b.get('size_data'), b.get('size_bss')), b.get('ok') and b.get('size_text', 0) > 0
            and len(b.get('hex_sha256', '')) == 64)
        check('…the twin proof: EQUIVALENT — %s frames, identical field by field (%s); raw UART identical' % (
            p.get('frames_compared'), ', '.join(p.get('fields_compared') or [])), p.get('equivalent') and p.get('frames_compared', 0) >= 30
            and not p.get('differences') and p.get('raw_uart_identical') and 'temp_c' in p.get('fields_compared', []))
        check('…the stimulus is recorded (seconds, seed, ADC0 ramp, the 3 commands by cycle and sha) and the commands took effect '
              '(a commanded frame with led_on true and pwm_duty 42, a later one with pwm_duty clamped to 100)',
              len(p['stimulus']['commands']) == 3 and len(p['stimulus']['command_frames_sha256']) == 3
              and any(s['status'] == 'commanded' and s['led_on'] and s['pwm_duty'] == 42 for s in p['samples'])
              and p['samples'][-1]['pwm_duty'] == 100)
        check('…the hand-written build it replaces = board\'s own uno-sim-rig .hex (4188f6ae…), sizes recorded for both',
              p['reference']['hex_sha256'].startswith('4188f6ae7d65bfc7') and p['reference']['size_text'] > 0 and p['glue']['size_text'] > 0)
        check('…the record still matches the committed render (proof.files_sha256 = files_sha256): nothing proven is stale',
              p.get('files_sha256') == rec['files_sha256'] and b.get('files_sha256') == rec['files_sha256'])
        conf = rec.get('conformed') or {}
        check('conform read the rendered project back as a PLAIN project: its polari-firmware.json is committed, the glue\'s own atoms '
              '(polari_graph.main + the two copied) beside the HAL\'s', conf.get('atoms', 0) > 10 and 'polari_graph.main' in conf.get('glue_atoms', [])
              and os.path.isfile(os.path.join(os.path.dirname(GL.RECORDS), 'graphs', G, 'polari-firmware.json')), conf)
        from cmod.custom.rows import graph_rows
        gr = graph_rows()
        g = gr['CGraph'][0]
        check('rows: CGraph status proven (the record matches the current graph), 18 nodes, 15 edges, 13 atoms; one CGlueBuild row, equivalent',
              g['status'] == 'proven' and (g['node_count'], g['edge_count'], g['atom_count']) == (18, 15, 13) and len(gr['CGlueBuild']) == 1
              and gr['CGlueBuild'][0]['equivalent'], (g['status'], g['node_count'], g['edge_count'], g['atom_count']))
        nodes = {n['instance']: n for n in gr['CGraphNode']}
        check('node rows carry the atom\'s derived ports / cost / ISR-safety (adc: in channel, out return; 36 B as a node)',
              'in channel:int64' in nodes['adc']['ports_summary'] and nodes['adc']['cost_bytes'] == 36 and nodes['adc']['isr_safe'] == 'yes')

    def cost_estimate():
        from cmod.custom import glue as GL
        r = GL.render(G, write=False)
        c = r['cost']
        rec = GL.load_record(G)
        check('the cost BEFORE building = Σ atoms as nodes + the ISRs they share globals with + the replaced main as the glue reference '
              '(%d B), the same figure the record carries' % c['total_bytes'], c['total_bytes'] == sum(p[1] for p in c['parts'])
              and c['total_bytes'] == rec['cost_estimate']['total_bytes'] and {'hal.USART_RX_vect', 'hal.TIMER2_COMPA_vect'} <= {p[0] for p in c['parts']})
        b = rec.get('build') or {}
        e = b.get('estimate_minus_attributable') or {}
        # ucd-0b: a graph with a FirmwareSolution's GENERATED pin_config.c adds ONE named, measured, fixed-size call
        # (`pin_config_init();`) into the glue's own main() that the hand-written reference main() it is compared
        # against never had — the SAME bytes the two atoms (hal_led_init/hal_pwm_init) now shrink by, just relocated
        # rather than vanished, so the reconciliation below NAMES that call-site overhead instead of papering over it.
        main_ref_declared = next((p[1] for p in c['parts'] if p[2].startswith('glue + library reference')), 0)
        main_shipped = (b.get('cost_measured_breakdown') or {}).get('main (glue + inlined atoms + inlined library)', 0)
        pin_config_call_overhead = max(0, main_shipped - main_ref_declared)
        check('…compared after the build: estimate − measured attributable = exactly the bytes the shipped build inlined or shrank (%s B)%s'
              % (e.get('bytes'), (' + the %d B pin_config_init() call site main() gained over the reference it is compared against (ucd-0b)'
                                  % pin_config_call_overhead) if pin_config_call_overhead else ''),
              e and e['bytes'] + pin_config_call_overhead == e['explained_bytes'] and b['cost_estimate_bytes'] >= b['cost_measured_attributable_bytes'], e)

    return (render_deterministic, refusals, idempotent_and_hand_edit, compiler_seam, record_and_rows, cost_estimate)


FAKE_GCC = '''#!/bin/sh
echo "$0 $*" >> "$FAKE_LOG"
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
for a in "$@"; do case "$a" in *.c) [ -f "$a" ] || { echo "missing $a" >&2; exit 1; } ;; esac; done
printf 'ELF' > "$out"
'''
FAKE_OBJCOPY = '#!/bin/sh\necho "$0 $*" >> "$FAKE_LOG"\nfor a in "$@"; do last="$a"; done\nprintf ":00000001FF\\n" > "$last"\n'
FAKE_SIZE = '#!/bin/sh\necho "$0 $*" >> "$FAKE_LOG"\nprintf "firmware.elf  :\\nsection  size  addr\\n.data  8  0\\n.text  4302  0\\n.bss  483  0\\n"\n'


def _make_with_fake_avr_gcc(check, proj, tmp):
    """`make` alone in the rendered project with a FAKE avr-gcc / avr-objcopy / avr-size on the PATH (no engine): the Makefile
    compiles exactly the listed sources with the template's flags and produces firmware.hex."""
    if not shutil.which('make'):
        print('  [SKIP] no host make — the probe builds the project with the real toolchain')
        return
    fake = os.path.join(tmp, 'fakebin')
    os.makedirs(fake)
    for name, body in (('avr-gcc', FAKE_GCC), ('avr-objcopy', FAKE_OBJCOPY), ('avr-size', FAKE_SIZE)):
        p = os.path.join(fake, name)
        open(p, 'w').write(body)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    log = os.path.join(tmp, 'fake.log')
    env = dict(os.environ, PATH=fake + os.pathsep + os.environ.get('PATH', ''), FAKE_LOG=log)
    r = subprocess.run(['make'], cwd=proj, env=env, capture_output=True, text=True, timeout=60)
    calls = open(log).read().splitlines() if os.path.isfile(log) else []
    gcc = [c for c in calls if '/avr-gcc ' in c]
    check('the generated Makefile builds with make alone (a FAKE avr-gcc on the PATH): one compile of exactly `hal.c pin_config.c '
          'polari_graph.c` with the template flags (-mmcu=atmega328p … -Werror … --gc-sections … -DPOLARI_PIN_CONFIG=1), then objcopy → '
          'firmware.hex and avr-size',
          r.returncode == 0 and len(gcc) == 1 and gcc[0].endswith('-o firmware.elf hal.c pin_config.c polari_graph.c') and '-mmcu=atmega328p' in gcc[0]
          and '-Werror' in gcc[0] and '-Wl,--gc-sections' in gcc[0] and '-DPOLARI_PIN_CONFIG=1' in gcc[0] and os.path.isfile(os.path.join(proj, 'firmware.hex'))
          and any('/avr-size -A firmware.elf' in c for c in calls), (r.returncode, r.stderr[-200:], calls))
    for f in ('firmware.elf', 'firmware.hex'):
        if os.path.isfile(os.path.join(proj, f)):
            os.remove(os.path.join(proj, f))
