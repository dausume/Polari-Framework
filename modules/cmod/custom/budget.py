"""
@module cmod.custom.budget

ipb-1 (INTERRUPT_POLL_BUDGET_PLAN.md §2b, §3): the polling + interrupt BUDGET, two columns per PROGRAM COUNTER (his ruling 2026-10-27: "two columns
of polls and interrupts per PC … two PCs, four columns"). A hart = one PC (RISC-V's word). Derived, never stored:

  hart_budgets_from_plan(plan, variant, knobs)  -> [HartBudget]  one per hart of every processor the Task Plan names; the plan's lanes become the
                                                   columns (loop -> polls, isr -> interrupts, init -> neither, called -> folded into its caller);
                                                   the numbers come from the cycle record of `variant` (board.custom.cycle_records, cyc-0) - -1 where none
  system_budget(plan, variant, knobs)           -> {harts[], columns (= 2 x harts), links[], tier, schedule_model, basis}
  bench_budget(bench, manager, knobs)           -> the same for the REAL boards on a Bench: a board with a Mission on a Hardware System gets its plan's
                                                   budget; any other board gets its hart facts and EMPTY columns ("no firmware assigned") - so the page
                                                   serves both planning (a Mission) and analysing what is on a bench (his ask).

Two columns ALWAYS (§2b): bare C has interrupts too; a column may be empty, never missing. `schedule_model` = superloop (bare C) | cyclic-executive (bare
C with a slot table - a knob, none today) | preemptive-rtos (FreeRTOS / Zephyr: tasks of context `task` are THREAD sub-rows of their hart).

Derived per hart (§3): scan_cycles = Σ cost_per_scan (cycles_max / poll_divider, unknown costs counted 0 and NAMED) + the loop's quiet-pass overhead
(the smallest measured poll-point gap); scan_ms at the hart's clock; polls_per_scan; scan_utilisation = scan_ms / scan_deadline_ms (knob; default =
the shortest wanted response / 2, said); isr_utilisation = Σ length_mean x expected_rate / clock over the rows where both are known; headroom =
1 - both; worst_latency_cycles stays -1 until the controller's entry latency is cited AND a masked window is measured (neither exists today: said).
The 2x check per poll: scan_ms <= wanted_response_ms / 2 -> ok | miss | unknown.

KNOBS (per process, in `_KNOBS`, NOT persisted - a restart forgets them; ipb-3 may move them to DerivedOverride rows): scan_deadline_ms, harts (for a
configurable machine), poll_divider {atom: n}, expected_rate_hz {vector: hz}, hart_of {task: hart index}.
"""
import json

from board.custom import cycle_records as CR
from board.custom import interrupt_controllers as IC

_KNOBS = {}   # (kind, name) -> knobs dict; per process

SCHEDULE_MODELS = ('superloop', 'cyclic-executive', 'preemptive-rtos')
TIER_MODEL = {'bare-c': 'superloop', 'freertos': 'preemptive-rtos', 'zephyr': 'preemptive-rtos'}


def knobs_for(kind, name):
    return _KNOBS.setdefault((kind, name), {})


def set_knobs(kind, name, body):
    k = knobs_for(kind, name)
    for key in ('scan_deadline_ms', 'harts'):
        if key in body:
            k[key] = float(body[key]) if key == 'scan_deadline_ms' else int(body[key])
    for key in ('poll_divider', 'expected_rate_hz', 'hart_of'):
        if isinstance(body.get(key), dict):
            k.setdefault(key, {}).update(body[key])
    return k


def _short(atom):
    """'uno:apps/light.sense_poll' -> 'apps/light.sense_poll' (the cycle record's key); 'uno:hal.INT0_vect' -> 'INT0_vect' is `_vector`."""
    return atom.split(':', 1)[1] if ':' in atom else atom


def _vector(atom):
    return atom.rsplit('.', 1)[-1]


def _stimulus_seconds(rec):
    argv = ((rec or {}).get('stimulus') or {}).get('argv') or []
    for i, a in enumerate(argv):
        if a == '--seconds' and i + 1 < len(argv):
            try:
                return float(argv[i + 1])
            except ValueError:
                return -1.0
    return -1.0


def _facts(proc):
    return IC.hart_facts(proc.get('soc', '')) or IC.facts_for_board(proc.get('board', '')) or {
        'processor': proc.get('soc') or proc.get('board', ''), 'title': 'unknown processor %r: not in the hart facts' % (proc.get('soc') or proc.get('board')), 'isa': 'unverified',
        'harts': 1, 'harts_note': 'assumed 1: no fact row', 'controller': '', 'clock_hz': -1, 'clock_citation': '', 'isa_open': 'unverified', 'core_rtl_open': 'unverified',
        'silicon_open': 'unverified', 'tooling_open': 'unverified', 'boards': [], 'notes': ''}


