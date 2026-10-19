"""board_cycle_selftest - cyc-0 (MISSION_PROFILE_SOLVER_PLAN.md section 16): the MEASURED CYCLE COUNTS on the simavr twin. Proves, SKIPPING honestly without a twin:
the harness gives the SAME counts on two runs of the same hex + stimulus (simavr is deterministic); a known-size function's measured count sits inside the bytes/2 ..
bytes x 4 bound and under rt-0's size-derived upper bound when nothing interrupts it; an atom the stimulus never reached is reported as not measured (never zero);
the twin's USART byte time is longer than the chip's and the split takes that wait out; the committed records are the records of THIS source (shipped hex sha256 matches a
fresh build) and carry their inputs (hex sha256, stimulus, tool versions, own sha256).

    PYTHONPATH=.:modules python3 -m board.board_cycle_selftest      # from polari-framework/ (standalone)
    (called by board.board_selftest.main as run_cycles(check))
"""
import json
import shutil
import tempfile

PROBE = {'telemetry_send', 'apply_command', 'hal_millis', 'hal_usart_send', 'loop'}


def run_cycles(check):
    from board.custom import board_engines as be, cycle_measure as CM, cycle_records as CR
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        check('SKIP cyc-0 (measured cycles on the twin): no simavr twin here - %s' % where['why'], True)
        return
    works = []
    try:
        w1, w2 = tempfile.mkdtemp(prefix='cyc0-st-'), tempfile.mkdtemp(prefix='cyc0-st-')
        works += [w1, w2]
        a = CM.measure('uno-light-unsensed', work=w1, only=PROBE)
        b = CM.measure('uno-light-unsensed', work=w2, only=PROBE)
        ca, cb = CM.counts(a), CM.counts(b)
        check('cyc-0: two runs of the same hex + stimulus give the SAME cycle counts (%d numbers: n / min / max of the probed atoms, every interrupt, every loop gap)' % len(ca),
              ca == cb and len(ca) >= 8 and a['inputs']['shipped_hex_sha256'] == b['inputs']['shipped_hex_sha256'] and a['inputs']['noinline_hex_sha256'] == b['inputs']['noinline_hex_sha256'], (ca, cb))
        check('cyc-0: the record seals identically for the same inputs (record_sha256 excludes only the time it was written)', a['record_sha256'] == b['record_sha256'])
        f = a['functions']
        hm = f['hal.hal_millis']
        tb = _text_bytes('hal.hal_millis')
        check('cyc-0: a known-size function (hal_millis, %d B as a node) measures inside the bytes/2 .. bytes x 4 bound, and its uninterrupted count is under rt-0\'s size bound (2 x bytes): '
              'min %d, max %d (an interrupt that lands inside the call is in max)' % (tb, hm['min'], hm['max']),
              hm['n'] > 100 and tb / 2 <= hm['min'] <= 2 * tb and hm['max'] <= 4 * tb, hm)
        ts, ap = f['apps/light.telemetry_send'], f['apps/light.apply_command']
        check('cyc-0: apply_command and telemetry_send - the two atoms rt-0 could not bound - are now measured (n > 0, generated code and everything they call inside the count)',
              ap['n'] >= 4 and ts['n'] >= 10 and ap['max'] >= ap['min'] > 0 and ts['max'] > 10 * ap['max'], (ap, ts))
        u = a['uart']
        check('cyc-0: the twin times a USART byte at %s cycles, the chip at %s (UBRR/U2X read from the build): the record says so and takes the twin\'s send wait out of telemetry_send '
              '(cpu max %s of %s)' % (u['twin_cycles_per_byte_min'], u['chip_cycles_per_byte'], ts.get('cpu_cycles_max'), ts['max']),
              u['twin_cycles_per_byte_min'] > u['chip_cycles_per_byte'] > 0 and ts.get('blocks_on_uart') and 0 < ts['cpu_cycles_max'] < ts['max'] // 5 and 'USART' in ts.get('twin_caveat', ''), (u, ts))
        lp = a['loop']
        sends = [g for g in lp['gaps'] if g.get('sends_report')]
        check('cyc-0: the main loop is measured end to end - every unconditional way back to the poll point has a gap count, the report pass is the longest, and its chip-timed figure is shorter',
              lp['gaps'] and len(sends) == 1 and lp['worst_gap_cycles'] == sends[0]['max_cycles'] and lp['worst_gap_chip_timed_cycles'] < lp['worst_gap_cycles'] and not lp['conditional_back_jumps_not_separable'], lp)
        check('cyc-0: the interrupts are measured from the shipped hex: INT0 (the button), the 1 ms tick and the receive interrupt all have n > 0 and a max under 200 cycles',
              all(a['isrs'].get(v, {}).get('n', 0) > 0 and a['isrs'][v]['max'] < 200 for v in ('INT0_vect', 'TIMER2_COMPA_vect', 'USART_RX_vect')), a['isrs'])
        # a negative control: an atom the stimulus never reached is NOT measured
        rec = CR.load('uno-light-unsensed')
        check('cyc-0: an atom the stimulus never calls (hal_presses - nothing in the light calls it) is recorded n = 0 with a note, and the lookup returns None - never a zero cycle count',
              rec and rec['functions']['hal.hal_presses']['n'] == 0 and 'never called' in rec['functions']['hal.hal_presses'].get('note', '') and CR.cycles_of('hal.hal_presses', 'uno-light-unsensed') is None, rec and rec['functions'].get('hal.hal_presses'))
        # the committed records are the records of this source
        stale = []
        for v in ('uno-light-unsensed',):
            if rec is None or rec['inputs']['shipped_hex_sha256'] != a['inputs']['shipped_hex_sha256'] or rec['inputs']['noinline_hex_sha256'] != a['inputs']['noinline_hex_sha256']:
                stale.append(v)
        check('cyc-0: the committed uno-light record is the record of THIS source (its shipped and -fno-inline hex sha256 equal a fresh build\'s); a stale record would fail here', not stale, stale)
        check('cyc-0: every committed record carries its inputs (hex + elf sha256, source sha256s, flags), its stimulus (flags, injected-file sha256s), the tool versions (image id, avr-gcc) and its own sha256',
              all(_full(CR.load(v)) for v in CR.variants()) and len(CR.variants()) >= 5, CR.variants())
    finally:
        for w in works:
            shutil.rmtree(w, ignore_errors=True)


def _text_bytes(atom):
    from cmod.custom import code_interface as CI
    return CI.find_atom('uno:' + atom)[2]['cost']['text_bytes_noinline']


def _full(r):
    if not r:
        return False
    i, s, t = r.get('inputs', {}), r.get('stimulus', {}), r.get('tools', {})
    body = {k: v for k, v in r.items() if k not in ('record_sha256', 'recorded_at')}
    import hashlib
    return (len(i.get('shipped_hex_sha256', '')) == 64 and len(i.get('noinline_hex_sha256', '')) == 64 and i.get('sources') and i.get('cflags') and s.get('argv') and 'files_sha256' in s
            and t.get('image', {}).get('id', '').startswith('sha256:') and t.get('avr-gcc') and r.get('record_sha256') == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest())


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else str(extra)[:400]))
    run_cycles(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
