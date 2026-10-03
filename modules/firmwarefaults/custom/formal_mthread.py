"""
@module firmwarefaults.custom.formal_mthread

THE FORMAL TIER'S SECOND ENGINE (sc-2c; D-sc-6 ruled 2026-10-02 "Mthread can join the formal engines";
AI-Notes/evaluations/FRAMA_C_EVALUATION.md): Frama-C 33.0's Mthread plugin (inside Eva, LGPL-2.1, open since 31.0) asks a
question CBMC states only per bound — "is every access the ISR and the main loop SHARE either under the interrupt lock or
safe without it?" — and answers it UNBOUNDED (an interference fixed point over the whole program: no unwind, no k).

The bridge (custom/mthread_model/, assumptions in polari_mthread.h — stated once, quoted on every row): the variant's OWN
hal.c, unedited, preprocessed with -DPOLARI_MTHREAD against mthread_model/stubs (searched first: cli()/sei()/ATOMIC_BLOCK →
acquire/release of ONE global interrupt lock) then the CBMC stubs (registers as bytes, the AVR's integer widths). The
ISR runs in a Frama_C_thread_create'd thread holding that lock for its body; the main loop is the other thread.

    hal-millis-race@uno-sim-rig            HAL_MILLIS_ATOMIC 1 → expected decided (unbounded)
    hal-millis-race@uno-sim-rig-torn       HAL_MILLIS_ATOMIC 0 → expected refuted: g_ms read bare in hal_millis vs g_ms++ in the tick
    rx-ring-race@uno-sim-rig               the ring: ISR writes rx_head + the slot, main writes rx_tail → expected decided (unbounded)
    rx-ring-race@uno-sim-rig+broken-flush  NEGATIVE CONTROL (the harness's own broken flush also writes rx_head from main) →
                                           expected refuted; it speaks to NO claim (the firmware is not the broken code)
    rx-ring-race@uno-sim-rig-ring512       hal.c's _Static_assert refuses RX_RING 512 → inapplicable

Mthread reports every variable two threads touch, each access with its thread, line and the mutexes held. classify() is
the rule that turns that into his vocabulary (pure — the selftest feeds it):
    PROTECTED      every access of the variable holds the interrupt lock
    BYTE-ATOMIC    the variable (an array: its element) is ONE byte — one lds/sts, which no interrupt can split — and only ONE
                   thread ever writes it (a single writer cannot lose an update)
    RACE           anything else: an unprotected access to a multi-byte object (it can TEAR), or a byte written by two threads
                   (an update can be LOST), or a variable whose size the harness did not report (conservative)
    no RACE → `decided (unbounded)` · a RACE → `refuted` (the two source lines are the counterexample) · the source does not
    compile → `inapplicable` · Mthread unavailable → refusal naming FORMAL_ENGINES_URL · never `proved` (the bridge is OUR
    model of the core, as CBMC's byte model is) · a run that did not reach Mthread's report → error (never a claim status).

    run_check(name, sink, home=None) → the FormalCheck dict · outcome_of(res, check) and classify(shared, sizes) are pure
"""
import datetime
import json
import os

from firmwarefaults.custom import formal_engines as fe
from firmwarefaults.custom import formal as F

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT_DIR = os.path.join(HERE, 'custom', 'mthread_model')
ENGINE = 'mthread-check'
IRQ_LOCK = 'polari_irq_mutex'
BOUND = 'unbounded'


def assumptions():
    """The bridge's assumptions, verbatim from polari_mthread.h (the block between the ASSUMPTIONS markers)."""
    src = open(os.path.join(MT_DIR, 'polari_mthread.h')).read()
    a, b = src.find('ASSUMPTIONS BEGIN'), src.find('ASSUMPTIONS END')
    body = src[a + len('ASSUMPTIONS BEGIN'):b] if a >= 0 and b > a else ''
    return '\n'.join(ln.strip().lstrip('*').strip() for ln in body.splitlines()).strip()


LIMITS = ('Mthread decides the C-level interference of the two threads over the WHOLE program (unbounded: no unwind, no k). The '
          'threads, the lock and the byte-atomicity rule are OUR model of the AVR core (custom/mthread_model/polari_mthread.h): '
          'the global interrupt lock models SREG.I masking; an ISR holds it for its whole body; nested ISRs and nested masking '
          'are excluded; machdep avr_16 (Frama-C\'s AVR model: int 16, long 32, pointers 16, as avr-gcc). Never `proved` — the instruction level is the simulation '
          'tier\'s, cross-checked on the twin.')
