"""
@module cmod.custom.budget_suggest

ipb-3 (INTERRUPT_POLL_BUDGET_PLAN.md §3 "Suggestions"): evidence-bearing suggestion rows over a system budget. Every row NAMES the measured /
derived rows it came from (rule `knobs-and-suggestions`); nothing is changed by a suggestion. Kinds:
  headroom      headroom < 0  -> raise the scan deadline, raise a poll divider, or move the costliest poll to an interrupt
  move-to-isr   a poll fails the 2x check -> move it to an interrupt (its event rate x a short handler fits) or raise its divider on the others
  masked-window the longest masked window exceeds the shortest interrupt's latency budget (not measurable yet: a single row says so)
  defer         an RTOS hart's interrupt has no thread to defer to
  unknowns      numbers the budget could not get (the honest row: what to measure / cite next)
  affinity      ipb-8: a null-affinity task refused on a non-smp chip (pin it); a null-affinity task that breaks the PollCycle of a hart it may land on
                -> "pin <task> to <hart> for isolation", the hart its best split gives it
"""


def _sug(hb, kind, text, evidence, severity='advice'):
    return {'hart': hb['hart'], 'kind': kind, 'severity': severity, 'suggestion': text, 'evidence': evidence}


def suggestions(sb):
    out = []
    for hb in sb['harts']:
        d, polls, ints = hb['derived'], hb['polls'], hb['interrupts']
        if d.get('headroom', -1) < 0 and d.get('scan_utilisation', -1) >= 0:
            costliest = max(polls, key=lambda p: p['cost_per_scan_cycles']) if polls else None
            out.append(_sug(hb, 'headroom', 'the scan cannot meet its deadline: raise scan_deadline_ms (knob), raise a poll divider, or move %s (the costliest poll, %s cycles per scan) '
                            'to an interrupt' % (costliest['atom_short'] if costliest else '?', costliest['cost_per_scan_cycles'] if costliest else '?'),
                            'derived.headroom = %.3g (scan_utilisation %.3g + isr_utilisation %.3g); scan_ms %.4g vs scan_deadline_ms %.4g (%s)'
                            % (d['headroom'], d['scan_utilisation'], d['isr_utilisation'], d['scan_ms'], d['scan_deadline_ms'], d['scan_deadline_basis']), 'blocker'))
        if d.get('poll_cycle_verdict') == 'miss':
            out.append(_sug(hb, 'poll-cycle', 'the worst case (every poll and every interrupt once) does not fit twice in the shortest wanted response: raise that deadline, '
                            'shorten the longest poll / handler, or move work off this hart', 'derived.poll_cycle_ms %.4g (%s); %s' % (d['poll_cycle_ms'], d['poll_cycle_basis'], d['poll_cycle_why']), 'warning'))
        elif d.get('poll_cycle_missing') and (polls or ints):
            out.append(_sug(hb, 'poll-cycle', 'the PollCycle is -1: measure or cite ' + d['poll_cycle_missing'], 'derived.poll_cycle_missing', 'info'))
        for c in hb['checks']:
            if c['verdict'] == 'refused':
                out.append(_sug(hb, 'affinity', 'pin %s to a hart (affinity <hart>, with a reason word) - %s' % (c['task'], c['why']), 'checks[%s]: %s' % (c['task'], c['check']), 'warning'))
        if d.get('poll_cycle_verdict') == 'miss' and d.get('any_tasks'):
            for task in d['any_tasks'].split(', '):
                to = (hb.get('any_split') or {}).get(task)
                if to and to != hb['hart']:
                    out.append(_sug(hb, 'affinity', 'pin %s to %s for isolation: as a null-affinity task it may land here, and here it breaks the PollCycle' % (task, to),
                                    'derived.poll_cycle_verdict miss with null-affinity task(s) %s booked; %s' % (d['any_tasks'], d.get('poll_cycle_best_split_basis', '')), 'warning'))
        if hb.get('mirror_of'):
            out.append(_sug(hb, 'lockstep', 'a mirror of %s (lockstep): assign nothing to it separately; its columns are the stream\'s' % hb['mirror_of'], 'hart.mirror_of; the parallelism facts row', 'info'))
        for c in hb['checks']:
            if c['verdict'] == 'miss':
                p = next((p for p in polls if p['atom_short'] == c['atom']), {})
                out.append(_sug(hb, 'move-to-isr', 'move %s to an interrupt (the %s trigger) or raise the other polls\' dividers so the scan reaches it in time' % (c['atom'], p.get('trigger', '')),
                                'checks[%s]: %s; polls[%s].cycles_max %s, poll_divider %s' % (c['atom'], c['why'], c['atom'], p.get('cycles_max'), p.get('poll_divider')), 'warning'))
        if ints and d.get('worst_latency_cycles', -1) < 0:
            need = []
            if d.get('masked_window_max_cycles', -1) < 0:
                need.append('measure the longest masked window (cli..sei / MIE cleared: the twin\'s --masked-windows run)')
            if hb['entry_latency_cycles'] < 0:
                need.append('cite %s\'s entry latency' % (hb['controller'] or 'the controller'))
            if not need:
                need.append('measure a handler length')
            out.append(_sug(hb, 'masked-window', ' and '.join(need) + ', so worst_latency_cycles can be a number', d.get('worst_latency_basis', ''), 'advice'))
        elif ints and d.get('worst_latency_cycles', -1) >= 0:
            # ipb-7: the window is MEASURED - a critical section longer than the longest handler is what bounds the latency, so it is the thing to shorten
            longest = max((i['length_max'] for i in ints if i['length_max'] >= 0), default=-1)
            if d.get('masked_window_max_cycles', 0) > longest >= 0:
                out.append(_sug(hb, 'masked-window', 'shorten the critical section in %s: the longest masked window (%d cycles) exceeds the longest handler (%d) and bounds worst_latency_cycles'
                                % (d.get('masked_window_where', '?'), d['masked_window_max_cycles'], longest), 'derived.masked_window_max_cycles vs max(interrupts[].length_max); %s' % d['worst_latency_basis'], 'advice'))
        if hb['schedule_model'] == 'preemptive-rtos':
            for i in ints:
                if not i['defers_to']:
                    out.append(_sug(hb, 'defer', 'interrupt %s runs with no thread to hand its work to: defer it (queue / semaphore) so the handler stays short' % i['vector'],
                                    'interrupts[%s].defers_to is empty on a %s hart' % (i['vector'], hb['schedule_model']), 'warning'))
        unknown = []
        if d.get('unknown_poll_costs'):
            unknown.append('poll costs not in the cycle record: %s' % d['unknown_poll_costs'])
        if d.get('isr_rows_without_rate'):
            unknown.append('%d interrupt row(s) without an expected rate (knob expected_rate_hz, or a period)' % d['isr_rows_without_rate'])
        if hb['clock_hz'] <= 0:
            unknown.append('the hart\'s clock is -1 (%s)' % hb['clock_citation'])
        if hb['entry_latency_cycles'] < 0:
            unknown.append('entry latency -1 for %s' % (hb['controller'] or 'no controller row'))
        if unknown:
            out.append(_sug(hb, 'unknowns', 'what to measure or cite next: ' + '; '.join(unknown), 'the -1 fields of this hart\'s rows', 'info'))
    return out
