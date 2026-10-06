"""cmod.custom.selftest_firmwaresol — fs-0 (DEMONSTRABLES_PLAN.md §9): the DERIVED schedule (D-fs-1), the DERIVED
register map (D-fs-2), validation (board exists, targets bound/unbound/conflict), and a copy-fixture refusal."""
import copy


def firmware_parts(check):
    def schedule_derivation():
        from cmod.custom import firmware as FW
        rows = FW.schedule_for('uno-sim-rig-graph', 'uno-sim-rig')
        by_lane = {}
        for r in rows:
            by_lane.setdefault(r['lane'], []).append(r['task'])
        check('schedule_for(uno-sim-rig-graph): 17 slots, all provenance=derived (D-fs-1 — never authored)',
              len(rows) == 17 and all(r['provenance'] == 'derived' for r in rows), len(rows))
        check('isr lane names the project\'s 3 ISR atoms (USART_RX_vect among them) — project-level, not graph nodes',
              sorted(by_lane.get('isr', [])) == ['hal.INT0_vect', 'hal.TIMER2_COMPA_vect', 'hal.USART_RX_vect'], by_lane.get('isr'))
        check('tick lane names the telemetry tick (the glue\'s own 10 Hz tick node)', by_lane.get('tick') == ['telemetry'], by_lane.get('tick'))
        check('init lane names the 5 init-stage atoms (usart/tick/led/pwm/adc init, boot order)',
              by_lane.get('init') == ['usart_init', 'tick_init', 'led_init', 'pwm_init', 'adc_init'], by_lane.get('init'))
        check('loop lane names the 6 loop-stage atoms; called lane names the 2 dispatched-only atoms (led, pwm)',
              set(by_lane.get('loop', [])) == {'rx_pop', 'apply', 'clock', 'adc', 'temp', 'send'}
              and set(by_lane.get('called', [])) == {'led', 'pwm'}, by_lane)
        # idempotent — a second derive gives byte-identical rows (same posture as cmod-1's render)
        check('schedule_for is idempotent (pure over committed rows — same input, same output)',
              FW.schedule_for('uno-sim-rig-graph', 'uno-sim-rig') == rows)

    def assignments_and_validate():
        from cmod.custom import firmware as FW
        rows = FW.assignments_for('uno-sim-rig-graph', 'uno-sim-rig')
        by_pin = {r['lives_on']: r['status'] for r in rows if r['lives_on'] != 'unbound'}
        check('assignments_for: ADC A0, PWM D6, LED D13, USART D0/D1 all BOUND (no false conflicts from cooperating '
              'init+use atoms of the SAME peripheral)',
              by_pin.get('arduino-uno-r3:A0') == 'bound' and by_pin.get('arduino-uno-r3:D6') == 'bound'
              and by_pin.get('arduino-uno-r3:D13') == 'bound' and by_pin.get('arduino-uno-r3:D0') == 'bound'
              and by_pin.get('arduino-uno-r3:D1') == 'bound', by_pin)
        unbound = {r['task'] + ('.' + r['port'] if r['port'] else '') for r in rows if r['status'] == 'unbound'}
        check('temp_c and uptime_ms are memory-field targets, UNBOUND = exposed (his words: real targets, just not placed)',
              {'temp.return', 'clock.return'} <= unbound, unbound)
        check('no conflicts in the real seeded graph (every shared pin is cooperating init+use, not two unrelated owners)',
              not any(r['status'] == 'conflict' for r in rows))

        fs = {'name': 'uno-sim-rig', 'graph': 'uno-sim-rig-graph', 'board_definition': 'arduino-uno-r3', 'board_variable': ''}
        ok, why, details = FW.validate(fs, manager=None)
        check('validate(uno-sim-rig) passes: board resolved, no conflicts, unbound targets named (never silently missing)',
              ok and 'A0' not in why and 'unbound' in why, why)

        # a stale board_variable, checked against a live (fake) manager with no matching BoardDefinition — refused, named
        from types import SimpleNamespace
        fake_mgr = SimpleNamespace(objectTables={'BoardDefinition': {}})
        fs_var = {'name': 'uno-sim-rig', 'graph': 'uno-sim-rig-graph', 'board_definition': '', 'board_variable': 'tracked-board-9000'}
        ok2, why2, _ = FW.validate(fs_var, manager=fake_mgr)
        check('validate() refuses a board_variable naming a board no longer in the register (his rule: validated at run '
              'time), naming the missing board', not ok2 and 'tracked-board-9000' in why2, why2)

    def cross_domain_validator():
        from hwnocode.custom import cross_domain as CD
        clean = {'stateInstances': [
            {'stateName': 'sim-rig', 'stateClass': 'FirmwareRunState'},
            {'stateName': 'uno-digital-twin', 'stateClass': 'HardwareInterface'},
            {'stateName': 'on-temp', 'stateClass': 'BackendStateChange'},
            {'stateName': 'commit', 'stateClass': 'StateChangeCommit'},
        ]}
        ok, why = CD.validate(clean)
        check('CrossDomainSolution validator PASSES a bridging/relay-only graph (Firmware Run + Bridge + Relay up/down)',
              ok, why)

        tainted = copy.deepcopy(clean)
        tainted['stateInstances'].append({'stateName': 'moving-avg', 'stateClass': 'AnalysisCall'})
        # AnalysisCall alone is allowed (the outbound call to a backend solution) — the REAL refusal is compute kinds:
        tainted['stateInstances'].append({'stateName': 'over?', 'stateClass': 'ConditionalChain'})
        ok2, why2 = CD.validate(tainted)
        check('…and REFUSES a copy that still contains moving-avg\'s compute (ConditionalChain), NAMING the offending state',
              not ok2 and 'over?' in why2 and 'ConditionalChain' in why2, why2)

    return (schedule_derivation, assignments_and_validate, cross_domain_validator)
