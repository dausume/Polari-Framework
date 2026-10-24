"""cmod_task_plan_selftest - fgm-3: Tasks and Task Plans (FIRMWARE_GENERATION_MODULE_PLAN.md section 9). The light Mission's plan on `uno-light-system` has the expected Tasks (init, handle-button-press,
receive-command, relay-state, sense) with triggers and deadlines read off the Purpose criteria (100 ms; debounce 30 ms; report period 100 ms), each on one processor; priorities are deadline-monotonic with
importance breaking ties and the tie marked; the agreement check compares each context with the lane its atoms derive (agrees / disagrees named / unchecked, never re-labelled); a hand edit is a
DerivedOverride beside the derived value, survives a re-derive and is flagged when the derived value changes under it; "Designed for" is written once; "Also runs on" resolves the same variants on the TQFP
package through sol-0's recorded assignment; the doors add on ONE real falcon.App beside the other Mission doors; the CLI; the page; the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_task_plan_selftest
"""
import contextlib
import copy
import io
import json
import os
import sys
from types import SimpleNamespace

LIGHT = 'uno-light-mission'
SYSTEM = 'uno-light-system'
TQFP = 'arduino-uno-r3 / atmega328p-32-tqfp'


def _manager():
    from cmod.custom.selftest_purpose import _manager as m
    return m()


def _register(mgr, cls_name, row):
    mgr.objectTables.setdefault(cls_name, {})[row.id] = row
    return row


def _t(plan, name):
    return next(t for t in plan['tasks'] if t['task'] == name)