def _new_hart(proc, facts, h, tier, knobs):
    c = IC.controller(facts['controller']) or {}
    model = TIER_MODEL.get(tier, 'superloop')
    return {'hart': '%s#%d' % (proc['name'], h), 'hart_index': h, 'processor': proc['name'], 'board': proc.get('board', ''), 'soc': facts['processor'], 'title': facts['title'],
            'isa': facts['isa'], 'controller': facts['controller'], 'controller_title': c.get('title', ''), 'nesting': c.get('nesting', 'unverified'),
            'entry_latency_cycles': c.get('entry_latency_cycles', -1), 'clock_hz': facts['clock_hz'], 'clock_citation': facts['clock_citation'],
            'openness': IC.openness_words(facts), 'tier': tier, 'schedule_model': model, 'polls': [], 'interrupts': [], 'threads': [], 'init': [],
            'derived': {}, 'checks': [], 'notes': [], 'knobs': {'scan_deadline_ms': knobs.get('scan_deadline_ms', -1.0)}}


def hart_budgets_from_plan(plan, variant='', knobs=None):
    knobs = knobs or {}
    rec = CR.load(variant) if variant else None
    rec_basis = ('cycle record %s (sha %s, clock %s Hz, on the simavr twin)' % (variant, (rec or {}).get('record_sha256', '')[:12], (rec or {}).get('clock_hz'))
                 if rec else ('no cycle record for %r: every measured number is -1' % variant if variant else 'no cycle record named: every measured number is -1'))
    seconds = _stimulus_seconds(rec)
    tier = plan.get('tier', 'bare-c')
    out = []
    for proc in plan.get('processors', []):
        facts = _facts(proc)
        n = facts['harts'] if facts['harts'] > 0 else int(knobs.get('harts', 2))
        harts = [_new_hart(proc, facts, h, tier, knobs) for h in range(n)]
        if facts['harts'] <= 0:
            for hb in harts:
                hb['notes'].append('hart count is a knob (%d): %s' % (n, facts.get('harts_note', '')))
        for hb in harts:
            hb['notes'].append(rec_basis)
            if rec and rec.get('clock_hz') and hb['clock_hz'] > 0 and rec['clock_hz'] != hb['clock_hz']:
                hb['notes'].append('the cycle record\'s clock (%s) differs from the hart fact (%s): the record wins for ms' % (rec['clock_hz'], hb['clock_hz']))
        for t in plan.get('tasks', []):
            if t.get('processor') != proc['name']:
                continue
            h = int((knobs.get('hart_of') or {}).get(t['task'], 0))
            hb = harts[min(h, n - 1)]
            _place_task(hb, t, rec, seconds, knobs)
        for hb in harts:
            _derive(hb, rec)
        out.extend(harts)
    return out


