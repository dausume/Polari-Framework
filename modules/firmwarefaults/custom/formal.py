"""
@module firmwarefaults.custom.formal

THE FORMAL TIER, narrow (FIRMWARE_SCENARIO_PLAN.md §5 tier 2, sc-2b): a FormalCheck row = one C function of one firmware
variant + one property + one bound, checked by CBMC through the formal engines seam (custom/formal_engines.py →
prf-formal-engines: goto-cc → goto-instrument → cbmc, driven by polari-cbmc-check). The harness (custom/cbmc_model/*.c) #includes
the variant's OWN generated hal.c, unedited, against stubs/ (registers as bytes, SREG.I as a variable, ATOMIC_BLOCK as
save-clear-restore); the interrupt is CBMC nondeterminism.

    hal-millis-not-torn@uno-sim-rig       HAL_MILLIS_ATOMIC 1 → expected decided (bounded)
    hal-millis-not-torn@uno-sim-rig-torn  HAL_MILLIS_ATOMIC 0 → expected refuted, with the C trace (the bytes, the ticks)
    rx-ring-index-bound@uno-sim-rig       the RX ring's indices / fill / order under an RX ISR between any two statements
    rx-ring-index-bound@uno-sim-rig-ring512   RX_RING 512 → hal.c's _Static_assert refuses it → inapplicable

His vocabulary: decided (bounded, k=…) ≠ proved; refuted keeps its counterexample; inapplicable = the source does not exist
as a program here; undetermined = the bound or the budget decided nothing. Each run adds the `formal` evidence tier to the
scenario's claim for that build (custom/claim_bridge.add_evidence) and records cbmc's version, the bound, wall time, peak
RSS and the counterexample trace's sha256 — the reproducibility rule.

    run_check(name, sink, home=None) → the FormalCheck dict · outcome_of(result, check) is pure (the selftest feeds it)
"""
import datetime
import hashlib
import json
import os

from firmwarefaults.custom import formal_engines as fe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAL_DIR = os.path.join(HERE, 'custom', 'cbmc_model')
LIMITS = ('CBMC has no AVR architecture: --16 (LP32 — int 16 bits as avr-gcc, long 32) on a little-endian target like the AVR; pointers '
          'are 32 bits (the AVR\'s are 16). The registers are plain bytes (stubs/avr/io.h); SREG.I is a variable; ATOMIC_BLOCK is '
          'save-clear-restore. The byte-wise read of g_ms and "an interrupt only while I is set" are OUR model of the core, '
          'cross-checked by the simulation tier on the twin — CBMC decides the C-level property under that model, up to the bound.')
_HAL_MILLIS = {
    'scenario': 'torn-millis-read', 'function': 'hal_millis',
    'property_text': 'hal_millis() returns a value g_ms actually held during the call (before a tick or after it) — never a mix of '
                     'bytes from both; interrupts are enabled again when it returns',
    'harness_files': ['hal_millis_isr.c', 'g_ms_avr_model.c'], 'volatile_models': ['g_ms:polari_avr_read_g_ms'], 'isr': 'polari_tick',
    'model': 'every read of the volatile g_ms → the AVR\'s four one-byte loads (low first) with up to K tick ISRs between any two '
             'loads (goto-instrument --nondet-volatile-model), and the tick also between any two statements that touch g_ms '
             '(goto-instrument --isr) — always only while SREG.I is set',
    'bound_k': 2, 'unwind': 4, 'defines': ['POLARI_K=2'], 'budget_s': 300.0,
    'cx_vars': ['init', 'pre', 'b0', 'b1', 'b2', 'b3', 'r', 'post'], 'cx_isr': 'polari_isr_timer2_compa',
    'bound_words': 'k = 2 ticks in any gap between two loads (+ the --isr points), unwind 4',
}
_RX_RING = {
    'scenario': 'rx-ring-over-256', 'function': 'hal_rx_pop + ISR(USART_RX_vect)',
    'property_text': 'rx_head and rx_tail never exceed RX_RING-1; the ring\'s fill equals bytes accepted minus bytes popped; a pop '
                     'returns bytes in arrival order — from ANY valid start state',
    'harness_files': ['rx_ring_bound.c'], 'volatile_models': [], 'isr': 'polari_rx_irq',
    'model': 'from an arbitrary valid ring state (rx_head, rx_tail any values in 0..RX_RING-1), K steps each either the RX '
             'interrupt (only while SREG.I is set) or hal_rx_pop(), with the RX interrupt also between any two statements of '
             'hal_rx_pop that touch the ring (goto-instrument --isr)',
    'bound_k': 4, 'unwind': 6, 'defines': ['POLARI_STEPS=4'], 'budget_s': 600.0,
    'cx_vars': ['h', 't', 'b'], 'cx_isr': 'polari_isr_usart_rx',
    'bound_words': 'k = 4 steps from an arbitrary valid start state (RX_RING as shipped: 64), unwind 6',
}