def task_plan_parts(check):
    cache = {}

    def solved():
        """The default attempt-engine run (cached by sol-0's door cache; 2 s warm, 12-17 s cold) - ONE per process."""
        if 'res' not in cache:
            from cmod.custom import solve_doors as SD
            cache['res'] = SD.compute(LIGHT, None, None, None, {}, None)
        return cache['res']

    def mgr_with_run():
        from cmod.custom import solve_record as REC
        mgr = _manager()
        row = _register(mgr, 'SolveRun', REC.store(mgr, solved(), 'sub-test'))
        return mgr, row

    def light_plan():
        from cmod.custom import task_plan as TP
        p = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=solved())
        cache['plan'] = p
        names = [t['task'] for t in p['tasks']]
        check('fgm-3: the light Mission\'s Task Plan on %s has the Tasks %s, each on ONE processor (%s), seeded from the attempt engine\'s chosen plan (%s, tier %s)'
              % (SYSTEM, names, p['processors'][0]['name'], p['candidate'], p['tier']),
              names == ['init', 'handle-button-press', 'receive-command', 'relay-state', 'sense'] and {t['processor'] for t in p['tasks']} == {'arduino-uno-r3:U1'} and p['tier'] == 'bare-c' and p['candidate']
              and 'seeded from' in p['run_basis'], names)
        trig = {t['task']: t for t in p['triggers']}
        check('fgm-3: triggers - init = boot, handle-button-press = edge (the Purpose\'s button, polled on the chosen route), receive-command = command (USART RX interrupt), relay-state = period, sense = edge',
              [t['kind'] for t in p['triggers']] == ['boot', 'edge', 'command', 'period', 'edge'] and trig['receive-command']['how'] == 'interrupt' and trig['receive-command']['source'].startswith('D0')
              and trig['handle-button-press']['route'] == 'gpio-poll' and trig['handle-button-press']['how'] == 'polled in the main loop', [(t['task'], t['kind'], t['how'], t['source']) for t in p['triggers']])
        dl = {t['task']: t['deadline_ms'] for t in p['tasks']}
        check('fgm-3: deadlines come from the Purpose criteria - every task 100 ms (max_latency_ms / freshness_ms), each with a basis that says "criterion"; the button\'s debounce is 30 ms and the report period 100 ms (rt-0\'s labelled estimate)',
              set(dl.values()) == {100.0} and all(t['deadline_basis'].startswith('criterion') for t in p['tasks']) and trig['handle-button-press']['debounce_ms'] == 30.0
              and trig['relay-state']['period_ms'] == 100.0 and 'TELEMETRY_HZ' in trig['relay-state']['period_basis'] and _t(p, 'relay-state')['period_ms'] == 100.0, (dl, trig['relay-state']['period_basis'][:80]))
        steps = {t['task']: [s['instance'] for s in t['steps']] for t in p['tasks']}
        check('fgm-3: steps are the graph\'s atoms in graph order - init: the five init atoms; the button task is fed by INT0_vect; the command task by USART_RX_vect; the report task by the tick (TIMER2_COMPA_vect) and, since smp-2, it ends with the polled sense (sense -> sense_poll, the graph\'s own sense nodes)',
              steps['init'] == ['usart_init', 'tick_init', 'led_init', 'button_init', 'boot_session_mint'] and steps['handle-button-press'][0] == 'INT0_vect' and steps['handle-button-press'][-1] == 'led_follow_state'
              and steps['receive-command'] == ['USART_RX_vect', 'rx_pop', 'apply', 'led', 'led_follow_state'] and steps['relay-state'][0] == 'TIMER2_COMPA_vect' and 'telemetry_send' in steps['relay-state']
              and steps['relay-state'][-2:] == ['sense', 'sense_poll'] and steps['sense'] == ['hal_sense_poll.hal_sense_read'], steps)
        counts = p['agreement_counts']
        check('fgm-3 / fgm-5b: the AGREEMENT CHECK passes for every task - all five agree, none disagree, none is unchecked: the sense task\'s chosen route (gpio-poll) now has atoms (hal_sense_poll, fgm-5b), so its context (loop) is compared with the lane they derive - never "agrees" by default',
              counts == {'agrees': 5, 'disagrees': 0, 'unchecked': 0} and all('derived lanes say' in t['agreement_why'] for t in p['tasks'] if t['agreement'] == 'agrees'), counts)
        sn = _t(p, 'sense')
        check('fgm-5b: the polled sense task\'s step is the route\'s read atom, whose lane (loop) is read from uno-light-graph\'s own sense nodes since smp-2 (called by sense_poll, which runs in the loop lane); its init atom belongs to the init task; it has a scheduler priority (it is a loop task)',
              [x['instance'] for x in sn['steps']] == ['hal_sense_poll.hal_sense_read'] and sn['steps'][0]['lane'] == 'loop' and 'sense_poll' in sn['steps'][0]['role'] and sn['context'] == 'loop' and sn['agreement'] == 'agrees'
              and 'hal_sense_poll.hal_sense_init belongs to the init task' in next(t for t in p['triggers'] if t['task'] == 'sense')['notes'] and sn['priority'] > 0 and 'derived lanes say loop' in sn['agreement_why'], (sn['steps'], sn['agreement_why']))
        pr = {t['task']: t['priority'] for t in p['tasks']}
        check('fgm-3: priorities - init runs once (0); the four 100 ms / required tasks TIE on deadline and importance, so they are ordered by the Mission\'s Purpose order and every one says TIE (never a silent order): %s' % pr,
              pr == {'init': 0, 'handle-button-press': 1, 'receive-command': 2, 'relay-state': 3, 'sense': 4} and all('TIE with' in _t(p, n)['priority_basis'] for n in pr if n != 'init'), pr)
        sb = {(b['task'], b['target']): b for b in p['struct_bindings']}
        check('fgm-3: shared data - g_toggle_pending is isr_shared (INT0_vect writes it, the loop takes it; the atom already wraps it in ATOMIC_BLOCK), the rx ring head is isr_shared with USART_RX_vect, g_ms with the tick; LightState.boot_session is a plain struct-field write (not shared)',
              sb[('handle-button-press', 'g_toggle_pending')]['isr_shared'] and 'INT0_vect' in sb[('handle-button-press', 'g_toggle_pending')]['isr_vectors']
              and 'ATOMIC_BLOCK' in sb[('handle-button-press', 'g_toggle_pending')]['atomic_today'] and sb[('receive-command', 'rx_head')]['isr_shared'] and sb[('relay-state', 'g_ms')]['isr_shared']
              and not sb[('init', 'LightState.boot_session')]['isr_shared'] and sb[('init', 'LightState.boot_session')]['kind'] == 'struct-field', sorted(sb))
        check('fgm-3: the plan carries the variants and the pins (profile -> pin) of the candidate it was seeded from, and the Designed-for origin names the system, processors, tier, variants and the run\'s sha256',
              p['variants'].get('read-button') == 'gpio-poll' and any(x['role'] == 'the button' and x['pin'] for x in p['pins']) and p['designed_for']['hardware_system'] == SYSTEM
              and p['designed_for']['result_sha256'] == solved()['result_sha256'] and p['designed_for']['tier'] == 'bare-c' and p['designed_for']['variants'] == p['variants'], p['designed_for'])

    def no_run_and_interrupt_plan():
        from cmod.custom import task_plan as TP
        from cmod.custom import solve as S
        p0 = TP.derive_task_plan(LIGHT, SYSTEM)
        check('fgm-3: with NO solve run the plan says so in words, has the four Purpose tasks, no sense task, no pins, an undetermined tier, and is not given a Designed-for context',
              not p0['candidate'] and 'NO solve run exists' in p0['run_basis'] and [t['task'] for t in p0['tasks']] == ['init', 'handle-button-press', 'receive-command', 'relay-state']
              and not p0['pins'] and p0['tier'] == '' and not p0['designed_for']['tier'] and any('bare-C main loop' in n for n in p0['notes']), p0['run_basis'][:80])
        r = cache.get('bench')
        if r is None:
            r = cache['bench'] = S.solve(LIGHT, boards=['arduino-uno-r3'], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'max_candidates': 400})
        demo = next(x for x in r['_ranked'] if x['routes'].get('read-button') == 'ext-interrupt' and x['routes'].get('sense-led-line') == 'ext-interrupt' and x['routes'].get('drive-led') == 'gpio-out'
                    and x['hardware']['package'] == 'atmega328p-28-spdip')
        p = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=r, candidate=demo['id'])
        s = _t(p, 'sense')
        trig = next(t for t in p['triggers'] if t['task'] == 'sense')
        check('fgm-3: the demo candidate (button INT0, sense INT1 on D3) gives a sense task fed by INT1_vect: its steps are the route\'s atoms with lanes read from the graph that schedules them (uno-light-graph, its own sense nodes since smp-2), the init atom is left to the init task, '
              'the context is isr (derived from the lanes), the agreement check says agrees, and it has no scheduler priority (0)',
              [x['instance'] for x in s['steps']] == ['hal.hal_sense_read', 'hal.INT1_vect'] and s['context'] == 'isr' and s['agreement'] == 'agrees' and s['priority'] == 0 and trig['source'].startswith('D3') and trig['how'] == 'interrupt'
              and 'hal.hal_sense_init belongs to the init task' in trig['notes'] and 'uno-light-graph' in s['steps'][0]['role'], (s['steps'], s['context'], s['agreement']))
        b = _t(p, 'handle-button-press')
        check('fgm-3: the button task\'s trigger is the interrupt route here (D2 / INT0) and no note contradicts the graph; on the polled candidate the note names the difference (the graph implements INT0, the chosen route is gpio-poll, status declared)',
              next(t for t in p['triggers'] if t['task'] == 'handle-button-press')['how'] == 'interrupt' and 'INT0_vect' in cache['plan']['triggers'][1]['notes'] and 'declared' in cache['plan']['triggers'][1]['notes'] and b['priority'] == 1, cache['plan']['triggers'][1]['notes'])

    def sense_routes_and_link():
        from cmod.custom import task_plan as TP
        from cmod.custom import task_plan_store as STORE
        from cmod.custom import solve as S
        r = cache.get('bench')
        if r is None:
            r = cache['bench'] = S.solve(LIGHT, boards=['arduino-uno-r3'], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'max_candidates': 400})
        pc = next((x for x in r['_ranked'] if x['routes'].get('sense-led-line') == 'pin-change-interrupt' and x['hardware']['package'] == 'atmega328p-28-spdip'), None)
        check('fgm-5b: the attempt engine offers a candidate whose sense route is pin-change-interrupt (so the sense task must be checkable whatever route it picks)', pc is not None, sorted({x['routes'].get('sense-led-line') for x in r['_ranked']}))
        if pc is not None:
            p = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=r, candidate=pc['id'])
            s = _t(p, 'sense')
            check('fgm-5b: on the pin-change sense candidate the sense task is fed by the PCINT vector the rendered template defines (an isr-lane atom of the project), the read atom stays `called`, the context is isr, the agreement check says agrees (priority 0: the hardware orders it)',
                  s['agreement'] == 'agrees' and s['context'] == 'isr' and s['steps'][-1]['instance'].startswith('hal_sense_pcint.PCINT') and s['steps'][-1]['lane'] == 'isr' and s['priority'] == 0
                  and [x['lane'] for x in s['steps']][:-1] == ['called'], (s['steps'], s['agreement_why']))
        # the link: HardwareSystem.task_plan <- the recorded TaskPlan
        from board.custom import hardware_system as HWS
        from board.custom import hwsys_doors as D
        mgr = _manager()
        _register(mgr, 'SolveRun', __import__('cmod.custom.solve_record', fromlist=['store']).store(mgr, solved(), 'sub-test'))
        hs = SimpleNamespace(id=1, name=SYSTEM, task_plan='', stage='S1-breadboard')
        mgr.objectTables['HardwareSystem'] = {1: hs}
        code, before = D.system_one(mgr, SYSTEM)
        check('fgm-5b: before any Task Plan is recorded the Hardware System door shows no link (task_plan empty) and the row field is empty', code == 200 and before['system']['task_plan'] == '' and hs.task_plan == '', before['system'].get('task_plan'))
        plan = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=solved(), manager=mgr, apply_edits=False)
        STORE.store_plan(plan, mgr, 'sub-test')
        code, after = D.system_one(mgr, SYSTEM)
        hs2 = SimpleNamespace(id=1, name=SYSTEM)
        check('fgm-5b: recording the Task Plan (what POST /api/missions/<mission>/task-plan does) links it: the HardwareSystem row field task_plan = %s, and GET /api/hardware-systems/%s shows the same link'
              % (plan['name'], SYSTEM), hs.task_plan == plan['name'] == '%s:%s' % (LIGHT, SYSTEM) and after['system']['task_plan'] == plan['name'] and HWS.linked_task_plan(SYSTEM, mgr) == plan['name'], (hs.task_plan, after['system'].get('task_plan')))
        hs.task_plan = ''   # a re-seed of the code-owned row blanks the field: the door still derives the link from the TaskPlan rows
        code, again = D.system_one(mgr, SYSTEM)
        check('fgm-5b: the door derives the link from the TaskPlan rows on every read, so a re-seed that blanks the code-owned row loses nothing; another system has no link', again['system']['task_plan'] == plan['name'] and HWS.linked_task_plan('nowhere', mgr) == '')
        from board.custom import hwsys_system as HS
        check('fgm-5b: the "Task Plan arrives with fgm-3" text is gone from the system\'s undetermined words, which now say how the link is made',
              all('arrives with fgm-3' not in r['undetermined'] and 'task_plan' in r['undetermined'] for r in HS.rows(HWS.default_tables())), None)

    def priorities():
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import task_plan as TP
        spec = copy.deepcopy(AI.from_mission(LIGHT))
        by = {p['purpose']: p for p in spec['purposes']}
        by['ensure-polari-can-control-light']['deadline_ms']['value'] = 50          # the tightest: the command task goes first
        by['ensure-polari-observes-hardware-state']['importance'] = 'safety'          # equal deadline to the button: the more important Purpose wins
        by['ensure-button-controls-light']['importance'] = 'desired'
        p = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=solved(), spec=spec)
        order = [t['task'] for t in sorted((t for t in p['tasks'] if t['priority']), key=lambda t: t['priority'])]
        check('fgm-3: DEADLINE-MONOTONIC (D-sys-3): a 50 ms command task is priority 2 and the sense task (which serves that 50 ms Purpose AND, since scl, the safety observe Purpose) inherits the 50 ms deadline and, being more important on equal deadline, is 1 (no tie); of the two equal 100 ms deadlines the "safety" report task beats the "desired" button task; order %s' % order,
              order == ['sense', 'receive-command', 'relay-state', 'handle-button-press'] and 'TIE' not in _t(p, 'receive-command')['priority_basis'] and 'importance safety' in _t(p, 'sense')['priority_basis'] and 'TIE' not in _t(p, 'relay-state')['priority_basis'] and 'TIE' not in _t(p, 'handle-button-press')['priority_basis'], order)
        by2 = copy.deepcopy(spec)
        for q in by2['purposes']:
            q['importance'] = 'required'
        by2['purposes'][2]['deadline_ms']['value'] = 100
        p2 = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=solved(), spec=by2)
        check('fgm-3: tasks equal on both deadline and importance are marked TIE with the names of the others, and ordered only by the Mission\'s Purpose order',
              'TIE with' in _t(p2, 'receive-command')['priority_basis'] and _t(p2, 'handle-button-press')['priority'] < _t(p2, 'receive-command')['priority'], _t(p2, 'receive-command')['priority_basis'])

    def agreement_is_never_silent():
        from cmod.custom import task_plan_steps as ST
        steps = cache['plan']['tasks'][1]['steps']
        v, why = ST.agreement('isr', steps, '', 'edge')
        v2, why2 = ST.agreement('init', steps, '', 'edge')
        v3, why3 = ST.agreement('loop', cache['plan']['tasks'][0]['steps'], '', 'boot')
        v4, why4 = ST.agreement('task', steps, '', 'edge')
        check('fgm-3: a context that does not match the lanes of its atoms is "disagrees" and NAMED (isr on loop atoms; init on a repeating trigger; loop on a boot task), never re-labelled; a thread (task) matches a loop lane',
              v == 'disagrees' and 'derived lanes say loop' in why and 'led_toggle (loop)' in why and v2 == 'disagrees' and 'marked init' in why2 and v3 == 'disagrees' and 'boot task' in why3 and v4 == 'agrees', (why, why2, why3))
        v5, why5 = ST.agreement('loop', [], 'no atoms', 'edge')
        check('fgm-3: a task with no scheduled step is "unchecked" with the reason - agreement is not claimed', v5 == 'unchecked' and 'no atoms' in why5, why5)

    def edits_survive():
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import task_plan as TP
        from cmod.custom import task_plan_edit as TE
        from cmod.custom import task_plan_store as STORE
        mgr, run = mgr_with_run()
        plan = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr, apply_edits=False)
        STORE.store_plan(plan, mgr, 'sub-test')
        rows_before = len(mgr.objectTables['TaskDefinition'])
        none, why = TE.edit(plan['name'], 'relay-state', 'priority', '1', '', 'sub-test', mgr)
        bad, why2 = TE.edit(plan['name'], 'relay-state', 'priority', 'high', 'x', 'sub-test', mgr)
        bad2, why3 = TE.edit(plan['name'], 'handle-button-press', 'steps_order', 'led_toggle,clock', 'x', 'sub-test', mgr)
        bad3, why4 = TE.edit(plan['name'], 'relay-state', 'colour', 'red', 'x', 'sub-test', mgr)
        check('fgm-3: an edit without a why, with a non-number priority, a steps_order that is not a permutation of the task\'s steps, or an unknown field is refused by name (422-style), nothing is written',
              none is None and 'why' in why and bad is None and 'number' in why2 and bad2 is None and 'reordered' in why3 and bad3 is None and 'no overridable field' in why4
              and not mgr.objectTables.get('DerivedOverride'), (why, why2, why3, why4))
        o, w = TE.edit(plan['name'], 'relay-state', 'priority', '1', 'the report must never wait behind a button press', 'sub-test', mgr)
        _register(mgr, 'DerivedOverride', o)
        o2, w2 = TE.edit(plan['name'], 'handle-button-press', 'steps_order', 'toggle_pending,led,led_toggle,clock,led_follow_state,INT0_vect', 'check the toggle before the clock is read', 'sub-test', mgr)
        _register(mgr, 'DerivedOverride', o2)
        o3, w3 = TE.edit(plan['name'], 'receive-command', 'deadline_ms', '60', 'a longer command path was measured', 'sub-test', mgr)
        _register(mgr, 'DerivedOverride', o3)
        again = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr)
        r = _t(again, 'relay-state')
        e = r['edits'][0]
        check('fgm-3: an edit is a DerivedOverride (who, when, why; derived value recorded) shown BESIDE the derived value: relay-state priority %s (derived %s), the basis names who and why, the task and the plan say source = edited'
              % (r['priority'], e['derived']), o is not None and o.target_class == 'TaskDefinition' and o.who == 'sub-test' and o.why and o.when and o.derived_value == '3' and r['priority'] == 1 and e['derived'] == 3 and e['who'] == 'sub-test'
              and 'the report must never wait' in r['priority_basis'] and r['source'] == 'edited' and again['source'] == 'edited' and not e['flag'], (r['priority'], e))
        b = _t(again, 'handle-button-press')
        d = _t(again, 'receive-command')
        check('fgm-3: the step order and the deadline are editable too - the steps follow the edit (INT0_vect now last) with the derived order kept beside it; the deadline shows 60 ms with the derived 100 ms beside',
              b['steps_order'].endswith('INT0_vect') and b['derived_steps_order'].startswith('INT0_vect') and [s['n'] for s in b['steps']] == [1, 2, 3, 4, 5, 6] and d['deadline_ms'] == 60.0 and d['derived_deadline_ms'] == 100.0, (b['steps_order'], d['deadline_ms']))
        cache['edit'] = (mgr, run, plan)
        # re-derive and RE-RECORD: the Task rows keep only derived values, the edits are untouched
        STORE.store_plan(TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr, apply_edits=False), mgr, 'sub-test')
        after = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr)
        stored = next(r2 for r2 in mgr.objectTables['TaskDefinition'].values() if r2.name == plan['name'] + ':relay-state')
        check('fgm-3: a re-derive and re-record KEEPS every edit (same priority, same order, same deadline), the stored Task rows still hold the DERIVED values only (priority %s, not the edited 1), and no rows were duplicated' % stored.priority,
              _t(after, 'relay-state')['priority'] == 1 and _t(after, 'handle-button-press')['steps_order'].endswith('INT0_vect') and _t(after, 'receive-command')['deadline_ms'] == 60.0
              and stored.priority == 3 and stored.source == 'derived' and len(mgr.objectTables['TaskDefinition']) == rows_before, stored.priority)
        spec = copy.deepcopy(AI.from_mission(LIGHT))
        next(p for p in spec['purposes'] if p['purpose'] == 'ensure-polari-observes-hardware-state')['deadline_ms']['value'] = 200   # the report is now the loosest
        moved = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr, spec=spec)
        mr = _t(moved, 'relay-state')
        check('fgm-3: when the DERIVED value changes under an edit (the report deadline loosened, so its derived priority is now %s) the edit is KEPT (priority stays 1) and FLAGGED with both values' % mr['derived_priority'],
              mr['priority'] == 1 and mr['derived_priority'] != 3 and 'CHANGED UNDER THIS EDIT' in mr['edits'][0]['flag'] and '(it was 3 when' in mr['edits'][0]['flag'], mr['edits'][0]['flag'])
        c, wc = TE.edit(plan['name'], 'handle-button-press', 'context', 'isr', 'try it', 'sub-test', mgr)
        _register(mgr, 'DerivedOverride', c)
        ctx = _t(TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr), 'handle-button-press')
        check('fgm-3: a context edit to isr is applied AND the agreement check turns it into "disagrees", naming the lanes - the edit is not rejected and the disagreement is not hidden',
              ctx['context'] == 'isr' and ctx['agreement'] == 'disagrees' and 'derived lanes say loop' in ctx['agreement_why'] and ctx['derived_agreement'] == 'agrees', ctx['agreement_why'])
        from cmod.custom import overrides as OV
        OV.retire(c.name, mgr)
        OV.retire(o.name, mgr)
        back = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr)
        check('fgm-3: retiring an edit restores the derived value (the record of the edit survives as a retired DerivedOverride)',
              _t(back, 'relay-state')['priority'] == 3 and _t(back, 'relay-state')['source'] == 'derived' and _t(back, 'handle-button-press')['context'] == 'loop' and c.status == 'retired', _t(back, 'relay-state')['priority'])

    def designed_for_once():
        from cmod.custom import task_plan as TP
        from cmod.custom import task_plan_store as STORE
        mgr, run, plan = cache['edit']
        row = STORE.plan_row(plan['name'], mgr)
        first = json.loads(row.designed_for_json)
        check('fgm-3: Designed for was written ONCE at the first record: system, processors, tier, variants, pins, the run\'s sha256, who and when',
              first['tier'] == 'bare-c' and first['result_sha256'] == run.result_sha256 and first['hardware_system'] == SYSTEM and first['processors'] == ['arduino-uno-r3:U1'] and first['variants'] == plan['variants'] and first.get('recorded_at'), first)
        r = cache['bench']
        demo = next(x for x in r['_ranked'] if x['routes'].get('read-button') == 'ext-interrupt' and x['routes'].get('sense-led-line') == 'ext-interrupt' and x['routes'].get('drive-led') == 'gpio-out' and x['hardware']['package'] == 'atmega328p-28-spdip')
        other = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=r, candidate=demo['id'], manager=mgr, apply_edits=False)
        STORE.store_plan(other, mgr, 'someone-else')
        after = json.loads(STORE.plan_row(plan['name'], mgr).designed_for_json)
        shown = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=r, candidate=demo['id'], manager=mgr)
        check('fgm-3: a second derive with ANOTHER candidate (the interrupt plan) and a second record does not change Designed for (same bytes), the plan still reports the recorded origin, says the derivation used another, and the current variants are the new ones',
              after == first and shown['designed_for'] == first and shown['designed_for_recorded'] and any('the record is never changed' in n for n in shown['notes']) and shown['variants'].get('read-button') == 'ext-interrupt', shown['notes'])
        STORE.store_plan(TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr, apply_edits=False), mgr, 'sub-test')

    def also_runs_on():
        from cmod.custom import task_plan_store as STORE
        mgr, run, plan = cache['edit']
        row, why, appended = STORE.check_also_runs_on(plan['name'], TQFP, mgr, who='sub-test')
        check('fgm-3: ALSO RUNS ON - the same variants resolved on the 32-pin TQFP package through sol-0\'s recorded assignment append a "resolver-valid" row (not proven on a twin or hardware), with what changed and the open rungs',
              appended and row['how_we_know'] == 'resolver-valid' and row['hardware'] == TQFP and row['tier'] == 'bare-c' and row['what_changed'] and 'NOT run on a twin' in row['detail'] and row['solve_run'] == run.name, (row, why))
        again, why2, appended2 = STORE.check_also_runs_on(plan['name'], 'atmega328p-32-tqfp', mgr)
        check('fgm-3: asking again (by the package alone) does not duplicate the row; the plan lists exactly one "also runs on"',
              not appended2 and why2 == 'already recorded' and len(json.loads(STORE.plan_row(plan['name'], mgr).also_runs_on_json)) == 1, why2)
        no, why3, a3 = STORE.check_also_runs_on(plan['name'], 'esp32-c3', mgr)
        none, why4, a4 = STORE.check_also_runs_on(plan['name'], 'nowhere', mgr)
        bad, why5, a5 = STORE.check_also_runs_on(plan['name'], TQFP, mgr, how_we_know='trust-me')
        check('fgm-3: hardware the same variants do not resolve on is REFUSED with sol-0\'s reason (the C3), an unknown hardware says what is known, and how_we_know must be one of the three rungs of the proof ladder',
              no is None and not a3 and 'esp32-c3' in why3 and none is None and 'lists no hardware' in why4 and bad is None and 'proven-on-hardware' in why5, (why3[:120], why4[:120], why5))
        from cmod.custom import task_plan as TP
        p = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=run.name, manager=mgr)
        rows = TP.designed_rows(p)
        check('fgm-3: the derived plan carries the also-runs-on list and its page rows: one "Designed for" and one "Also runs on" with how we know', [r['what'] for r in rows] == ['Designed for', 'Also runs on'] and rows[1]['how_we_know'] == 'resolver-valid', rows)

    def doors_and_cli():
        import falcon
        from falcon import testing
        from cmod.cmod_mission_api import MissionAPI
        from cmod.cmod_pin_profile_api import PinProfileAPI
        from cmod.cmod_approach_profile_api import ApproachProfileAPI
        from cmod.cmod_solve_api import SolveAPI
        from cmod.cmod_task_plan_api import TaskPlanAPI
        from cmod.custom import solve_record as REC
        from cmod.custom import task_plan as TP
        for first in (False, True):
            app, mgr = falcon.App(), _manager()
            _register(mgr, 'SolveRun', REC.store(mgr, solved(), 'sub-test'))
            ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
            order = (TaskPlanAPI, MissionAPI, PinProfileAPI, ApproachProfileAPI, SolveAPI)
            for cls in (order if first else tuple(reversed(order))):
                cls(polServer=ps, manager=mgr)
            c = testing.TestClient(app)
            r = c.simulate_get('/api/missions/%s/task-plan' % LIGHT)
            others = [c.simulate_get('/api/missions/%s/%s' % (LIGHT, s)).status_code for s in ('solution', 'resolution', 'pin-profiles', 'approach', 'solve-runs')] + [c.simulate_get('/api/missions').status_code]
            check('fgm-3: GET /api/missions/{name}/task-plan on ONE real falcon.App with the real MissionAPI, pin-profiles, approach and solve doors (%s first): all answer, none shadows another; the plan is seeded from the STORED run'
                  % ('mine' if first else 'theirs'), r.status_code == 200 and r.json['ok'] and r.json['tier'] == 'bare-c' and len(r.json['tasks']) == 5 and r.json['solve_run'].startswith(LIGHT + ':') and others == [200] * 6,
                  (r.status_code, r.text[:100], others))
        for v in ('tasks', 'agreement', 'triggers', 'shared-data', 'edits', 'designed-for'):
            rv = c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'view': v})
            check('fgm-3: ?view=%s answers flat plain-words rows for the page table' % v, rv.status_code == 200 and rv.json['view'] == v and rv.json['count'] == len(rv.json['rows']) > 0, rv.text[:100])
        check('fgm-3: an unknown Mission or system is a 404; an unknown run, candidate or view is a 422, each naming what is known',
              c.simulate_get('/api/missions/nope/task-plan').status_code == 404 and c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'system': 'nope'}).status_code == 404
              and 'uno-light-system' in c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'system': 'nope'}).json['error']
              and c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'run': 'nope'}).status_code == 422 and c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'candidate': 'nope'}).status_code == 422
              and c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'view': 'nope'}).status_code == 422)
        n0 = len((mgr.objectTables.get('TaskPlan') or {}))
        r = c.simulate_post('/api/missions/%s/task-plan' % LIGHT, json={})
        check('fgm-3: POST /api/missions/{name}/task-plan derives and RECORDS the plan (201): a TaskPlan row, five Task rows, five triggers and the shared-data rows, with Designed for written',
              r.status_code == 201 and r.json['stored'] and n0 == 0 and len(mgr.objectTables['TaskPlan']) == 1 and len(mgr.objectTables['TaskDefinition']) == 5 and len(mgr.objectTables['TaskTrigger']) == 5
              and json.loads(next(iter(mgr.objectTables['TaskPlan'].values())).designed_for_json)['tier'] == 'bare-c' and r.json['designed_for_recorded'], (r.status_code, r.text[:160]))
        plan_name = r.json['name']
        a = c.simulate_post('/api/task-plans/%s/also-runs-on' % plan_name, json={'hardware': TQFP})
        a2 = c.simulate_post('/api/task-plans/%s/also-runs-on' % plan_name, json={'hardware': TQFP})
        a3 = c.simulate_post('/api/task-plans/%s/also-runs-on' % plan_name, json={'hardware': 'esp32-c3'})
        a4 = c.simulate_post('/api/task-plans/%s/also-runs-on' % 'nope:nothing' % (), json={'hardware': TQFP}) if False else c.simulate_post('/api/task-plans/nope-mission:nothing/also-runs-on', json={'hardware': TQFP})
        g = c.simulate_get('/api/missions/%s/task-plan' % LIGHT)
        check('fgm-3: POST /api/task-plans/{plan}/also-runs-on adds a resolver-valid row on the TQFP (201), a repeat is 200 with no duplicate, the C3 is refused (422) with the reason, an unknown plan is 404; the next GET lists it',
              a.status_code == 201 and a.json['row']['how_we_know'] == 'resolver-valid' and a2.status_code == 200 and not a2.json['appended'] and len(a2.json['also_runs_on']) == 1
              and a3.status_code == 422 and 'esp32-c3' in a3.json['error'] and a4.status_code in (404, 422) and [x['hardware'] for x in g.json['also_runs_on']] == [TQFP], (a.status_code, a2.status_code, a3.status_code, a4.status_code, g.json.get('also_runs_on')))
        ov = c.simulate_get('/api/missions/%s/task-plan' % LIGHT, params={'view': 'edits'})
        check('fgm-3: with no hand edit the "edits" rows say so in words (one row), not an empty table', ov.json['count'] == 1 and 'no task has been edited' in ov.json['rows'][0]['why'], ov.text[:120])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = TP.main(['derive', LIGHT])
        out = buf.getvalue()
        check('fgm-3: CLI `derive uno-light-mission` prints the tasks with triggers, deadlines, priorities, agreement and the priority rule - and says plainly that no solve run exists (use --solve)',
              rc == 0 and 'NO solve run exists' in out and 'handle-button-press' in out and 'Priority rule: deadline-monotonic' in out and 'agreement agrees' in out, out[:200])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = TP.main(['derive', LIGHT, '--json'])
        check('fgm-3: CLI --json prints the same plan as JSON', rc == 0 and json.loads(buf.getvalue())['mission'] == LIGHT)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = TP.main(['derive', 'nope'])
            rc2 = TP.main(['derive', LIGHT, '--system', 'nope'])
            rc3 = TP.main(['derive', LIGHT, '--run', 'nope'])
        check('fgm-3: CLI refuses an unknown Mission, system or run (exit 3, [REFUSED])', rc == 3 and rc2 == 3 and rc3 == 3 and buf.getvalue().count('[REFUSED]') == 3, buf.getvalue()[:200])

    def page_and_manifest():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
        from cmod.custom import task_plan as TP
        pg = next((p for p in P if p['pageRoute'] == 'task-plan'), None)
        d = json.loads(pg['definition']) if pg else {'rows': []}
        items = [i for r in d['rows'] for i in r['items']] if pg else []
        check('fgm-3: /display/task-plan is a configured page titled "Task plan": 6 class-rows-tables (no raw JSON panel, no custom component), each described with "What this is for", reading ?view= of the door',
              pg is not None and d.get('title') == 'Task plan' and len(items) == 6 and all(i['componentProps']['componentName'] == 'class-rows-table' for i in items) and all('What this is for' in i['description'] for i in items)
              and all(i['componentProps']['inputs']['dataPath'].startswith('/api/missions/%s/task-plan?view=' % LIGHT) for i in items), len(items))
        plan = TP.derive_task_plan(LIGHT, SYSTEM, solve_run=solved())
        served = {'tasks': TP.task_rows(plan), 'agreement': TP.agreement_rows(plan), 'triggers': TP.trigger_rows(plan), 'shared-data': TP.shared_rows(plan), 'edits': TP.edit_rows(plan), 'designed-for': TP.designed_rows(plan)}
        missing, raw = [], []
        for i in items:
            view = i['componentProps']['inputs']['dataPath'].split('view=')[1].split('&')[0]
            missing += [c for c in i['componentProps']['inputs']['columns'].split(',') if c not in served[view][0]]
            raw += [v for r in served[view] for v in r.values() if str(v).startswith(('{', '['))]
        check('fgm-3: every column the page asks for is a field of the served row, and no served value is raw JSON', not missing and not raw, (missing, raw[:2]))
        m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))
        f = m['files']
        want = {'api': ['cmod_task_plan_api'], 'page': ['cmod_task_plan_page'], 'selftests': ['cmod_task_plan_selftest'],
                'objects': ['objects/cmod/TaskDefinition', 'objects/cmod/TaskPlan', 'objects/cmod/TaskStructBinding', 'objects/cmod/TaskTrigger'],
                'custom': ['custom/task_plan', 'custom/task_plan_doors', 'custom/task_plan_edit', 'custom/task_plan_steps', 'custom/task_plan_store']}
        got = {k: [n for n in names if n not in f.get(k, [])] for k, names in want.items()}
        check('fgm-3 MANIFEST: polari-app.json lists every new file (api, page, selftest, four classes, five custom modules) and the classes TaskPlanAPI, TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding',
              not any(got.values()) and all(c in m['classes'] for c in ('TaskPlanAPI', 'TaskPlan', 'TaskDefinition', 'TaskTrigger', 'TaskStructBinding')), got)
        check('...each listed file exists on disk', all(os.path.isfile(os.path.join(os.path.dirname(__file__), n + '.py')) for n in sum(want.values(), [])))
        from cmod.cmod_basis import CMOD_CLASSES, TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding
        from polariapps.apps_seed import SEED_POLARI_APPS
        reg = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'polariApiServer', 'polariServer.py')).read()
        fi = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'polariApiServer', 'feature_imports.py')).read()
        check('fgm-3: the four classes are registered (cmod_basis, polariServer defClassList, feature_imports) and the Hardware app nav has its own "Task plan" group opening the page',
              all(c in CMOD_CLASSES for c in (TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding)) and 'TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding' in reg and "'TaskPlan', 'TaskDefinition', 'TaskTrigger', 'TaskStructBinding'" in fi
              and '/display/task-plan' in json.dumps(SEED_POLARI_APPS), None)
        check('fgm-3: every class says in plain words what it is (plain_words) and has a docstring that begins "What it is:"',
              all(getattr(c, 'plain_words', '') and (c.__doc__ or '').lstrip().startswith('What it is:') for c in (TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding)))

    return (light_plan, no_run_and_interrupt_plan, sense_routes_and_link, priorities, agreement_is_never_silent, edits_survive, designed_for_once, also_runs_on, doors_and_cli, page_and_manifest)


def main():
    passed = total = 0
    failures = []

    def check(label, cond, detail=None):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append(label)
        print(('PASS ' if cond else 'FAIL ') + label + ('' if cond or detail is None else '   <- %s' % (str(detail)[:500],)))
    for part in task_plan_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
