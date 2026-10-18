"""
@module cmod.custom.approach_profile

rt-0 (MISSION_PROFILE_SOLVER_PLAN.md section 8.2): the APPROACH PRE-PROFILER. `approach_profile(mission, board)` reads what a Hardware Mission demands of the
processor - its independent triggers and their deadlines, the periodic tasks, the operations that block, the concurrent responsibilities, the data rate -
and RECOMMENDS a runtime tier with the reasons in plain words, then CHECKS every tier against the hardware (memory, support by name, the isotope variants
that stay eligible). DERIVED, never authored; ADVISED, never forced: a person may pick another tier and the cost of doing so is shown.

The rule (section 8.2), applied per processor:
  bare-c    a main loop + interrupts meets every deadline. The argument: one pass of the loop (every loop task once + the longest waits) stretched by the
            share of the CPU the interrupts take must fit inside the tightest deadline (less the debounce time for a button). Computed from the atoms'
            measured sizes (cycle UPPER BOUNDS, estimated) and the transmit time of the largest frame (estimated). Parts this profiler cannot bound
            (loops, generated/library calls) are listed with the room left for them - the answer stays "provisional" until a twin cycle count closes it.
  freertos  the same argument FAILS: several independent periodic / blocking tasks whose deadlines one loop cannot guarantee. A preemptive scheduler bounds a
            task by its own work, not by the whole loop (the preemptive response analysis itself is the Task Plan's job, fgm-3).
  zephyr    FreeRTOS is warranted AND the system is large: many drivers or bus devices, or many threads (named thresholds below; rules of this profiler, not
            measured facts).
CLI:  python3 -m cmod.custom.approach_profile mission <name> [--board B] [--tier T] [--json]
"""
import json

from cmod.custom import approach_profile_atoms as A
from cmod.custom import approach_profile_input as AI
from cmod.custom import approach_profile_tiers as T
from cmod.custom.approach_profile_atoms import q, undetermined

ZEPHYR_MIN_DRIVERS = 4          # distinct non-basic peripheral drivers (UART, ADC, SPI, I2C, ...)
ZEPHYR_MIN_BUS_DEVICES = 3      # distinct external bus devices
ZEPHYR_MIN_THREADS = 8          # independent loop/periodic activities
THRESHOLD_BASIS = 'a rule of thumb of this profiler (named constant in cmod.custom.approach_profile), not a measured or cited fact'


def _count(n, unit, basis):
    return q('measured', n, unit, 'counted: ' + basis)


def _shape(kind):
    return {'boot': 'one-shot at boot', 'period': 'periodic'}.get(kind, 'an event, not on a clock')