_MILLIS = {
    'scenario': 'torn-millis-read', 'function': 'hal_millis + ISR(TIMER2_COMPA_vect)',
    'property_text': 'every access the tick ISR and the main loop share (g_ms) holds the interrupt lock, or is one byte with one writer '
                     '— so hal_millis cannot read g_ms torn',
    'harness_files': ['hal_millis_race.c'], 'shared_of_interest': ['g_ms'],
    'model': 'thread "polari_tick_thread": repeatedly the real ISR(TIMER2_COMPA_vect) body under the interrupt lock; thread <main>: '
             'repeatedly the real hal_millis(); ATOMIC_BLOCK = the interrupt lock held across the read',
    'defines': ['POLARI_MTHREAD=1'], 'budget_s': 120.0,
}
_RING = {
    'scenario': 'rx-ring-over-256', 'function': 'hal_rx_pop + ISR(USART_RX_vect)',
    'property_text': 'every access the RX ISR and the main loop share (rx_head, rx_tail, rx_ring) holds the interrupt lock, or is one byte '
                     'written by one thread only — the single-producer / single-consumer discipline',
    'harness_files': ['rx_ring_race.c'], 'shared_of_interest': ['rx_head', 'rx_tail', 'rx_ring'],
    'model': 'thread "polari_rx_thread": repeatedly the real ISR(USART_RX_vect) body under the interrupt lock; thread <main>: '
             'repeatedly the real hal_rx_pop()',
    'defines': ['POLARI_MTHREAD=1'], 'budget_s': 120.0,
}


def _mc(name, title, variant, base, expected, notes='', defines=(), claim=True):
    d = dict(base)
    d.update(name=name, title=title, variant=variant, expected=expected, notes=notes, defines=list(base['defines']) + list(defines), claim=claim)
    return d


MTHREAD_CHECKS = [
    _mc('hal-millis-race@uno-sim-rig', 'g_ms is never touched outside the interrupt lock — the shipped build (HAL_MILLIS_ATOMIC 1)', 'uno-sim-rig',
        _MILLIS, 'decided', 'scenario 1\'s AFTER build: ATOMIC_BLOCK → the lock, held by both sides'),
    _mc('hal-millis-race@uno-sim-rig-torn', 'g_ms is read bare against the tick — the torn build (HAL_MILLIS_ATOMIC 0)', 'uno-sim-rig-torn',
        _MILLIS, 'refuted', 'scenario 1\'s BEFORE build: the four-byte g_ms read in hal_millis with the lock NOT held'),
    _mc('rx-ring-race@uno-sim-rig', 'the RX ring: one writer per index, one byte each — the shipped ring (RX_RING 64)', 'uno-sim-rig',
        _RING, 'decided', 'scenario 1b\'s safe side: rx_head written only by the ISR, rx_tail only by main, uint8_t each'),
    _mc('rx-ring-race@uno-sim-rig+broken-flush', 'NEGATIVE CONTROL — a flush in main that also writes rx_head (the harness\'s, not the firmware\'s)',
        'uno-sim-rig', _RING, 'refuted', 'the selftest\'s negative control: two writers of rx_head must be found; speaks to no claim',
        defines=['POLARI_BROKEN_FLUSH=1'], claim=False),
    _mc('rx-ring-race@uno-sim-rig-ring512', 'the RX ring at 512 slots — refused by hal.c\'s static guard', 'uno-sim-rig-ring512', _RING,
        'inapplicable', 'scenario 1b: the _Static_assert refuses the source, so there is no program to analyse'),
]


def find(name):
    return next((dict(c) for c in MTHREAD_CHECKS if c['name'] == name), None)


def seed_rows():
    keys = ('name', 'title', 'scenario', 'variant', 'function', 'property_text', 'model', 'budget_s', 'expected', 'notes')
    out = []
    for c in MTHREAD_CHECKS:
        r = {k: c[k] for k in keys}
        r.update(harness=', '.join(c['harness_files']), harness_files_json=json.dumps(c['harness_files']), width='avr_16', bound_k=0, unwind=0,
                 bound=BOUND, defines_json=json.dumps(c['defines']), volatile_models_json='[]', isr='', engine='frama-c-mthread',
                 limits=LIMITS, outcome='not-run')
        out.append(r)
    return out


