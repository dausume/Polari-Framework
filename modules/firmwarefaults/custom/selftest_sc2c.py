"""firmwarefaults.custom.selftest_sc2c — the sc-2c half of the module selftest (FIRMWARE_SCENARIO_PLAN.md §5, §9 sc-2c; D-sc-6 ruled
2026-10-02): Frama-C/Mthread as the formal tier's second engine. The wrapper's parse of Mthread's report (fixtures = the REAL
report lines of the four checks, 2026-10-02), the classification rule (protected / byte-atomic single writer / race), the outcome
mapping in his vocabulary (decided (unbounded) ≠ decided (bounded) ≠ refuted ≠ inapplicable; never proved; a run that never
reached the report = error) incl. the NEGATIVE CONTROL (two writers of rx_head → refuted, speaking to no claim), the refusal
naming FORMAL_ENGINES_URL when no engine resolves (an image built before sc-2c is not handed an Mthread run), the bridge's files (hal.c #included, never copied; cli/sei/ATOMIC_BLOCK →
one lock; the assumptions block), the argv, the seeded rows, CBMC's checks unchanged. No engine runs here —
tests/firmwarefaults_probe.py runs the real Mthread checks when prf-formal-engines (sc-2c build) exists.
"""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # the module dir
RFNODE = os.path.abspath(os.path.join(HERE, '..', '..', '..'))               # polari-rf-node


def _formal_engines_src(name):
    """A file from the prf-formal-engines sibling checkout, resolved the way the formal engines seam resolves
    everything else there: FORMAL_ENGINES_SRC override first, then RFNODE/prf-formal-engines. Returns None —
    never raises — when neither exists (e.g. inside the backend image, where /app IS the framework root with
    no rf-node parent at all); callers skip honestly instead of crashing the run.
    """
    for base in (os.environ.get('FORMAL_ENGINES_SRC'), os.path.join(RFNODE, 'prf-formal-engines')):
        if base and os.path.isfile(os.path.join(base, name)):
            return os.path.join(base, name)
    return None


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _acc(kind, thread, where, lock=None, maybe=False):
    return {'kind': kind, 'thread': thread, 'where': where, 'protected_by': [lock] if lock else [], 'maybe': maybe,
            'text': '%s by %s at %s, %s' % (kind, thread, where, ('protected by %s%s' % ('(?)' if maybe else '', lock)) if lock else 'unprotected')}


L = 'polari_irq_mutex'
#: the shared accesses as Mthread reported them for the four checks (frama-c 33.0, -machdep avr_16, -eva-slevel 15, 2026-10-02)
SHARED_TORN = [{'var': 'g_ms', 'accesses': [_acc('read', '<main>', 'hal.c:134'), _acc('read', 'polari_tick_isr', 'hal.c:110', L),
                                            _acc('write', 'polari_tick_isr', 'hal.c:110', L)]}]
SHARED_ATOMIC = [{'var': 'g_ms', 'accesses': [_acc('read', '<main>', 'hal.c:132', L), _acc('read', 'polari_tick_isr', 'hal.c:110', L),
                                              _acc('write', 'polari_tick_isr', 'hal.c:110', L)]}]
SHARED_RING = [{'var': 'rx_tail', 'accesses': [_acc('read', '<main>', 'hal.c:75'), _acc('read', '<main>', 'hal.c:76'), _acc('read', '<main>', 'hal.c:77'),
                                               _acc('read', 'polari_rx_isr', 'hal.c:66', L), _acc('write', '<main>', 'hal.c:77')]},
               {'var': 'rx_head', 'accesses': [_acc('read', '<main>', 'hal.c:75'), _acc('read', 'polari_rx_isr', 'hal.c:65', L),
                                               _acc('read', 'polari_rx_isr', 'hal.c:67', L), _acc('write', 'polari_rx_isr', 'hal.c:68', L)]},
               {'var': 'rx_ring[0..63]', 'accesses': [_acc('read', '<main>', 'hal.c:76'), _acc('write', 'polari_rx_isr', 'hal.c:67', L)]}]
SHARED_BROKEN = [SHARED_RING[0], dict(SHARED_RING[1], accesses=SHARED_RING[1]['accesses'][:3] + [_acc('write', '<main>', 'rx_ring_race.c:33')]
                                      + SHARED_RING[1]['accesses'][3:]), SHARED_RING[2]]