# ------------------------------------------------------------------ the demand
def _superloop(proc, purposes):
    """The argument for a main loop on one processor."""
    loop = [t for t in proc['tasks'] if t['lane'] in ('loop', 'thread')]
    known_us = sum(t['known_us'] for t in loop)
    blocks = [(t['name'], b) for t in loop for b in t['blocking'] if not b.get('inside_measured')]   # cyc-0: a wait already inside a measured count is not added twice
    block_us = sum(b['worst_us']['value'] for _n, b in blocks if b['worst_us']['value'] is not None)
    unknown_blocks = [(n, b) for n, b in blocks if b['worst_us']['value'] is None]
    bases = [t.get('cycles_basis', 'upper-bound') for t in loop]
    cycle_basis = 'measured' if bases and all(b == 'measured' for b in bases) else ('upper-bound' if not any(b != 'upper-bound' for b in bases) else 'mixed')
    unbounded = [{'task': t['name'], 'why': '; '.join(t['unbounded'])} for t in loop if t['unbounded']]
    util, left_out = 0.0, []
    for i in proc['isrs']:
        if i['rate_hz']['value'] is None or i['per_event_us']['value'] is None:
            left_out.append(i['name'])
        else:
            util += i['rate_hz']['value'] * i['per_event_us']['value'] / 1e6
    inflate = 1.0 / (1.0 - util) if util < 1 else float('inf')
    pass_us = (known_us + block_us) * inflate
    checks = []
    for p in purposes:
        if p['deadline_ms'] is None or str((p['trigger'] or {}).get('kind')) == 'boot':
            continue
        deb = (p['debounce_ms'] or {}).get('value') or 0
        budget = p['deadline_ms']['value'] - deb
        margin = budget * 1000.0 - pass_us
        checks.append({'purpose': p['purpose'], 'importance': p['importance'], 'deadline_ms': p['deadline_ms'], 'debounce_ms': p['debounce_ms'],
                       'budget_us': q('criterion', round(budget * 1000.0, 1), 'us', 'deadline %s ms minus debounce %s ms' % (p['deadline_ms']['value'], deb)),
                       'margin_us': q('estimated', round(margin, 1), 'us', 'the budget minus one pass of the loop (known parts, stretched by the interrupt share)'),
                       'state': 'fails' if margin < 0 else 'fits'})
    for t in loop:                       # a periodic task must also finish its pass before its next period
        if t.get('period_ms') and t['period_ms'].get('value') is not None:
            margin = t['period_ms']['value'] * 1000.0 - pass_us
            checks.append({'purpose': 'period of %s' % t['name'], 'importance': '', 'deadline_ms': t['period_ms'], 'debounce_ms': None,
                           'budget_us': q(t['period_ms']['kind'], round(t['period_ms']['value'] * 1000.0, 1), 'us', 'its period'),
                           'margin_us': q('estimated', round(margin, 1), 'us', 'the period minus one pass of the loop'), 'state': 'fails' if margin < 0 else 'fits'})
    worst = min(checks, key=lambda c: c['margin_us']['value']) if checks else None
    verdict = 'fails' if worst and worst['state'] == 'fails' else ('fits-known' if (unbounded or unknown_blocks or left_out) else 'fits')
    if not checks:
        verdict = 'no-deadline'
    return {'processor': proc['name'], 'loop_tasks': [t['name'] for t in loop],
            'cycle_basis': cycle_basis, 'measured_gap': proc.get('loop_measured'), 'uart_split': any(t.get('measured') and t['measured']['split'] for t in loop),
            'pass_known_us': q('estimated', round(pass_us, 1), 'us', 'one pass of the loop, worst case, known parts: %.1f us of atom code (%s) + %.1f us of waiting on hardware (estimated from the baud), '
                               'stretched by the interrupt share %.1f%% (x%.3f)' % (known_us, {'measured': 'worst counts MEASURED on the simavr twin', 'mixed': 'measured where a cycle record has it, else upper bounds'}.get(cycle_basis, 'upper bounds'),
                                                                                  block_us, util * 100, inflate if inflate != float('inf') else 0)),
            'atom_us': q('measured' if cycle_basis == 'measured' else 'estimated', round(known_us, 1), 'us',
                         'sum of the loop tasks\' worst %s' % {'measured': 'cycle counts measured on the twin (CPU part where a task waits on the USART): %s' % '; '.join(
                             '%s %d' % (t['name'], t.get('cycles', 0)) for t in loop), 'mixed': 'cycle counts (measured where a cycle record has them, else upper bounds)'}.get(cycle_basis, 'cycle upper bounds')),
            'blocking_us': q('estimated', round(block_us, 1), 'us', 'sum of the worst waits in the loop'),
            'isr_share': q('estimated', round(util * 100, 2), '%', 'sum over the interrupts of rate x per-event upper bound; interrupts without a rate are left out: %s' % (', '.join(left_out) or 'none')),
            'isr_left_out': left_out, 'checks': checks, 'worst': worst, 'unbounded': unbounded,
            'unknown_blocking': [{'task': n, 'what': b['what']} for n, b in unknown_blocks],
            'room_for_unbounded_us': q('estimated', worst['margin_us']['value'], 'us', 'what is left of the tightest budget for the parts this profiler cannot bound: %s' % (', '.join(u['task'] for u in unbounded) or 'none')) if worst else undetermined('no deadline'),
            'verdict': verdict}


