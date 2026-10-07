"""In-process live-boot PROBE of cmod-0 (C_MODULARIZATION_PLAN.md §10): boot the REAL polariServer with cmod (+ board and what
board needs) enabled and hit its routes — the guarded imports, defClassList, the seeds (the UNO's committed polari-firmware.json
projected into rows), the page seed and the routes outside the selftest. With --engines (the board engines seam must resolve):
the BYTE-IDENTICAL proof — every shipped UNO variant built from the annotated template AND from a copy with every POLARI_NODE
annotation stripped, through board's own gen + build; the .hex shas must match. cmod-1 (--engines): the REAL behaviour
equivalence — the committed rendered graph built by make alone and the hand-written uno-sim-rig run in the simavr twin with the
same stimulus, frames compared field by field — plus a NEGATIVE CONTROL (the same graph with the status rule at 500 ms instead
of 1000, rendered to a scratch dir) that the comparison must catch. Without the engine image those checks SKIP, saying so.
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/cmod_liveboot_probe.py [--engines]
"""
import json
import os
import shutil
import sys
import tempfile
os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board,cmod,hwnocode'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


def byte_identical():
    """Annotated template vs the same template with every annotation line removed → the same .hex for every variant."""
    from board.custom import gen, build
    from board.custom import board_engines as be
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    from cmod.custom.annotation import find
    if be.resolve('avr-gcc')['how'] == 'refused':
        print('SKIP: no avr-gcc through the board engines seam — the byte-identical proof needs the engine')
        return
    tpl = gen.TEMPLATES['arduino-uno-r3']
    stripped = tempfile.mkdtemp(prefix='cmod-stripped-')
    shutil.copytree(tpl, stripped, dirs_exist_ok=True)
    removed = 0
    for d, _dirs, files in os.walk(stripped):
        for f in files:
            if f.endswith('.c'):
                p = os.path.join(d, f)
                lines = open(p).read().split('\n')
                drop = set()
                for a in find(open(p).read(), f):   # the annotation's own line span (strings may hold parentheses)
                    drop |= set(range(a['line'] - 1, a['end_line']))
                    removed += 1
                open(p, 'w').write('\n'.join(x for i, x in enumerate(lines) if i not in drop))
    check('the stripped copy lost all 12 annotations (and nothing else matched)', removed == 12, removed)
    shas = {}
    for which, root in (('annotated', tpl), ('stripped', stripped)):
        gen.TEMPLATES['arduino-uno-r3'] = root
        try:
            for v in SEED_FIRMWARE_VARIANTS:
                if v['name'] == 'uno-pair':
                    continue
                w = tempfile.mkdtemp(prefix='cmod-bi-')
                gen.gen('uno', work=w, variant=v['name'])
                r = build.build('uno', work=w)
                shas.setdefault(v['name'], {})[which] = r['artifact_sha256']
                shutil.rmtree(w, ignore_errors=True)
        finally:
            gen.TEMPLATES['arduino-uno-r3'] = tpl
    for name, s in shas.items():
        check('byte-identical .hex with and without the annotations: %s (%s)' % (name, s.get('annotated', '')[:16]),
              s.get('annotated') and s.get('annotated') == s.get('stripped'), s)
    shutil.rmtree(stripped, ignore_errors=True)


from falcon import testing  # noqa: E402
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
from board_probe_boot import boot  # noqa: E402
manager = boot(FRAMEWORK)
client = testing.TestClient(manager.polServer.falconServer)
tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
for cls in ('CProject', 'CModule', 'CFunctionAtom', 'CPort', 'CGraph', 'CGraphNode', 'CGraphEdge', 'CGlueBuild',
           'TargetDefinition', 'CapabilityDefinition', 'CapabilityInstance'):
    check('class %s is typed after boot' % cls, cls in typed)
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
m = json.load(open(os.path.join(FRAMEWORK, 'modules', 'board', 'custom', 'firmware', 'uno', 'polari-firmware.json')))
check('seeded from the committed manifest: 1 project, 7 modules, 34 atoms, %d ports; cmod-1: 1 graph, 18 nodes, 15 edges, 1 glue build; '
      'demo-4: 16 targets, 3 capabilities (+2 hw priorities P1), 5 instances' % m['counts']['ports'],
      tuple(n(c) for c in ('CProject', 'CModule', 'CFunctionAtom', 'CPort', 'CGraph', 'CGraphNode', 'CGraphEdge', 'CGlueBuild',
                           'TargetDefinition', 'CapabilityDefinition', 'CapabilityInstance'))
      == (1, 7, 34, m['counts']['ports'], 1, 18, 15, 1, 16, 3, 5),
      tuple(n(c) for c in ('CProject', 'CModule', 'CFunctionAtom', 'CPort', 'CGraph', 'CGraphNode', 'CGraphEdge', 'CGlueBuild',
                           'TargetDefinition', 'CapabilityDefinition', 'CapabilityInstance')))