SIZES_RING = {'rx_head': 1, 'rx_tail': 1, 'rx_ring': 1}


def sc2c_parts(check):
    def rule_and_outcomes():
        from firmwarefaults.custom import formal_mthread as M
        cls = {c['var']: c for c in M.classify(SHARED_RING, SIZES_RING)}
        check('the rule: rx_head / rx_tail / rx_ring are BYTE-ATOMIC (one byte, one writer each) — unprotected by main, yet no race',
              {v: c['verdict'] for v, c in cls.items()} == {'rx_head': 'BYTE-ATOMIC', 'rx_tail': 'BYTE-ATOMIC', 'rx_ring[0..63]': 'BYTE-ATOMIC'}
              and cls['rx_head']['writers'] == ['polari_rx_isr'] and cls['rx_tail']['writers'] == ['<main>'], cls)
        c = M.classify(SHARED_TORN, {'g_ms': 4})[0]
        check('the rule: g_ms (4 bytes) read by main with the lock NOT held → RACE (it can tear), the pair main:hal.c:134 vs the tick\'s write',
              c['verdict'] == 'RACE' and 'TEAR' in c['why'] and [a['where'] for a in c['counterexample']] == ['hal.c:134', 'hal.c:110']
              and c['counterexample'][1]['kind'] == 'write', c)
        check('the rule: every access under the lock → PROTECTED; a size the harness did not report → RACE (conservative); a "(?)" lock '
              '(held on SOME paths) counts as not held',
              M.classify(SHARED_ATOMIC, {'g_ms': 4})[0]['verdict'] == 'PROTECTED' and M.classify(SHARED_TORN, {})[0]['verdict'] == 'RACE'
              and M.classify([{'var': 'x', 'accesses': [_acc('read', 'a', 'f:1', L, maybe=True), _acc('write', 'b', 'f:2', L)]}], {'x': 4})[0]['verdict'] == 'RACE')
        c = {x['var']: x for x in M.classify(SHARED_BROKEN, SIZES_RING)}['rx_head']
        check('the rule: a byte written by TWO threads (the broken flush) → RACE (an update can be lost); the pair = the two writes',
              c['verdict'] == 'RACE' and 'LOST' in c['why'] and [(x['kind'], x['where']) for x in c['counterexample']]
              == [('write', 'rx_ring_race.c:33'), ('write', 'hal.c:68')]
              and c['writers'] == ['<main>', 'polari_rx_isr'], c)
        check('a variable only one thread touches is not shared: classify skips it', M.classify([{'var': 'y', 'accesses': [_acc('write', 'a', 'f:1')]}], {}) == [])
        mk = lambda shared, sizes: {'verdict': 'analysed', 'shared': shared, 'sizes': sizes}  # noqa: E731
        o = M.outcome_of(mk(SHARED_ATOMIC, {'g_ms': 4}), M.find('hal-millis-race@uno-sim-rig'))
        check('atomic hal_millis → decided (unbounded) — the words say "not proved" and "no bound"', o['outcome'] == 'decided'
              and o['claim_status'] == 'decided (unbounded)' and 'not proved' in o['words'] and 'no bound' in o['words'] and 'proved' not in o['claim_status'], o)
        o = M.outcome_of(mk(SHARED_TORN, {'g_ms': 4}), M.find('hal-millis-race@uno-sim-rig-torn'))
        check('torn hal_millis → refuted, the counterexample = the two source lines (main\'s bare read vs the tick\'s write)',
              o['outcome'] == 'refuted' and o['counterexample']['var'] == 'g_ms' and 'hal.c:134' in o['counterexample']['pair']
              and 'hal.c:110' in o['counterexample']['pair'] and 'unprotected' in o['counterexample']['pair'], o['counterexample'])
        o = M.outcome_of(mk(SHARED_RING, SIZES_RING), M.find('rx-ring-race@uno-sim-rig'))
        check('the ring → decided (unbounded): every shared variable is byte-atomic with one writer', o['outcome'] == 'decided'
              and o['claim_status'] == 'decided (unbounded)' and 'NOTE' not in o['words'], o['words'])
        o = M.outcome_of(mk(SHARED_BROKEN, SIZES_RING), M.find('rx-ring-race@uno-sim-rig+broken-flush'))
        check('NEGATIVE CONTROL: the broken flush → refuted on rx_head', o['outcome'] == 'refuted' and o['counterexample']['var'] == 'rx_head', o['words'])
        o = M.outcome_of(mk([], {}), M.find('rx-ring-race@uno-sim-rig'))
        check('no shared variable at all → decided, but the words NOTE that rx_head/rx_tail/rx_ring never appeared (the harness missed them)',
              o['outcome'] == 'decided' and 'NOTE' in o['words'] and 'rx_head' in o['words'])
        o = M.outcome_of({'verdict': 'refused-at-compile', 'why': ['hal.c:25: static assertion failed: RX_RING must be a power of two']},
                         M.find('rx-ring-race@uno-sim-rig-ring512'))
        check('the source does not compile (hal.c\'s _Static_assert) → inapplicable, quoting it', o['outcome'] == 'inapplicable' and 'RX_RING' in o['words'])
        check('a timeout / no [mt] report → error — never a claim status (Mthread has no budget concept to be undetermined about)',
              M.outcome_of({'verdict': 'timeout'}, M.find('hal-millis-race@uno-sim-rig'))['claim_status'] == ''
              and M.outcome_of({'verdict': 'error', 'why': ['no [mt]']}, M.find('hal-millis-race@uno-sim-rig'))['outcome'] == 'error')

    def wrapper_parse():
        wp = _formal_engines_src('polari_mthread_check.py')
        if not wp:
            print('  SKIP wrapper_parse: prf-formal-engines source not present in this image (%s)'
                  % os.path.join(RFNODE, 'prf-formal-engines', 'polari_mthread_check.py'))
            return
        w = _load(wp, 'polari_mthread_check_selftest')
        got = w.parse(FIXTURE_TORN)
        g = {s['var']: s for s in got['shared']}
        check('the wrapper keeps the LAST race report (the fixed point, after 3 iterations), not the first "none"',
              got['iterations'] == 3 and 'g_ms' in g and got['mt_lines'][0].startswith('[mt] Possible') and len(got['mt_lines']) == 5, got['mt_lines'])
        check('polari-mthread-check parses Mthread\'s report: g_ms with its accesses (thread, line, lock) + the sizes Eva printed',
              set(g) >= {'g_ms'} and got['sizes'].get('g_ms') == 4 and any(a['thread'] == '<main>' and not a['protected_by'] for a in g['g_ms']['accesses'])
              and any(a['protected_by'] == [L] for a in g['g_ms']['accesses']), got)
        got = w.parse(FIXTURE_ATOMIC)
        check('…and the atomic build\'s report: every g_ms access protected by %s' % L,
              all(a['protected_by'] == [L] for s in got['shared'] if s['var'] == 'g_ms' for a in s['accesses']) and got['shared'], got)
        check('parse_protection: "unprotected" → none; "protected by (?)m" → m, maybe', w.parse_protection('unprotected') == ([], False)
              and w.parse_protection('protected by (?)m1, m2') == (['m1', 'm2'], True))

    def refusal():
        from firmwarefaults.custom import formal_engines as fe, formal_mthread as M
        from firmwarefaults.custom.sink import LocalSink
        saved = (fe.local_image, fe.topology_url, os.environ.get(fe.KNOB), fe.shutil.which, fe.image_engines)
        try:
            os.environ.pop(fe.KNOB, None)
            fe.local_image = lambda: ''
            fe.topology_url = lambda: ''
            fe.shutil.which = lambda b: None
            w = fe.resolve('mthread-check')
            check('no Mthread anywhere → refused, naming FORMAL_ENGINES_URL, prf-formal-engines and firmwarefaults.formal',
                  w['how'] == 'refused' and 'FORMAL_ENGINES_URL' in w['why'] and 'prf-formal-engines' in w['why'] and 'firmwarefaults.formal' in w['why'], w)
            try:
                M.run_check('hal-millis-race@uno-sim-rig', LocalSink(), home='/nonexistent-polari')
                why = ''
            except fe.FormalRefused as e:
                why = str(e)
            check('…run_check refuses before anything is generated (FormalRefused, the knob named)', 'FORMAL_ENGINES_URL' in why, why[:200])
            fe.local_image = lambda: 'sha256:0ld1mage'
            fe.image_engines = lambda: fe.PRE_LABEL_ENGINES
            w, wc = fe.resolve('mthread-check'), fe.resolve('cbmc-check')
            check('a local image built BEFORE sc-2c (no org.polari.engines label): CBMC still runs there, Mthread is refused with "rebuild it"',
                  wc['how'] == 'local-image' and w['how'] == 'refused' and 'predates mthread-check' in w['why'], (w, wc))
            fe.image_engines = saved[4]
            fe.local_image = lambda: ''
            os.environ[fe.KNOB] = 'http://127.0.0.1:9'
            fe._CAP.clear()
            w = fe.resolve('mthread-check')
            check('FORMAL_ENGINES_URL set but unreachable → mthread-check refused too, never a silent fallback',
                  w['how'] == 'refused' and 'unreachable' in w['why'] and 'FORMAL_ENGINES_URL' in w['why'], w)
            fe._CAP['http://127.0.0.1:9'] = (__import__('time').time(), {'engines': {'cbmc-check': {'available': True}}})
            w = fe.resolve('mthread-check')
            check('a reachable worker WITHOUT mthread-check (an sc-2b worker) → refused, "lacks mthread-check"', w['how'] == 'refused' and 'lacks mthread-check' in w['why'], w)
        finally:
            fe.local_image, fe.topology_url, fe.shutil.which, fe.image_engines = saved[0], saved[1], saved[3], saved[4]
            if saved[2] is None:
                os.environ.pop(fe.KNOB, None)
            else:
                os.environ[fe.KNOB] = saved[2]
            fe._CAP.clear()

    def bridge_and_rows():
        from firmwarefaults.custom import formal_mthread as M, formal as F
        files = M.model_files()
        check('the bridge files: mt_stubs/avr/interrupt.h + mt_stubs/util/atomic.h (searched first) over the CBMC stubs, unchanged',
              {'mt_stubs/avr/interrupt.h', 'mt_stubs/util/atomic.h', 'polari_mthread.h', 'stubs/avr/io.h', 'stubs/stdint.h'} <= set(files)
              and files['stubs/avr/interrupt.h'] == F.stub_files()['stubs/avr/interrupt.h'])
        intr, atom = files['mt_stubs/avr/interrupt.h'].decode(), files['mt_stubs/util/atomic.h'].decode()
        check('cli() → polari_irq_lock(), sei() → polari_irq_unlock(), ATOMIC_BLOCK → lock … unlock; both refuse without -DPOLARI_MTHREAD',
              '#define cli() polari_irq_lock()' in intr and '#define sei() polari_irq_unlock()' in intr and 'polari_irq_lock()' in atom
              and 'polari_irq_unlock()' in atom and '#error' in intr and '#error' in atom)
        for h in ('hal_millis_race.c', 'rx_ring_race.c'):
            src = open(os.path.join(M.MT_DIR, h)).read()
            check('%s #includes the variant\'s OWN hal.c (never a copy of hal_millis / hal_rx_pop) and spawns the ISR thread (POLARI_SPAWN = '
                  'Frama_C_thread_create + Frama_C_thread_start)' % h,
                  '#include "hal.c"' in src and 'POLARI_SPAWN(' in src and 'uint32_t hal_millis' not in src and 'int hal_rx_pop' not in src)
        hdr = files['polari_mthread.h'].decode()
        check('polari_mthread.h: Frama-C\'s own <mthread.h>; a thread is created then STARTED (created suspended otherwise — 0 iterations)',
              '#include <mthread.h>' in hdr and 'Frama_C_thread_start(Frama_C_thread_create(' in hdr)
        a = M.assumptions()
        check('the assumptions block (verbatim on the report): the global lock = interrupt masking; nested ISRs excluded; Mthread\'s race definition',
              'interrupt' in a and 'nested' in a.lower() and 'race' in a.lower() and len(a) > 300, a[:200])
        av = M.argv_for(M.find('rx-ring-race@uno-sim-rig+broken-flush'))
        check('the mthread-check argv: the harness, mt_stubs BEFORE stubs, machdep avr_16, -D POLARI_MTHREAD=1 (+ POLARI_BROKEN_FLUSH=1 for the control)',
              av[:2] == ['--src', 'rx_ring_race.c'] and av.index('mt_stubs') < av.index('stubs') and 'avr_16' in av and 'POLARI_MTHREAD=1' in av
              and 'POLARI_BROKEN_FLUSH=1' in av)
        rows = M.seed_rows()
        check('five Mthread FormalChecks seeded (engine frama-c-mthread, bound "unbounded", limits stated); the negative control speaks to no claim',
              {r['name']: r['expected'] for r in rows} == {'hal-millis-race@uno-sim-rig': 'decided', 'hal-millis-race@uno-sim-rig-torn': 'refuted',
                                                           'rx-ring-race@uno-sim-rig': 'decided', 'rx-ring-race@uno-sim-rig+broken-flush': 'refuted',
                                                           'rx-ring-race@uno-sim-rig-ring512': 'inapplicable'}
              and all(r['engine'] == 'frama-c-mthread' and r['bound'] == 'unbounded' and 'unbounded' in r['limits'] for r in rows)
              and M.find('rx-ring-race@uno-sim-rig+broken-flush')['claim'] is False)
        check('CBMC\'s four checks unchanged (names, expectations, bound k) and now carry bound "k=… (bounded)"; all_checks lists 4 + 5',
              [c['name'] for c in F.FORMAL_CHECKS] == ['hal-millis-not-torn@uno-sim-rig', 'hal-millis-not-torn@uno-sim-rig-torn', 'rx-ring-index-bound@uno-sim-rig',
                                                      'rx-ring-index-bound@uno-sim-rig-ring512']
              and [r['bound'] for r in F.seed_rows()] == ['k=2 (bounded)', 'k=2 (bounded)', 'k=4 (bounded)', 'k=4 (bounded)'] and len(M.all_checks()) == 9)
        from firmwarefaults.firmwarefaults_seed import FIRMWAREFAULTS_SEED_PAIRS
        n = [len(rows) for cname, _, rows in FIRMWAREFAULTS_SEED_PAIRS if cname == 'FormalCheck'][0]
        from mathproofs.mathproofs_basis import CHECKERS
        check('the seed carries 9 FormalChecks; mathproofs knows the checker frama-c-mthread', n == 9 and 'frama-c-mthread' in CHECKERS, n)

    return (rule_and_outcomes, wrapper_parse, refusal, bridge_and_rows)


