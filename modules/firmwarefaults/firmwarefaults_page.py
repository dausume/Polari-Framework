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


def _kind_description(fam, title, cls):
    """Every fault KIND table shares the same row/column logic (one row = one named instance of this fault kind,
    cited rate, named remedies); only the family text and the kind-specific extra columns differ — generated here
    so all ~11 kind tables stay accurate without hand-writing near-duplicate prose."""
    extra = _KIND_EXTRA.get(cls, '')
    extra_txt = (' Kind-specific columns: %s.' % extra) if extra else ''
    return ('What this is for: %s One row = one named %s instance — the assumption it breaks, how it is OBSERVED '
            '(what a run watches to tell it happened), named remedies, and its rate when one is cited (never guessed; '
            'rate_source names where it came from, forcing_status says whether the scenario harness can trigger it '
            'today).%s' % (title, cls, extra_txt))


def _kind_rows(start):
    rows, i = [], start
    for fam, title, classes in _FAMILIES:
        for k in range(0, len(classes), 2):
            pair = classes[k:k + 2]
            rows.append(_row(i, [_table('ff-kind-%s' % c, n, 12 // len(pair), '%s — %s' % (title, c) if n == 0 and k == 0 else c, c,
                                        columns=','.join(x for x in (_FAULT_COLS, _KIND_EXTRA.get(c, '')) if x),
                                        column_formats='assumption_broken:ref:Assumption',
                                        description=_kind_description(fam, title, c))
                                 for n, c in enumerate(pair)], min_height=200))
            i += 1
    return rows