r = client.simulate_get('/api/cmod')
check('GET /api/cmod → the uno project, 34 atoms, pycparser in this process', r.status_code == 200 and r.json['projects'][0]['name'] == 'uno'
      and r.json['atoms'] == 34 and r.json['parser']['engine'] == 'pycparser', r.text[:200])
r = client.simulate_get('/api/cmod/atoms/hal_millis')
check('GET /api/cmod/atoms/hal_millis → isr_safe yes, out(return) [ms], text 24 B shipped', r.status_code == 200 and r.json['atom']['isr_safe'] == 'yes'
      and r.json['ports'][0]['unit'] == 'ms' and r.json['atom']['text_bytes'] == 24, r.text[:300])
r = client.simulate_get('/api/cmod/atoms', params={'project': 'uno', 'kind': 'isr'})
check('GET /api/cmod/atoms?project=uno&kind=isr → USART_RX_vect, TIMER2_COMPA_vect, INT0_vect', r.status_code == 200
      and sorted(a['isr_vector'] for a in r.json['atoms']) == ['INT0_vect', 'TIMER2_COMPA_vect', 'USART_RX_vect'], r.text[:200])
r = client.simulate_get('/api/cmod/ports', params={'atom': 'uno:hal.hal_adc_read'})
check('GET /api/cmod/ports?atom=uno:hal.hal_adc_read → channel (in) + return (out, count)', r.status_code == 200
      and [(p['port'], p['direction'], p['unit']) for p in r.json['ports']] == [('channel', 'in', ''), ('return', 'out', 'count')], r.text[:200])
r = client.simulate_get('/api/cmod/engines')
check('GET /api/cmod/engines → avr-gcc / avr-nm / make placement (nothing run)', r.status_code == 200 and set(r.json['engines']) == {'avr-gcc', 'avr-nm', 'make'})
r = client.simulate_get('/api/cmod/projects/uno/drift')
check('GET /api/cmod/projects/uno/drift → the committed manifest matches the sources', r.status_code == 200 and r.json['stale'] is False, r.text[:200])
r = client.simulate_get('/api/cmod/projects/nope/drift')
check('drift of an unknown project → 404 in plain words', r.status_code == 404 and 'no template project' in r.json['error'])
pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'c-atoms']
check('/display/c-atoms is seeded with ten configured surfaces (cmod-1 added graphs, nodes, edges, glue builds; demo-4 the used-by link)',
      len(pages) == 1 and sum(len(row['items']) for row in json.loads(pages[0].definition)['rows']) == 10, len(pages))
r = client.simulate_get('/api/cmod/graphs')
check('GET /api/cmod/graphs → uno-sim-rig-graph, status proven', r.status_code == 200 and [g['name'] for g in r.json['graphs']] == ['uno-sim-rig-graph']
      and r.json['graphs'][0]['status'] == 'proven', r.text[:300])
r = client.simulate_get('/api/cmod/graphs/uno-sim-rig-graph')
check('GET /api/cmod/graphs/uno-sim-rig-graph → 18 nodes, 15 edges, the glue build (equivalent)', r.status_code == 200 and len(r.json['nodes']) == 18
      and len(r.json['edges']) == 15 and r.json['glue_builds'][0]['equivalent'] is True, r.text[:300])
r = client.simulate_get('/api/cmod/graphs/uno-sim-rig-graph/render')
rec = json.load(open(os.path.join(FRAMEWORK, 'modules', 'cmod', 'custom', 'glue_builds', 'uno-sim-rig-graph.json')))
check('GET …/render renders FROM THE LIVE ROWS in memory: the same files sha as the committed record, nothing written, the cost before '
      'building', r.status_code == 200 and r.json['files_sha256'] == rec['files_sha256'] and r.json['unchanged'] is True
      and r.json['cost_before_building']['total_bytes'] == rec['cost_estimate']['total_bytes'], r.text[:300])