#: REAL frama-c 33.0 output (excerpts, in order) of hal_millis_race.c on uno-sim-rig-torn / uno-sim-rig, 2026-10-02 — Mthread prints a
#: race report per iteration (the first is "none", before the tick thread was computed); the LAST one is the fixed point
FIXTURE_TORN = '''[eva:show] hal_millis_race.c:29: Frama_C_show_each_polari_size_g_ms: {4}
[mt] Possible read/write data races:
  none
[mt] Mutexes for concurrent accesses:
[mt] ***** Shared variables computed
[eva:show] hal_millis_race.c:29: Frama_C_show_each_polari_size_g_ms: {4}
[mt] *** Thread <main> computed
[mt] ***** Threads computed for iteration 3.
[mt] ***** Computing shared variables
[mt] Possible read/write data races:
  g_ms:
    read by polari_tick_isr at hal.c:110, protected by polari_irq_mutex
    read by <main> at hal.c:134, unprotected
    write by polari_tick_isr at hal.c:110, protected by polari_irq_mutex
[mt] Mutexes for concurrent accesses:
  g_ms  write protected by polari_irq_mutex,
        read protected by (?)polari_irq_mutex
[mt] ***** Shared variables computed
[mt] ******* Analysis performed, 3 iterations
'''
FIXTURE_ATOMIC = '''[eva:show] hal_millis_race.c:29: Frama_C_show_each_polari_size_g_ms: {4}
[mt] Possible read/write data races:
  none
[mt] ***** Threads computed for iteration 3.
[mt] ***** Computing shared variables
[mt] Possible read/write data races:
  g_ms:
    read by polari_tick_isr at hal.c:110, protected by polari_irq_mutex
    read by <main> at hal.c:132, protected by polari_irq_mutex
    write by polari_tick_isr at hal.c:110, protected by polari_irq_mutex
[mt] Mutexes for concurrent accesses:
  g_ms  protected by polari_irq_mutex
[mt] ***** Shared variables computed
[mt] ******* Analysis performed, 3 iterations
'''