def _drivers(proc):
    ids = set()
    for t in proc['tasks']:
        ids |= {p for p in t['peripherals'] if not AI.BASIC.match(p)}
    return sorted(ids)


def demand_of(spec, manager=None):
    purposes = spec['purposes']
    trig = [p for p in purposes if str((p['trigger'] or {}).get('kind')) != 'boot']
    dl = [p for p in purposes if p['deadline_ms'] is not None]
    tight = min(dl, key=lambda p: (p['deadline_ms']['value'], str((p['trigger'] or {}).get('kind')) == 'boot')) if dl else None
    periodic, blocking, conc, rate = [], [], [], []
    for pr in spec['processors']:
        for t in pr['tasks']:
            if t.get('period_ms') and t['period_ms'].get('value') is not None:
                periodic.append({'processor': pr['name'], 'task': t['name'], 'period_ms': t['period_ms'], 'serves': t['serves']})
            for b in t['blocking']:
                if t['lane'] != 'called' and not any(x['atom'] == b['atom'] and x['kind'] == b['kind'] for x in blocking):
                    blocking.append(dict(b, processor=pr['name'], in_task=t['name']))
        drv = _drivers(pr)
        lanes = {}
        for t in pr['tasks']:
            lanes[t['lane']] = lanes.get(t['lane'], 0) + 1
        conc.append({'processor': pr['name'], 'board': pr['board'], 'interrupt_vectors': _count(len(pr['isrs']), 'vectors', 'ISR atoms linked into the glue'),
                     'loop_tasks': _count(lanes.get('loop', 0) + lanes.get('thread', 0), 'tasks', 'loop-lane tasks of the schedule'),
                     'init_tasks': _count(lanes.get('init', 0), 'tasks', 'init-lane tasks'),
                     'called': _count(lanes.get('called', 0), 'tasks', 'tasks called by another task'),
                     'drivers': drv, 'driver_count': _count(len(drv), 'drivers', 'distinct non-basic peripherals the atoms touch: %s' % (', '.join(drv) or 'none')),
                     'bus_devices': _count(len([b for b in pr['tasks'] if any(x['kind'] in ('bus-read', 'bus-transaction') for x in b['blocking'])]), 'devices', 'tasks that wait on a bus transaction')})
        for t in pr['tasks']:
            if t.get('period_ms') and t['period_ms'].get('value') and pr.get('frame_bytes') and pr.get('baud'):
                bps = pr['frame_bytes'] * 1000.0 / t['period_ms']['value']
                cap = pr['baud'] / 10.0
                rate.append({'processor': pr['name'], 'task': t['name'], 'bytes_per_s': q('estimated', round(bps, 1), 'B/s', 'the largest frame (%d B) once per period (%s ms)' % (pr['frame_bytes'], t['period_ms']['value'])),
                             'line_capacity': q('cited', cap, 'B/s', 'baud %d / 10 bits per byte (8N1)' % pr['baud']), 'share_of_line': q('estimated', round(bps / cap * 100, 1), '%', 'rate over line capacity')})
    pins = _pin_profiles(spec, manager)
    sl = [_superloop(pr, purposes) for pr in spec['processors']]
    return {'independent_triggers': {'count': _count(len(trig), 'triggers', 'Purposes whose trigger is not the one-shot boot'),
                                     'items': [{'purpose': p['purpose'], 'importance': p['importance'], 'kind': (p['trigger'] or {}).get('kind', ''),
                                                'shape': _shape((p['trigger'] or {}).get('kind')), 'what': (p['trigger'] or {}).get('what', '')} for p in purposes]},
            'tightest_deadline': {'value': tight['deadline_ms'], 'purpose': tight['purpose'], 'key': tight['deadline_key']} if tight else None,
            'periodic': periodic, 'blocking': blocking, 'concurrency': conc, 'data_rate': rate, 'pin_profiles': pins, 'superloop': sl}


