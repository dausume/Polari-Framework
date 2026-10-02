"""firmwarefaults_selftest — sc-0 (FIRMWARE_SCENARIO_PLAN.md §9): the taxonomy's integrity (every fault kind has its family, the
assumption it breaks and remedies that exist), the step-kind catalogue (only scenarios whose steps are ALL forcible are runnable),
the runner's decision on fixture frame sequences (backwards → refuted, monotone → witnessed, never fired → undetermined, refused
build → inapplicable), the disassembly resolution (fixture avr-objdump text of both hal_millis builds), the static stack parse,
the harness flags, the claim bridge in his vocabulary, the scenario variants, the hal.c knob + static guard, the page (configured
tables only) and the API doors over a fake manager. No engine is run here — tests/firmwarefaults_probe.py runs the REAL pair.

    PYTHONPATH=.:modules python3 -m firmwarefaults.firmwarefaults_selftest      # from polari-framework/
"""
import inspect
import json
import os
import re
import sys

from types import SimpleNamespace

passed = total = 0
HERE = os.path.dirname(os.path.abspath(__file__))
_SCRATCH = SimpleNamespace(objectTables={}, idList=[], db=None)   # rows built only to prove their fields need a manager for ids


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


# avr-objdump -d / avr-nm -n of the two scenario-1 builds (avr-gcc 14.2.0 -Os, prf-board-engines:trixie, 2026-10-02)
OBJ_TORN = """
000001ba <hal_millis>:
     1ba:\t60 91 08 01 \tlds\tr22, 0x0108\t; 0x800108 <g_ms>
     1be:\t70 91 09 01 \tlds\tr23, 0x0109\t; 0x800109 <g_ms+0x1>
     1c2:\t80 91 0a 01 \tlds\tr24, 0x010A\t; 0x80010a <g_ms+0x2>
     1c6:\t90 91 0b 01 \tlds\tr25, 0x010B\t; 0x80010b <g_ms+0x3>
     1ca:\t08 95       \tret
"""
OBJ_ATOMIC = """
000001ba <hal_millis>:
     1ba:\t2f b7       \tin\tr18, 0x3f\t; 63
     1bc:\tf8 94       \tcli
     1be:\t60 91 08 01 \tlds\tr22, 0x0108\t; 0x800108 <g_ms>
     1c2:\t70 91 09 01 \tlds\tr23, 0x0109\t; 0x800109 <g_ms+0x1>
     1c6:\t80 91 0a 01 \tlds\tr24, 0x010A\t; 0x80010a <g_ms+0x2>
     1ca:\t90 91 0b 01 \tlds\tr25, 0x010B\t; 0x80010b <g_ms+0x3>
     1ce:\t2f bf       \tout\t0x3f, r18\t; 63
     1d0:\t08 95       \tret
"""
NM = """00000000 W __heap_end
00000000 T __vectors
000000a6 T __vector_18
0000015c T __vector_7
000001ba T hal_millis
0000033c T main
00800108 b g_ms
0080010d b rx_head
008002eb B __bss_end
"""
CI = '''graph: { title: "main.c"
node: { title: "main" label: "main\\nmain.c:89:5\\n105 bytes (static)" }
node: { title: "hal_pwm_apply" label: "hal_pwm_apply\\nhal.h:49:9" shape : ellipse }
edge: { sourcename: "main" targetname: "hal_pwm_apply" label: "main.c:80:5" }
node: { title: "strcpy" label: "strcpy\\n/usr/lib/avr/include/string.h:303:14" shape : ellipse }
edge: { sourcename: "main" targetname: "strcpy" label: "main.c:107:5" }
}
graph: { title: "hal.c"
node: { title: "hal_pwm_apply" label: "hal_pwm_apply\\nhal.c:158:9\\n10 bytes (static)" }
node: { title: "__vector_7" label: "__vector_7\\nhal.c:81:1\\n9 bytes (static)" }
node: { title: "__vector_18" label: "__vector_18\\nhal.c:35:1\\n10 bytes (static)" }
}'''