def _base(var):
    return var.split('[')[0].split('.')[0].split('-')[0]


def classify(shared, sizes, lock=IRQ_LOCK):
    """Mthread's shared variables + the harness-reported sizes → [{var, size, writers, verdict PROTECTED|BYTE-ATOMIC|RACE, why,
    lines}] for every variable touched by two threads. Pure."""
    out = []
    for s in shared or []:
        acc = s.get('accesses') or []
        threads = {a['thread'] for a in acc}
        if len(threads) < 2:
            continue
        var = s['var']
        size = sizes.get(_base(var))
        writers = sorted({a['thread'] for a in acc if a['kind'] == 'write'})
        held = lambda a: lock in (a.get('protected_by') or []) and not a.get('maybe')  # noqa: E731
        bare = [a for a in acc if not held(a)]
        if not bare:
            v, why = 'PROTECTED', 'every access holds %s' % lock
        elif size == 1 and len(writers) <= 1:
            v, why = 'BYTE-ATOMIC', 'one byte (one lds/sts — no interrupt can split it) with a single writer (%s): unprotected but cannot tear or lose an update' % (
                writers[0] if writers else 'none')
        elif size == 1:
            v, why = 'RACE', 'one byte written by %d threads (%s) — an update can be LOST' % (len(writers), ', '.join(writers))
        elif size is None:
            v, why = 'RACE', 'its size was not reported by the harness — conservatively a race (%d unprotected access(es))' % len(bare)
        else:
            v, why = 'RACE', '%d bytes accessed with the lock NOT held — the access can TEAR' % size
        pair = []
        if v == 'RACE' and size == 1:          # a lost update: one write from each of two threads (the unprotected one first)
            ws = sorted([a for a in acc if a['kind'] == 'write'], key=held)
            pair = ws[:1] + [a for a in ws if a['thread'] != ws[0]['thread']][:1]
        elif v == 'RACE':                      # a tear: an unprotected access + a write from the other thread
            a0 = bare[0]
            other = [a for a in acc if a['thread'] != a0['thread'] and (a['kind'] == 'write' or a0['kind'] == 'write')]
            pair = [a0] + other[:1]
        out.append({'var': var, 'size': size, 'writers': writers, 'threads': sorted(threads), 'verdict': v, 'why': why,
                    'lines': [a.get('text') or '%s by %s at %s' % (a['kind'], a['thread'], a['where']) for a in acc],
                    'counterexample': [{'kind': a['kind'], 'thread': a['thread'], 'where': a['where'],
                                        'protected_by': a.get('protected_by') or []} for a in pair]})
    return out


def outcome_of(res, check):
    """polari-mthread-check's result → {outcome, claim_status, words, classes, counterexample}. Pure — never `proved`."""
    v = (res or {}).get('verdict', 'error')
    if v == 'refused-at-compile':
        return {'outcome': 'inapplicable', 'claim_status': 'inapplicable', 'classes': [], 'counterexample': {},
                'words': 'the source does not compile, so there is no program to analyse: %s' % ' '.join(res.get('why') or [])[:300]}
    if v == 'timeout':
        return {'outcome': 'error', 'claim_status': '', 'classes': [], 'counterexample': {},
                'words': 'Mthread did not reach its fixed point inside the budget (%s s) — an engine failure, not a claim status' % check.get('budget_s')}
    if v != 'analysed':
        return {'outcome': 'error', 'claim_status': '', 'classes': [], 'counterexample': {},
                'words': 'the analysis failed to run: %s' % ' '.join((res or {}).get('why') or [])[:300]}
    cls = classify(res.get('shared'), res.get('sizes') or {})
    races = [c for c in cls if c['verdict'] == 'RACE']
    seen = ', '.join('%s %s' % (c['var'], c['verdict']) for c in cls) or 'no variable is touched by both threads'
    missing = [x for x in check.get('shared_of_interest', []) if x not in {_base(c['var']) for c in cls}]
    if races:
        r = races[0]
        cx = {'var': r['var'], 'why': r['why'], 'accesses': r['counterexample'], 'lines': r['lines'],
              'pair': ' vs '.join('%s by %s at %s (%s)' % (a['kind'], a['thread'], a['where'], 'protected by ' + ', '.join(a['protected_by'])
                                                             if a['protected_by'] else 'unprotected') for a in r['counterexample'])}
        return {'outcome': 'refuted', 'claim_status': 'refuted', 'classes': cls, 'counterexample': cx,
                'words': 'Mthread found a race on %s: %s — %s (all shared: %s)' % (r['var'], cx['pair'], r['why'], seen)}
    words = ('no race: %s — decided (unbounded): Mthread\'s interference fixed point covers every interleaving of the two threads, with '
             'no bound; not proved: the threads, the lock and the byte rule are our model of the core' % seen)
    if missing:
        words += '; NOTE: %s never appeared as shared (the harness did not reach it — check the model)' % ', '.join(missing)
    return {'outcome': 'decided', 'claim_status': 'decided (unbounded)', 'classes': cls, 'counterexample': {}, 'words': words}