def _pin_profiles(spec, manager):
    if not spec.get('mission') or spec.get('source', '').startswith('synthetic'):
        return {'profiles': undetermined('pin profiles are read from real Purposes; this Mission is synthetic'), 'interrupt_inputs': undetermined('as above')}
    try:
        from cmod.custom import pin_profile_mission as PM
        res = PM.mission_profiles(spec['mission'], manager=manager)
        irq = [p for p in res['profiles'] if p['kind'] == 'interrupt-in']
        return {'profiles': _count(res['pins_needed'], 'pin needs', 'pp-0 rolled-up pin profiles of the Mission'),
                'interrupt_inputs': _count(len(irq), 'pins', 'pp-0 profiles of kind interrupt-in')}
    except Exception as e:  # noqa: BLE001 - the profile roll-up is context, not a gate
        return {'profiles': undetermined('pin profiles not readable: %s' % e), 'interrupt_inputs': undetermined('as above')}


# ------------------------------------------------------------------ the recommendation
def _ms(us):
    return '%.1f ms' % (us / 1000.0)


def recommend(demand):
    """-> {tier, reasons[], provisional (bool), caveats[], escalated_by}"""
    reasons, caveats = [], []
    trig = demand['independent_triggers']
    n = trig['count']['value']
    shapes = ['%s (%s)' % (i['what'] or i['kind'], i['shape']) for i in trig['items'] if i['kind'] != 'boot']
    td = demand['tightest_deadline']
    reasons.append('%d independent trigger%s besides boot: %s.' % (n, '' if n == 1 else 's', '; '.join(shapes) or 'none'))
    if td:
        reasons.append('The tightest deadline is %s ms (%s of %s).' % (td['value']['value'], td['key'], td['purpose']))
    if demand['periodic']:
        reasons.append('Periodic work: %s.' % '; '.join('%s every %s ms' % (p['task'], A.text(p['period_ms']).split(' (')[0].replace(' ms', '')) for p in demand['periodic']))
    else:
        reasons.append('No periodic task.')
    if demand['blocking']:
        reasons.append('Operations that block: %s.' % '; '.join('%s (%s: %s, up to %s)' % (b['in_task'], b['kind'], b['what'], A.text(b['worst_us'])) for b in demand['blocking']))
    else:
        reasons.append('Nothing in the loop blocks.')
    tier, esc, prov = 'bare-c', '', False
    fails = [s for s in demand['superloop'] if s['verdict'] == 'fails']
    for s in demand['superloop']:
        w = s['worst']
        if w is None:
            continue
        reasons.append('%s: one pass of a main loop takes at most about %s (%s of atom code + %s waiting, stretched %.1f%% by interrupts); the tightest budget is %s (%s), so the margin is %s.' % (
            s['processor'], _ms(s['pass_known_us']['value']), _ms(s['atom_us']['value']), _ms(s['blocking_us']['value']), s['isr_share']['value'],
            _ms(w['budget_us']['value']), w['purpose'], _ms(w['margin_us']['value'])))
        if s.get('cycle_basis') == 'measured':
            reasons.append('The atom code in that pass is MEASURED on the simavr twin, not bounded from sizes (%s; cycles are the worst count per call over a recorded run - see the cycle record).' % s['atom_us']['basis'].split(': ', 1)[-1])
            if s.get('uart_split'):
                caveats.append('the wait to send a report is derived from the baud, not read from the twin: the twin\'s USART takes longer per byte than the chip\'s, so the CPU part of the send is measured and the wait is added separately.')
        mg = s.get('measured_gap')
        if mg:
            reasons.append('End to end on the twin, the longest the main loop went without polling was %s (%d cycles, %s)%s.' % (
                _ms(mg['worst_gap_cycles'] / 16.0), mg['worst_gap_cycles'], mg['ref'],
                ('; at the chip\'s byte time %s' % _ms(mg['worst_gap_chip_timed_cycles'] / 16.0)) if mg.get('worst_gap_chip_timed_cycles') and mg['worst_gap_chip_timed_cycles'] != mg['worst_gap_cycles'] else ''))
        if s['unbounded']:
            prov = True
            caveats.append('%d task(s) have parts this profiler cannot bound (%s). They may use up to %s of the margin before the answer changes; measure their cycles on the twin to close it.' % (
                len(s['unbounded']), ', '.join(u['task'] for u in s['unbounded']), _ms(s['room_for_unbounded_us']['value']) if s['room_for_unbounded_us']['value'] is not None else 'an unknown part'))
        if s['unknown_blocking']:
            prov = True
            caveats.append('waits with no derived duration: %s.' % '; '.join('%s %s' % (u['task'], u['what']) for u in s['unknown_blocking']))
        if s['isr_left_out']:
            caveats.append('interrupts whose rate depends on the outside world are left out of the CPU share: %s.' % ', '.join(s['isr_left_out']))
    if fails:
        tier = 'freertos'
        for s in fails:
            w = s['worst']
            reasons.append('A main loop CANNOT guarantee %s on %s: its pass (%s) leaves a margin of %s, which is negative. Several independent periodic or blocking tasks need a preemptive scheduler: FreeRTOS.' % (
                w['purpose'], s['processor'], _ms(s['pass_known_us']['value']), _ms(w['margin_us']['value'])))
        esc = 'the main-loop argument fails'
        drivers = max((c['driver_count']['value'] for c in demand['concurrency']), default=0)
        bus = max((c['bus_devices']['value'] for c in demand['concurrency']), default=0)
        threads = max((c['loop_tasks']['value'] for c in demand['concurrency']), default=0)
        z = []
        if drivers >= ZEPHYR_MIN_DRIVERS:
            z.append('%d distinct peripheral drivers (threshold %d)' % (drivers, ZEPHYR_MIN_DRIVERS))
        if bus >= ZEPHYR_MIN_BUS_DEVICES:
            z.append('%d bus devices (threshold %d)' % (bus, ZEPHYR_MIN_BUS_DEVICES))
        if threads >= ZEPHYR_MIN_THREADS:
            z.append('%d independent activities (threshold %d)' % (threads, ZEPHYR_MIN_THREADS))
        if z:
            tier = 'zephyr'
            esc = 'FreeRTOS is warranted and the system is large'
            reasons.append('The system is also large - %s - which is where Zephyr\'s driver model and devicetree start to pay (%s).' % ('; '.join(z), THRESHOLD_BASIS))
        else:
            reasons.append('Not large enough for Zephyr: %d driver(s) (threshold %d), %d bus device(s) (threshold %d), %d activities (threshold %d); %s.' % (
                drivers, ZEPHYR_MIN_DRIVERS, bus, ZEPHYR_MIN_BUS_DEVICES, threads, ZEPHYR_MIN_THREADS, THRESHOLD_BASIS))
    else:
        reasons.append('So a main loop plus interrupts meets every deadline%s: bare C is the smallest runtime that does.' % (' on the known parts' if prov else ''))
    return {'tier': tier, 'label': T.label(tier), 'reasons': reasons, 'provisional': prov, 'caveats': caveats, 'escalated_by': esc,
            'superloop_failure': '; '.join('%s on %s' % (s['worst']['purpose'], s['processor']) for s in fails)}


