"""selftest_cycles - cyc-0 (MISSION_PROFILE_SOLVER_PLAN.md section 16), the FEED side: measured twin cycle counts (board.custom.cycle_records) in the cost basis.
Proves: an atom's cost gains `cycles` (kind measured, with the run reference) without touching the committed manifest; rt-0 bounds every light-Mission loop task by
measurement (apply_command and telemetry_send, which it could not bound before), so the bare-C verdict is no longer provisional and its basis says measured - while with the
records switched off the old provisional answer comes back (the measured replacement is the ONLY difference); iso-0's variant cost gains cycles; sol-0's fastest-cycle model
reads measured cycles where a record has the route's atoms, labels each part's basis, and the candidate says how many parts are measured. The twin runs themselves are in
board.board_cycle_selftest. Run by cmod_selftest.main() (cycles_parts)."""
import contextlib


@contextlib.contextmanager
def records_off():
    """The cycle records pointed at nothing (the baseline the measured answer is compared with)."""
    from board.custom import cycle_records as CR
    saved = CR.DIR
    CR.DIR = '/nonexistent-cycle-records'
    CR._CACHE.clear()
    try:
        yield
    finally:
        CR.DIR = saved
        CR._CACHE.clear()


def cycles_parts(check):
    UNO, LIGHT = 'arduino-uno-r3', 'uno-light-mission'

    def atom_cost():
        from cmod.custom import code_interface as CI
        from board.custom import cycle_records as CR
        _p, _m, ts = CI.find_atom('uno:apps/light.telemetry_send')
        cy = ts['cost'].get('cycles') or {}
        check('cyc-0: an atom\'s cost gains `cycles` - kind measured, the worst count, the run reference (record + hex sha256), by variant (telemetry_send: %s cycles)' % cy.get('value'),
              cy.get('kind') == 'measured' and cy['value'] > 100000 and 'cycle record uno-light' in cy['ref'] and 'uno-light' in cy['by_variant'] and cy['by_variant']['uno-light']['cpu_max'] < 20000, cy)
        _p, _m, isr = CI.find_atom('uno:hal.INT0_vect')
        check('cyc-0: an interrupt atom carries its measured cycles per event too (INT0_vect)', (isr['cost'].get('cycles') or {}).get('kind') == 'measured' and isr['cost']['cycles']['unit'] == 'cycles', isr['cost'].get('cycles'))
        with records_off():
            _p, _m, ts2 = CI.find_atom('uno:apps/light.telemetry_send')
            check('cyc-0: with no records the atom has no cycles entry (nothing invented), and the committed manifest file is untouched by the overlay',
                  'cycles' not in ts2['cost'] and CR.cycles_of('apps/light.telemetry_send') is None)

    def rt0():
        from cmod.custom import approach_profile as AP
        from cmod.custom import approach_profile_input as AI
        r = AP.approach_profile(LIGHT, board=UNO)
        sl, rec = r['demand']['superloop'][0], r['recommended']
        spec = AI.from_mission(LIGHT)
        tasks = {t['name']: t for t in spec['processors'][0]['tasks'] if t['lane'] == 'loop'}
        check('cyc-0: every loop task of the light Mission is bounded by MEASUREMENT (apply, telemetry_send included): wcet kind measured, basis names the cycle record and the stimulus',
              set(tasks) >= {'rx_pop', 'apply', 'clock', 'led_toggle', 'telemetry_send'} and all(t['cycles_basis'] == 'measured' and t['wcet_us']['kind'] == 'measured' and not t['unbounded']
                                                                                              and 'cycle record' in t['wcet_us']['basis'] and 'stimulus' in t['wcet_us']['basis'] for t in tasks.values()),
              {n: (t['cycles_basis'], t['wcet_us']['kind']) for n, t in tasks.items()})
        ts = tasks['telemetry_send']
        check('cyc-0: telemetry_send is the CPU part (the twin\'s USART wait taken out: %d cycles), the send wait stays the baud arithmetic (9.5 ms estimated, added once)' % ts['cycles'],
              ts['measured']['split'] and ts['cycles'] < 20000 and sl['blocking_us']['value'] == 9548.6 and sl['blocking_us']['kind'] == 'estimated', (ts['measured'], sl['blocking_us']))
        check('cyc-0: the bare-C verdict is no longer provisional - cycle basis measured, nothing unbounded, verdict fits-known (only the world-driven interrupt RATES stay out of the CPU share, said); the basis text says MEASURED and names the numbers',
              not rec['provisional'] and sl['cycle_basis'] == 'measured' and not sl['unbounded'] and sl['verdict'] == 'fits-known' and sl['atom_us']['kind'] == 'measured'
              and 'measured on the twin' in sl['atom_us']['basis'] and 'telemetry_send' in sl['atom_us']['basis'] and 'MEASURED' in ' '.join(rec['reasons']), (sl['verdict'], rec['provisional'], sl['atom_us']))
        mg = sl['measured_gap']
        check('cyc-0: the worst loop pass is also measured end to end (%.2f ms on the twin, %.2f ms at the chip\'s byte time) beside the %.1f ms argued from the atoms' % (
            mg['worst_gap_cycles'] / 16000.0, mg['worst_gap_chip_timed_cycles'] / 16000.0, sl['pass_known_us']['value'] / 1000.0),
              mg and 4 < mg['worst_gap_chip_timed_cycles'] / 16000.0 < mg['worst_gap_cycles'] / 16000.0 < 12 and sl['pass_known_us']['value'] > mg['worst_gap_chip_timed_cycles'] / 16.0
              and any(x['item'].startswith('Longest gap between polls, measured') for x in AP.demand_rows(r)), mg)
        check('cyc-0: the interrupts\' per-event time is MEASURED where a record has it (INT0, the tick, the receive interrupt, the PCINT) and the CPU share is stretched by those',
              all(i['per_event_us']['kind'] == 'measured' for i in spec['processors'][0]['isrs'] if i['cycles_basis'] == 'measured') and sum(1 for i in spec['processors'][0]['isrs'] if i['cycles_basis'] == 'measured') >= 4,
              [(i['name'], i['cycles_basis']) for i in spec['processors'][0]['isrs']])
        with records_off():
            r0 = AP.approach_profile(LIGHT, board=UNO)
        s0 = r0['demand']['superloop'][0]
        check('cyc-0: with the records switched off the OLD answer returns - provisional, apply and telemetry_send unbounded, an estimated 10.7 ms pass: the measurement is the only difference',
              r0['recommended']['provisional'] and {u['task'] for u in s0['unbounded']} == {'apply', 'telemetry_send'} and 10000 < s0['pass_known_us']['value'] < 11500 and s0['cycle_basis'] == 'upper-bound', (s0['verdict'], s0['unbounded']))

    def iso0():
        from cmod.custom import isotope_variants as IV
        vs = {v['name']: v for v in IV.variants()}
        c = IV.costs(vs['read-button:pin-change-interrupt'])
        check('cyc-0: an isotope variant\'s cost gains `cycles` - measured, summed over its non-init atoms, with the run reference: pin-change button %s cycles per use' % c['cycles']['value'],
              c['cycles']['kind'] == 'measured' and c['cycles']['value'] > 100 and 'cycle record uno-light-pcint' in c['cycles']['basis'], c['cycles'])
        c2 = IV.costs(vs['read-button:analog-threshold'])
        check('cyc-0: the analog button\'s ADC read is measured: button_counts + hal_take_toggle_pending %s cycles per use (a 13-clock conversion at /128 is 1664 cycles)' % c2['cycles']['value'],
              c2['cycles']['kind'] == 'measured' and c2['cycles']['value'] > 3300, c2['cycles'])
        c3 = IV.costs(vs['read-button:analog-comparator'])
        check('cyc-0: a route with no atoms stays without a cycles entry (never a partial or zero sum)', 'cycles' not in c3 or c3['cycles']['kind'] == 'undetermined', c3.get('cycles'))
        d = IV.variant_dict(vs['read-button:pin-change-interrupt'])
        check('cyc-0: the flat table column carries it in plain words', d.get('cost_cycles', '').endswith('(measured)'), d.get('cost_cycles'))

    def sol0():
        from cmod.custom import solve as S
        from cmod.custom import solve_report as SR
        r = S.solve(LIGHT, boards=[UNO], tiers=['bare-c'], objective='fastest-cycle')
        c = r['chosen_candidate']
        b = c['cycle']['bases']
        parts = [x for p in c['cycle']['purposes'] for x in p['parts']]
        check('cyc-0: sol-0\'s fastest-cycle model reads measured cycles - the chosen candidate\'s cycle has %d measured parts and %d estimated/counted, each part labelled' % (b['measured'], b['estimated']),
              b['measured'] >= 8 and b['estimated'] >= 1 and all(x['kind'] in ('measured', 'estimated', 'undetermined') and x['basis'] for x in parts)
              and 'MEASURED cycles on the simavr twin' in ' '.join(x['basis'] for x in parts), b)
        check('cyc-0: a part that adds an ESTIMATED wait to measured cycles is labelled estimated (the send: measured CPU + 9.5 ms from the baud), and a route with no atoms is counted',
              any('plus 95' in x['basis'] and x['kind'] == 'estimated' for x in parts) and any('counted by structure' in x['basis'] and x['kind'] == 'estimated' for x in parts), [(x['kind'], x['basis'][:80]) for x in parts][:6])
        check('cyc-0: the candidate\'s total says the mix in words, and the trade-study row carries it ("%s")' % SR.cycle_basis_text(c),
              'parts: %d measured on the twin' % b['measured'] in c['cycle']['total_us']['basis'] and SR.trade_rows([c], 1)[0]['cycle_basis'].startswith('%d measured' % b['measured']), c['cycle']['total_us'])
        with records_off():
            r0 = S.solve(LIGHT, boards=[UNO], tiers=['bare-c'], objective='fastest-cycle')
        c0 = r0['chosen_candidate']
        check('cyc-0: with the records off sol-0 is as it was (0 measured parts, the ~9.7 ms estimate); with them the same plan costs %.2f ms - %.2f ms of measured CPU work the upper bounds had left out'
              % (c['cycle_us'] / 1000.0, (c['cycle_us'] - c0['cycle_us']) / 1000.0),
              c0['cycle']['bases']['measured'] == 0 and 9000 < c0['cycle_us'] < 10200 and c['cycle_us'] > c0['cycle_us'] and c['routes'] == c0['routes'], (c0['cycle_us'], c['cycle_us']))

    return (atom_cost, rt0, iso0, sol0)