def _fc(name, title, variant, base, expected, notes=''):
    d = dict(base)
    d.update(name=name, title=title, variant=variant, expected=expected, notes=notes)
    return d


FORMAL_CHECKS = [
    _fc('hal-millis-not-torn@uno-sim-rig', 'hal_millis cannot tear — the shipped build (HAL_MILLIS_ATOMIC 1)', 'uno-sim-rig', _HAL_MILLIS,
        'decided', 'the AFTER build of scenario 1: ATOMIC_BLOCK masks the tick across the four loads'),
    _fc('hal-millis-not-torn@uno-sim-rig-torn', 'hal_millis CAN tear — the bare read (HAL_MILLIS_ATOMIC 0)', 'uno-sim-rig-torn', _HAL_MILLIS,
        'refuted', 'the BEFORE build of scenario 1: CBMC must find the interleaving the twin forced at hal_millis+0x4'),
    _fc('rx-ring-index-bound@uno-sim-rig', 'the RX ring\'s indices stay in range — the shipped ring (RX_RING 64, uint8_t indices)',
        'uno-sim-rig', _RX_RING, 'decided', 'scenario 1b\'s safe side: one-byte indices under a masked increment'),
    _fc('rx-ring-index-bound@uno-sim-rig-ring512', 'the RX ring at 512 slots — refused by hal.c\'s static guard', 'uno-sim-rig-ring512',
        _RX_RING, 'inapplicable', 'scenario 1b: the _Static_assert refuses the source, so there is no program to check'),
]


def find(name):
    return next((dict(c) for c in FORMAL_CHECKS if c['name'] == name), None)


def seed_rows():
    """FormalCheck rows as seeded (not-run): the definition; a run fills the outcome."""
    keys = ('name', 'title', 'scenario', 'variant', 'function', 'property_text', 'model', 'bound_k', 'unwind', 'isr', 'budget_s', 'expected', 'notes')
    out = []
    for c in FORMAL_CHECKS:
        r = {k: c[k] for k in keys}
        r.update(harness=', '.join(c['harness_files']), harness_files_json=json.dumps(c['harness_files']), width='16',
                 defines_json=json.dumps(c['defines']), volatile_models_json=json.dumps(c['volatile_models']), engine='cbmc', limits=LIMITS,
                 outcome='not-run', bound='k=%s (bounded)' % c['bound_k'])
        out.append(r)
    return out


def _sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _int(v):
    try:
        return int(str(v).rstrip('ulUL'), 0)
    except (TypeError, ValueError):
        return v