def _place_task(hb, t, rec, seconds, knobs):
    trig = t.get('trigger') if isinstance(t.get('trigger'), dict) else {'kind': t.get('trigger', ''), 'how': '', 'what': '', 'route': ''}
    deadline = float(t.get('deadline_ms', -1) or -1)
    if t.get('context') == 'task':
        hb['threads'].append({'hart': hb['hart'], 'task': t['task'], 'period_ms': float(t.get('period_ms', -1) or -1), 'priority': t.get('priority', -1),
                              'deadline_ms': deadline, 'exec_cycles': -1, 'basis': 'a thread sub-row of its hart (no PC of its own); execution cycles not measured on an RTOS yet'})
    folded = 0
    for s in t.get('steps', []):
        lane, atom = s.get('lane', ''), s.get('atom', '')
        if lane == 'loop':
            dup = next((p for p in hb['polls'] if p['atom'] == atom), None)
            if dup is not None:   # the loop runs an atom ONCE per pass however many tasks it serves
                dup['task'] = '%s, %s' % (dup['task'], t['task'])
                dup['wanted_response_ms'] = min(x for x in (dup['wanted_response_ms'], deadline) if x > 0) if (dup['wanted_response_ms'] > 0 or deadline > 0) else -1.0
                continue
            fn = ((rec or {}).get('functions') or {}).get(_short(atom)) or {}
            div = int((knobs.get('poll_divider') or {}).get(atom, (knobs.get('poll_divider') or {}).get(_short(atom), 1)))
            cmax = fn.get('max', -1)
            hb['polls'].append({'hart': hb['hart'], 'task': t['task'], 'atom': atom, 'atom_short': _short(atom), 'trigger': trig.get('kind', ''), 'wanted_response_ms': deadline,
                                'poll_divider': div, 'cycles_min': fn.get('min', -1), 'cycles_max': cmax, 'calls_measured': fn.get('n', -1),
                                'cost_per_scan_cycles': (cmax / div) if cmax >= 0 and div > 0 else -1, 'masked_window_cycles': -1,
                                'basis': ('measured: %s' % ('function entry -> ret in the -fno-inline build' if fn else '')) if fn else 'not in the cycle record (inlined, or no record)'})
        elif lane == 'isr':
            vec = _vector(atom)
            ir = ((rec or {}).get('isrs') or {}).get(vec) or {}
            rate = -1.0
            basis = 'rate: unknown'
            if trig.get('kind') == 'period' and float(t.get('period_ms', -1) or -1) > 0:
                rate, basis = 1000.0 / float(t['period_ms']), 'rate: 1000 / the task period (%s ms)' % t['period_ms']
            if vec in (knobs.get('expected_rate_hz') or {}):
                rate, basis = float(knobs['expected_rate_hz'][vec]), 'rate: knob'
            elif rate < 0 and ir.get('n', -1) > 0 and seconds > 0:
                rate, basis = ir['n'] / seconds, 'rate: %d takes over the record\'s %.3g s stimulus (what the twin saw, not a spec)' % (ir['n'], seconds)
            mean = ir.get('mean', -1)
            util = (mean * rate / hb['clock_hz']) if mean >= 0 and rate >= 0 and hb['clock_hz'] > 0 else -1
            hb['interrupts'].append({'hart': hb['hart'], 'task': t['task'], 'atom': atom, 'vector': vec, 'source': trig.get('what', '') or trig.get('route', ''),
                                     'how': trig.get('how', ''), 'expected_rate_hz': rate, 'rate_basis': basis, 'priority_level': ir.get('vector', -1),
                                     'nests': hb['nesting'], 'length_min': ir.get('min', -1), 'length_max': ir.get('max', -1), 'length_mean': mean,
                                     'latency_max': ir.get('latency_max', -1), 'takes_measured': ir.get('n', -1), 'utilisation': util,
                                     'defers_to': t['task'] if hb['schedule_model'] == 'preemptive-rtos' else '',
                                     'basis': ir.get('basis', 'not in the cycle record')})
        elif lane == 'init':
            hb['init'].append({'hart': hb['hart'], 'task': t['task'], 'atom': atom})
        elif lane == 'called':
            folded += 1
    if folded:
        hb['notes'].append('%s: %d called step(s) folded into their callers\' measured cycles' % (t['task'], folded))


def _derive(hb, rec):
    polls, ints = hb['polls'], hb['interrupts']
    clock = (rec or {}).get('clock_hz') or hb['clock_hz']
    gaps = ((rec or {}).get('loop') or {}).get('gaps') or []
    overhead = min((g.get('min_cycles', -1) for g in gaps if g.get('min_cycles', -1) >= 0), default=-1)
    known = [p for p in polls if p['cost_per_scan_cycles'] >= 0]
    unknown = [p['atom_short'] for p in polls if p['cost_per_scan_cycles'] < 0]
    scan_cycles = sum(p['cost_per_scan_cycles'] for p in known) + (overhead if overhead >= 0 else 0)
    scan_ms = (scan_cycles / clock * 1000.0) if clock and clock > 0 and known else -1.0   # no known poll cost -> the scan is unknown, not 0
    wanted = [p['wanted_response_ms'] for p in polls if p['wanted_response_ms'] > 0]
    deadline = hb['knobs']['scan_deadline_ms']
    deadline_basis = 'knob'
    if deadline <= 0:
        deadline = (min(wanted) / 2.0) if wanted else -1.0
        deadline_basis = 'default: the shortest wanted response / 2' if wanted else 'none: no poll states a wanted response'
    scan_util = (scan_ms / deadline) if scan_ms >= 0 and deadline > 0 else -1.0
    util_known = [i['utilisation'] for i in ints if i['utilisation'] >= 0]
    isr_util = sum(util_known) if ints else 0.0
    headroom = (1.0 - scan_util - isr_util) if scan_util >= 0 else -1.0
    worst_gap = ((rec or {}).get('loop') or {}).get('worst_gap_cycles', -1)
    hb['derived'] = {'polls_per_scan': round(sum(1.0 / p['poll_divider'] for p in polls), 3), 'loop_overhead_cycles': overhead,
                     'scan_cycles': scan_cycles, 'scan_basis': 'bound: each poll\'s max cycles / divider, summed once per atom, + the quiet pass',
                     'measured_worst_gap_cycles': worst_gap, 'measured_worst_gap_ms': (worst_gap / clock * 1000.0) if worst_gap >= 0 and clock and clock > 0 else -1.0,
                     'scan_ms': scan_ms, 'unknown_poll_costs': ', '.join(unknown), 'scan_deadline_ms': deadline, 'scan_deadline_basis': deadline_basis,
                     'scan_utilisation': scan_util, 'isr_utilisation': isr_util, 'isr_rows_without_rate': len(ints) - len(util_known), 'headroom': headroom,
                     'worst_latency_cycles': -1, 'worst_latency_basis': 'unverified: the controller\'s entry latency is -1 (%s) and no masked window is measured yet' % (hb['controller'] or 'no controller row'),
                     'columns': 2, 'clock_hz': clock}
    for p in polls:
        if scan_ms < 0 or p['wanted_response_ms'] <= 0:
            verdict, why = 'unknown', 'scan time or wanted response unknown'
        elif scan_ms <= p['wanted_response_ms'] / 2.0:
            verdict, why = 'ok', 'scan %.3f ms <= %.1f ms / 2' % (scan_ms, p['wanted_response_ms'])
        else:
            verdict, why = 'miss', 'scan %.3f ms > %.1f ms / 2: scanned too slowly for its response' % (scan_ms, p['wanted_response_ms'])
        hb['checks'].append({'hart': hb['hart'], 'atom': p['atom_short'], 'task': p['task'], 'check': 'scanned at least twice as fast as it must answer', 'verdict': verdict, 'why': why})


