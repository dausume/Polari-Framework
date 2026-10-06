"""
@module cmod.custom.selftest_uno

The UNO half of cmod_selftest (cmod-0, C_MODULARIZATION_PLAN.md §10): the template's atoms, the committed manifest vs a parse
now, the annotation macro expanding to nothing, the torn build's verdict, the cross-check against a real `cpp` when the host has
one, the register snapshot, the seeds / page / API over a fake manager, `manifests conform cmod`.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.dirname(os.path.dirname(HERE))
UNO = os.path.join(MODULES, 'board', 'custom', 'firmware', 'uno')
HAL_ATOMS = {'hal.hal_rx_pop', 'hal.hal_usart_init', 'hal.hal_usart_send', 'hal.hal_tick_init', 'hal.hal_millis', 'hal.hal_led_init', 'hal.hal_led',
             'hal.hal_pwm_init', 'hal.hal_pwm_apply', 'hal.hal_adc_init', 'hal.hal_adc_read', 'hal.hal_uart_errors', 'hal.hal_button_init',
             'hal.hal_presses', 'hal.hal_wdt_boot', 'hal.USART_RX_vect', 'hal.TIMER2_COMPA_vect', 'hal.INT0_vect'}
ANNOTATED = {'hal.hal_rx_pop', 'hal.hal_usart_send', 'hal.hal_millis', 'hal.hal_led', 'hal.hal_pwm_apply', 'hal.hal_adc_read',
             'apps/sim_rig.sensor_value', 'apps/sim_rig.apply_command', 'apps/echo.echo_command', 'apps/scenario_rig.crc8',
             'apps/scenario_rig.slot_read', 'apps/scenario_rig.ack_step'}


def uno_parts(check):
    state = {}

    def uno_atoms():
        from cmod.custom import analyse as AN
        p = AN.parse_project('uno')
        state['p'] = p
        a = p['atoms']
        check('the UNO template parses over its 6 configurations (4 seeded variants + 2 coverage) into 34 atoms, no preprocessor problem',
              len(p['configs']) == 6 and len(a) == 34 and not p['problems'], (len(a), p['problems'][:3]))
        check('every hal.c function is an atom (18 incl. the 3 ISRs and the knob-gated ones: hal_uart_errors, hal_presses, hal_wdt_boot)',
              HAL_ATOMS <= set(a), sorted(HAL_ATOMS - set(a)))
        check('the 12 POLARI_NODE annotations attach to their functions (hal 6, sim_rig 2, echo 1, scenario_rig 3)',
              {k for k, v in a.items() if v.get('annotation')} == ANNOTATED, sorted({k for k, v in a.items() if v.get('annotation')} ^ ANNOTATED))
        m = a['hal.hal_millis']
        check('hal_millis: out(return) uint32_t → int64 [ms], reads g_ms (shared with the tick ISR) INSIDE the atomic block → isr_safe yes',
              [(x['name'], x['direction'], x['polari_type'], x['unit']) for x in m['ports']] == [('return', 'out', 'int64', 'ms')]
              and m['globals']['g_ms']['inside_atomic'] and not m['globals']['g_ms']['outside_atomic'] and m['isr_safe'] == 'yes')
        r = AN.resources(a['hal.hal_adc_read'])
        check('hal_adc_read touches ADMUX (w), ADCSRA (rw), ADC (r) — all peripheral ADC; ports in channel, out return [count]',
              {(x['name'], x['access'], x['peripheral']) for x in r if x['kind'] == 'register'} == {('ADMUX', 'w', 'ADC'), ('ADCSRA', 'rw', 'ADC'), ('ADC', 'r', 'ADC')}
              and [x['name'] for x in a['hal.hal_adc_read']['ports']] == ['channel', 'return'])
        rx = a['hal.USART_RX_vect']
        check('ISR(USART_RX_vect) (both #if branches, unioned) reads UCSR0A + UDR0 (USART0), writes rx_head / rx_ring and the error counters',
              rx['isr'] == 'USART_RX_vect' and {'UCSR0A', 'UDR0'} <= set(rx['registers']) and rx['globals']['rx_head']['w']
              and rx['globals']['g_uart_fe']['w'] and len(rx['configs']) == 4)
        check('hal_rx_pop: the 1-byte ring indices the RX ISR writes need no atomic block (one lds each) → isr_safe yes; b → out',
              a['hal.hal_rx_pop']['isr_safe'] == 'yes' and a['hal.hal_rx_pop']['ports'][0]['direction'] == 'out')
        check('pure atoms are exactly the two that compute: sim_rig.sensor_value (the TMP36 formula) and scenario_rig.crc8',
              sorted(k for k, v in a.items() if v['pure']) == ['apps/scenario_rig.crc8', 'apps/sim_rig.sensor_value'])
        check('the header functions (the generated <class>_packets.h) are library, never atoms of the project',
              not any('crc32' in k or 'SimRigState' in k for k in a) and 'polari_crc32' in p['library'])

    def torn_build():
        from board.custom import gen
        from cmod.custom import analyse as AN
        w = tempfile.mkdtemp(prefix='cmod-torn-')
        v = {'name': 'cmod-torn', 'app': 'sim_rig', 'board_definition': 'arduino-uno-r3', 'classes_json': '["SimRigState"]',
             'features_json': '{"led": true, "pwm": true, "adc": true, "commands": true}', 'knobs_json': '{}', 'build_flags_json': '["HAL_MILLIS_ATOMIC=0"]'}
        row = gen.gen('uno', work=w, variant='cmod-torn', variant_rows=[v])
        p = AN.parse_project(row['project_dir'])
        a = p['atoms']
        check('the TORN build (HAL_MILLIS_ATOMIC=0, scenario 1\'s BEFORE) parsed as a plain project: hal_millis → isr_safe no — "g_ms (4 B, '
              'written by ISR …) … tears it" — the scanner sees the fault firmwarefaults forces on the twin',
              a['hal.hal_millis']['isr_safe'] == 'no' and 'g_ms (4 B' in a['hal.hal_millis']['isr_safe_why'], a['hal.hal_millis']['isr_safe_why'])
        check('…and main, which calls it, inherits the verdict (calls hal_millis)', a['main.main']['isr_safe'] == 'no'
              and 'hal_millis' in a['main.main']['isr_safe_why'])
        shutil.rmtree(w, ignore_errors=True)

    def macro_is_empty():
        from cmod.custom.preprocess import preprocess
        halh = open(os.path.join(UNO, 'hal.h')).read()
        check('hal.h defines POLARI_NODE(...) as NOTHING (guarded #ifndef) — the annotation cannot change a byte the compiler sees',
              re.search(r'#ifndef POLARI_NODE\n#define POLARI_NODE\(\.\.\.\)\n#endif', halh) is not None)
        p = state['p']
        cfg = p['configs'][0]
        text, _ = preprocess(os.path.join(cfg['dir'], 'hal.c'), [cfg['dir']])
        check('the preprocessed hal.c of uno-sim-rig contains no POLARI_NODE token (6 annotations in the source, 0 after cpp)',
              'POLARI_NODE' not in text and open(os.path.join(UNO, 'hal.c')).read().count('\nPOLARI_NODE(') == 6)

    def cross_check_cpp():
        """An independent preprocessor: the host's GNU cpp with the same fake headers → the same functions."""
        from pycparser import c_ast, c_parser
        from cmod.custom import preprocess as PP
        cpp = shutil.which('cpp')
        if not cpp:
            print('  [SKIP] no host cpp — the PLY preprocessor stands alone')
            return
        cfg = state['p']['configs'][0]
        names = {}
        for how in ('ply', 'gnu'):
            if how == 'ply':
                text, _ = PP.preprocess(os.path.join(cfg['dir'], 'hal.c'), [cfg['dir']])
            else:
                args = [cpp, '-nostdinc', '-undef', '-I', PP.fake_dir(), '-I', cfg['dir']] + ['-D%s' % d.replace(' ', '=', 1) if ' ' in d else '-D%s=' % d
                                                                                             for d in PP.EXTENSION_DEFINES] + [os.path.join(cfg['dir'], 'hal.c')]
                text = subprocess.run(args, capture_output=True, text=True, timeout=60).stdout
            ast = c_parser.CParser().parse(text, 'hal.c')
            names[how] = sorted((e.decl.name, e.coord.line) for e in ast.ext if isinstance(e, c_ast.FuncDef) and e.coord.file.endswith('hal.c'))
        check('cross-check: GNU cpp and the PLY preprocessor give the SAME functions at the SAME lines in hal.c (%d)' % len(names['ply']),
              names['ply'] == names['gnu'] and len(names['ply']) == 13, (names['ply'][:3], names['gnu'][:3]))

    def committed_manifest():
        from cmod.custom import manifest as MF
        path = os.path.join(UNO, 'polari-firmware.json')
        m = json.load(open(path))
        check('the UNO\'s polari-firmware.json is committed beside its Makefile, validates, schema polari-firmware/1, 34 atoms',
              not MF.validate(m) and m['schema'] == 'polari-firmware/1' and m['counts']['atoms'] == 34, MF.validate(m))
        r = MF.conform('uno', measure=False, write=False)
        check('no drift: a parse NOW equals the committed manifest (conform without measuring would write nothing)',
              not r['changed'], (r['added'], r['removed'], r['edited'][:4]))
        atoms = m['atoms']
        costed = [a for a in atoms if a['cost'] and isinstance(a['cost'].get('text_bytes_noinline'), int) and a['cost']['text_bytes_noinline'] > 0]
        check('every atom carries ports (a list), resources (a list) and a measured cost: text bytes as a node > 0 for all 34',
              all(isinstance(a['ports'], list) and isinstance(a['resources'], list) for a in atoms) and len(costed) == 34, len(costed))
        nostack = [a['name'] for a in atoms if a['cost']['stack_bytes'] is None]
        check('stack frames from GCC\'s .su for 33 atoms; the one without is hal_wdt_boot — a naked function, stated in the cost row',
              nostack == ['hal.hal_wdt_boot'] and 'naked' in next(a for a in atoms if a['name'] == 'hal.hal_wdt_boot')['cost']['why'], nostack)
        mk = [c.get('make_alone') or {} for c in m['configurations']]
        check('make ALONE built every configuration (6/6, the .hex sha recorded) — no Polari in that loop',
              len(mk) == 6 and all(x.get('ok') and len(x.get('hex_sha256', '')) == 64 for x in mk))
        sim = next(c for c in m['configurations'] if c['name'] == 'uno-sim-rig')
        check('uno-sim-rig built by make alone = the .hex board\'s own pipeline builds (4188f6ae…, unchanged by the annotations)',
              sim['make_alone']['hex_sha256'].startswith('4188f6ae7d65bfc7'), sim['make_alone']['hex_sha256'][:16])
        check('the build block reads the flags FROM the Makefile and states the measurement (shipped / noinline)',
              m['build']['from'] == 'the project Makefile' and '-Werror' in m['build']['cflags'] and 'noinline' in m['build']['measure'])

    def registers_snapshot():
        from cmod.custom import registers as R
        s = R.load()
        check('register snapshot DERIVED from avr-libc 2.2.1 <avr/io.h> (-dM): 96 registers, 25 vectors, the -dM text\'s sha kept',
              len(s['registers']) == 96 and len(s['vectors']) == 25 and s['avr_libc'] == '2.2.1' and len(s['dm_sha256']) == 64)
        check('peripheral by the datasheet\'s naming: UDR0 → USART0, OCR2A → TIMER2, PORTB → GPIO PORTB, ADMUX → ADC, MCUSR → WDT, SREG → CPU',
              [R.peripheral(x) for x in ('UDR0', 'OCR2A', 'PORTB', 'ADMUX', 'MCUSR', 'SREG')] == ['USART0', 'TIMER2', 'GPIO PORTB', 'ADC', 'WDT', 'CPU'])

    def seeds_page_api():
        from types import SimpleNamespace
        from falcon import testing
        import falcon
        from cmod.cmod_seed import CMOD_SEED_PAIRS
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS
        from cmod.cmod_api import CModAPI
        counts = {n: len(r) for n, _c, r in CMOD_SEED_PAIRS}
        m = json.load(open(os.path.join(UNO, 'polari-firmware.json')))
        check('seeds = the committed manifest projected: 1 project, 7 modules, 34 atoms, %d ports; cmod-1: 1 graph, 18 nodes, 15 edges, '
              '1 glue build; demo-4: TargetDefinition/CapabilityDefinition/CapabilityInstance derived over the seeded graph; '
              'fs-0: one FirmwareSolution (uno-sim-rig) + its derived ScheduleSlot/RegisterAssignment rows' % m['counts']['ports'],
              counts == {'CProject': 1, 'CModule': 7, 'CFunctionAtom': 34, 'CPort': m['counts']['ports'], 'CGraph': 1, 'CGraphNode': 18,
                         'CGraphEdge': 15, 'CGlueBuild': 1, 'TargetDefinition': 16, 'CapabilityDefinition': 1, 'CapabilityInstance': 2,
                         'FirmwareSolution': 1, 'ScheduleSlot': 17, 'RegisterAssignment': 16}, counts)
        page = SEED_CMOD_PAGE_DISPLAYS[0]
        items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
        comp_names = {it['componentProps']['componentName'] for it in items}
        check('/display/c-atoms = 10 CONFIGURED surfaces (projects, atoms, ports, costs, modules; cmod-1: graphs, nodes, edges, glue builds; '
              "demo-4: 'used by' reverse link) — class-rows-table + api-structured-panel only, no raw JSON, no new component",
              page['pageRoute'] == 'c-atoms' and len(items) == 10 and comp_names == {'class-rows-table', 'api-structured-panel'})
        canvas_page = SEED_CMOD_PAGE_DISPLAYS[1]
        canvas_items = [it for row in json.loads(canvas_page['definition'])['rows'] for it in row['items']]
        check('/display/c-canvas: the canvas panel first, then described tables (atoms available, targets, capabilities, instances)',
              canvas_page['pageRoute'] == 'c-canvas' and canvas_items[0]['componentProps']['componentName'] == 'c-graph-canvas-panel'
              and canvas_items[0]['componentProps']['inputs']['graph'] == 'uno-sim-rig-graph'
              and {it['componentProps']['componentName'] for it in canvas_items[1:]} == {'class-rows-table'})
        import inspect
        from cmod.cmod_basis import CMOD_CLASSES
        known = {c.__name__: c for c in CMOD_CLASSES}
        bad = []
        for it in [i for i in items + canvas_items if i['componentProps']['componentName'] == 'class-rows-table']:
            cn = it['componentProps']['inputs']['className']
            params = set(inspect.signature(known[cn].__init__).parameters) if cn in known else set()
            bad += ['%s.%s' % (cn, col) for col in it['componentProps']['inputs']['columns'].split(',') if col and col not in params]
        check('…every table (c-atoms + c-canvas) names a cmod class and only columns that class has', not bad, bad)
        tables = {}
        mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
        for name, cls, rows in CMOD_SEED_PAIRS:
            for r in rows:
                o = cls(manager=mgr, **{k: v for k, v in r.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
        app = falcon.App()
        CModAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
        c = testing.TestClient(app)
        r = c.simulate_get('/api/cmod')
        check('GET /api/cmod → the uno project with 34 atoms, the parser named', r.status_code == 200 and r.json['projects'][0]['atoms'] == 34
              and r.json['parser']['engine'] == 'pycparser', r.text[:200])
        r = c.simulate_get('/api/cmod/atoms/hal_millis')
        check('GET /api/cmod/atoms/hal_millis → uno:hal.hal_millis with its one port', r.status_code == 200 and r.json['atom']['name'] == 'uno:hal.hal_millis'
              and [p['port'] for p in r.json['ports']] == ['return'], r.text[:200])
        r = c.simulate_get('/api/cmod/atoms/apply_command')
        check('an ambiguous short name (apply_command: sim_rig and scenario_rig) → 404 naming both', r.status_code == 404
              and 'uno:apps/sim_rig.apply_command' in r.json['error'] and 'uno:apps/scenario_rig.apply_command' in r.json['error'], r.text[:200])
        r = c.simulate_get('/api/cmod/atoms', params={'kind': 'isr'})
        check('GET /api/cmod/atoms?kind=isr → the 3 ISRs', r.status_code == 200 and len(r.json['atoms']) == 3)
        r = c.simulate_get('/api/cmod/projects/uno/drift')
        check('GET /api/cmod/projects/uno/drift → not stale (parsed now, nothing measured or written)', r.status_code == 200 and r.json['stale'] is False, r.text[:200])

    def manifest_conform():
        from moduleService import manifests as M
        r = M.conform('cmod')
        check('manifests conform cmod: no drift (files, classes, imports, endpoints, seeds, pages, requires)', r['ok'], r['findings'])
        m = M.load('cmod')
        check('polari-app.json requires board only and declares its engines honestly (pycparser in-process; avr-gcc / avr-nm / make via the board seam)',
              m['requires']['modules'] == ['board'] and {'pycparser', 'avr-gcc', 'avr-nm', 'make'} <= {e['name'] for e in m['requires']['engines']})

    return (uno_atoms, torn_build, macro_is_empty, cross_check_cpp, committed_manifest, registers_snapshot, seeds_page_api, manifest_conform)