def classes_and_rows():
    from firmwarefaults.firmwarefaults_basis import FIRMWAREFAULTS_CLASSES, FAULT_KINDS, FAULT_KIND_CLASSES, FirmwareFault, BASE_FIELDS
    from firmwarefaults.custom.fault_rows import SEED_FAULT_ROWS
    from firmwarefaults.custom.taxonomy import SEED_PRIMITIVES, SEED_ASSUMPTIONS, SEED_TECHNIQUES
    check('16 fault KIND classes: 7 concurrency + 6 physical-trigger + 3 space-safety (plan §1)',
          [len(FAULT_KINDS[f]) for f in ('concurrency', 'physical-trigger', 'space-safety')] == [7, 6, 3])
    check('every kind extends FirmwareFault and names treeObject (the manifest scan), one class per file under objects/<family>/',
          all(issubclass(c, FirmwareFault) and 'treeObject' in [b.__name__ for b in c.__bases__] for c in FAULT_KIND_CLASSES)
          and all(os.path.isfile(os.path.join(HERE, 'objects', inspect.getmodule(c).__name__.split('.')[-2], c.__name__ + '.py')) for c in FAULT_KIND_CLASSES))
    check('24 row classes (the base + 16 kinds + primitive, assumption, technique, scenario, step, run, trace cycle)', len(FIRMWAREFAULTS_CLASSES) == 24)
    check('every kind carries the base fields in its constructor (layer, assumption_broken, observable, remedies, rate, rate_source …)',
          all(set(BASE_FIELDS) <= set(inspect.signature(c.__init__).parameters) for c in FAULT_KIND_CLASSES))
    names = {c.__name__: c for c in FAULT_KIND_CLASSES}
    per = {}
    for cls, row in SEED_FAULT_ROWS:
        per.setdefault(cls, []).append(row)
    check('ONE seeded row per kind (16)', sorted(per) == sorted(names) and all(len(v) == 1 for v in per.values()))
    a_names = {a['name'] for a in SEED_ASSUMPTIONS}
    t_names = {t['name'] for t in SEED_TECHNIQUES}
    p_names = {p['name'] for p in SEED_PRIMITIVES}
    bad = [(c, r['name']) for c, r in SEED_FAULT_ROWS if r['assumption_broken'] not in a_names or not json.loads(r['remedies_json'])
           or not set(json.loads(r['remedies_json'])) <= t_names or not set(json.loads(r['primitives_json'])) <= p_names
           or not r['observable'] or not r['rate_source']]
    check('TAXONOMY INTEGRITY: every fault names an existing assumption, ≥ 1 existing remedy, existing primitives, an observable, a rate source',
          not bad, bad)
    built = []
    try:
        built = [names[c](manager=_SCRATCH, **r) for c, r in SEED_FAULT_ROWS]
        check('every fault row constructs its kind class; the layer is the family\'s (never blank)',
              all(b.layer == type(b).LAYER and b.layer for b in built))
    except TypeError as e:
        check('every fault row constructs its kind class', False, str(e))
    check('a rate is never a silent guess: every source is a citation, `measured …`, an `estimate …` or says unverified/per run',
          all(any(w in r['rate_source'] for w in ('unverified', 'estimate', 'measured', 'datasheet', 'design fact', 'cited', 'DatasheetFact'))
              for _, r in SEED_FAULT_ROWS))
    check('the UNO\'s three primitives are marked uno_uses (irq-mask, volatile-flag, spsc-ring); the RTOS ones need an RTOS',
          sorted(p['name'] for p in SEED_PRIMITIVES if p['uno_uses']) == ['irq-mask', 'spsc-ring', 'volatile-flag']
          and all(p['needs_rtos'] for p in SEED_PRIMITIVES if not p['uno_uses']))
    check('every technique restores an existing assumption, uses an existing primitive (or none), and its idiom is plain C (RULE 2)',
          all(t['restores'] in a_names and (not t['primitive'] or t['primitive'] in p_names)
              and not any(x in t['idiom_c'] for x in ('Serial.', 'digitalWrite', 'Arduino.h')) and not re.search(r'(?<!\w)millis\(\)', t['idiom_c'])
              for t in SEED_TECHNIQUES))
    at = {t['name']: t for t in SEED_TECHNIQUES}['atomic-block']
    check('atomic-block carries the disassembly\'s cost (+6 B, +3 cycles) with its source; static-guard costs nothing',
          (at['typical_cost_bytes'], at['typical_cost_cycles']) == (6, 3) and 'disassembly' in at['cost_source']
          and {t['name']: t for t in SEED_TECHNIQUES}['static-guard']['typical_cost_bytes'] == 0)