r = client.simulate_get('/api/cmod/graphs/uno-sim-rig-graph/diff')
check('GET …/diff → clean: the committed project is the render of the live graph', r.status_code == 200 and r.json['clean'] is True, r.text[:300])
r = client.simulate_get('/api/cmod/graphs/nope')
check('an unknown graph → 404 in plain words', r.status_code == 404 and 'no graph' in r.json['error'])
comp = [c for c in (tables.get('GraphCompilerDefinition', {}) or {}).values() if getattr(c, 'name', '') == 'cmod-glue']
check('the cmod-glue GraphCompilerDefinition row is seeded (the existing compiler seam)', len(comp) == 1, len(comp))
check('board still boots beside it: the five seeded FirmwareVariants', n('FirmwareVariant') >= 5, n('FirmwareVariant'))

# ------------------------------------------------------------------ demo-4: /display/c-canvas opens the DisplayDefinition
# then GETs the exact graph payload the canvas loads — the liveboot proof that the page's own seeded input (not a
# hand-picked name here) really resolves to a live, working endpoint.
canvas_pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'c-canvas']
check('/display/c-canvas DisplayDefinition is seeded, canvas panel first', len(canvas_pages) == 1
      and json.loads(canvas_pages[0].definition)['rows'][0]['items'][0]['componentProps']['componentName'] == 'c-graph-canvas-panel',
      len(canvas_pages))
canvas_def = json.loads(canvas_pages[0].definition)
canvas_graph = canvas_def['rows'][0]['items'][0]['componentProps']['inputs']['graph']
r = client.simulate_get('/api/cmod/graphs/%s' % canvas_graph)
check('GETs the graph payload the canvas loads for its own seeded input (%s): nodes, edges, targets, used_by all present'
      % canvas_graph, r.status_code == 200 and r.json['graph']['name'] == canvas_graph and len(r.json['nodes']) == 18
      and len(r.json['edges']) == 15 and len(r.json['targets']) == 16 and isinstance(r.json['used_by'], list), r.text[:300])
check('the REVERSE link resolves live: used_by names uno-temp-split (hwnocode booted beside cmod)',
      any(h['name'] == 'uno-temp-split' for h in r.json['used_by']), r.json['used_by'])
hs = [h for h in (tables.get('HardwareSolution', {}) or {}).values() if h.name == 'uno-temp-split']
check('the FORWARD link: HardwareSolution.cgraph names this same graph', len(hs) == 1 and hs[0].cgraph == canvas_graph,
      hs[0].cgraph if hs else None)
r = client.simulate_get('/api/cmod/graphs/%s/targets' % canvas_graph)
check('GET …/targets → the ADC pin target + the temp_c memory-field target are both present',
      r.status_code == 200 and {'adc.channel', 'temp.return'} <= {t['port_ref'] for t in r.json['targets']}, r.text[:300])
r = client.simulate_get('/api/cmod/capabilities')
demo4_cap = next((c for c in (r.json.get('capabilities') or []) if c['name'].endswith('temperature-sensor-solution')), None)
check('GET /api/cmod/capabilities → "temperature sensor solution" with its two instances (+2 hw priorities P1 capabilities)',
      r.status_code == 200 and len(r.json['capabilities']) == 3 and demo4_cap is not None and len(demo4_cap['instances']) == 2, r.text[:300])

# hw priorities P1 (AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4): the new, widened-field CapabilityDefinition doors
r = client.simulate_get('/api/capabilities')
names = sorted(x['name'] for x in (r.json.get('capabilities') or []))
check('GET /api/capabilities → the 3 CapabilityDefinition rows, status re-derived (never hand-set)',
      r.status_code == 200 and names == sorted(['uno-sim-rig-graph:temperature-sensor-solution', 'temp-sensor-to-os', 'blink-on-command'])
      and all(x['status'] in ('planned', 'proven-on-twin', 'proven-on-hardware', 'failing') for x in r.json['capabilities']), r.text[:300])
r = client.simulate_get('/api/capabilities/temp-sensor-to-os')
check('GET /api/capabilities/temp-sensor-to-os → tasks by runtime, targets with their RegisterAssignment state, validator ok',
      r.status_code == 200 and r.json['validation']['ok']
      and r.json['tasks_by_runtime']['c-device'] and all(t['registered'] for t in r.json['targets']), r.text[:300])