def link_rows(plan, harts):
    """ipb-5 seed: every command / message trigger is a LINK into a hart - from the host (Polari over the UART) or from another hart. One row per link."""
    by_proc = {}
    for hb in harts:
        by_proc.setdefault(hb['processor'], hb)
    out = []
    for t in plan.get('tasks', []):
        trig = t.get('trigger') if isinstance(t.get('trigger'), dict) else {'kind': t.get('trigger', '')}
        if trig.get('kind') not in ('command', 'message'):
            continue
        hb = by_proc.get(t.get('processor'))
        if hb is None:
            continue
        isr = next((i for i in hb['interrupts'] if i['task'] == t['task']), None)
        route = trig.get('route', '') or next((r['route'] for r in t.get('routes', []) if r.get('job') == 'receive-command'), '')
        out.append({'from': 'host (Polari)' if trig['kind'] == 'command' else 'another hart', 'to_hart': hb['hart'], 'task': t['task'], 'transport': 'uart' if 'uart' in route else route or 'unverified',
                    'route': route, 'baud': -1, 'frame_bytes': -1, 'transit_ms': -1, 'receiving_interrupt': isr['vector'] if isr else '', 'defers_to': (isr or {}).get('defers_to', ''),
                    'chain': '%s -> link -> %s -> %s' % ('host' if trig['kind'] == 'command' else 'hart', (isr or {}).get('vector', 'poll'), t['task']),
                    'basis': 'baud / frame / transit: -1 until the variant\'s UART knobs are read into the link (ipb-5)'})
    return out


def system_budget(plan, variant='', knobs=None):
    harts = hart_budgets_from_plan(plan, variant, knobs)
    return {'ok': True, 'mission': plan.get('mission', ''), 'hardware_system': plan.get('hardware_system', ''), 'plan': plan.get('name', ''), 'tier': plan.get('tier', ''),
            'schedule_model': harts[0]['schedule_model'] if harts else '', 'harts': harts, 'columns': 2 * len(harts), 'links': link_rows(plan, harts), 'variant': variant,
            'basis': 'derived now from the Task Plan (%s) + the cycle record; nothing stored' % plan.get('run_basis', '')}


# ---------------------------------------------------------------------------------------------------- the bench use
def _mission_for_board(board, manager=None):
    """(mission name, system name) for a board that a seeded / live Mission runs on, else ('', '')."""
    from cmod.custom import mission_seeds as M
    from cmod.custom import task_plan as TP
    for m in M.MISSION_SEEDS:
        parts = m.get('participants') or json.loads(m.get('participants_json') or '[]')
        if any(p.get('role') == 'board' and p.get('ref') == board for p in parts):
            try:
                return m['name'], TP.default_system(board, manager)
            except Exception:  # noqa: BLE001
                return m['name'], ''
    return '', ''