# ------------------------------------------------------------------ derived priorities (terminology section 8)
def priorities(spec, tier, demand):
    """deadline-monotonic: shorter deadline = higher priority; equal deadlines -> higher importance; still equal -> the schedule order (said)."""
    rank = {k: i for i, k in enumerate(AI.IMPORTANCE)}
    by_p = {p['purpose']: p for p in spec['purposes']}
    rows = []
    for pr in spec['processors']:
        for order, t in enumerate(pr['tasks']):
            if t['lane'] not in ('loop', 'thread'):
                continue
            serving = [by_p[s] for s in t['serves'] if s in by_p]
            dls = [(p['deadline_ms']['value'], p['purpose']) for p in serving if p['deadline_ms'] is not None]
            if t.get('period_ms') and t['period_ms'].get('value') is not None:
                dls.append((t['period_ms']['value'], 'its own period'))
            dl = min(dls) if dls else None
            imp = min((p['importance'] for p in serving), key=lambda k: rank.get(k, 9), default='')
            rows.append({'processor': pr['name'], 'task': t['name'], 'order': order, 'deadline_ms': q('criterion' if dl and dl[1] != 'its own period' else 'estimated', dl[0], 'ms', 'tightest of the Purposes it serves (%s)' % dl[1]) if dl else undetermined('no Purpose that this task serves states a deadline'),
                         'importance': imp or 'none', 'serves': ', '.join(t['serves']) or 'no Purpose names it', '_dl': dl[0] if dl else float('inf'), '_imp': rank.get(imp, 9)})
    rows.sort(key=lambda r: (r['_dl'], r['_imp'], r['order']))
    for i, r in enumerate(rows, 1):
        r['priority'] = i
        r['tie'] = any(o is not r and o['_dl'] == r['_dl'] and o['_imp'] == r['_imp'] for o in rows)
    for r in rows:
        del r['_dl'], r['_imp']
    note = ('A bare-C main loop has no priorities: this is the order the loop should serve its tasks in.' if tier == 'bare-c'
            else 'Priority 1 is the highest.')
    ties = [r['task'] for r in rows if r['tie']]
    return {'tier': tier, 'rule': 'deadline-monotonic: a shorter deadline is a higher priority; equal deadlines: the more important Purpose wins; still equal: the schedule order (marked tie)',
            'preview': 'preview - the real plan is the Task Plan: page /display/task-plan, door GET /api/missions/<name>/task-plan (recorded by POST); nothing here is stored and a person\'s override is a DerivedOverride (who, when, why)',
            'note': note, 'ties': ties, 'rows': rows,
            'tie_note': ('%d task(s) tie on both deadline and importance, so their relative order is only the schedule order: %s' % (len(ties), ', '.join(ties))) if ties else ''}