r = client.simulate_get('/api/capabilities/no-such-capability')
check('GET /api/capabilities/<missing> → 404, named', r.status_code == 404)
hw_pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'hardware-solutions']
check('/display/hardware-solutions embeds the SAME canvas component on its own cgraph (the forward link opened in place)',
      len(hw_pages) == 1 and any(it['componentProps']['componentName'] == 'c-graph-canvas-panel'
                                 for row in json.loads(hw_pages[0].definition)['rows'] for it in row['items']))

# ------------------------------------------------------------------ fs-1 item 2/4: /display/firmware-solutions opens with
# the new three-part canvas FIRST (the described tables below it are the same rows, read-only confirmation), and the
# installer-page fallback door is live.
fw_pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'firmware-solutions']
check('/display/firmware-solutions DisplayDefinition is seeded, firmware-solution-panel first', len(fw_pages) == 1
      and json.loads(fw_pages[0].definition)['rows'][0]['items'][0]['componentProps']['componentName'] == 'firmware-solution-panel',
      len(fw_pages))
r = client.simulate_get('/api/firmware/solutions/uno-sim-rig')
check('GET /api/firmware/solutions/uno-sim-rig → the real shape fs-1\'s panel reads: schedule (4 lanes present), assignments, validation',
      r.status_code == 200 and r.json['solution']['name'] == 'uno-sim-rig'
      and {'init', 'isr', 'loop'} <= {s['lane'] for s in r.json['schedule']}
      and any(a['status'] == 'bound' for a in r.json['assignments']) and 'ok' in r.json['validation'], r.text[:300])
r = client.simulate_get('/api/firmware/solutions/for-installer')
check('GET /api/firmware/solutions/for-installer (fs-1 item 4 fallback) → {ok, rows} with the documented pol firmware run command, no JSON wall',
      r.status_code == 200 and r.json['ok'] and any(row['name'] == 'uno-sim-rig'
      and row['run_command'] == 'pol firmware run uno-sim-rig --mode digital-twin' for row in r.json['rows']), r.text[:300])
fi_pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'firmware-installer']
check('/display/firmware-installer carries the Firmware Solutions fallback table (data_path to the for-installer door)',
      len(fi_pages) == 1 and any(it['componentProps']['inputs'].get('dataPath') == '/api/firmware/solutions/for-installer'
                                 for row in json.loads(fi_pages[0].definition)['rows'] for it in row['items']))

# ------------------------------------------------------------------ fs-2a (his ruling 2026-10-06): the two new doors,
# live over the REAL boot — GET /api/board/<board>/pins/<pin> and GET /api/firmware/solutions/<name>/tasks/<task>/valid-targets
r = client.simulate_get('/api/board/arduino-uno-r3/pins/D13')
check('GET /api/board/arduino-uno-r3/pins/D13 (live) → PB5, register port B, SCK/PCINT5 alternate functions, registered_tasks carries led',
      r.status_code == 200 and r.json['soc_pin'] == 'PB5' and r.json['register']['port'] == 'B'
      and {f['function'] for f in r.json['alternate_functions']} == {'SCK', 'PCINT5'}
      and any(t['task'] == 'led' for t in r.json['registered_tasks']), r.text[:400])
r = client.simulate_get('/api/board/arduino-uno-r3/pins/A0')
check('GET /api/board/arduino-uno-r3/pins/A0 (live) → PC0, ADC0 alternate function, registered_tasks carries adc',
      r.status_code == 200 and r.json['soc_pin'] == 'PC0' and 'ADC0' in {f['function'] for f in r.json['alternate_functions']}
      and any(t['task'] == 'adc' for t in r.json['registered_tasks']), r.text[:400])
r = client.simulate_get('/api/board/arduino-uno-r3/pins/no-such-pin')
check('an unknown pin → 404 in plain words', r.status_code == 404 and 'no pin' in r.json['error'])
r = client.simulate_get('/api/firmware/solutions/uno-sim-rig/tasks/adc/valid-targets')
check('GET .../tasks/adc/valid-targets (live) → analog-in, A0-A5 valid exactly',
      r.status_code == 200 and r.json['kind'] == 'analog-in'
      and sorted(p['pin'] for p in r.json['pins'] if p['verdict'] == 'valid') == ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], r.text[:400])
