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
1 - both; worst_latency_cycles (ipb-7) = the controller's cited entry latency + the longest MASKED WINDOW the twin measured in main-line code (cycle record `masked`,
the --masked-windows run: cli -> the instruction that set I again, outside ISRs) + the longest handler when handlers do not nest; -1 names what is missing. Per poll,
masked_window_cycles = the longest window inside the task's loop + called atoms (the callee's ATOMIC_BLOCK is the poll's to pay).
The 2x check per poll: scan_ms <= wanted_response_ms / 2 -> ok | miss | unknown.

KNOBS (per process, in `_KNOBS`, NOT persisted - a restart forgets them; ipb-3 may move them to DerivedOverride rows): scan_deadline_ms, harts (for a
configurable machine), poll_divider {atom: n}, expected_rate_hz {vector: hz}, hart_of {task: hart index}, isr_hart_of {vector: hart index} (ipb-6: an
interrupt routed to a different hart than its task - the interrupt-matrix case), lockstep (ipb-6: true forces every hart of a chip to MIRROR hart 0).

ipb-6 (§2c, his ask 2026-10-27): the WORST-CASE POLL CYCLE = "hit the hart with every possible interrupt and poll and complete all of them": every poll
once at its max cycles (dividers ignored), every interrupt once at its max length + the controller's entry latency, plus the loop's quiet pass. That number
is the hart's standard **PollCycle** (derived.poll_cycle_cycles / _ms); a part that is -1 makes the whole -1 and NAMES what is missing (poll_cycle_missing).
Beside it the rate-aware bound poll_cycle_inflated_cycles = (polls + overhead) / (1 - isr_utilisation): what the cycle stretches to when interrupts fire at
their expected rates instead of once. Per hart the check "one PollCycle fits the shortest wanted response / 2".
Harts of one chip are assignable separately (hart_of / isr_hart_of) unless the chip's parallelism facts say LOCKSTEP (board.custom.parallelism) or the
knob says so: then hart 0 holds the stream and the others are mirrors (mirror_of) with the same columns, not assignable.