def steps_and_scenarios():
    from firmwarefaults.custom import scenarios as SC
    from firmwarefaults.custom import runner
    from firmwarefaults.custom.sink import LocalSink
    check('the step-kind catalogue holds all eight plan kinds; irq-at-pc, irq-at-cycle, corrupt-word are forcible; the rest say why not',
          sorted(SC.STEP_KINDS) == sorted(['irq-at-pc', 'irq-at-cycle', 'corrupt-word', 'drop-nth-frame', 'flip-bit-at-cycle', 'uart-ber',
                                           'hold-lock-order', 'clock-skew'])
          and sorted(SC.FORCIBLE_KINDS) == ['corrupt-word', 'irq-at-cycle', 'irq-at-pc']
          and all(why for k, (ok, why) in SC.STEP_KINDS.items() if not ok))
    check('seeded steps are only of forcible kinds, flagged so; scenario 1 and 1b are runnable',
          all(s['kind'] in SC.FORCIBLE_KINDS and s['forcible'] and not s['not_forcible_reason'] for s in SC.SEED_STEPS)
          and all(SC.runnable(s) for s in SC.SEED_SCENARIOS))
    fake_sc = dict(SC.SEED_SCENARIOS[0], name='fixture-ber')
    fake_steps = [{'name': 'fixture-ber#1', 'scenario': 'fixture-ber', 'order': 1, 'kind': 'uart-ber', 'args_json': '{"p": 1e-4}',
                   'condition_json': '{}', 'forcible': False, 'not_forcible_reason': SC.STEP_KINDS['uart-ber'][1], 'notes': ''}]
    check('a scenario with a NOT-YET-FORCIBLE step is not runnable', not SC.runnable(fake_sc, fake_steps))
    try:
        runner.run_side(fake_sc, 'before', LocalSink(), fake_steps)
        refused = ''
    except runner.ScenarioRefused as e:
        refused = str(e)
    check('…and the runner REFUSES it before building anything, naming the kind and the reason', 'uart-ber' in refused and 'sc-1' in refused, refused)
    s1 = SC.find('torn-millis-read')
    check('scenario 1: BEFORE uno-sim-rig-torn, AFTER uno-sim-rig, TornReadFault torn-read-g-ms breaks g-ms-read-atomic, technique atomic-block',
          (s1['before_variant'], s1['after_variant'], s1['fault_class'], s1['fault'], s1['breaks'], s1['technique'], s1['observable_kind'])
          == ('uno-sim-rig-torn', 'uno-sim-rig', 'TornReadFault', 'torn-read-g-ms', 'g-ms-read-atomic', 'atomic-block', 'uptime-monotone'))
    st = json.loads(SC.steps_of('torn-millis-read')[0]['args_json'])
    check('its one step: irq-at-pc on hal_millis before load 2 of g_ms, vector 7 (TIMER2_COMPA), when g_ms & 0xFF == 0xFF',
          (st['symbol'], st['of'], st['before_load'], st['vec']) == ('hal_millis', 'g_ms', 2, 7)
          and json.loads(SC.steps_of('torn-millis-read')[0]['condition_json']) == {'symbol': 'g_ms', 'width': 4, 'mask': 255, 'value': 255})
    check('scenario 1b is a build-refused scenario of BufferOverrunFault with the static-guard technique',
          (SC.find('rx-ring-over-256')['observable_kind'], SC.find('rx-ring-over-256')['technique']) == ('build-refused', 'static-guard'))