r = client.simulate_get('/api/firmware/solutions/uno-sim-rig/tasks/pwm/valid-targets')
check('GET .../tasks/pwm/valid-targets (live) → pwm-out, the six timer pins valid, D13 invalid',
      r.status_code == 200 and r.json['kind'] == 'pwm-out'
      and sorted(p['pin'] for p in r.json['pins'] if p['verdict'] == 'valid') == ['D10', 'D11', 'D3', 'D5', 'D6', 'D9']
      and next(p for p in r.json['pins'] if p['pin'] == 'D13')['verdict'] == 'invalid', r.text[:400])
r = client.simulate_post('/api/firmware/solutions/uno-sim-rig/assign', json={'task': 'pwm', 'lives_on': 'arduino-uno-r3:D13'})
check('POST .../assign (live) REFUSES PWM onto D13, 422, naming the reason', r.status_code == 422 and r.json.get('refused')
      and 'Output Compare' in r.json.get('error', ''), r.text[:400])
r = client.simulate_get('/api/board/target-compat')
check('GET /api/board/target-compat (live) → one row per TASK_KINDS, each cited', r.status_code == 200
      and len(r.json['rows']) >= 13 and all(row['source_url'].startswith('http') for row in r.json['rows']), r.text[:300])


def equivalence():
    """The REAL twin equivalence of the committed render + a negative control the comparison must catch."""
    from board.custom import board_engines as be
    from board.custom.engine_run import EngineRefused
    from cmod.custom import glue as GL, glue_build as GB
    from cmod.custom.graph_seed import seed_graph
    if be.resolve('avr-twin')['how'] == 'refused' or be.resolve('avr-gcc')['how'] == 'refused':
        print('SKIP: no avr-gcc / avr-twin through the board engines seam — the equivalence proof needs the engine image')
        return
    # cmod's `make alone` proof runs ONLY where avr-gcc runs LOCALLY (a local binary or the
    # local board-engines image) — a remote BOARD_ENGINES_URL worker runs single engines, not
    # make, and refuses honestly (cmod_engines.run('make') -> EngineRefused). That refusal is
    # correct by design (the worker was never meant to run make), not a bug to work around —
    # the probe reports it as a named SKIP instead of crashing.
    try:
        p = GB.prove('uno-sim-rig-graph', write=False)
    except EngineRefused as e:
        print('SKIP: make-alone refused (%s) — needs a LOCAL avr-gcc binary or the local prf-board-engines image '
              '(unset BOARD_ENGINES_URL, or run where the image is), not a remote worker' % e)
        return
    check('EQUIVALENT on the twin: the rendered glue (make alone) vs the hand-written uno-sim-rig, same stimulus — %d frames identical on %s'
          % (p['frames_compared'], ', '.join(p['fields_compared'])), p['equivalent'] and p['frames_compared'] >= 30 and p['frames_hand'] == p['frames_glue'],
          p['differences'][:3])
    check('…raw UART streams identical, frame tx cycles identical (delta %s..%s), the commands took effect (first commanded frame %s)'
          % (p['cycles']['frame_tx_cycle_delta_min'], p['cycles']['frame_tx_cycle_delta_max'], p['first_commanded_frame']),
          p['raw_uart_identical'] and p['cycles']['frame_tx_cycle_delta_max'] == 0 and p['first_commanded_frame'] is not None)
    check('…sizes recorded for both: hand .text %d .data %d .bss %d, glue .text %d .data %d .bss %d%s' % (
        p['reference']['size_text'], p['reference']['size_data'], p['reference']['size_bss'], p['glue']['size_text'], p['glue']['size_data'],
        p['glue']['size_bss'], ' (byte-identical .hex)' if p['hex_identical'] else ''), p['glue']['size_text'] > 0 and p['reference']['size_text'] > 0)
    rows = seed_graph('uno-sim-rig-graph')
    rule = next(x for x in rows['nodes'] if x['instance'] == 'boot_ok')
    rule['params'] = rule['params'].replace('after_ms=1000', 'after_ms=500')
    tmp = tempfile.mkdtemp(prefix='cmod-negative-')
    try:
        GL.render('uno-sim-rig-graph', rows=rows, out_dir=tmp)
        q = GB.prove_dir(tmp, 'uno-sim-rig')
        check('NEGATIVE CONTROL: the same graph with the status rule at 500 ms → NOT equivalent, and the differences are the status field '
              '(%d differences, e.g. %s)' % (q['n_differences'], (q['differences'] or ['-'])[0]), not q['equivalent']
              and all(' status:' in x for x in q['differences']), q['differences'][:3])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if '--engines' in sys.argv:
    byte_identical()
    equivalence()
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