# ------------------------------------------------------------------ the whole answer
def approach_profile(mission, board=None, manager=None, spec=None, tier=None):
    """-> the approach for a Mission on a board. `spec` (a normalised input) is for tests / synthetic Missions; `tier` = a tier a person asks about."""
    from cmod.custom import isotope_variants_eligibility as E
    spec = spec or AI.from_mission(mission, manager)
    board_basis = 'asked for'
    if not board:
        board, board_basis = spec.get('board_ref') or '', 'the Mission\'s own board participant'
    ctx = E.context(board)
    if ctx is None:
        raise KeyError('no board %r with a SoC row (known: %s)' % (board, ', '.join(E.boards())))
    demand = demand_of(spec, manager)
    rec = recommend(demand)
    reps = {t: T.check_tier(t, board, ctx, spec, rec['tier'], manager) for t in T.TIERS}
    for t in T.TIERS:
        reps[t]['cost_of_choosing'] = T.cost_of_choosing(t, reps[t], rec['tier'], rec['superloop_failure'], spec, reps, board)
    avail = [t for t in T.TIERS if reps[t]['state'] == 'available' and T.TIERS.index(t) >= T.TIERS.index(rec['tier'])]
    lowest = avail[0] if avail else ''
    if not lowest:
        advice = '%s is the tier the Mission asks for, and the %s offers none at or above it (see the verdicts).' % (T.label(rec['tier']), board)
    elif lowest == rec['tier']:
        advice = '%s is recommended and is available on the %s.' % (T.label(rec['tier']), board)
    else:
        advice = '%s is what the Mission asks for, but the %s does not offer it (%s). The lowest available tier that still meets the demand is %s.' % (
            T.label(rec['tier']), board, reps[rec['tier']]['why'], T.label(lowest))
    out = {'ok': True, 'mission': spec['mission'], 'board': board, 'board_basis': board_basis, 'source': spec['source'],
           'measured_on': sorted({p['board'] for p in spec['processors'] if p.get('build')}), 'demand': demand,
           'recommended': dict(rec, lowest_available=lowest, advice=advice), 'tiers': reps,
           'priorities': priorities(spec, lowest or rec['tier'], demand),
           'chosen': None,
           'notes': ['Advised, never forced: any tier can be chosen; the cost of each is in the tier table.',
                     'Nothing here is stored: it is worked out from the Purposes, the atoms and the board rows every time it is asked.']}
    if tier:
        if tier not in reps:
            raise KeyError('no tier %r (the tiers are %s)' % (tier, ', '.join(T.TIERS)))
        out['chosen'] = {'tier': tier, 'state': reps[tier]['state'], 'why': reps[tier]['why'], 'cost': reps[tier]['cost_of_choosing'],
                         'record': 'a person\'s chosen tier is recorded as a DerivedOverride (who, when, why) beside this derived recommendation; this read does not write it'}
    return out