SEED_FIRMWAREFAULTS_PAGE_DISPLAYS = [
    _page('firmware-faults', 'firmware-faults',
          'Firmware faults — force a concurrency or physics bug on purpose on the UNO twin, see the cycle where it goes wrong, then see '
          'the technique that makes it safe and what that technique costs (`pol faults run <scenario> --both`; `pol faults stats <scenario>`). '
          'Every scenario targets a FirmwareVariant from /display/firmware-installer; the C each variant compiles can be read as atoms on '
          '/display/c-atoms. Below the scenario/run tables sit one pair of tables per FAULT KIND (concurrency, physical, space/safety), '
          'each the cited facts for that one bug.',
          'Scenario', [
              _row(0, [_table('ff-scenarios', 0, 12, 'Scenarios — the forcing recipe: BEFORE variant (no technique), AFTER variant (with it), the fault, '
                              'the assumption it breaks, the observable that decides', 'Scenario',
                              description='What this is for: the FORCING RECIPE for one bug — which board/variant, which fault, which '
                                          'assumption it breaks, how a run decides pass/fail. One row = one Scenario. Columns: before_variant/'
                                          'after_variant (the FirmwareVariant without vs with the technique), fault_class/fault (which kind '
                                          'table below it comes from), observable_kind (uptime-monotone | build-refused — what the runner '
                                          'checks), status (runnable only when every step is forcible on the simulator today).',
                              columns='name,title,before_variant,after_variant,fault_class,fault,breaks,technique,observable_kind,run_seconds,seed,status',
                              column_formats='name:ref:Scenario,breaks:ref:Assumption,technique:ref:Technique,before_variant:ref:FirmwareVariant,'
                                             'after_variant:ref:FirmwareVariant')], min_height=200),
              _row(1, [_table('ff-runs', 0, 12, 'Runs — outcome, the decisive reading, the forced cycle and PC (or the forced event), where the '
                              'interrupt LANDED, the torn value, the frames, resets, and what the technique cost (AFTER − BEFORE: flash bytes, the '
                              'pricing function\'s or ISR\'s cycles, worst ISR latency); plan §4 space/safety on every run: stack high-water, ISR '
                              'latency and length, sizes', 'ScenarioRun',
                              description='What this is for: what ACTUALLY happened when a scenario ran, BEFORE and AFTER. One row = one side '
                                          'of one run. Columns: outcome/verdict_words (pass/fail in words), fault_cycle/fault_symbol/'
                                          'landed_symbol (exactly where the forced event landed), torn_value/expected_value (the corrupted '
                                          'value vs what should have been there), cost_flash_bytes_delta/cost_cycles_delta/'
                                          'isr_latency_max_cycles (AFTER minus BEFORE — the technique\'s MEASURED cost), stack_high_water '
                                          '(space/safety, every run).',
                              columns='name,side,variant,technique_applied,outcome,observable_value,verdict_words,fault_cycle,fault_symbol,landed_symbol,'
                                      'torn_value,expected_value,frames_seen,frames_backwards,bad_crc,uptime_sequence,reset_count,cost_flash_bytes_delta,'
                                      'cost_cycles_delta,latency_delta_cycles,isr_latency_max_cycles,isr_cycles_max,isr_cycles_vector,fn_cycles_min,'
                                      'stack_high_water,stack_static_peak,size_text,size_data,size_bss,claim,trace_sha256,ran_at',
                              column_formats='name:ref:ScenarioRun,claim:ref:MathClaim,technique_applied:ref:Technique')], min_height=260),
              _row(2, [_table('ff-trace', 0, 12, 'The cycles around the fault — one row per instruction boundary from the run\'s VCD (pyvcd, engine '
                              'side): PC as symbol+offset, the instruction, SREG.I, the running vector, r22..r25 (what hal_millis returns), g_ms',
                              'ScenarioTraceCycle',
                              description='What this is for: the INSTRUCTION-LEVEL replay around the forced event, read from the run\'s own VCD '
                                          '— this is the closest thing to "watching the bug happen" these tables carry (the full 2D trace '
                                          'viewer is a later arc). One row = one instruction boundary. Columns: pc/symbol (where execution was), '
                                          'sreg_i (interrupts enabled/disabled), isr_vector (which ISR, if any, is running), r22..r25 (hal_millis\' '
                                          'return registers), forced (this is the cycle the harness acted on).',
                              columns='run,idx,rel_cycle,cycle,pc,symbol,instruction,sreg_i,isr_vector,r22,r23,r24,r25,watch,forced,note',
                              column_formats='run:ref:ScenarioRun')], min_height=320),
              _row(3, [_table('ff-claims', 0, 12, 'Claims the runs wrote — "firmware F under scenario S is free of fault K": refuted (with the '
                              'counterexample), witnessed (one interleaving — never a proof), inapplicable, undetermined', 'MathClaim',
                              description='What this is for: the formal STATEMENT a run or formal check produced, in mathproofs\' own claim '
                                          'shape. One row = one MathClaim. Columns: proof_status (refuted | witnessed | inapplicable | '
                                          'undetermined — witnessed is ONE interleaving, never a proof of absence), evidence_level/'
                                          'evidence_tiers_json (how strong), counterexample_json (the trace when refuted).',
                              columns='name,kind,proof_status,checker,evidence_level,evidence_tiers_json,measure_json,about_refs_json,counterexample_json,'
                                      'certificate_ref',
                              column_formats='name:ref:MathClaim,about_refs_json:refs')], min_height=200),
              _row(4, [_table('ff-techniques', 0, 12, 'Techniques — what each restores, the C idiom, the seeded cost (and its source) beside what a '
                              'scenario pair MEASURED on the twin', 'Technique',
                              description='What this is for: the FIX applied in an AFTER variant — what assumption it restores and what it '
                                          'costs, seeded vs measured. One row = one Technique. Columns: restores (the Assumption it fixes), '
                                          'idiom_c (the actual C pattern), typical_cost_* (a seeded estimate, cost_source cited), measured_cost_*'
                                          '/measured_by_run (what a real scenario pair MEASURED — the number that matters).',
                              columns='name,restores,primitive,idiom_c,typical_cost_bytes,typical_cost_cycles,typical_latency_cycles,cost_source,'
                                      'measured_cost_bytes,measured_ram_bytes,measured_cost_cycles,measured_cost_what,measured_latency_delta_cycles,'
                                      'measured_by_run,caveats',
                              column_formats='name:ref:Technique,restores:ref:Assumption,measured_by_run:ref:ScenarioRun')], min_height=240),
              _row(5, [_table('ff-stats', 0, 12, 'Statistics (sc-1) — many seeded runs → a rate with its 95 % Wilson interval: scenario 4 under '
                              'a bit error rate (commands lost, and the RESIDUAL the parser itself adds beyond what the line destroyed), scenario 1 '
                              'under asynchronous traffic (torn reads per byte-0 carry). Coverage = these seeds, this window, this build', 'ScenarioStatistic',
                              description='What this is for: ONE scenario run MANY times (many seeds) to turn a pass/fail into a RATE with a '
                                          'confidence interval. One row = one (scenario, side, parameter value) statistic. Columns: events/'
                                          'events_per_1000/rate + ci_low/ci_high (the 95% Wilson interval), residual_rate (what still gets '
                                          'through even WITH the technique), notes naming the exact coverage (these seeds, this window, this '
                                          'build — never a field rate).',
                              columns='name,scenario,side,variant,parameter,parameter_value,seeds,trials,events,events_per_1000,rate,ci_low,ci_high,residual_events,'
                                      'residual_rate,residual_ci_low,residual_ci_high,measure,per_seed,notes,wall_s,ran_at',
                              column_formats='scenario:ref:Scenario')], min_height=220),
              _row(6, [_table('ff-assumptions', 0, 7, 'Assumptions the firmware makes — who relies on each, how it can be checked', 'Assumption',
                              description='What this is for: the things the firmware silently assumes are true. One row = one Assumption. '
                                          'Columns: who_relies (which code depends on it), checkable_by (what kind of check could verify it), '
                                          'holds_in_shipped (whether the shipped build actually upholds it).',
                              columns='name,statement,who_relies,checkable_by,holds_in_shipped', column_formats='name:ref:Assumption'),
                       _table('ff-primitives', 1, 5, 'Concurrency primitives — the UNO uses irq-mask, volatile-flag, spsc-ring', 'ConcurrencyPrimitive',
                              description='What this is for: the concurrency-safety tools actually available on this hardware. One row = one '
                                          'primitive. Columns: uno_uses (whether this firmware uses it), needs_rtos (unavailable on bare-metal), '
                                          'typical_cost_cycles, site (where in the code it is used).',
                              columns='name,kind,uno_uses,needs_rtos,typical_cost_cycles,site')], min_height=220),
              _row(7, [_table('ff-steps', 0, 12, 'Scenario steps — the kind, its arguments (a PC as symbol + pattern, re-resolved per build), the '
                              'condition, and whether the harness can force that kind today (and why not)', 'ScenarioStep',
                              description='What this is for: the ORDERED actions a scenario forces (irq-at-pc, corrupt-word, …), each checked '
                                          'against what the harness can actually do. One row = one step. Columns: args_json (a PC as symbol + '
                                          'pattern, re-resolved per build — never a hardcoded address), forcible/not_forcible_reason (honesty '
                                          'about harness limits).',
                              columns='scenario,position,kind,args_json,condition_json,forcible,not_forcible_reason,notes',
                              column_formats='scenario:ref:Scenario')], min_height=180),
              # sc-2: the statistics tier as campaigns + the likelihood table per fault kind
              _row(8, [_table('ff-campaigns', 0, 12, 'Campaigns (sc-2) — the fault\'s RATE as the stimulus: scenario x fault x rate(s) x seeds; per '
                              'rate the likelihood WITHOUT the technique and the technique\'s RESIDUAL (95 % Wilson), the time to the first fault; '
                              '`pol faults campaign run <name>`', 'ScenarioCampaign',
                              description='What this is for: a scenario run across MULTIPLE physical rates at once (e.g. several bit-error '
                                          'rates), each with many seeds — the campaign IS the physical-rate sweep. One row = one campaign. '
                                          'Columns: rates_json (the stimulus values swept), likelihood_summary/ttff_summary (the headline '
                                          'numbers; FaultLikelihood below has the per-rate detail), event_before/event_after.',
                              columns='name,scenario,fault_class,fault,parameter,rates_json,seeds,run_seconds,status,likelihood_summary,ttff_summary,'
                                      'event_before,event_after,stimulus,runs,wall_s,ran_at',
                              column_formats='name:ref:ScenarioCampaign,scenario:ref:Scenario')], min_height=220),
              _row(9, [_table('ff-likelihoods', 0, 12, 'Likelihood per fault kind (sc-2) — one row per (fault, stimulus value): how often the bug '
                              'happened without the technique and with it, each with its 95 % Wilson interval; coverage stated (a twin under these '
                              'seeds — never a field rate until a cited physical rate is the stimulus)', 'FaultLikelihood',
                              description='What this is for: the per-rate DETAIL behind a campaign\'s summary. One row = one (fault, stimulus '
                                          'value) pair. Columns: before_rate/before_ci_low/before_ci_high (without the technique), '
                                          'after_rate/after_ci_low/after_ci_high (with it), ttff_median_ms (time to first fault), coverage '
                                          '(states exactly what was tested — a twin under these seeds, never a claimed field rate).',
                              columns='fault_class,fault,parameter,parameter_value,trial_unit,before_events,before_trials,before_rate,before_ci_low,'
                                      'before_ci_high,technique,after_events,after_trials,after_rate,after_ci_low,after_ci_high,ttff_median_ms,campaign,'
                                      'coverage,notes',
                              column_formats='campaign:ref:ScenarioCampaign,technique:ref:Technique,scenario:ref:Scenario')], min_height=220),
              # sc-2b: the formal tier (CBMC) and the static rules (cppcheck)
              _row(10, [_table('ff-formal', 0, 12, 'Formal checks (sc-2b + sc-2c) — two engines on the variant\'s own hal.c: CBMC with the '
                               'interrupt as nondeterminism (decided (bounded, k)) and Frama-C/Mthread with the ISR as a thread and cli/sei/'
                               'ATOMIC_BLOCK as one interrupt lock (decided (unbounded) — no k); never proved; refuted with its trace or the two '
                               'racing lines, inapplicable when the source does not compile; the model\'s limits on every row '
                               '(`pol faults formal run all`)', 'FormalCheck',
                               description='What this is for: TWO independent formal engines (CBMC, Frama-C/Mthread) checking a variant\'s '
                                           'hal.c directly, no simulation. One row = one engine run on one variant. Columns: engine/bound '
                                           '(CBMC: bounded,k; Mthread: unbounded, no k), outcome/claim_status (refuted with a trace/race, or '
                                           'inapplicable when the source will not compile for that engine — never "proved"), limits (the '
                                           'model\'s own stated limits, every row).',
                               columns='name,engine,bound,outcome,claim_status,wall_s,peak_rss_mb,variant,function,property_text,outcome_words,'
                                       'expected,engine_version,trace_sha256,claim,limits,ran_at',
                               column_formats='name:ref:FormalCheck,variant:ref:FirmwareVariant,claim:ref:MathClaim,scenario:ref:Scenario')],
                   min_height=220),
              _row(11, [_table('ff-static', 0, 5, 'Static rules per variant (sc-2b) — cppcheck built-ins + threadsafety (MISRA not run: its texts '
                               'are not free); findings are rows, never a build failure', 'StaticCheck',
                               description='What this is for: cppcheck run over a variant\'s C — findings are ROWS, never a build failure. One '
                                           'row = one variant\'s static-check summary. Columns: errors/warnings/style/portability/performance '
                                           '(counts by cppcheck category), not_run (MISRA — its rule texts are not free, so it is honestly '
                                           'absent, not silently skipped).',
                               columns='variant,findings,errors,warnings,style,portability,performance,tool_version,addons,not_run,wall_s,ran_at',
                               column_formats='variant:ref:FirmwareVariant'),
                        _table('ff-static-findings', 1, 7, 'Static findings — id, severity, where', 'StaticFinding',
                               description='What this is for: the individual findings behind the summary beside it. One row = one finding. '
                                           'Columns: severity/check_id (cppcheck\'s own ids), file/line (exactly where), cwe (when cppcheck '
                                           'names one).',
                               columns='variant,severity,check_id,file,line,message,cwe,addon', column_formats='variant:ref:FirmwareVariant')],
                   min_height=220),
          ] + _kind_rows(12)),
]