def counterexample(traces, check):
    """The failing property's trace → the values a person reads: the named locals' LAST values, how many times the ISR ran."""
    if not traces:
        return {}
    t = traces[0]
    vals, isr_calls = {}, 0
    for st in t.get('steps') or []:
        if st.get('step') == 'assign':
            short = st.get('lhs', '').split('::')[-1]
            if short in check.get('cx_vars', []):
                vals[short] = _int(st.get('value'))
        elif st.get('step') == 'call' and st.get('function') == check.get('cx_isr'):
            isr_calls += 1
    out = {'property': t.get('property', ''), 'description': t.get('description', ''), 'values': vals, 'isr_calls': isr_calls,
           'trace_steps': t.get('raw_steps', 0)}
    if check['function'] == 'hal_millis' and all(k in vals for k in ('r', 'pre', 'post')):
        out['reads'] = ('pre 0x%08X · returned 0x%08X · post 0x%08X — the bytes b0..b3 = %s' % (
            vals['pre'], vals['r'], vals['post'], ' '.join('0x%02X' % vals[k] for k in ('b0', 'b1', 'b2', 'b3') if isinstance(vals.get(k), int))))
    return out


def outcome_of(res, check):
    """polari-cbmc-check's result → {outcome, claim_status, words}. Pure — his vocabulary, never `proved`."""
    v = (res or {}).get('verdict', 'error')
    k, u = check.get('bound_k'), check.get('unwind')
    if v == 'holds':
        return {'outcome': 'decided', 'claim_status': 'decided (bounded, k=%s)' % k,
                'words': 'every property holds up to the bound (%s); the unwinding assertions hold too — decided (bounded), not proved: '
                         'a longer run or a weaker model is outside what was checked' % check.get('bound_words', 'k=%s, unwind %s' % (k, u))}
    if v == 'refuted':
        failed = [p for p in res.get('properties', []) if p.get('status') == 'FAILURE' and '.unwind.' not in p.get('property', '')]
        return {'outcome': 'refuted', 'claim_status': 'refuted',
                'words': 'CBMC found an interleaving that breaks it: %s (%s)' % (failed[0]['description'] if failed else '?',
                                                                                failed[0]['property'] if failed else '?')}
    if v == 'bound-too-small':
        return {'outcome': 'undetermined', 'claim_status': 'undetermined',
                'words': 'only an unwinding assertion failed: the bound (unwind %s) is too small to decide anything — nothing is said of '
                         'the property' % u}
    if v == 'refused-at-compile':
        why = ' '.join(res.get('why') or [])[:300]
        return {'outcome': 'inapplicable', 'claim_status': 'inapplicable',
                'words': 'the source does not compile, so there is no program to check: %s' % why}
    if v == 'timeout':
        return {'outcome': 'undetermined', 'claim_status': 'undetermined',
                'words': 'the budget (%s s) ran out before CBMC decided — undecided, never a counterexample' % check.get('budget_s')}
    return {'outcome': 'error', 'claim_status': '', 'words': 'the check failed to run: %s' % ' '.join((res or {}).get('why') or [])[:300]}


def gen_project(variant, home):
    """The variant's generated project (offline, pinned contract) — no compile needed for a formal check."""
    from board.custom import gen
    from firmwarefaults.custom import scenarios as SC
    work = os.path.join(home, 'formal-gen', variant)
    row = gen.gen('uno', None, work, variant=variant, variant_rows=SC.scenario_variants())
    p = row['project_dir']
    return row, {fn: open(os.path.join(p, fn), 'rb').read() for fn in sorted(os.listdir(p)) if fn.endswith(('.c', '.h'))}


def stub_files():
    out = {}
    root = os.path.join(FORMAL_DIR, 'stubs')
    for d, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith('.h'):
                fp = os.path.join(d, fn)
                out[os.path.relpath(fp, FORMAL_DIR)] = open(fp, 'rb').read()
    return out


def argv_for(check):
    a = []
    for f in check['harness_files']:
        a += ['--src', f]
    a += ['-I', 'stubs', '-I', '.', '--width', '16']
    for m in check['volatile_models']:
        a += ['--volatile-model', m]
    if check.get('isr'):
        a += ['--isr', check['isr']]
    for d in check['defines']:
        a += ['-D', d]
    return a + ['--unwind', str(check['unwind']), '--timeout', '%g' % check['budget_s'], '--out', 'result.json', '--trace', 'trace.json']