# ------------------------------------------------------------------ flat rows for the page tables (plain words, no JSON)
def demand_rows(res):
    d, rows = res['demand'], []
    rows.append({'item': 'Independent triggers', 'value': A.text(d['independent_triggers']['count']), 'detail': '; '.join('%s: %s [%s, %s]' % (i['purpose'], i['what'] or i['kind'], i['shape'], i['importance']) for i in d['independent_triggers']['items'])})
    td = d['tightest_deadline']
    rows.append({'item': 'Tightest deadline', 'value': A.text(td['value']) if td else 'undetermined', 'detail': ('%s of %s' % (td['key'], td['purpose'])) if td else 'no Purpose states a deadline'})
    rows.append({'item': 'Periodic tasks', 'value': str(len(d['periodic'])), 'detail': '; '.join('%s every %s' % (p['task'], A.text(p['period_ms'])) for p in d['periodic']) or 'none'})
    rows.append({'item': 'Blocking operations', 'value': str(len(d['blocking'])), 'detail': '; '.join('%s: %s, up to %s' % (b['in_task'], b['what'], A.text(b['worst_us'])) for b in d['blocking']) or 'none'})
    for c in d['concurrency']:
        rows.append({'item': 'Concurrent responsibilities on %s' % c['processor'], 'value': '%s interrupt vectors, %s loop tasks' % (c['interrupt_vectors']['value'], c['loop_tasks']['value']),
                     'detail': 'init tasks %s, called tasks %s; peripheral drivers: %s' % (c['init_tasks']['value'], c['called']['value'], ', '.join(c['drivers']) or 'none beyond pins, timers and interrupts')})
    for r in d['data_rate']:
        rows.append({'item': 'Data rate (%s)' % r['task'], 'value': A.text(r['bytes_per_s']), 'detail': 'about %s of the serial line (%s)' % (A.text(r['share_of_line']), A.text(r['line_capacity']))})
    pp = d['pin_profiles']
    rows.append({'item': 'Pin needs (pp-0)', 'value': A.text(pp['profiles']), 'detail': '%s of them interrupt inputs' % A.text(pp['interrupt_inputs'])})
    for s in d['superloop']:
        w = s['worst']
        rows.append({'item': 'Main-loop pass on %s' % s['processor'], 'value': A.text(s['pass_known_us']), 'detail': '%s; interrupts take %s' % (s['pass_known_us']['basis'], A.text(s['isr_share']))})
        mg = s.get('measured_gap')
        if mg:
            rows.append({'item': 'Longest gap between polls, measured (%s)' % s['processor'], 'value': '%.2f ms (measured)' % (mg['worst_gap_cycles'] / 16000.0),
                         'detail': 'simavr twin, %s; at the chip\'s byte time %.2f ms (derived)' % (mg['ref'], (mg.get('worst_gap_chip_timed_cycles') or mg['worst_gap_cycles']) / 16000.0)})
        if w:
            rows.append({'item': 'Margin on the tightest budget', 'value': A.text(w['margin_us']), 'detail': '%s: budget %s; verdict %s%s' % (w['purpose'], A.text(w['budget_us']), s['verdict'],
                         ('; room for the unbounded parts (%s)' % ', '.join(u['task'] for u in s['unbounded'])) if s['unbounded'] else '')})
    rec = res['recommended']
    rows.append({'item': 'Recommended tier', 'value': rec['label'] + (' (provisional)' if rec['provisional'] else ''), 'detail': ' '.join(rec['reasons'] + rec['caveats'])})
    rows.append({'item': 'On %s' % res['board'], 'value': rec['lowest_available'] or 'none', 'detail': rec['advice']})
    return rows


