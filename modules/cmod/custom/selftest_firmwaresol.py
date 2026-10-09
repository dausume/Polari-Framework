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
        check('schedule_for(uno-sim-rig-graph): 18 slots, all provenance=derived (D-fs-1 — never authored; ucd-0e2 '
              'added the project\'s 4th ISR, INT1_vect, as a new isr-lane slot)',
              len(rows) == 18 and all(r['provenance'] == 'derived' for r in rows), len(rows))
        check('isr lane names the project\'s 4 ISR atoms (USART_RX_vect, INT1_vect among them — ucd-0e2) — project-level, not graph nodes',
              sorted(by_lane.get('isr', [])) == ['hal.INT0_vect', 'hal.INT1_vect', 'hal.TIMER2_COMPA_vect', 'hal.USART_RX_vect'], by_lane.get('isr'))
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

    def target_compat_and_valid_targets():
        """fs-2a (his ruling 2026-10-06): the per-task valid-targets door, the solution payload's unregistered/
        registered tasks, and POST .../assign refusing an incompatible drop (PWM onto D13 — no Output Compare
        function) while accepting a compatible one. A live falcon app, seeded exactly like the server boots it
        (same posture as demo4_targets' API half)."""
        from cmod.custom import firmware as FW
        kinds = {'adc': 'analog-in', 'pwm': 'pwm-out', 'send': 'uart-tx', 'rx_pop': 'uart-rx', 'led': 'digital-out'}
        for task, kind in kinds.items():
            from cmod.custom import targets as T
            check('requirement_kind(%s) == %s (derived from the atom\'s own resources, never typed in)' % (task, kind),
                  T.requirement_kind('uno-sim-rig-graph', task) == kind, T.requirement_kind('uno-sim-rig-graph', task))

        adc_vt = FW.valid_targets_for_task('uno-sim-rig-graph', 'uno-sim-rig', 'adc')
        check('ADC task valid-targets (pure, no manager) == A0-A5 exactly',
              sorted(p['pin'] for p in adc_vt['pins'] if p['verdict'] == 'valid') == ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], adc_vt)
        pwm_vt = FW.valid_targets_for_task('uno-sim-rig-graph', 'uno-sim-rig', 'pwm')
        check('PWM task valid-targets == the six timer pins (D6, its own current pin, included — cooperating with pwm_init/apply)',
              sorted(p['pin'] for p in pwm_vt['pins'] if p['verdict'] == 'valid') == ['D10', 'D11', 'D3', 'D5', 'D6', 'D9'], pwm_vt)
        d13 = next(p for p in pwm_vt['pins'] if p['pin'] == 'D13')
        check('PWM onto D13 is invalid in the valid-targets listing too (no Output Compare function)', d13['verdict'] == 'invalid', d13)

        ok, status, why = FW.check_drop('uno-sim-rig-graph', 'uno-sim-rig', 'pwm', 'arduino-uno-r3:D13')
        check('check_drop refuses PWM onto D13 (the true invalid case — digital-out onto an analog pin is actually valid)',
              not ok and 'Output Compare' in why, why)
        # A0 itself is already claimed by the 'adc' task (a real conflict, correctly refused) — A1 is unclaimed, so
        # this isolates the COMPATIBILITY question (is an analog pin GPIO-capable?) from the conflict question
        ok2, status2, why2 = FW.check_drop('uno-sim-rig-graph', 'uno-sim-rig', 'led', 'arduino-uno-r3:A1')
        check('…and digital-out onto A1 (an unclaimed analog pin) is NOT refused by compatibility (every I/O pin is GPIO-capable)',
              ok2, why2)

        # the live API: a manager seeded exactly like the server boots it
        from types import SimpleNamespace
        from falcon import testing
        import falcon
        from cmod.cmod_seed import CMOD_SEED_PAIRS
        from cmod.cmod_firmware_api import FirmwareAPI
        tables = {}
        mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
        for name, cls, seed_rows in CMOD_SEED_PAIRS:
            for row in seed_rows:
                o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
        app = falcon.App()
        FirmwareAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
        c = testing.TestClient(app)

        r = c.simulate_get('/api/firmware/solutions/uno-sim-rig/tasks/pwm/valid-targets')
        check('GET .../tasks/pwm/valid-targets (live, over the seeded manager) → the six timer pins valid',
              r.status_code == 200 and r.json['ok'] and r.json['kind'] == 'pwm-out'
              and sorted(p['pin'] for p in r.json['pins'] if p['verdict'] == 'valid') == ['D10', 'D11', 'D3', 'D5', 'D6', 'D9'], r.text[:300])

        r = c.simulate_get('/api/firmware/solutions/uno-sim-rig')
        check('the solution payload gains unregistered_tasks (temp.return, clock.return — real targets, not placed)',
              {'temp.return', 'clock.return'} <= {(a['task'] + ('.' + a['port'] if a['port'] else ''))
                                                   for a in r.json['unregistered_tasks']}, r.json.get('unregistered_tasks'))
        check('…and per-pin registered_tasks (D6 carries pwm_init + pwm, cooperating)',
              any(t['task'] == 'pwm' and t['cooperating'] for t in r.json['registered_tasks'].get('arduino-uno-r3:D6', [])),
              r.json['registered_tasks'].get('arduino-uno-r3:D6'))

        r = c.simulate_post('/api/firmware/solutions/uno-sim-rig/assign', json={'task': 'pwm', 'lives_on': 'arduino-uno-r3:D13'})
        check('POST .../assign REFUSES PWM onto D13, 422, naming the reason (no Output Compare function)',
              r.status_code == 422 and r.json.get('refused') and 'Output Compare' in r.json.get('error', ''), r.text[:300])
        # the row is UNCHANGED after the refusal (never a silent partial write)
        still = next(a for a in c.simulate_get('/api/firmware/solutions/uno-sim-rig').json['assignments'] if a['task'] == 'pwm')
        check('…and the row is unchanged after the refusal (still on D6, not D13)', still['lives_on'] == 'arduino-uno-r3:D6', still)

        r = c.simulate_post('/api/firmware/solutions/uno-sim-rig/assign', json={'task': 'pwm', 'port': 'duty', 'lives_on': 'arduino-uno-r3:D5'})
        check('POST .../assign ACCEPTS PWM onto D5 (a true PWM-capable, unclaimed pin)',
              r.status_code == 200 and r.json['ok'] and r.json['assignment']['lives_on'] == 'arduino-uno-r3:D5', r.text[:300])

        r = c.simulate_post('/api/firmware/solutions/uno-sim-rig/assign', json={'task': 'led', 'lives_on': 'arduino-uno-r3:GND'})
        check('POST .../assign REFUSES a power/ground pin, 422, naming the rule', r.status_code == 422
              and 'never assignable' in r.json.get('error', ''), r.text[:300])

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

    return (schedule_derivation, assignments_and_validate, target_compat_and_valid_targets, cross_domain_validator)