def claim_base(check, build_name):
    from firmwarefaults.custom import scenarios as SC
    from firmwarefaults.custom.claim_bridge import _latex
    sc = SC.find(check['scenario']) or {}
    return {'description': 'Firmware build %s (variant %s) under scenario %s is free of fault %s (%s) — stated by the formal tier' % (
                build_name, check['variant'], check['scenario'], sc.get('fault', ''), sc.get('fault_class', '')),
            'kind': 'safe-under-scenario', 'statement_json': '{}', 'statement_latex': _latex(build_name, check['scenario'], sc.get('fault_class', '')),
            'about_refs_json': json.dumps(['Scenario:%s' % check['scenario'], 'FirmwareBuild:%s' % build_name,
                                           '%s:%s' % (sc.get('fault_class', ''), sc.get('fault', ''))]),
            'assumptions_json': json.dumps([LIMITS]), 'proof_status': 'conjectured', 'checker': '', 'counterexample_json': '{}',
            'evidence_level': 'none', 'provenance': 'firmwarefaults formal tier (sc-2b)'}


def run_check(name, sink, home=None, check=None):
    """Run ONE FormalCheck: gen the variant, send hal.c + the harness + stubs to cbmc-check, map the verdict, write the row and
    the claim's formal tier. Raises formal_engines.FormalRefused when no engine resolves (the reason names the knob)."""
    from firmwarefaults.custom import sink as S
    from firmwarefaults.custom.claim_bridge import claim_name, add_evidence
    check = check or find(name)
    if check is None:
        raise fe.FormalRefused('no FormalCheck %r — one of %s' % (name, ', '.join(c['name'] for c in FORMAL_CHECKS)))
    where = fe.resolve('cbmc-check')        # refuse BEFORE generating anything (the reason names FORMAL_ENGINES_URL)
    if where['how'] == 'refused':
        raise fe.FormalRefused(where['why'])
    home = home or S.home()
    t0 = datetime.datetime.now()
    row, proj = gen_project(check['variant'], home)
    files = dict(stub_files())
    for f in check['harness_files']:
        files[f] = open(os.path.join(FORMAL_DIR, f), 'rb').read()
    for fn in ('hal.c', 'hal.h', 'board_config.h'):
        files[fn] = proj[fn]
    r = fe.run('cbmc-check', argv_for(check), files, timeout=int(check['budget_s']) + 60)
    try:
        res = json.loads((r['files'].get('result.json') or b'{}').decode())
    except ValueError:
        res = {'verdict': 'error', 'why': [(r.get('stderr') or r.get('stdout') or '')[-400:]]}
    trace_bytes = r['files'].get('trace.json') or b'[]'
    try:
        traces = json.loads(trace_bytes.decode())
    except ValueError:
        traces = []
    o = outcome_of(res, check)
    cx = counterexample(traces, check) if o['outcome'] == 'refuted' else {}
    out_dir = os.path.join(home, 'formal', S.safe_name(check['name']))
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'trace.json'), 'wb').write(trace_bytes)
    open(os.path.join(out_dir, 'result.json'), 'w').write(json.dumps(res, indent=1))
    harness_sha = _sha(b''.join(files[f] for f in check['harness_files']))
    build_name = row['name']
    cname = claim_name(check['scenario'], build_name)
    words = o['words'] + ('; counterexample: %s' % cx['reads'] if cx.get('reads') else '')
    fc = dict(seed_rows()[[c['name'] for c in FORMAL_CHECKS].index(check['name'])] if find(check['name']) else {}, **{
        'name': check['name'], 'build_name': build_name, 'engine_version': res.get('cbmc_version', ''), 'engine_where': '%s %s' % (r.get('how'), r.get('where')),
        'outcome': o['outcome'], 'claim_status': o['claim_status'], 'verdict_raw': res.get('verdict', ''), 'outcome_words': words,
        'properties_json': json.dumps([p for p in res.get('properties', []) if 'assertion' in p.get('property', '') or p.get('status') != 'SUCCESS']),
        'failed_property': cx.get('property', ''), 'counterexample_json': json.dumps(cx), 'trace_sha256': _sha(trace_bytes) if traces else '',
        'trace_steps': int(cx.get('trace_steps', 0)), 'source_sha256': _sha(proj['hal.c']), 'harness_sha256': harness_sha,
        'wall_s': float(res.get('wall_s', 0.0)), 'cpu_s': float(res.get('cpu_s', 0.0)), 'peak_rss_mb': float(res.get('peak_rss_mb', 0.0)),
        'claim': cname if o['outcome'] != 'error' else '', 'ran_at': t0.isoformat(timespec='seconds'),
        'repro_json': json.dumps({'inputs': [{'label': 'hal.c (%s)' % check['variant'], 'sha256': _sha(proj['hal.c'])},
                                             {'label': 'board_config.h', 'sha256': _sha(proj['board_config.h'])},
                                             {'label': 'harness %s' % '+'.join(check['harness_files']), 'sha256': harness_sha},
                                             {'label': 'stubs/', 'sha256': _sha(b''.join(v for k, v in sorted(files.items()) if k.startswith('stubs/')))}],
                                  'tools': {'cbmc': res.get('cbmc_version', ''), 'engine': fe.digest()},
                                  'knobs': {'argv': ['polari-cbmc-check'] + argv_for(check), 'width': '--16', 'bound_k': check['bound_k'], 'unwind': check['unwind']},
                                  'seeds': {'deterministic': True, 'why': 'CBMC is a decision procedure: the same goto program and bound give the same verdict'},
                                  'generated_files': [{'path': 'trace.json', 'sha256': _sha(trace_bytes)}, {'path': 'result.json'}],
                                  'steps': [{k: s.get(k) for k in ('step', 'rc', 'wall_s', 'cpu_s', 'peak_rss_mb')} for s in res.get('steps', [])],
                                  'how_to_rerun': 'pol faults formal run %s' % check['name'],
                                  'rule': 'every result carries the initial conditions that produced it (2026-09-26)'}, default=str)})
    sink.upsert('FormalCheck', fc)
    if o['outcome'] != 'error':
        tier_status = o['outcome'] if o['outcome'] in ('decided', 'refuted') else o['outcome']
        add_evidence(sink, cname, {'tier': 'formal', 'status': tier_status, 'ref': check['name'], 'measure': o['claim_status'],
                                   'bound_k': check['bound_k'], 'engine': res.get('cbmc_version', ''), 'trace_sha256': fc['trace_sha256']},
                     base=claim_base(check, build_name), counterexample=dict(cx, check=check['name']) if cx else None,
                     certificate=check['name'])
        sink.upsert('ProofRun', {'name': '%s@cbmc@%s' % (cname, fc['ran_at']), 'description': 'FormalCheck %s' % check['name'], 'claim': cname,
                                 'checker': 'cbmc', 'checker_version': res.get('cbmc_version', ''),
                                 'verdict': {'decided': 'holds', 'refuted': 'refuted', 'inapplicable': 'inapplicable'}.get(o['outcome'], 'undecided'),
                                 'detail_json': json.dumps({'check': check['name'], 'outcome': o['outcome'], 'claim_status': o['claim_status'],
                                                            'counterexample': cx}, default=str),
                                 'output_tail': words[-400:], 'elapsed_s': fc['wall_s'], 'rows_state_hash': fc['source_sha256'], 'ran_at': fc['ran_at'],
                                 'ran_where': fc['engine_where'], 'notes': 'bounded model check — decided (bounded) is never proved'})
    fc['_raw'] = res
    return fc