def tier_rows(res):
    rows = []
    for t in T.TIERS:
        r = res['tiers'][t]
        ok = sum(v['ok'] for v in r['variants'])
        und = sum(v['undetermined'] for v in r['variants'])
        blk = sum(v['blocked'] for v in r['variants'])
        mem = {m['what']: m for m in r['memory']}
        rows.append({'tier': r['label'], 'verdict': r['state'] + (' (recommended)' if r['recommended'] else ''), 'why': r['why'],
                     'flash': '%s of %s' % (A.text(mem['flash']['application']), A.text(mem['flash']['limit'])),
                     'ram': '%s of %s' % (A.text(mem['static RAM']['application']), A.text(mem['static RAM']['limit'])),
                     'kernel': '%s flash, %s RAM' % (A.text(r['kernel']['flash']), A.text(r['kernel']['sram'])),
                     'variants': '%d eligible, %d undetermined, %d blocked (%d variants)' % (ok, und, blk, ok + und + blk),
                     'cost': r['cost_of_choosing']['text']})
    return rows


def priority_rows(res):
    p = res['priorities']
    return [{'priority': r['priority'], 'task': r['task'], 'deadline': A.text(r['deadline_ms']), 'importance': r['importance'], 'serves': r['serves'],
             'tie': 'tie (schedule order)' if r['tie'] else '', 'note': 'preview - the real plan: /display/task-plan'} for r in p['rows']]


# ------------------------------------------------------------------ the CLI
def _print(res):
    print('Approach for %s on %s (%s)' % (res['mission'], res['board'], res['board_basis']))
    print('Recommended: %s%s' % (res['recommended']['label'], '  [provisional]' if res['recommended']['provisional'] else ''))
    for r in res['recommended']['reasons']:
        print('  - ' + r)
    for c in res['recommended']['caveats']:
        print('  ! ' + c)
    print('On this board: %s' % res['recommended']['advice'])
    print('\nDemand')
    for r in demand_rows(res):
        print('  %-38s %s' % (r['item'], r['value']))
    print('\nTiers on %s' % res['board'])
    for r in tier_rows(res):
        print('  %-44s %s' % (r['tier'], r['verdict']))
        print('      %s' % r['why'])
        print('      flash %s | RAM %s | kernel %s' % (r['flash'], r['ram'], r['kernel']))
        print('      variants: %s' % r['variants'])
        print('      choosing it: %s' % r['cost'])
    p = res['priorities']
    print('\nDerived priorities (%s) - %s' % (p['tier'], p['preview']))
    print('  rule: %s' % p['rule'])
    for r in priority_rows(res):
        print('  %2d %-18s deadline %-22s importance %-10s %s' % (r['priority'], r['task'], r['deadline'], r['importance'], r['tie']))
    if p['tie_note']:
        print('  ' + p['tie_note'])
    if res['chosen']:
        print('\nIf you choose %s: %s - %s\n  %s' % (res['chosen']['tier'], res['chosen']['state'], res['chosen']['why'], res['chosen']['cost']['text']))


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='approach_profile', description='Pre-profile the runtime tier a Hardware Mission needs, checked against a board.')
    sub = ap.add_subparsers(dest='cmd')
    m = sub.add_parser('mission')
    m.add_argument('name')
    m.add_argument('--board', default='')
    m.add_argument('--tier', default='')
    m.add_argument('--json', action='store_true')
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.cmd != 'mission':
        ap.print_help()
        return 2
    try:
        res = approach_profile(a.name, board=a.board or None, tier=a.tier or None)
    except (ValueError, KeyError) as e:
        print('[REFUSED] %s' % (e.args[0] if e.args else e))
        return 3
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        _print(res)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