def outcome_logic():
    from firmwarefaults.custom import outcome as O
    d = O.decide_uptime([0, 100, 200, 511, 400, 500], 0, {'fired': 1, 'landed': 1})
    check('fixture BEFORE frames (0,100,200,511,400,500) → failed / refuted, torn value 511, CRC named as fine',
          d['outcome'] == 'failed' and d['claim_status'] == 'refuted' and d['torn_value'] == 511 and 'CRC passed' in d['words'])
    d = O.decide_uptime([0, 100, 200, 300, 400, 500], 0, {'fired': 1, 'landed': 1})
    check('fixture AFTER frames (monotone) → passed / witnessed, worded as a witness (not a proof)',
          d['outcome'] == 'passed' and d['claim_status'] == 'witnessed' and 'not a proof' in d['words'])
    d = O.decide_uptime([0, 100, 200], 0, {'fired': 0})
    check('the forcing condition never held → undetermined (never a pass)', d['outcome'] == 'undetermined' and d['claim_status'] == 'undetermined')
    check('equal consecutive uptimes are NOT backwards (a repeated value is not a tear)', O.backwards([0, 254, 254, 300]) == [])
    d = O.decide_build_refused('refused', 'hal.c:25:1: error: static assertion failed: "RX_RING must be…"\n 25 | _Static_assert')
    check('a refused build → inapplicable (not defined on this state space), quoting the assertion',
          d['outcome'] == 'inapplicable' and d['claim_status'] == 'inapplicable' and 'static assertion failed' in d['words'])
    check('a build that went through on a build-refused scenario → undetermined (sc-1 must force it)',
          O.decide_build_refused('built')['outcome'] == 'undetermined')
    n = O.natural_rate([0, 100, 200, 511, 400, 500, 600], 2560, calls=1000, cycles=100000)
    check('natural rate: tears = backwards drops, carries = final_ms // 256, exposure = 2 cycles x calls / cycles',
          (n['tears'], n['carries'], round(n['rate'], 3), n['exposure_per_carry']) == (1, 10, 0.1, 0.02))
    check('the claim map is his vocabulary, four words kept apart',
          O.CLAIM_STATUS == {'failed': 'refuted', 'passed': 'witnessed', 'inapplicable': 'inapplicable', 'undetermined': 'undetermined'})


def disassembly_and_flags():
    from firmwarefaults.custom import disasm, harness, stack_static
    from firmwarefaults.custom import scenarios as SC
    nm = disasm.parse_nm(NM)
    torn, atom = disasm.parse_objdump(OBJ_TORN), disasm.parse_objdump(OBJ_ATOMIC)
    lt, la = disasm.lds_sequence(torn, 'hal_millis', 'g_ms'), disasm.lds_sequence(atom, 'hal_millis', 'g_ms')
    check('the lds sequence of g_ms in hal_millis: four loads, bytes 0..3 into r22..r25, in both builds',
          [x['byte'] for x in lt] == [0, 1, 2, 3] == [x['byte'] for x in la] and [x['reg'] for x in lt] == ['r22', 'r23', 'r24', 'r25'])
    step = json.loads(SC.steps_of('torn-millis-read')[0]['args_json'])
    rt, ra = disasm.resolve_step(step, torn, nm), disasm.resolve_step(step, atom, nm)
    check('the step re-resolves PER BUILD: load 2 at hal_millis+0x4 (bare, 0x1be) and hal_millis+0x8 (atomic, 0x1c2) — plan §3',
          rt['ok'] and ra['ok'] and rt['pc'] == 0x1be and ra['pc'] == 0x1c2 and disasm.symbolize(nm, rt['pc']) == 'hal_millis+0x4'
          and disasm.symbolize(nm, ra['pc']) == 'hal_millis+0x8')
    check('static cycles of hal_millis: 12 bare, 15 atomic → +3 (the in, cli, out of the technique)',
          disasm.static_cycles(torn, 'hal_millis') == 12 and disasm.static_cycles(atom, 'hal_millis') == 15)
    nm_noisr = {k: v for k, v in nm.items() if k != '__vector_7'}
    r = disasm.resolve_step(step, torn, nm_noisr)
    check('a build without the ISR → not ok with the reason (the run is inapplicable there)', not r['ok'] and '__vector_7' in r['why'])
    r = disasm.resolve_step(dict(step, of='rx_head'), torn, nm)
    check('a variable read in fewer loads than the step needs → not ok ("a single-load read cannot tear")', not r['ok'] and 'cannot tear' in r['why'])
    check('symbolize: the vector table and a linker marker at 0 are named sensibly (not __heap_end)',
          disasm.symbolize(nm, 0x1c).startswith('__vectors+0x1c (vector 7)') and disasm.symbolize(nm, 0x400) == 'main+0xc4')
    argv = harness.render([(SC.steps_of('torn-millis-read')[0], rt)], nm, 0.6, 0, watch=('g_ms', 4), fn=(0x1ba, 0x1ca))
    s = ' '.join(argv)
    check('harness flags: --irq-at pc=0x1be,vec=7,shots=1,when=0x108/4&0xff=0xff, the watch, the stack paint from __bss_end, fn cycles, '
          'free-running, the VCD window, the seed',
          'pc=0x1be,vec=7,shots=1,when=0x108/4&0xff=0xff' in s and '--watch 0x108/4=g_ms' in s and '--stack-fill 0x2eb' in s
          and '--fn-cycles 0x1ba:0x1ca' in s and '--free' in argv and '--trace-vcd' in argv and '--seed' in argv and '--isr-latency' in argv, s)
    nat = harness.render([(SC.steps_of('torn-millis-read')[0], rt)], nm, 10, 0, watch=('g_ms', 4), fn=(0x1ba, 0x1ca), forcing=False)
    check('a natural run renders NO forcing and no VCD (only the measurements)', '--irq-at' not in nat and '--trace-vcd' not in nat and '--sp-watch' in nat)
    pk = stack_static.peak(*stack_static.parse_ci([CI]))
    check('static stack: main 105 B → hal_pwm_apply 10 B (+2 B per call, +2 B crt) + the largest ISR (__vector_18 10 B + 2 B PC) = 131 B; '
          'strcpy listed as uncounted', pk['ok'] and pk['peak_bytes'] == 131 and pk['isr'] == '__vector_18' and 'strcpy' in pk['uncounted'], pk)