def _plan_for(mission, system, manager=None):
    from cmod.custom import solve_doors as SD
    from cmod.custom import task_plan as TP
    run = SD.compute(mission, None, None, None, {}, manager)
    return TP.derive_task_plan(mission, system or None, solve_run=run, manager=manager, apply_edits=True)


def default_variant(mission):
    v = mission.replace('-mission', '')
    return v if CR.load(v) else ''


def bench_budget(bench_name, manager=None, knobs=None, plan_for=None):
    """The budget of the REAL boards on a bench. `plan_for(mission, system)` is injectable (selftests)."""
    from board.custom import bench as B
    b = B.bench(bench_name, manager)
    if b is None:
        return None
    plan_for = plan_for or (lambda m, s: _plan_for(m, s, manager))
    harts, links, boards = [], [], []
    for row in B.board_rows(b, manager):
        facts = IC.facts_for_board(row['board'])
        mission, system = _mission_for_board(row['board'], manager)
        entry = {'bench': bench_name, 'board': row['board'], 'label': row['label'], 'testing': row['testing'], 'mission': mission, 'system': system,
                 'processor': facts['processor'] if facts else '', 'harts': facts['harts'] if facts else -1, 'openness': IC.openness_words(facts) if facts else 'unverified: no hart facts',
                 'state': ''}
        if facts is None:
            entry['state'] = 'no hart facts for this board: add a row in board.custom.interrupt_controllers'
            boards.append(entry)
            continue
        if mission:
            plan = plan_for(mission, system)
            sb = system_budget(plan, default_variant(mission), knobs)
            for hb in sb['harts']:
                hb['bench'], hb['label'] = bench_name, row['label']
            harts.extend(sb['harts'])
            links.extend(sb['links'])
            entry['state'] = 'budget from the Mission %s on %s (%d hart(s), %d columns)' % (mission, system, len(sb['harts']), sb['columns'])
        else:
            proc = {'name': '%s:%s' % (row['board'], facts['processor']), 'board': row['board'], 'soc': facts['processor'], 'role': 'the board'}
            n = facts['harts'] if facts['harts'] > 0 else int((knobs or {}).get('harts', 2))
            for h in range(n):
                hb = _new_hart(proc, facts, h, 'bare-c', knobs or {})
                hb['bench'], hb['label'] = bench_name, row['label']
                hb['notes'].append('no firmware assigned on this bench: the columns are empty, the facts stand; %s' % row['testing'])
                _derive(hb, None)
                harts.append(hb)
            entry['state'] = 'no Mission runs on this board: facts only, empty columns (%d hart(s))' % n
        boards.append(entry)
    return {'ok': True, 'bench': bench_name, 'boards': boards, 'harts': harts, 'columns': 2 * len(harts), 'links': links,
            'basis': 'the bench\'s boards -> hart facts; a board with a Mission gets that Mission\'s Task Plan budget; nothing stored'}


# ---------------------------------------------------------------------------------------------------- flat rows for the tables
def _f(x):
    return ('%.4g' % x) if isinstance(x, float) else x


def hart_rows(sb):
    return [{k: _f(v) for k, v in dict({kk: hb[kk] for kk in ('hart', 'board', 'soc', 'title', 'isa', 'controller', 'nesting', 'clock_hz', 'openness', 'tier', 'schedule_model')},
                                        polls=len(hb['polls']), interrupts=len(hb['interrupts']), threads=len(hb['threads']), headroom=hb['derived'].get('headroom', -1),
                                        label=hb.get('label', ''), notes='; '.join(hb['notes'])).items()} for hb in sb['harts']]


def poll_rows(sb):
    return [{k: _f(v) for k, v in p.items()} for hb in sb['harts'] for p in hb['polls']]


def interrupt_rows(sb):
    return [{k: _f(v) for k, v in i.items()} for hb in sb['harts'] for i in hb['interrupts']]


def thread_rows(sb):
    return [{k: _f(v) for k, v in t.items()} for hb in sb['harts'] for t in hb['threads']]


def derived_rows(sb):
    return [dict({'hart': hb['hart'], 'label': hb.get('label', '')}, **{k: _f(v) for k, v in hb['derived'].items()}) for hb in sb['harts']]


def check_rows(sb):
    return [c for hb in sb['harts'] for c in hb['checks']]


def board_rows(sb):
    return [{k: _f(v) for k, v in e.items()} for e in sb.get('boards', [])]


VIEWS = {'harts': hart_rows, 'polls': poll_rows, 'interrupts': interrupt_rows, 'threads': thread_rows, 'derived': derived_rows, 'checks': check_rows,
         'links': lambda sb: sb['links'], 'boards': board_rows}
