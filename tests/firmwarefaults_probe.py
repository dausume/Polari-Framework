"""sc-0 PROBE — scenario 1 (the torn millis read) on the REAL simavr UNO twin, then the module on a live boot.

Part A (offline runner, the CLI's path): BEFORE (uno-sim-rig-torn, HAL_MILLIS_ATOMIC 0) with the tick IRQ forced at the PC between
the 1st and 2nd `lds` of g_ms (found in the build's own disassembly) → refuted at a named cycle, uptime_ms 511 then 400, CRC fine,
VCD sha; AFTER (uno-sim-rig) with the same forcing → witnessed, landed after `out SREG`; the cost pair (+6 B, +3 cycles, the
ISR-latency delta); both re-run BIT-IDENTICALLY from row + seed; the natural run (10 s, no forcing) → the measured rate on the
fault row; scenario 1b → the refused build (inapplicable); a corrupt-word poke proves the --poke mechanism.
Part B (live boot): a THROWAWAY in-process server with firmwarefaults (+ board, grpcbridge, mathproofs …) — typed classes, the
seeds, the page, the doors, and POST /api/firmwarefaults/run executing the pair IN the server (rows + claims + measured cost).
Skips HONESTLY (exit 0, every check listed as SKIP) when no twin / disassembler resolves on this device.

  cd <throwaway dir> && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/firmwarefaults_probe.py [--json out.json] [--no-boot]
"""
import json
import os
import sys
import tempfile

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules')); sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
HERE = os.path.abspath(os.getcwd()) if os.path.abspath(os.getcwd()) != FRAMEWORK else tempfile.mkdtemp(prefix='ff-probe-')
os.environ['POLARI_FAULTS_HOME'] = os.path.join(HERE, 'faults-home')
os.environ['POLARI_BOARD_HOME'] = os.path.join(HERE, 'board-home')

results, report = [], {}


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra and not cond else ''))