def claims():
    from firmwarefaults.custom.claim_bridge import write, claim_name
    from firmwarefaults.custom.sink import LocalSink
    from firmwarefaults.custom.scenarios import find
    from mathproofs.mathproofs_basis import CLAIM_KINDS, CHECKERS, PROOF_STATUSES
    check('mathproofs knows the kind safe-under-scenario, the checker sim, and the status inapplicable (apart from undetermined)',
          'safe-under-scenario' in CLAIM_KINDS and 'sim' in CHECKERS and {'inapplicable', 'undetermined', 'refuted', 'witnessed'} <= set(PROOF_STATUSES))
    sc = find('torn-millis-read')
    base = {'name': 'r1', 'build_name': 'uno-sim-rig-torn-x', 'variant': 'uno-sim-rig-torn', 'side': 'before', 'seed': 0, 'outcome': 'failed',
            'fault_cycle': 4083147, 'fault_pc': '0x01be', 'fault_symbol': 'hal_millis+0x4', 'landed_pc': '0x01be', 'landed_symbol': 'hal_millis+0x4',
            'torn_value': 511, 'expected_value': 255, 'uptime_sequence': '0, 100, 200, 511, 400', 'trace_sha256': 'ab', 'ran_at': 't1',
            'verdict_words': 'backwards', 'harness_digest': 'h', 'wall_s': 0.1, 'firmware_sha256': 'f'}
    sink = LocalSink()
    n, after, before = write(sink, base, sc)
    c = sink.get('MathClaim', n)
    check('a FAILED run writes the claim refuted, kind safe-under-scenario, checker sim, evidence measured, the counterexample (cycle, PC, '
          'landed PC, torn value), about the Scenario + FirmwareBuild + fault row',
          n == claim_name('torn-millis-read', 'uno-sim-rig-torn-x') and c['proof_status'] == 'refuted' and c['kind'] == 'safe-under-scenario'
          and c['checker'] == 'sim' and c['evidence_level'] == 'measured' and json.loads(c['counterexample_json'])['torn_value'] == 511
          and json.loads(c['about_refs_json']) == ['Scenario:torn-millis-read', 'FirmwareBuild:uno-sim-rig-torn-x', 'TornReadFault:torn-read-g-ms'])
    check('…with a ProofRun (checker sim, verdict refuted) as its certificate', any(r['verdict'] == 'refuted' and r['claim'] == n for r in sink.rows('ProofRun')))
    n2, after2, before2 = write(sink, dict(base, outcome='passed', ran_at='t2'), sc)
    check('a later PASSING run on the SAME build never flips a refuted claim back (a counterexample outranks a witness); its ProofRun is kept',
          after2 == 'refuted' and before2 == 'refuted' and json.loads(sink.get('MathClaim', n)['counterexample_json'])['torn_value'] == 511
          and len(sink.rows('ProofRun')) == 2)
    n3, after3, _ = write(sink, dict(base, build_name='uno-sim-rig-y', variant='uno-sim-rig', side='after', outcome='passed', torn_value=-1), sc)
    check('the AFTER build is a DIFFERENT claim: witnessed, no counterexample', after3 == 'witnessed' and sink.get('MathClaim', n3)['counterexample_json'] == '{}')
    n4, after4, _ = write(sink, dict(base, build_name='z', outcome='inapplicable'), sc)
    check('inapplicable maps to inapplicable (evidence none)', after4 == 'inapplicable' and sink.get('MathClaim', n4)['evidence_level'] == 'none')
    check('the claims carry no term (mathproofs\' boot pass checks only claims with one) but a LaTeX rendering for people',
          all(c['statement_json'] == '{}' and c['statement_latex'].startswith(r'\mathrm{safe}') for c in sink.rows('MathClaim')))


