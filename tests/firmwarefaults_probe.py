"""sc-0 + sc-1 PROBE — the scenarios on the REAL simavr UNO twin, then the module on a live boot.

Part A (offline runner, the CLI's path): BEFORE (uno-sim-rig-torn, HAL_MILLIS_ATOMIC 0) with the tick IRQ forced at the PC between
the 1st and 2nd `lds` of g_ms (found in the build's own disassembly) → refuted at a named cycle, uptime_ms 511 then 400, CRC fine,
VCD sha; AFTER (uno-sim-rig) with the same forcing → witnessed, landed after `out SREG`; the cost pair (+6 B, +3 cycles, the
ISR-latency delta); both re-run BIT-IDENTICALLY from row + seed; the natural run (10 s, no forcing) → the measured rate on the
fault row; scenario 1b → the refused build (inapplicable); a corrupt-word poke proves the --poke mechanism.
Part S1 (sc-1, offline runner): every forcible single-board pair for real — S2 lost ack (BEFORE hangs, AFTER retries), S3 bounce (3
counted vs 2), S4 residual (1 of 2 applied vs 2 of 2), S5 brownout (half record vs the old one) + the EEPROM persistence control,
the watchdog (hung vs reset + resumed) — each with its measured cost on the Technique row; the RTOS scenarios refused with the
reason; a 2-seed smoke of each statistics batch (the 20/60-seed numbers are `pol faults stats`, recorded in COST.md).
Part B (live boot): a THROWAWAY in-process server with firmwarefaults (+ board, grpcbridge, mathproofs …) — typed classes, the
seeds, the page, the doors, and POST /api/firmwarefaults/run executing the pair IN the server (rows + claims + measured cost).
Skips HONESTLY (exit 0, every check listed as SKIP) when no twin / disassembler resolves on this device.

  cd <throwaway dir> && PYTHONPATH=<fw>:<fw>/modules python3 <fw>/tests/firmwarefaults_probe.py [--json out.json] [--no-boot] [--no-sc1|--only-sc1]
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


def part_s1():
    from firmwarefaults.custom import runner, statistics as ST
    from firmwarefaults.custom.sink import LocalSink
    sink = LocalSink()
    rep = report.setdefault('sc1', {})

    def pair(name):
        b, a = runner.run_scenario(name, 'both', sink)['runs']
        rep[name] = {s: {k: r[k] for k in ('name', 'outcome', 'observable_value', 'verdict_words', 'fault_cycle', 'fault_symbol', 'landed_symbol',
                                            'reset_count', 'isr_cycles_max', 'fn_cycles_min', 'isr_latency_max_cycles', 'stack_high_water',
                                            'stack_high_water_paint', 'size_text', 'size_data', 'size_bss', 'firmware_sha256', 'uart_sha256', 'claim',
                                            'claim_status')} for s, r in (('before', b), ('after', a))}
        rep[name]['cost'] = json.loads(a['cost_delta_json'])
        return b, a, json.loads(a['cost_delta_json'])

    b, a, cd = pair('lost-ack-hang')
    ob = json.loads(b['observed_json'])
    oa = json.loads(a['observed_json'])
    check('S2 BEFORE (uno-ack-wait, ack #1 dropped at cycle %d): %s → refuted' % (b['fault_cycle'], b['verdict_words'][:140]),
          b['outcome'] == 'failed' and b['claim_status'] == 'refuted' and ob['ack_state'] == 1 and len(ob['requests_ms']) == 1)
    check('S2 AFTER (uno-ack-wait-timeout): %s → witnessed' % a['verdict_words'][:150],
          a['outcome'] == 'passed' and a['claim_status'] == 'witnessed' and oa['ack_state'] == 2 and len(oa['requests_ms']) == 2
          and 45 <= oa['requests_ms'][1] - oa['requests_ms'][0] <= 55)
    check('S2 cost of timeout-fsm: %+d B flash, %+d B RAM, %d cycles per ack_step() pass' % (cd['flash_bytes'], cd['ram_bytes'], cd['cycles']),
          cd['flash_bytes'] > 0 and cd['cycles'] > 0 and sink.get('Technique', 'timeout-fsm')['measured_by_run'] == a['name'])
    b, a, cd = pair('button-bounce-double-count')
    check('S3 BEFORE (uno-button-count): %s; AFTER (uno-button-debounce): %s' % (b['observable_value'], a['observable_value']),
          b['outcome'] == 'failed' and b['observable_value'].startswith('3 counted') and a['outcome'] == 'passed' and a['observable_value'].startswith('2 counted'))
    check('S3 cost of the debounce: %+d B flash, %+d B RAM, %+d INT0 ISR cycles (max %d → %d)' % (cd['flash_bytes'], cd['ram_bytes'], cd['cycles'],
                                                                                              b['isr_cycles_max'], a['isr_cycles_max']),
          cd['cycles'] > 0 and b['isr_cycles_max'] > 0 and sink.get('Technique', 'debounce-synchroniser')['measured_ram_bytes'] == cd['ram_bytes'])
    b, a, cd = pair('uart-residual-frame-loss')
    check('S4 BEFORE (the shipped resync parser): %s; AFTER (keep-tail): %s; cost %+d B flash, %+d B RAM' % (
          b['observable_value'], a['observable_value'], cd['flash_bytes'], cd['ram_bytes']),
          b['outcome'] == 'failed' and b['observable_value'].startswith('1 applied / 2 intact') and a['outcome'] == 'passed'
          and a['observable_value'].startswith('2 applied / 2 intact'))
    ob = json.loads(b['observed_json'])
    check('S4: the USART error counters are compiled in and read (FE0 %s, DOR0 %s, ring drops %s on a clean line)' % (
          ob['framing_errors_counted'], ob['overruns_counted'], ob['ring_drops_counted']),
          (ob['framing_errors_counted'], ob['overruns_counted'], ob['ring_drops_counted']) == (0, 0, 0))
    b, a, cd = pair('brownout-mid-eeprom-write')
    check('S5 BEFORE (in place, reset at the 3rd eeprom_write_byte, cycle %d): %s → refuted' % (b['fault_cycle'], b['observable_value']),
          b['outcome'] == 'failed' and b['observable_value'].startswith('0x11112222') and b['reset_count'] == 1)
    check('S5 AFTER (two slots, crc last): %s → witnessed; cost %+d B flash' % (a['observable_value'], cd['flash_bytes']),
          a['outcome'] == 'passed' and a['observable_value'].startswith('0x11111111'))
    ctl = runner.run_scenario('brownout-mid-eeprom-write', 'control', sink)['runs'][0]
    rep['eeprom_persistence'] = {'run': ctl['name'], 'value': ctl['observable_value'], 'words': ctl['verdict_words']}
    check('EEPROM PERSISTS across avr_reset on the twin (control: reset after the write completed → the new record at boot: %s)' % ctl['observable_value'],
          ctl['observable_value'].startswith('0x22222222') and ctl['claim'] == '')
    b, a, cd = pair('runaway-hang-watchdog')
    ra = json.loads(a['observed_json'])['resets']['list']
    check('watchdog BEFORE (uno-sim-rig): %s; AFTER (uno-sim-rig-wdt): %s, WDRF %s' % (b['observable_value'], a['observable_value'], [r['wdrf'] for r in ra]),
          b['outcome'] == 'failed' and a['outcome'] == 'passed' and a['reset_count'] == 1 and ra[0]['wdrf'] == 1)
    check('every sc-1 run records plan §4 space/safety: stack high-water (SP watch == paint), worst ISR latency, sizes',
          all(r[s]['stack_high_water'] == r[s]['stack_high_water_paint'] > 0 and r[s]['size_text'] > 0
              for n, r in rep.items() if isinstance(r, dict) and 'before' in r for s in ('before', 'after')))
    for name in ('priority-inversion-mutex', 'two-lock-deadlock'):
        try:
            runner.run_scenario(name, 'both', sink)
            why = ''
        except runner.ScenarioRefused as e:
            why = str(e)
        check('%s is REFUSED (not-yet-forcible: %s…)' % (name, why[len('scenario %s is not-yet-forcible: ' % name):][:60]), 'FreeRTOS' in why)
    again = runner.run_scenario('lost-ack-hang', 'both', LocalSink())['runs']
    check('S2 re-runs BIT-IDENTICALLY (firmware + UART sha256 on both sides)',
          [(r['firmware_sha256'], r['uart_sha256']) for r in again] == [(rep['lost-ack-hang'][s]['firmware_sha256'], rep['lost-ack-hang'][s]['uart_sha256'])
                                                                         for s in ('before', 'after')])
    out = ST.uart_ber(sink, bers=(1e-3,), seeds=2)
    bb, aa = out[('before', 1e-3)], out[('after', 1e-3)]
    check('statistics smoke (BER 1e-3, 2 seeds x 500 commands): BEFORE residual %d, AFTER residual %d, the same line loss on both (paired seeds)'
          % (bb['residual_events'], aa['residual_events']),
          aa['residual_events'] == 0 and bb['residual_events'] >= aa['residual_events'] and bb['trials'] == aa['trials'] == 1000)
    sw = ST.tear_phase_sweep(sink, seeds=2)
    check('statistics smoke (phase sweep, 2 seeds): %d tear(s) in %d carries; the frames agree (%d backwards + %d torn final frame)' % (
          sw['sweep']['events'], sw['sweep']['trials'], sw['frames_backwards'], sw['torn_final_frames']),
          sw['sweep']['trials'] == 78 and sw['frames_backwards'] + sw['torn_final_frames'] == sw['sweep']['events'] and sw['natural']['carries'] == 39)


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
    check('live boot: all 25 firmwarefaults classes are typed', all(c.__name__ in typed for c in FIRMWAREFAULTS_CLASSES),
          [c.__name__ for c in FIRMWAREFAULTS_CLASSES if c.__name__ not in typed])
    n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
    kinds = sum(n(c.__name__) for c in FIRMWAREFAULTS_CLASSES[1:17])
    check('live boot: 17 fault rows, 11 techniques, 13 assumptions, 6 primitives, 9 scenarios, 14 steps seeded',
          (kinds, n('Technique'), n('Assumption'), n('ConcurrencyPrimitive'), n('Scenario'), n('ScenarioStep')) == (17, 11, 13, 6, 9, 14),
          (kinds, n('Technique'), n('Assumption'), n('ConcurrencyPrimitive'), n('Scenario'), n('ScenarioStep')))
    check('live boot: the eleven scenario variants are FirmwareVariant rows beside board\'s five',
          {'uno-sim-rig-torn', 'uno-sim-rig-ring512', 'uno-ack-wait', 'uno-ack-wait-timeout', 'uno-button-count', 'uno-button-debounce',
           'uno-echo-uartstat', 'uno-echo-keeptail', 'uno-eeprom-record', 'uno-eeprom-commit', 'uno-sim-rig-wdt'}
          <= {getattr(v, 'name', '') for v in (tables.get('FirmwareVariant', {}) or {}).values()})
    pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'firmware-faults']
    comps = [it['componentProps']['componentName'] for row in json.loads(pages[0].definition)['rows'] for it in row['items']] if pages else []
    check('live boot: /display/firmware-faults is seeded — configured tables only (%d)' % len(comps), len(pages) == 1 and comps and set(comps) == {'class-rows-table'})
    r = client.simulate_get('/api/firmwarefaults')
    check('GET /api/firmwarefaults answers: 17 fault rows, 7 scenarios runnable, the 2 RTOS ones not', r.status_code == 200 and r.json['fault_rows'] == 17
          and sum(s['runnable'] for s in r.json['scenarios']) == 7, r.text[:300])
    r = client.simulate_get('/api/firmwarefaults/engines')
    check('GET /api/firmwarefaults/engines: avr-twin + avr-objdump resolve on this device', r.status_code == 200
          and r.json['engines']['avr-twin']['how'] != 'refused' and r.json['engines']['avr-objdump']['how'] != 'refused', r.text[:300])
    r = client.simulate_post('/api/firmwarefaults/run', body=json.dumps({'scenario': 'torn-millis-read', 'side': 'both'}), headers={'Content-Type': 'application/json'})
    ok = r.status_code == 201 and [x['outcome'] for x in r.json['runs']] == ['failed', 'passed']
    check('POST /api/firmwarefaults/run {torn-millis-read, both} runs the pair IN the server → failed, passed', ok, r.text[:400])
    runs = list((tables.get('ScenarioRun', {}) or {}).values())
    claims = {c.name: c.proof_status for c in (tables.get('MathClaim', {}) or {}).values() if c.name.startswith('fw-safe:torn-millis-read')}
    check('…its rows are in the tree: 2 ScenarioRuns, trace rows, the claims refuted + witnessed, the Technique\'s measured cost',
          len([x for x in runs if x.scenario == 'torn-millis-read']) == 2 and n('ScenarioTraceCycle') > 10 and sorted(claims.values()) == ['refuted', 'witnessed']
          and next(t for t in tables['Technique'].values() if t.name == 'atomic-block').measured_cost_bytes == 6, (len(runs), n('ScenarioTraceCycle'), claims))
    r2 = client.simulate_post('/api/firmwarefaults/run', body=json.dumps({'scenario': 'lost-ack-hang', 'side': 'both'}), headers={'Content-Type': 'application/json'})
    check('POST /api/firmwarefaults/run {lost-ack-hang, both} (sc-1) runs IN the server → failed, passed, the Technique\'s measured cost',
          r2.status_code == 201 and [x['outcome'] for x in r2.json['runs']] == ['failed', 'passed']
          and next(t for t in tables['Technique'].values() if t.name == 'timeout-fsm').measured_cost_cycles > 0, r2.text[:400])
    r3 = client.simulate_post('/api/firmwarefaults/run', body=json.dumps({'scenario': 'priority-inversion-mutex', 'side': 'both'}),
                              headers={'Content-Type': 'application/json'})
    check('POST /run of an RTOS scenario → 409 not-yet-forcible (nothing built)', r3.status_code == 409 and 'FreeRTOS' in r3.json['error'], r3.text[:200])
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
    if '--only-sc1' not in argv:
        part_a()
    if '--no-sc1' not in argv:
        part_s1()
    if '--no-boot' not in argv:
        part_b()
    if '--json' in argv:
        json.dump(report, open(argv[argv.index('--json') + 1], 'w'), indent=1, default=str)
    print('\n%d/%d checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