def part_a():
    from firmwarefaults.custom import runner, fault_engines as fe
    from firmwarefaults.custom.sink import LocalSink
    from firmwarefaults.custom import scenarios as SC
    sink = LocalSink()
    out = runner.run_scenario('torn-millis-read', 'both', sink)
    b, a = out['runs']
    report['before'] = {k: b[k] for k in ('name', 'outcome', 'fault_cycle', 'fault_pc', 'fault_symbol', 'landed_pc', 'landed_symbol', 'torn_value',
                                          'expected_value', 'uptime_sequence', 'bad_crc', 'trace_sha256', 'uart_sha256', 'firmware_sha256', 'size_text',
                                          'fn_cycles_min', 'isr_latency_max_cycles', 'stack_high_water', 'stack_high_water_paint', 'stack_static_peak', 'wall_s', 'claim')}
    report['after'] = {k: a[k] for k in report['before']}
    report['after'].update(cost_delta=json.loads(a['cost_delta_json']))
    ups = [int(x) for x in b['uptime_sequence'].split(', ')]
    i511 = ups.index(511) if 511 in ups else -1
    check('BEFORE (uno-sim-rig-torn): FAILED at cycle %d, PC %s = %s — the 2nd lds of g_ms (found in the build\'s disassembly)'
          % (b['fault_cycle'], b['fault_pc'], b['fault_symbol']), b['outcome'] == 'failed' and b['fault_symbol'] == 'hal_millis+0x4' and b['fault_cycle'] > 0)
    check('BEFORE: the ISR ran with the 2nd lds as its return address (landed %s), hal_millis returned 511 for g_ms 0xFF (torn)'
          % b['landed_symbol'], b['landed_pc'] == b['fault_pc'] and b['torn_value'] == 511 and b['expected_value'] == 255
          and json.loads(b['observed_json']).get('returned_after_event') == 511)
    check('BEFORE: the decoded frames carry uptime_ms 511 then 400 (backwards) and every CRC passed: %s' % b['uptime_sequence'],
          i511 > 0 and ups[i511 + 1] == 400 and b['bad_crc'] == 0)
    check('BEFORE: the VCD window is recorded by sha256 (%s…) with trace rows naming the torn return' % b['trace_sha256'][:16],
          len(b['trace_sha256']) == 64 and any('TORN' in t['note'] for t in b['_trace_rows']))
    check('BEFORE: its claim flipped conjectured → refuted, with the counterexample cycle', b['_claim_flip'] == ('conjectured', 'refuted')
          and json.loads(sink.get('MathClaim', b['claim'])['counterexample_json'])['cycle'] == b['fault_cycle'])
    check('AFTER (uno-sim-rig, the shipped ATOMIC_BLOCK): PASSED — same forcing at %s with SREG.I clear; the IRQ stayed pending and landed at %s, '
          'after `out SREG`' % (a['fault_symbol'], a['landed_symbol']),
          a['outcome'] == 'passed' and a['fault_symbol'] == 'hal_millis+0x8' and bool(a['landed_pc'])
          and a['landed_cycle'] > min([t['cycle'] for t in a['_trace_rows'] if t['instruction'].startswith('out 0x3f') and t['cycle'] >= a['fault_cycle']]
                                      or [10 ** 12]))
    check('AFTER: uptime_ms monotone (%s); hal_millis returned 255; claim conjectured → witnessed' % a['uptime_sequence'],
          a['frames_backwards'] == 0 and json.loads(a['observed_json']).get('returned_after_event') == 255 and a['_claim_flip'] == ('conjectured', 'witnessed'))
    cd = json.loads(a['cost_delta_json'])
    check('COST of atomic-block, measured: %+d B flash, %+d cycles per hal_millis call, %+d cycles worst ISR latency (plan: +6 B, +3 cycles, ≈ 9 est.)'
          % (cd['flash_bytes'], cd['guarded_fn_cycles'], cd['isr_latency_max_cycles']),
          cd['flash_bytes'] == 6 and cd['guarded_fn_cycles'] == 3 and cd['isr_latency_max_cycles'] > 0)
    check('the stack high-water is recorded on BOTH builds (SP watch == 0xA5 paint; static peak ≥ measured): %d / %d B, static %d B'
          % (a['stack_high_water'], b['stack_high_water'], a['stack_static_peak']),
          b['stack_high_water'] == b['stack_high_water_paint'] > 0 and a['stack_high_water'] == a['stack_high_water_paint'] > 0
          and a['stack_static_peak'] >= a['stack_high_water'])
    t = sink.get('Technique', 'atomic-block')
    check('the Technique row carries the measured cost and the run that measured it', t['measured_cost_bytes'] == 6 and t['measured_cost_cycles'] == 3
          and t['measured_by_run'] == a['name'])
    again = runner.run_scenario('torn-millis-read', 'both', LocalSink())['runs']
    check('both runs REPRODUCE BIT-IDENTICALLY from row + seed (firmware, VCD and UART sha256 equal on a second run)',
          all(x['firmware_sha256'] == y['firmware_sha256'] and x['trace_sha256'] == y['trace_sha256'] and x['uart_sha256'] == y['uart_sha256']
              for x, y in zip((b, a), again)))
    nat = runner.run_scenario('torn-millis-read', 'natural', sink)['runs'][0]
    n = json.loads(nat['observed_json'])['natural']
    report['natural'] = dict(n, run=nat['name'], wall_s=nat['wall_s'], sim_seconds=nat['sim_seconds'], frames=nat['frames_seen'])
    row = sink.get('TornReadFault', 'torn-read-g-ms')
    check('NATURAL (no forcing, %.0f s): %d torn read(s) in %d byte-0 carries (%.1f %%); exposure under a uniform phase %.2f %% — written onto '
          'the fault row as a measured rate_source' % (nat['sim_seconds'], n['tears'], n['carries'], 100 * n['rate'], 100 * n['exposure_per_carry']),
          n['carries'] >= 38 and row['rate_source'].startswith('measured: run %s' % nat['name']))
    r1b = runner.run_scenario('rx-ring-over-256', 'both', sink)['runs'][0]
    report['1b'] = {'outcome': r1b['outcome'], 'words': r1b['verdict_words'], 'claim': r1b['claim']}
    check('scenario 1b: RX_RING 512 is REFUSED by the static guard → inapplicable (technique static-guard), claim inapplicable',
          r1b['outcome'] == 'inapplicable' and r1b['technique_applied'] == 'static-guard' and sink.get('MathClaim', r1b['claim'])['proof_status'] == 'inapplicable')
    poke_sc = dict(SC.find('torn-millis-read'), name='probe-poke', run_seconds=0.3)
    steps = [{'name': 'probe-poke#1', 'scenario': 'probe-poke', 'order': 1, 'kind': 'corrupt-word',
              'args_json': json.dumps({'symbol': 'g_ms', 'width': 4, 'value': 0x10000, 'cycle': 1600000, 'vec': 7, 'of': 'g_ms', 'pattern': 'lds-sequence',
                                       'before_load': 2}), 'condition_json': '{}', 'forcible': True, 'not_forcible_reason': '', 'notes': ''}]
    from firmwarefaults.custom import harness, disasm
    bb = runner.prepare_build('uno-sim-rig-torn')
    h = harness.run(harness.render([(steps[0], {'ok': True})], bb['nm'], 0.3, 0, watch=('g_ms', 4)), bb['hex'])
    ups_p, _ = runner.decode_frames(h['uart'])
    check('the --poke mechanism (corrupt-word): g_ms := 0x10000 at cycle 1 600 000 → the frames jump past 65 536 ms (%s)' % ups_p,
          h['ok'] and h['final']['pokes'][0]['done'] == 1 and max(ups_p) >= 65536)
    report['engines'] = fe.placement()
    report['harness'] = fe.harness_digest()