def model_files():
    """The bridge as the worker sees it: mt_stubs/ (searched first), stubs/ (the CBMC stubs, unchanged), the harness, the header."""
    files = {}
    root = os.path.join(MT_DIR, 'stubs')
    for d, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith('.h'):
                fp = os.path.join(d, fn)
                files['mt_stubs/' + os.path.relpath(fp, root)] = open(fp, 'rb').read()
    files['polari_mthread.h'] = open(os.path.join(MT_DIR, 'polari_mthread.h'), 'rb').read()
    files.update(F.stub_files())
    return files


def argv_for(check):
    a = []
    for f in check['harness_files']:
        a += ['--src', f]
    a += ['-I', 'mt_stubs', '-I', 'stubs', '-I', '.', '--machdep', 'avr_16']
    for d in check['defines']:
        a += ['-D', d]
    return a + ['--timeout', '%g' % check['budget_s'], '--out', 'result.json']


def run_check(name, sink, home=None, check=None):
    """Run ONE Mthread check: gen the variant, send hal.c + the bridge to mthread-check, classify, write the row and (unless a
    negative control) the claim's formal tier beside CBMC's. Raises formal_engines.FormalRefused naming FORMAL_ENGINES_URL."""
    from firmwarefaults.custom import sink as S
    from firmwarefaults.custom.claim_bridge import claim_name, add_evidence
    check = check or find(name)
    if check is None:
        raise fe.FormalRefused('no Mthread FormalCheck %r — one of %s' % (name, ', '.join(c['name'] for c in MTHREAD_CHECKS)))
    where = fe.resolve(ENGINE)
    if where['how'] == 'refused':
        raise fe.FormalRefused(where['why'])
    home = home or S.home()
    t0 = datetime.datetime.now()
    row, proj = F.gen_project(check['variant'], home)
    files = model_files()
    for f in check['harness_files']:
        files[f] = open(os.path.join(MT_DIR, f), 'rb').read()
    for fn in ('hal.c', 'hal.h', 'board_config.h'):
        files[fn] = proj[fn]
    r = fe.run(ENGINE, argv_for(check), files, timeout=int(check['budget_s']) + 60)
    try:
        res = json.loads((r['files'].get('result.json') or b'{}').decode())
    except ValueError:
        res = {}
    if not res:
        res = {'verdict': 'error', 'why': [(r.get('stderr') or r.get('stdout') or '')[-400:]]}
    o = outcome_of(res, check)
    out_dir = os.path.join(home, 'formal', S.safe_name(check['name']))
    os.makedirs(out_dir, exist_ok=True)
    report = '\n'.join(res.get('mt_lines') or [])
    open(os.path.join(out_dir, 'mthread-report.txt'), 'w').write(report)
    open(os.path.join(out_dir, 'result.json'), 'w').write(json.dumps(res, indent=1))
    harness_sha = F._sha(b''.join(files[f] for f in check['harness_files']))
    bridge_sha = F._sha(b''.join(v for k, v in sorted(files.items()) if k.startswith('mt_stubs/') or k == 'polari_mthread.h'))
    build_name = row['name']
    cname = claim_name(check['scenario'], build_name) if check.get('claim', True) else ''
    step = res.get('step') or {}
    fc = dict(seed_rows()[[c['name'] for c in MTHREAD_CHECKS].index(check['name'])], **{
        'name': check['name'], 'build_name': build_name, 'engine_version': res.get('frama_c_version', ''),
        'engine_where': '%s %s' % (r.get('how'), r.get('where')), 'outcome': o['outcome'], 'claim_status': o['claim_status'],
        'verdict_raw': res.get('verdict', ''), 'outcome_words': o['words'],
        'properties_json': json.dumps(o['classes']), 'failed_property': (o['counterexample'] or {}).get('var', ''),
        'counterexample_json': json.dumps(o['counterexample']), 'trace_sha256': F._sha(report) if report else '',
        'trace_steps': len(res.get('mt_lines') or []), 'source_sha256': F._sha(proj['hal.c']), 'harness_sha256': harness_sha,
        'wall_s': float(res.get('wall_s', 0.0)), 'cpu_s': float(res.get('cpu_s', 0.0) or 0.0), 'peak_rss_mb': float(res.get('peak_rss_mb', 0.0) or 0.0),
        'claim': cname if o['outcome'] != 'error' else '', 'ran_at': t0.isoformat(timespec='seconds'),
        'repro_json': json.dumps({'inputs': [{'label': 'hal.c (%s)' % check['variant'], 'sha256': F._sha(proj['hal.c'])},
                                             {'label': 'board_config.h', 'sha256': F._sha(proj['board_config.h'])},
                                             {'label': 'harness %s' % '+'.join(check['harness_files']), 'sha256': harness_sha},
                                             {'label': 'the bridge (mt_stubs/ + polari_mthread.h)', 'sha256': bridge_sha},
                                             {'label': 'stubs/ (the CBMC stubs, unchanged)', 'sha256': F._sha(b''.join(v for k, v in sorted(files.items()) if k.startswith('stubs/')))}],
                                  'tools': {'frama-c': res.get('frama_c_version', ''), 'engine': fe.digest(ENGINE)},
                                  'knobs': {'argv': ['polari-mthread-check'] + argv_for(check), 'frama_c_argv': step.get('argv'), 'bound': BOUND},
                                  'seeds': {'deterministic': True, 'why': 'Eva/Mthread compute a fixed point: the same program gives the same report'},
                                  'generated_files': [{'path': 'mthread-report.txt', 'sha256': F._sha(report) if report else ''}, {'path': 'result.json'}],
                                  'how_to_rerun': 'pol faults formal run %s' % check['name'],
                                  'rule': 'every result carries the initial conditions that produced it (2026-09-26)'}, default=str)})
    sink.upsert('FormalCheck', fc)
    if o['outcome'] != 'error' and cname:
        add_evidence(sink, cname, {'tier': 'formal', 'status': o['outcome'], 'ref': check['name'], 'measure': o['claim_status'], 'bound': BOUND,
                                   'engine': res.get('frama_c_version', ''), 'trace_sha256': fc['trace_sha256']},
                     base=dict(F.claim_base(check, build_name), assumptions_json=json.dumps([LIMITS, assumptions()]),
                               provenance='firmwarefaults formal tier (sc-2c: Frama-C/Mthread)'), counterexample=dict(o['counterexample'], check=check['name']) if o['counterexample'] else None,
                     checker='frama-c-mthread', certificate=check['name'])
        sink.upsert('ProofRun', {'name': '%s@mthread@%s' % (cname, fc['ran_at']), 'description': 'FormalCheck %s' % check['name'], 'claim': cname,
                                 'checker': 'frama-c-mthread', 'checker_version': res.get('frama_c_version', ''),
                                 'verdict': {'decided': 'holds', 'refuted': 'refuted', 'inapplicable': 'inapplicable'}.get(o['outcome'], 'undecided'),
                                 'detail_json': json.dumps({'check': check['name'], 'outcome': o['outcome'], 'claim_status': o['claim_status'],
                                                            'classes': o['classes'], 'counterexample': o['counterexample']}, default=str),
                                 'output_tail': report[-400:], 'elapsed_s': fc['wall_s'], 'rows_state_hash': fc['source_sha256'], 'ran_at': fc['ran_at'],
                                 'ran_where': fc['engine_where'], 'notes': 'Mthread interference analysis — decided (unbounded) is never proved'})
    fc['_raw'] = res
    return fc


def all_checks():
    """Both engines' FormalChecks, CBMC first (the table, the CLI and the API list them together)."""
    return list(F.FORMAL_CHECKS) + list(MTHREAD_CHECKS)


def find_any(name):
    return F.find(name) or find(name)


def run_any(name, sink, home=None):
    """Dispatch by the check's engine: an Mthread check → run_check here, a CBMC one → formal.run_check (unchanged)."""
    return run_check(name, sink, home=home) if find(name) else F.run_check(name, sink, home=home)