def variants_and_firmware():
    from firmwarefaults.custom.scenarios import scenario_variants
    from board.custom import variants as V
    vs = {v['name']: v for v in scenario_variants()}
    r = V.resolve(vs['uno-sim-rig-torn'])
    cfg = V.render_config(r)
    check('variant uno-sim-rig-torn = the whole rig + build flag HAL_MILLIS_ATOMIC=0, rendered into board_config.h by board\'s own variant code',
          r['app'] == 'sim_rig' and r['flags'] == [('HAL_MILLIS_ATOMIC', 0)] and '#define HAL_MILLIS_ATOMIC 0' in cfg)
    check('variant uno-sim-rig-ring512 = build flag RX_RING=512 (the build hal.c refuses)', V.resolve(vs['uno-sim-rig-ring512'])['flags'] == [('RX_RING', 512)])
    hal = open(os.path.join(HERE, '..', 'board', 'custom', 'firmware', 'uno', 'hal.c')).read()
    check('hal.c: HAL_MILLIS_ATOMIC defaults to 1 (the shipped build is unchanged) and the bare read exists only under #else',
          '#ifndef HAL_MILLIS_ATOMIC\n#define HAL_MILLIS_ATOMIC 1' in hal and '#if HAL_MILLIS_ATOMIC\n    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_ms; }\n#else\n    v = g_ms;' in hal)
    check('hal.c: _Static_assert(RX_RING <= 256 …) guards the uint8_t ring indices (scenario 1b = a refused build)',
          '_Static_assert(RX_RING >= 2u && RX_RING <= 256u' in hal and '#ifndef RX_RING' in hal)


