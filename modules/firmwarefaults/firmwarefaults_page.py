"""
@module firmwarefaults.firmwarefaults_page

/display/firmware-faults — the scenario analysis as CONFIGURED tables only (no new component, no raw JSON —
FIRMWARE_SCENARIO_PLAN.md §6): the scenarios and their steps, the runs (outcome, the fault cycle and PC, where the
forced interrupt landed, the torn value, the costs), the cycles around the fault (ScenarioTraceCycle rows read from the
VCD by pyvcd), the claims the runs wrote (mathproofs' MathClaim), the techniques with seeded and measured costs, the
assumptions and primitives, and one table per fault KIND grouped by family. The 2D semantic-zoom viewer takes the VCD
later; until then the trace is these rows plus the VCD sha on the run.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_FAULT_COLS = 'name,assumption_broken,observable,remedies_json,rate,rate_unit,rate_source,forcing_status'
_KIND_EXTRA = {
    'TornReadFault': 'width_bytes,read_order', 'PriorityInversionFault': 'bounded', 'DeadlockFault': 'lock_cycle_json',
    'UartBitErrorFault': 'ber', 'DoubleEdgeFault': 'bounce_us', 'MetastableInputFault': 'mtbf_params_json',
    'BrownoutMidWriteFault': 'droop_v,droop_ms,bod_level_v', 'BitFlipFault': 'upsets_per_bit_day', 'ClockSkewFault': 'ppm',
    'StackOverflowFault': 'headroom_bytes', 'BufferOverrunFault': 'buffer,bound', 'MissedDeadlineFault': 'deadline_cycles',
}
_FAMILIES = [
    ('concurrency', 'Concurrency faults — logic: can this interleaving happen at all?',
     ['TornReadFault', 'DoubleGiveFault', 'LostWakeupFault', 'PriorityInversionFault', 'DeadlockFault', 'LivelockFault', 'StarvationFault']),
    ('physical', 'Physical triggers — physics breaks an assumption; the RATE comes from physics (sourced or unverified)',
     ['UartBitErrorFault', 'DoubleEdgeFault', 'MetastableInputFault', 'BrownoutMidWriteFault', 'BitFlipFault', 'ClockSkewFault']),
    ('space', 'Space and safety — space pressure is a cause', ['StackOverflowFault', 'BufferOverrunFault', 'MissedDeadlineFault']),
]


def _kind_rows(start):
    rows, i = [], start
    for fam, title, classes in _FAMILIES:
        for k in range(0, len(classes), 2):
            pair = classes[k:k + 2]
            rows.append(_row(i, [_table('ff-kind-%s' % c, n, 12 // len(pair), '%s — %s' % (title, c) if n == 0 and k == 0 else c, c,
                                        columns=','.join(x for x in (_FAULT_COLS, _KIND_EXTRA.get(c, '')) if x),
                                        column_formats='assumption_broken:ref:Assumption')
                                 for n, c in enumerate(pair)], min_height=200))
            i += 1
    return rows


SEED_FIRMWAREFAULTS_PAGE_DISPLAYS = [
    _page('firmware-faults', 'firmware-faults',
          'Firmware faults — force a concurrency or physics bug on purpose on the UNO twin, see the cycle where it goes wrong, then see '
          'the technique that makes it safe and what that technique costs (`pol faults run <scenario> --both`; `pol faults stats <scenario>`)',
          'Scenario', [
              _row(0, [_table('ff-scenarios', 0, 12, 'Scenarios — the forcing recipe: BEFORE variant (no technique), AFTER variant (with it), the fault, '
                              'the assumption it breaks, the observable that decides', 'Scenario',
                              columns='name,title,before_variant,after_variant,fault_class,fault,breaks,technique,observable_kind,run_seconds,seed,status',
                              column_formats='name:ref:Scenario,breaks:ref:Assumption,technique:ref:Technique,before_variant:ref:FirmwareVariant,'
                                             'after_variant:ref:FirmwareVariant')], min_height=200),
              _row(1, [_table('ff-runs', 0, 12, 'Runs — outcome, the decisive reading, the forced cycle and PC (or the forced event), where the '
                              'interrupt LANDED, the torn value, the frames, resets, and what the technique cost (AFTER − BEFORE: flash bytes, the '
                              'pricing function\'s or ISR\'s cycles, worst ISR latency); plan §4 space/safety on every run: stack high-water, ISR '
                              'latency and length, sizes', 'ScenarioRun',
                              columns='name,side,variant,technique_applied,outcome,observable_value,verdict_words,fault_cycle,fault_symbol,landed_symbol,'
                                      'torn_value,expected_value,frames_seen,frames_backwards,bad_crc,uptime_sequence,reset_count,cost_flash_bytes_delta,'
                                      'cost_cycles_delta,latency_delta_cycles,isr_latency_max_cycles,isr_cycles_max,isr_cycles_vector,fn_cycles_min,'
                                      'stack_high_water,stack_static_peak,size_text,size_data,size_bss,claim,trace_sha256,ran_at',
                              column_formats='name:ref:ScenarioRun,claim:ref:MathClaim,technique_applied:ref:Technique')], min_height=260),
              _row(2, [_table('ff-trace', 0, 12, 'The cycles around the fault — one row per instruction boundary from the run\'s VCD (pyvcd, engine '
                              'side): PC as symbol+offset, the instruction, SREG.I, the running vector, r22..r25 (what hal_millis returns), g_ms',
                              'ScenarioTraceCycle',
                              columns='run,idx,rel_cycle,cycle,pc,symbol,instruction,sreg_i,isr_vector,r22,r23,r24,r25,watch,forced,note',
                              column_formats='run:ref:ScenarioRun')], min_height=320),
              _row(3, [_table('ff-claims', 0, 12, 'Claims the runs wrote — "firmware F under scenario S is free of fault K": refuted (with the '
                              'counterexample), witnessed (one interleaving — never a proof), inapplicable, undetermined', 'MathClaim',
                              columns='name,kind,proof_status,checker,evidence_level,about_refs_json,counterexample_json,certificate_ref',
                              column_formats='name:ref:MathClaim,about_refs_json:refs')], min_height=200),
              _row(4, [_table('ff-techniques', 0, 12, 'Techniques — what each restores, the C idiom, the seeded cost (and its source) beside what a '
                              'scenario pair MEASURED on the twin', 'Technique',
                              columns='name,restores,primitive,idiom_c,typical_cost_bytes,typical_cost_cycles,typical_latency_cycles,cost_source,'
                                      'measured_cost_bytes,measured_ram_bytes,measured_cost_cycles,measured_cost_what,measured_latency_delta_cycles,'
                                      'measured_by_run,caveats',
                              column_formats='name:ref:Technique,restores:ref:Assumption,measured_by_run:ref:ScenarioRun')], min_height=240),
              _row(5, [_table('ff-stats', 0, 12, 'Statistics (sc-1) — many seeded runs → a rate with its 95 % Wilson interval: scenario 4 under '
                              'a bit error rate (commands lost, and the RESIDUAL the parser itself adds beyond what the line destroyed), scenario 1 '
                              'under asynchronous traffic (torn reads per byte-0 carry). Coverage = these seeds, this window, this build', 'ScenarioStatistic',
                              columns='name,scenario,side,variant,parameter,parameter_value,seeds,trials,events,events_per_1000,rate,ci_low,ci_high,residual_events,'
                                      'residual_rate,residual_ci_low,residual_ci_high,measure,per_seed,notes,wall_s,ran_at',
                              column_formats='scenario:ref:Scenario')], min_height=220),
              _row(6, [_table('ff-assumptions', 0, 7, 'Assumptions the firmware makes — who relies on each, how it can be checked', 'Assumption',
                              columns='name,statement,who_relies,checkable_by,holds_in_shipped', column_formats='name:ref:Assumption'),
                       _table('ff-primitives', 1, 5, 'Concurrency primitives — the UNO uses irq-mask, volatile-flag, spsc-ring', 'ConcurrencyPrimitive',
                              columns='name,kind,uno_uses,needs_rtos,typical_cost_cycles,where')], min_height=220),
              _row(7, [_table('ff-steps', 0, 12, 'Scenario steps — the kind, its arguments (a PC as symbol + pattern, re-resolved per build), the '
                              'condition, and whether the harness can force that kind today (and why not)', 'ScenarioStep',
                              columns='scenario,order,kind,args_json,condition_json,forcible,not_forcible_reason,notes',
                              column_formats='scenario:ref:Scenario')], min_height=180),
          ] + _kind_rows(8)),
]