ipb-8 (§2d, his ask 2026-10-28 "affinity for hart-name ... null-affinity tasks ... may go to any of the chips"): every task row carries `affinity`
(the hart it is pinned to, by its hart name | `any` = null affinity, the scheduler places it | `mirror` on a lockstep mirror) and `affinity_reason`, a WORD
from AFFINITY_REASONS (D-ipb-10 recommended five): owns-interrupt <vector> · polls-peripheral <name> · latency · isolation · by-default (nobody chose).
Sources, first wins: the knobs `affinity {task: any | hart index | '<processor>#n'}` + `affinity_reason {task: word}` -> the task row's own fields -> `hart_of`
-> hart 0 by-default; with no reason word, a pinned task whose interrupt `isr_hart_of` routes to the same hart reads owns-interrupt <vector>. `any` is legal
only on an `smp` chip (parallelism.multicore_model): there it is BOOKED ON EVERY HART (each hart's PollCycle carries it: the worst case) and the best split
(each null-affinity task given to the least-loaded hart, greedy by cost) is the optimistic column `poll_cycle_best_split_cycles`; on any other chip it is
REFUSED by name (a check row, placed on hart 0). Tier `freertos-smp` (parallelism.SCHEDULER_TIERS) schedules preemptively like freertos.
"""
import json
import re

from board.custom import cycle_records as CR
from board.custom import interrupt_controllers as IC
from board.custom import parallelism as PX

_KNOBS = {}   # (kind, name) -> knobs dict; per process

SCHEDULE_MODELS = ('superloop', 'cyclic-executive', 'preemptive-rtos')
TIER_MODEL = {'bare-c': 'superloop', 'freertos': 'preemptive-rtos', 'freertos-smp': 'preemptive-rtos', 'zephyr': 'preemptive-rtos'}
AFFINITY_REASONS = ('owns-interrupt', 'polls-peripheral', 'latency', 'isolation', 'by-default')
_REASON_ARG = ('owns-interrupt', 'polls-peripheral')   # these two name their evidence: the vector / the peripheral
_HART_WORD = re.compile(r'^(?:.*#|hart)?(\d+)$')


def knobs_for(kind, name):
    return _KNOBS.setdefault((kind, name), {})


def set_knobs(kind, name, body):
    k = knobs_for(kind, name)
    for key in ('scan_deadline_ms', 'harts'):
        if key in body:
            k[key] = float(body[key]) if key == 'scan_deadline_ms' else int(body[key])
    if 'lockstep' in body:
        k['lockstep'] = str(body['lockstep']).lower() in ('1', 'true', 'yes', 'on')
    for task, v in (body.get('affinity') or {}).items() if isinstance(body.get('affinity'), dict) else ():
        bad = affinity_problem(v)
        if bad:
            raise ValueError('affinity[%s]: %s' % (task, bad))
    for task, v in (body.get('affinity_reason') or {}).items() if isinstance(body.get('affinity_reason'), dict) else ():
        bad = reason_problem(v)
        if bad:
            raise ValueError('affinity_reason[%s]: %s' % (task, bad))
    for key in ('poll_divider', 'expected_rate_hz', 'hart_of', 'isr_hart_of', 'affinity', 'affinity_reason'):
        if isinstance(body.get(key), dict):
            k.setdefault(key, {}).update(body[key])
    return k


def affinity_problem(v):
    """ipb-8: '' when `v` is a settable affinity (any | a hart index | '<processor>#n' | 'hart<n>'), else why not."""
    v = str(v).strip()
    if v == 'any' or _HART_WORD.match(v):
        return ''
    if v == 'mirror':
        return 'mirror is not set: it is what a lockstep chip makes of its other harts (knob lockstep)'
    return 'affinity is any, a hart index, or a hart name ending #<n> (got %r)' % v


def reason_problem(v):
    """ipb-8: '' when `v` is a reason word from AFFINITY_REASONS (owns-interrupt / polls-peripheral name their evidence), else why not."""
    parts = str(v).split()
    if not parts or parts[0] not in AFFINITY_REASONS:
        return 'the reason is one of %s (got %r)' % (', '.join(AFFINITY_REASONS), v)
    if parts[0] in _REASON_ARG and len(parts) != 2:
        return '%s names its %s: "%s <%s>"' % (parts[0], 'vector' if parts[0] == 'owns-interrupt' else 'peripheral', parts[0], 'vector' if parts[0] == 'owns-interrupt' else 'name')
    if parts[0] not in _REASON_ARG and len(parts) != 1:
        return '%s takes no argument' % parts[0]
    return ''


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
    px = PX.facts_for(facts['processor'])
    return {'hart': '%s#%d' % (proc['name'], h), 'hart_index': h, 'processor': proc['name'], 'board': proc.get('board', ''), 'soc': facts['processor'], 'title': facts['title'],
            'isa': facts['isa'], 'controller': facts['controller'], 'controller_title': c.get('title', ''), 'nesting': c.get('nesting', 'unverified'),
            'entry_latency_cycles': c.get('entry_latency_cycles', -1), 'clock_hz': facts['clock_hz'], 'clock_citation': facts['clock_citation'],
            'openness': IC.openness_words(facts), 'tier': tier, 'schedule_model': model, 'parallelism': PX.words(px), 'lockstep': px['lockstep'], 'mirror_of': '',
            'multicore_model': px['multicore_model'], 'amp_with': px['amp_with'],
            'polls': [], 'interrupts': [], 'threads': [], 'init': [],
            'derived': {}, 'checks': [], 'notes': [], 'knobs': {'scan_deadline_ms': knobs.get('scan_deadline_ms', -1.0)}}


def _mirror(hb, src):
    """ipb-6 lockstep: `hb` executes the same instruction stream as `src` - its columns are a copy, its derived block the same, and it says so."""
    hb['mirror_of'] = src['hart']
    why = 'lockstep: mirror of %s' % src['hart']
    hb['polls'] = [dict(p, hart=hb['hart'], affinity='mirror', affinity_reason=why, basis='mirror of %s (lockstep): %s' % (src['hart'], p['basis'])) for p in src['polls']]
    hb['interrupts'] = [dict(i, hart=hb['hart'], affinity='mirror', affinity_reason=why, basis='mirror of %s (lockstep): %s' % (src['hart'], i['basis'])) for i in src['interrupts']]
    hb['threads'] = [dict(t, hart=hb['hart'], affinity='mirror', affinity_reason=why) for t in src['threads']]
    hb['init'] = [dict(x, hart=hb['hart']) for x in src['init']]
    hb['notes'].append('LOCKSTEP: this hart runs the same instruction stream as %s and compares results; nothing is assignable to it separately (hart_of / isr_hart_of ignored)' % src['hart'])


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
        lockstep = bool(knobs.get('lockstep')) or PX.is_lockstep(PX.facts_for(facts['processor']))
        if facts['harts'] <= 0:
            for hb in harts:
                hb['notes'].append('hart count is a knob (%d): %s' % (n, facts.get('harts_note', '')))
        for hb in harts:
            hb['notes'].append(rec_basis)
            if lockstep:
                hb['lockstep'] = 'yes (knob)' if knobs.get('lockstep') else hb['lockstep']
            if rec and rec.get('clock_hz') and hb['clock_hz'] > 0 and rec['clock_hz'] != hb['clock_hz']:
                hb['notes'].append('the cycle record\'s clock (%s) differs from the hart fact (%s): the record wins for ms' % (rec['clock_hz'], hb['clock_hz']))
        px = PX.facts_for(facts['processor'])
        for t in plan.get('tasks', []):
            if t.get('processor') != proc['name']:
                continue
            aff = _affinity(t, knobs, harts, px, lockstep)
            if aff['refusal']:
                harts[0]['checks'].append({'hart': harts[0]['hart'], 'atom': '', 'task': t['task'], 'check': 'null affinity needs an smp chip', 'verdict': 'refused', 'why': aff['refusal']})
            for hb in ([harts[i] for i in range(n)] if aff['affinity'] == 'any' else [harts[min(aff['hart'], n - 1)]]):
                _place_task(hb, t, rec, seconds, knobs, harts if not lockstep else None, aff)
        if lockstep:
            for hb in harts[1:]:
                _mirror(hb, harts[0])
        for hb in harts:
            _derive(hb, rec)
        _best_split(harts)
        out.extend(harts)
    return out


def _affinity(t, knobs, harts, px, lockstep):
    """ipb-8: {affinity, hart, reason, basis, refusal} for one task on one chip - see the module docstring for the order of sources."""
    task, n = t['task'], len(harts)
    want = (knobs.get('affinity') or {}).get(task, t.get('affinity'))
    src = 'knob affinity' if task in (knobs.get('affinity') or {}) else ('the task row' if t.get('affinity') not in (None, '') else '')
    reason = (knobs.get('affinity_reason') or {}).get(task) or t.get('affinity_reason') or ''
    if lockstep:
        return {'affinity': harts[0]['hart'], 'hart': 0, 'reason': reason or 'by-default', 'refusal': '',
                'basis': 'lockstep: one assignable stream on %s%s' % (harts[0]['hart'], ' (%s %r ignored)' % (src, want) if src else '')}
    if want in (None, '') and task in (knobs.get('hart_of') or {}):
        want, src = (knobs.get('hart_of') or {})[task], 'knob hart_of'
    if str(want).strip() == 'any':
        if PX.is_smp(px):
            return {'affinity': 'any', 'hart': -1, 'reason': reason, 'refusal': '',
                    'basis': 'null affinity (%s): %s is %s - booked on every hart (worst case); the best split is the optimistic column' % (src, px['processor'], px['multicore_model'])}
        refusal = ('task %s asks for any hart (null affinity), but %s is %s, not smp: only one kernel over identical harts may place it freely - placed on %s; '
                   'pin it (affinity <hart>) or use an smp chip' % (task, px['processor'], px['multicore_model'], harts[0]['hart']))
        return {'affinity': harts[0]['hart'], 'hart': 0, 'reason': reason or 'by-default', 'refusal': refusal, 'basis': 'refused: ' + refusal}
    m = _HART_WORD.match(str(want).strip()) if want not in (None, '') else None
    if m is None:
        return {'affinity': harts[0]['hart'], 'hart': 0, 'reason': reason or 'by-default', 'refusal': '', 'basis': 'nobody chose: hart 0'}
    h = min(int(m.group(1)), n - 1)
    if not reason:
        vecs = [_vector(s.get('atom', '')) for s in t.get('steps', []) if s.get('lane') == 'isr']
        owned = [v for v in vecs if str((knobs.get('isr_hart_of') or {}).get(v, h)) == str(h)] if vecs else []
        reason = ('owns-interrupt %s' % owned[0]) if owned else ''
    return {'affinity': harts[h]['hart'], 'hart': h, 'reason': reason, 'refusal': '',
            'basis': 'pinned by %s%s' % (src, '' if reason else '; no reason word given (set affinity_reason)')}


def _best_split(harts):
    """ipb-8: the optimistic column - the hart's PollCycle when each null-affinity task lands on ONE hart (greedy: costliest first, to the least-loaded hart)
    instead of being booked on all of them. -1 when the PollCycle is -1 or a null-affinity row's cost is unknown; equal to the PollCycle when nothing is `any`."""
    def cost(hb, task):
        rows = [p['cycles_max'] for p in hb['polls'] if p.get('affinity_task') == task] + \
               [i['length_max'] + max(hb['entry_latency_cycles'], 0) if i['length_max'] >= 0 else -1 for i in hb['interrupts'] if i.get('affinity_task') == task]
        return -1 if any(r < 0 for r in rows) else sum(rows)
    anys = sorted({r['affinity_task'] for hb in harts for r in hb['polls'] + hb['interrupts'] if r.get('affinity') == 'any'})
    if not anys:
        for hb in harts:
            hb['derived']['poll_cycle_best_split_cycles'] = hb['derived']['poll_cycle_cycles']
            hb['derived']['poll_cycle_best_split_basis'] = 'no null-affinity task: the same as the PollCycle'
            hb['derived']['any_tasks'] = ''
        return
    per = {a: [cost(hb, a) for hb in harts] for a in anys}
    costs = {a: (-1 if any(c < 0 for c in per[a]) else max(per[a])) for a in anys}
    base = [hb['derived']['poll_cycle_cycles'] - sum(max(cost(hb, a), 0) for a in anys) if hb['derived']['poll_cycle_cycles'] >= 0 else -1 for hb in harts]
    unknown = [a for a in anys if costs[a] < 0]
    load, split = list(base), {}
    ok = not unknown and all(b >= 0 for b in base)   # the split needs every hart's pinned load: one unknown hart = no split anywhere
    if ok:
        for a in sorted(anys, key=lambda x: -costs[x]):
            i = min(range(len(harts)), key=lambda j: load[j])
            load[i] += costs[a]
            split[a] = harts[i]['hart']
    blocked = [hb['hart'] for i, hb in enumerate(harts) if base[i] < 0]
    for i, hb in enumerate(harts):
        hb['any_split'] = dict(split)
        hb['derived']['poll_cycle_best_split_cycles'] = load[i] if ok else -1
        hb['derived']['poll_cycle_best_split_basis'] = (
            'best split: null-affinity task(s) %s each on ONE hart (greedy, costliest first): %s' % (', '.join(anys), ', '.join('%s -> %s' % kv for kv in sorted(split.items()))) if ok else
            'unknown: %s' % ('the cost of %s' % ', '.join(unknown) if unknown else 'the PollCycle of %s is -1' % ', '.join(blocked)))
        hb['derived']['any_tasks'] = ', '.join(anys)


def _masked_for(rec, atoms):
    """ipb-7: (cycles, basis) - the longest masked window the twin measured INSIDE these atoms' functions (a task's loop + called steps: the window sits in the
    callee - hal_millis's ATOMIC_BLOCK - and the poll pays it); 0 = measured, none inside; -1 = no masked block in the record (an older record or image)."""
    mk = (rec or {}).get('masked') or {}
    if mk.get('n', -1) < 0:
        return -1, 'not measured: no masked-windows block in the cycle record (%s)' % (mk.get('basis') or 'no record')
    fns = {(((rec or {}).get('functions') or {}).get(_short(a)) or {}).get('function') or _short(a).rsplit('.', 1)[-1] for a in atoms}
    hits = [s for s in mk.get('sites', []) if s.get('function') in fns]
    if not hits:
        return 0, 'measured: no cli inside %s (the record\'s masked windows sit elsewhere)' % ', '.join(sorted(fns))
    top = max(hits, key=lambda s: s['max'])
    return top['max'], 'measured: cli at %s in %s, %d cycles max over %d windows (shipped hex, --masked-windows)' % (top['pc'], top['function'], top['max'], top['n'])


def _place_task(hb, t, rec, seconds, knobs, harts=None, aff=None):
    aff = aff or {'affinity': hb['hart'], 'reason': 'by-default', 'basis': 'nobody chose'}
    tag = {'affinity': aff['affinity'], 'affinity_reason': aff['reason'], 'affinity_basis': aff['basis'], 'affinity_task': t['task']}
    trig = t.get('trigger') if isinstance(t.get('trigger'), dict) else {'kind': t.get('trigger', ''), 'how': '', 'what': '', 'route': ''}
    deadline = float(t.get('deadline_ms', -1) or -1)
    masked, masked_basis = _masked_for(rec, [s.get('atom', '') for s in t.get('steps', []) if s.get('lane') in ('loop', 'called')])
    if t.get('context') == 'task':
        hb['threads'].append({'hart': hb['hart'], 'task': t['task'], 'period_ms': float(t.get('period_ms', -1) or -1), 'priority': t.get('priority', -1),
                              'deadline_ms': deadline, 'exec_cycles': -1, 'basis': 'a thread sub-row of its hart (no PC of its own); execution cycles not measured on an RTOS yet',
                              'affinity': aff['affinity'], 'affinity_reason': aff['reason']})
    folded = 0
    for s in t.get('steps', []):
        lane, atom = s.get('lane', ''), s.get('atom', '')
        if lane == 'loop':
            dup = next((p for p in hb['polls'] if p['atom'] == atom), None)
            if dup is not None:   # the loop runs an atom ONCE per pass however many tasks it serves
                dup['task'] = '%s, %s' % (dup['task'], t['task'])
                dup['wanted_response_ms'] = min(x for x in (dup['wanted_response_ms'], deadline) if x > 0) if (dup['wanted_response_ms'] > 0 or deadline > 0) else -1.0
                if masked > dup['masked_window_cycles']:
                    dup['masked_window_cycles'], dup['masked_window_basis'] = masked, masked_basis
                continue
            fn = ((rec or {}).get('functions') or {}).get(_short(atom)) or {}
            div = int((knobs.get('poll_divider') or {}).get(atom, (knobs.get('poll_divider') or {}).get(_short(atom), 1)))
            cmax = fn.get('max', -1)
            hb['polls'].append({'hart': hb['hart'], 'task': t['task'], 'atom': atom, 'atom_short': _short(atom), 'trigger': trig.get('kind', ''), 'wanted_response_ms': deadline,
                                'poll_divider': div, 'cycles_min': fn.get('min', -1), 'cycles_max': cmax, 'calls_measured': fn.get('n', -1),
                                'cost_per_scan_cycles': (cmax / div) if cmax >= 0 and div > 0 else -1, 'masked_window_cycles': masked, 'masked_window_basis': masked_basis,
                                'basis': ('measured: %s' % ('function entry -> ret in the -fno-inline build' if fn else '')) if fn else 'not in the cycle record (inlined, or no record)', **tag})
        elif lane == 'isr':
            vec = _vector(atom)
            target = hb
            routed = (knobs.get('isr_hart_of') or {}).get(vec)
            if routed is not None and harts:
                target = harts[min(int(routed), len(harts) - 1)]
                if any(i['vector'] == vec and i['task'] == t['task'] for i in target['interrupts']):
                    continue   # a null-affinity task booked on every hart: its routed interrupt lands once
                if target is not hb:
                    target['notes'].append('%s routed to this hart by isr_hart_of (knob) while its task %s runs on %s: the deferred work crosses harts' % (vec, t['task'], hb['hart']))
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
            util = (mean * rate / target['clock_hz']) if mean >= 0 and rate >= 0 and target['clock_hz'] > 0 else -1
            target['interrupts'].append({'hart': target['hart'], 'task': t['task'], 'atom': atom, 'vector': vec, 'source': trig.get('what', '') or trig.get('route', ''),
                                         'how': trig.get('how', ''), 'expected_rate_hz': rate, 'rate_basis': basis, 'priority_level': ir.get('vector', -1),
                                         'nests': target['nesting'], 'length_min': ir.get('min', -1), 'length_max': ir.get('max', -1), 'length_mean': mean,
                                         'latency_max': ir.get('latency_max', -1), 'takes_measured': ir.get('n', -1), 'utilisation': util,
                                         'defers_to': t['task'] if hb['schedule_model'] == 'preemptive-rtos' else '',
                                         'basis': ir.get('basis', 'not in the cycle record'), **tag})
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
    # ipb-6: the WORST-CASE POLL CYCLE - every poll once at max (dividers ignored), every interrupt once at max length + entry latency, + the quiet pass
    missing = ['poll %s cycles_max' % p['atom_short'] for p in polls if p['cycles_max'] < 0]
    missing += ['interrupt %s length_max' % i['vector'] for i in ints if i['length_max'] < 0]
    if ints and hb['entry_latency_cycles'] < 0:
        missing.append('entry latency of %s' % (hb['controller'] or 'the controller'))
    if polls and overhead < 0:
        missing.append('the loop\'s quiet-pass overhead (no poll-point gaps in the record)')
    entry = max(hb['entry_latency_cycles'], 0)
    pc_polls = sum(p['cycles_max'] for p in polls if p['cycles_max'] >= 0) + max(overhead, 0)
    pc_ints = sum(i['length_max'] + entry for i in ints if i['length_max'] >= 0)
    poll_cycle = (pc_polls + pc_ints) if not missing and (polls or ints) else -1
    poll_cycle_ms = (poll_cycle / clock * 1000.0) if poll_cycle >= 0 and clock and clock > 0 else -1.0
    inflated = (pc_polls / (1.0 - isr_util)) if poll_cycle >= 0 and len(util_known) == len(ints) and isr_util < 1.0 else -1
    wanted_all = [p['wanted_response_ms'] for p in polls if p['wanted_response_ms'] > 0]
    if poll_cycle_ms < 0 or not wanted_all:
        pc_verdict, pc_why = 'unknown', ('missing: %s' % '; '.join(missing)) if missing else ('no wanted response on any poll' if not wanted_all else 'no clock')
    elif poll_cycle_ms <= min(wanted_all) / 2.0:
        pc_verdict, pc_why = 'ok', 'one PollCycle %.4g ms <= the shortest wanted response %.4g ms / 2' % (poll_cycle_ms, min(wanted_all))
    else:
        pc_verdict, pc_why = 'miss', 'one PollCycle %.4g ms > the shortest wanted response %.4g ms / 2: even the worst case must fit twice' % (poll_cycle_ms, min(wanted_all))
    # ipb-7: the WORST LATENCY an interrupt can see = the controller's entry latency + the longest masked window in main-line code (measured by the twin) + the
    # longest handler when handlers do not nest (AVR: I cleared on entry, 'software' nesting = only if a handler sets it again - the UNO's do not); hardware nesting adds nothing
    mk = (rec or {}).get('masked') or {}
    masked_max = mk.get('max', -1) if mk.get('n', -1) >= 0 else -1
    masked_where = ('%s at %s' % (mk.get('max_function') or '?', mk.get('max_pc') or '?')) if masked_max > 0 else ('none measured' if masked_max == 0 else 'not measured')
    longest_isr = max((i['length_max'] for i in ints if i['length_max'] >= 0), default=-1)
    blocking = (longest_isr if hb['nesting'] != 'hardware' and ints else 0)
    lat_missing = []
    if hb['entry_latency_cycles'] < 0:
        lat_missing.append('the entry latency of %s' % (hb['controller'] or 'the controller'))
    if masked_max < 0:
        lat_missing.append('a measured masked window (cli..sei / MIE cleared)')
    if ints and longest_isr < 0:
        lat_missing.append('a measured handler length')
    if lat_missing:
        worst_latency, worst_basis = -1, 'unverified: needs ' + ' and '.join(lat_missing)
    else:
        worst_latency = hb['entry_latency_cycles'] + masked_max + blocking
        worst_basis = ('entry latency %d (cited) + the longest masked window %d (%s) + the longest handler %d (%s nesting: a running handler blocks the next)' % (
            hb['entry_latency_cycles'], masked_max, masked_where, blocking, hb['nesting']) if blocking else
            'entry latency %d (cited) + the longest masked window %d (%s)%s' % (hb['entry_latency_cycles'], masked_max, masked_where,
                                                                               '; hardware nesting: a higher priority preempts, no handler term' if ints else '; no interrupt rows'))
    hb['derived'] = {'polls_per_scan': round(sum(1.0 / p['poll_divider'] for p in polls), 3), 'loop_overhead_cycles': overhead,
                     'poll_cycle_cycles': poll_cycle, 'poll_cycle_ms': poll_cycle_ms, 'poll_cycle_missing': '; '.join(missing),
                     'poll_cycle_basis': 'the hart\'s standard PollCycle = every poll once at cycles_max (dividers ignored: %d polls) + every interrupt once at length_max + entry latency %s '
                                         '(%d interrupts) + the quiet pass; -1 names what is missing' % (len(polls), hb['entry_latency_cycles'] if hb['entry_latency_cycles'] >= 0 else '-1', len(ints)),
                     'poll_cycle_inflated_cycles': inflated,
                     'poll_cycle_inflated_basis': 'polls / (1 - isr_utilisation): the cycle when interrupts fire at their expected rates instead of once' if inflated >= 0 else
                                                  'needs every interrupt\'s rate and the PollCycle known',
                     'poll_cycle_verdict': pc_verdict, 'poll_cycle_why': pc_why,
                     'scan_cycles': scan_cycles, 'scan_basis': 'bound: each poll\'s max cycles / divider, summed once per atom, + the quiet pass',
                     'measured_worst_gap_cycles': worst_gap, 'measured_worst_gap_ms': (worst_gap / clock * 1000.0) if worst_gap >= 0 and clock and clock > 0 else -1.0,
                     'scan_ms': scan_ms, 'unknown_poll_costs': ', '.join(unknown), 'scan_deadline_ms': deadline, 'scan_deadline_basis': deadline_basis,
                     'scan_utilisation': scan_util, 'isr_utilisation': isr_util, 'isr_rows_without_rate': len(ints) - len(util_known), 'headroom': headroom,
                     'masked_window_max_cycles': masked_max, 'masked_window_where': masked_where,
                     'worst_latency_cycles': worst_latency, 'worst_latency_us': (worst_latency / clock * 1e6) if worst_latency >= 0 and clock and clock > 0 else -1.0,
                     'worst_latency_basis': worst_basis,
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
    return [{k: _f(v) for k, v in dict({kk: hb[kk] for kk in ('hart', 'board', 'soc', 'title', 'isa', 'controller', 'nesting', 'clock_hz', 'openness', 'tier', 'schedule_model',
                                                              'parallelism', 'lockstep', 'mirror_of', 'multicore_model', 'amp_with')},
                                        polls=len(hb['polls']), interrupts=len(hb['interrupts']), threads=len(hb['threads']), headroom=hb['derived'].get('headroom', -1),
                                        poll_cycle_ms=hb['derived'].get('poll_cycle_ms', -1), poll_cycle_verdict=hb['derived'].get('poll_cycle_verdict', ''),
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