def seeds_page_api():
    from firmwarefaults.firmwarefaults_seed import FIRMWAREFAULTS_SEED_PAIRS
    from firmwarefaults.firmwarefaults_page import SEED_FIRMWAREFAULTS_PAGE_DISPLAYS
    from firmwarefaults.firmwarefaults_basis import FIRMWAREFAULTS_CLASSES
    ok = True
    for cname, cls, rows in FIRMWAREFAULTS_SEED_PAIRS:
        for r in rows:
            try:
                cls(manager=_SCRATCH, **{k: v for k, v in r.items() if k != '_converge'})
            except TypeError as e:
                ok = False
                print('      ', cname, r.get('name'), e)
    check('every seed row constructs its class (no stray field)', ok)
    seeded = {n: len(rows) for n, _, rows in FIRMWAREFAULTS_SEED_PAIRS}
    check('seeded: 6 primitives, 12 assumptions, 10 techniques, 2 scenarios, 2 steps, 2 scenario variants; runs + trace rows observed only',
          (seeded['ConcurrencyPrimitive'], seeded['Assumption'], seeded['Technique'], seeded['Scenario'], seeded['ScenarioStep'],
           seeded.get('FirmwareVariant'), seeded['ScenarioRun'], seeded['ScenarioTraceCycle']) == (6, 12, 10, 2, 2, 2, 0, 0), seeded)
    check('what a run MEASURES is not converged by a re-seed (technique measured_*, a fault\'s rate / rate_source)',
          all('measured_by_run' not in r['_converge'] for n, _, rows in FIRMWAREFAULTS_SEED_PAIRS if n == 'Technique' for r in rows)
          and all('rate_source' not in r['_converge'] for n, _, rows in FIRMWAREFAULTS_SEED_PAIRS if n.endswith('Fault') for r in rows))
    page = SEED_FIRMWAREFAULTS_PAGE_DISPLAYS[0]
    items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
    comps = {it['componentProps']['componentName'] for it in items}
    known = {c.__name__: c for c in FIRMWAREFAULTS_CLASSES}
    from mathproofs.mathproofs_basis import MathClaim
    known['MathClaim'] = MathClaim
    bad_cols = []
    for it in items:
        cn = it['componentProps']['inputs']['className']
        cols = [c for c in it['componentProps']['inputs']['columns'].split(',') if c]
        params = set(inspect.signature(known[cn].__init__).parameters) if cn in known else set()
        bad_cols += ['%s.%s' % (cn, c) for c in cols if c not in params]
    check('/display/firmware-faults is CONFIGURED TABLES ONLY (class-rows-table; no api-json-panel, no new component)', comps == {'class-rows-table'}, comps)
    check('…every table names a real class and only columns that class has', not bad_cols, bad_cols)
    check('…including the cycles around the fault (ScenarioTraceCycle), the runs, the claims and one table per fault kind (16)',
          {'ScenarioTraceCycle', 'ScenarioRun', 'MathClaim', 'Technique'} <= {it['componentProps']['inputs']['className'] for it in items}
          and sum(1 for it in items if it['id'].startswith('ff-kind-')) == 16)
    # the API doors over a fake manager holding the seeded rows
    import falcon
    from falcon import testing
    from firmwarefaults.firmwarefaults_endpoints import construct_firmwarefaults_endpoints
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for cname, cls, rows in FIRMWAREFAULTS_SEED_PAIRS:
        for r in rows:
            o = cls(manager=mgr, **{k: v for k, v in r.items() if k != '_converge'})
            tables.setdefault(cname, {})[o.id] = o
    app = falcon.App()
    construct_firmwarefaults_endpoints(SimpleNamespace(falconServer=app, manager=mgr, idList=[]))
    c = testing.TestClient(app)
    s = c.simulate_get('/api/firmwarefaults').json
    check('GET /api/firmwarefaults: 16 fault rows by family, both scenarios runnable, the step-kind catalogue',
          s['ok'] and s['fault_rows'] == 16 and all(x['runnable'] for x in s['scenarios']) and len(s['step_kinds']) == 8, str(s)[:300])
    f = c.simulate_get('/api/firmwarefaults/faults').json
    check('GET /api/firmwarefaults/faults groups the rows by family with the kind fields',
          [len(f['families'][k]) for k in ('concurrency', 'physical-trigger', 'space-safety')] == [7, 6, 3]
          and next(x for x in f['families']['concurrency'] if x['kind'] == 'TornReadFault')['width_bytes'] == 4)
    sc = c.simulate_get('/api/firmwarefaults/scenarios').json
    check('GET /api/firmwarefaults/scenarios carries the ordered steps', [len(x['steps']) for x in sc['scenarios']] == [1, 1])
    check('GET /api/firmwarefaults/runs/<missing> → 404; POST /run without a scenario → 400',
          c.simulate_get('/api/firmwarefaults/runs/nope').status_code == 404
          and c.simulate_post('/api/firmwarefaults/run', body='{}').status_code == 400)
    check('GET /api/firmwarefaults/techniques lists ten', len(c.simulate_get('/api/firmwarefaults/techniques').json['techniques']) == 10)


def manifest():
    from moduleService import manifests as M
    r = M.conform('firmwarefaults')
    check('manifests conform firmwarefaults: no drift (files, classes, imports, endpoints, seeds, pages, requires)', r['ok'], r['findings'])
    m = M.load('firmwarefaults')
    check('polari-app.json requires board + grpcbridge + mathproofs (D-sc-1) and declares its engines honestly (avr-twin via the board seam, '
          'avr-gcc -fstack-usage, avr-objdump, pyvcd)',
          sorted(m['requires']['modules']) == ['board', 'grpcbridge', 'mathproofs']
          and {'avr-twin', 'avr-gcc', 'avr-objdump', 'pyvcd'} <= {e['name'] for e in m['requires']['engines']})


def main():
    print('firmwarefaults selftest (sc-0)')
    for part in (classes_and_rows, steps_and_scenarios, outcome_logic, disassembly_and_flags, claims, variants_and_firmware, seeds_page_api, manifest):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