def part_b():
    os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board,mathproofs,firmwarefaults'
    os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
    from falcon import testing
    from board_probe_boot import boot
    manager = boot(FRAMEWORK, HERE)
    client = testing.TestClient(manager.polServer.falconServer)
    tables = manager.objectTables
    typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
    from firmwarefaults.firmwarefaults_basis import FIRMWAREFAULTS_CLASSES
    check('live boot: all 24 firmwarefaults classes are typed', all(c.__name__ in typed for c in FIRMWAREFAULTS_CLASSES),
          [c.__name__ for c in FIRMWAREFAULTS_CLASSES if c.__name__ not in typed])
    n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
    kinds = sum(n(c.__name__) for c in FIRMWAREFAULTS_CLASSES[1:17])
    check('live boot: 16 fault rows (one per kind), 10 techniques, 12 assumptions, 6 primitives, 2 scenarios, 2 steps seeded',
          (kinds, n('Technique'), n('Assumption'), n('ConcurrencyPrimitive'), n('Scenario'), n('ScenarioStep')) == (16, 10, 12, 6, 2, 2),
          (kinds, n('Technique'), n('Assumption'), n('ConcurrencyPrimitive'), n('Scenario'), n('ScenarioStep')))
    check('live boot: the two scenario variants are FirmwareVariant rows beside board\'s five',
          {'uno-sim-rig-torn', 'uno-sim-rig-ring512'} <= {getattr(v, 'name', '') for v in (tables.get('FirmwareVariant', {}) or {}).values()})
    pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'firmware-faults']
    comps = [it['componentProps']['componentName'] for row in json.loads(pages[0].definition)['rows'] for it in row['items']] if pages else []
    check('live boot: /display/firmware-faults is seeded — configured tables only (%d)' % len(comps), len(pages) == 1 and comps and set(comps) == {'class-rows-table'})
    r = client.simulate_get('/api/firmwarefaults')
    check('GET /api/firmwarefaults answers: 16 fault rows, both scenarios runnable', r.status_code == 200 and r.json['fault_rows'] == 16
          and all(s['runnable'] for s in r.json['scenarios']), r.text[:300])
    r = client.simulate_get('/api/firmwarefaults/engines')
    check('GET /api/firmwarefaults/engines: avr-twin + avr-objdump resolve on this device', r.status_code == 200
          and r.json['engines']['avr-twin']['how'] != 'refused' and r.json['engines']['avr-objdump']['how'] != 'refused', r.text[:300])
    r = client.simulate_post('/api/firmwarefaults/run', body=json.dumps({'scenario': 'torn-millis-read', 'side': 'both'}), headers={'Content-Type': 'application/json'})
    ok = r.status_code == 201 and [x['outcome'] for x in r.json['runs']] == ['failed', 'passed']
    check('POST /api/firmwarefaults/run {torn-millis-read, both} runs the pair IN the server → failed, passed', ok, r.text[:400])
    runs = list((tables.get('ScenarioRun', {}) or {}).values())
    claims = {c.name: c.proof_status for c in (tables.get('MathClaim', {}) or {}).values() if c.name.startswith('fw-safe:')}
    check('…its rows are in the tree: 2 ScenarioRuns, trace rows, the claims refuted + witnessed, the Technique\'s measured cost',
          len(runs) == 2 and n('ScenarioTraceCycle') > 10 and sorted(claims.values()) == ['refuted', 'witnessed']
          and next(t for t in tables['Technique'].values() if t.name == 'atomic-block').measured_cost_bytes == 6, (len(runs), n('ScenarioTraceCycle'), claims))
    if ok:
        r = client.simulate_get('/api/firmwarefaults/runs/%s' % r.json['runs'][0]['name'])
        check('GET /api/firmwarefaults/runs/<before> → the run, its trace rows, the refuted claim', r.status_code == 200 and r.json['trace']
              and r.json['claim']['proof_status'] == 'refuted', r.text[:300])
    report['live_boot'] = {'claims': claims, 'trace_rows': n('ScenarioTraceCycle')}


def main(argv):
    from firmwarefaults.custom import fault_engines as fe
    if not fe.available():
        print('SKIP: no simavr twin / disassembler on this device (%s) — build the image: docker compose -f '
              'polari-rf-node/docker-compose.board-engines.yml build' % fe.placement())
        return 0
    part_a()
    if '--no-boot' not in argv:
        part_b()
    if '--json' in argv:
        json.dump(report, open(argv[argv.index('--json') + 1], 'w'), indent=1, default=str)
    print('\n%d/%d checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
