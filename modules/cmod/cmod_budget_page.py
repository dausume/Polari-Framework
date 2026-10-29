"""
@module cmod.cmod_budget_page

ipb-2: /display/budget - the polling + interrupt budget, TWO COLUMNS PER HART (program counter), for BOTH uses his ask names: planning (the Mission's
Task Plan: the "Plan" tabs) and analysing the real boards on a Bench (the "Bench" tabs). Every panel is a configured table over a budget door;
the words use RISC-V names with the chip's own mechanism beside them (the Controllers tab). No raw JSON on screens.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab

_B = '/api/benches/home-bench/budget'
_M = '/api/missions/uno-light-mission/budget'
_F = '/api/hart-facts'

_POLL_COLS = 'hart,atom_short,task,affinity,affinity_reason,trigger,wanted_response_ms,poll_divider,cycles_min,cycles_max,cost_per_scan_cycles,calls_measured,masked_window_cycles,basis'
_INT_COLS = 'hart,vector,task,affinity,affinity_reason,source,how,expected_rate_hz,rate_basis,priority_level,nests,length_min,length_max,length_mean,latency_max,utilisation,defers_to,basis'
_DER_COLS = ('hart,label,polls_per_scan,scan_cycles,measured_worst_gap_cycles,scan_ms,scan_deadline_ms,scan_deadline_basis,scan_utilisation,isr_utilisation,headroom,'
             'poll_cycle_cycles,poll_cycle_ms,poll_cycle_verdict,poll_cycle_why,poll_cycle_inflated_cycles,poll_cycle_best_split_cycles,any_tasks,poll_cycle_missing,masked_window_max_cycles,masked_window_where,'
             'worst_latency_cycles,worst_latency_us,unknown_poll_costs')
_HART_COLS = 'hart,label,board,soc,isa,controller,nesting,clock_hz,multicore_model,tier,schedule_model,polls,interrupts,threads,headroom,poll_cycle_ms,poll_cycle_verdict,lockstep,mirror_of,parallelism,openness,notes'
_SUG_COLS = 'hart,kind,severity,suggestion,evidence'

_INTRO = ('What a scan is: one pass of all the polls (the main loop on bare C; a thread\'s own loop on an RTOS). Interrupts do not wait for gaps between polls - '
          'they preempt a poll; what bounds them is the longest masked window, and what polls and interrupts fight over is CPU time: that is the budget. '
          'Two columns ALWAYS, even on bare C: a column may be empty, never missing. The unit is one program counter (a RISC-V hart): two chips = four columns.')


def _two_columns(prefix, base, who):
    return [
        _row(0, [_table(prefix + '-polls', 0, 6, 'POLLS - the left column', 'HardwareMission',
                        description='One row = one atom the loop runs each pass (an atom several tasks share is counted once). Columns: hart, atom, the tasks it serves, the trigger kind, '
                                    'wanted_response_ms (the tightest Purpose deadline it serves), poll_divider (knob: run every Nth scan), cycles min/max (measured on the twin, cyc-0; '
                                    '-1 = not measured), cost_per_scan_cycles (max / divider), calls_measured, basis. GET %s?view=polls.' % base,
                        columns=_POLL_COLS, data_path=base + '?view=polls', empty_text='No polls: %s names no loop-lane atom (or no firmware is assigned).' % who),
                 _table(prefix + '-ints', 6, 6, 'INTERRUPTS - the right column', 'HardwareMission',
                        description='One row = one interrupt handler atom. Columns: hart, vector (the chip\'s name; the controller row maps it to mie/mip/mcause), task, source, how, '
                                    'expected_rate_hz with its basis (a period, a knob, or what the twin saw), priority_level (the chip\'s own numbering), nests (from the controller row), '
                                    'length min/max/mean and latency_max in cycles (measured, cyc-0), utilisation (= mean x rate / clock), defers_to (the thread, on an RTOS), basis. '
                                    'GET %s?view=interrupts.' % base,
                        columns=_INT_COLS, data_path=base + '?view=interrupts', empty_text='No interrupts: %s enables none (the column exists because the hart can take them).' % who)],
             min_height=360),
        _row(1, [_table(prefix + '-derived', 0, 12, 'The budget per hart: scan, deadline, utilisation, headroom', 'HardwareMission',
                        description='One row = one hart. scan_cycles = the bound (each poll\'s max / divider, once per atom, + the quiet pass); measured_worst_gap_cycles = what the twin '
                                    'actually saw between two visits of the poll point (the evidence beside the bound); scan_ms at the clock; scan_deadline_ms (knob; default = the '
                                    'shortest wanted response / 2, said in its basis); scan_utilisation = scan_ms / deadline; isr_utilisation = the sum of the interrupt rows\' utilisation; '
                                    'headroom = 1 - both (negative = the scan cannot meet its deadline); poll_cycle_cycles / _ms = the hart\'s standard PollCycle: the WORST CASE of every poll '
                                    'once at its max (dividers ignored) + every interrupt once at its max length + entry latency + the quiet pass - with its verdict (one PollCycle must fit '
                                    'twice in the shortest wanted response), poll_cycle_missing naming what keeps it -1, and the rate-aware bound polls / (1 - isr_utilisation); '
                                    'masked_window_max_cycles = the longest stretch of main-line code the twin ran with interrupts masked (cli..sei / an ATOMIC_BLOCK; ipb-7, measured, '
                                    'with where); worst_latency_cycles = the cited entry latency + that window + the longest handler when handlers do not nest (-1 names what is '
                                    'missing). GET %s?view=derived.' % base,
                        columns=_DER_COLS, data_path=base + '?view=derived')], min_height=240),
        _row(2, [_table(prefix + '-checks', 0, 6, 'The 2x check per poll', 'HardwareMission',
                        description='A polled input must be scanned at least twice as fast as it must be answered: ok | miss | unknown, with why. GET %s?view=checks.' % base,
                        columns='hart,atom,task,verdict,why', data_path=base + '?view=checks'),
                 _table(prefix + '-sugg', 6, 6, 'Suggestions, each naming its evidence', 'HardwareMission',
                        description='Nothing is changed by a suggestion. Kinds: headroom (blocker), move-to-isr (warning), masked-window and defer (advice), unknowns (what to measure '
                                    'or cite next). GET %s?view=suggestions.' % base,
                        columns=_SUG_COLS, data_path=base + '?view=suggestions')], min_height=260),
        _row(3, [_table(prefix + '-links', 0, 6, 'Links into a hart (the chain across columns)', 'HardwareMission',
                        description='One row = one message / command path into a hart: from the host or another hart, over which transport, which interrupt receives it and which task '
                                    'it defers to; baud / frame / transit are -1 until ipb-5 reads the UART knobs. GET %s?view=links.' % base,
                        columns='from,to_hart,task,transport,route,receiving_interrupt,defers_to,chain,baud,frame_bytes,transit_ms,basis', data_path=base + '?view=links'),
                 _table(prefix + '-threads', 6, 6, 'Thread sub-rows (RTOS harts only)', 'HardwareMission',
                        description='A thread has no PC of its own: it is a sub-row of the hart it time-shares. Columns: hart, task, period_ms, priority, deadline_ms, exec_cycles, basis. '
                                    'Empty on bare C. GET %s?view=threads.' % base,
                        columns='hart,task,affinity,affinity_reason,period_ms,priority,deadline_ms,exec_cycles,basis', data_path=base + '?view=threads', empty_text='No threads: a bare-C hart (superloop).')],
             min_height=220)]


def _bench_tab():
    return _tab('bench', 'Bench: the real boards (home-bench)', [
        _row(0, [_table('bg-boards', 0, 6, 'The boards on the bench and where their budget comes from', 'Bench',
                        description='One row = one board on the bench: its processor, hart count, openness (ISA / core RTL / silicon / tooling), the Mission that runs on it (if any) '
                                    'and the state: a budget from that Mission\'s plan, or facts only with empty columns. GET %s?view=boards.' % _B,
                        columns='label,board,processor,harts,openness,mission,system,testing,state', data_path=_B + '?view=boards'),
                 _table('bg-harts', 6, 6, 'One row per hart (program counter): two columns each', 'HardwareMission',
                        description='Columns: hart, board, soc, isa, controller (the RISC-V-named row it maps onto), nesting, clock_hz, schedule_model (superloop | cyclic-executive | '
                                    'preemptive-rtos), the count of polls / interrupts / threads, headroom, openness, notes (the cycle record used, folded steps). GET %s?view=harts.' % _B,
                        columns=_HART_COLS, data_path=_B + '?view=harts')], min_height=300)] + _two_columns('bgb', _B, 'this bench'),
        description='ANALYSING: the real boards on the bench. ' + _INTRO)


def _plan_tab():
    return _tab('plan', 'Plan: the Mission (uno-light)', [
        _row(0, [_table('bgp-harts', 0, 12, 'The harts the Task Plan names', 'HardwareMission',
                        description='PLANNING: the budget of the Mission\'s Task Plan on its Hardware System (derived now, the plan\'s edits applied; numbers from the Mission\'s cycle '
                                    'record). GET %s?view=harts.' % _M, columns=_HART_COLS, data_path=_M + '?view=harts')], min_height=200)] + _two_columns('bgp', _M, 'this plan'),
        description='PLANNING: the Mission\'s plan as a budget. ' + _INTRO)


def _facts_tab():
    return _tab('facts', 'Controllers + harts (cited facts)', [
        _row(0, [_table('bg-controllers', 0, 12, 'Interrupt controllers - RISC-V names canonical, each chip\'s mechanism beside them', 'HardwareMission',
                        description='One row = one controller family. The fields are the RISC-V questions (global enable = mstatus.MIE, per-source enable = mie, pending = mip, '
                                    'trap vector = mtvec, cause = mcause, timer / external source, idle, cycle counter); an AVR / Arm / Xtensa row answers them with its own '
                                    'mechanism\'s name = the adaptation. Every number is cited or -1; to_read names the document that would fill a -1. GET %s?view=controllers.' % _F,
                        columns='name,isa,global_enable,per_source_enable,pending,vector_mode,cause,priority_levels,priority_0_meaning,nesting,entry_latency_cycles,exit_instruction,'
                                'timer_source,external_source,idle_instruction,cycle_counter,max_sources,spec_openness,citation,to_read,notes',
                        data_path=_F + '?view=controllers')], min_height=360),
        _row(1, [_table('bg-hart-facts', 0, 12, 'Hart facts per processor: how many PCs, which controller, which clock, how open', 'HardwareMission',
                        description='One row = one processor the chips-and-levels ladder knows (+ the QEMU RISC-V virt machine the open test cases run on). harts = the PCs that '
                                    'take instructions (an LP core is not counted until its ISA row is read; "configurable" for the virtual machine); openness = ISA / core RTL / '
                                    'silicon / tooling, each open, closed or unverified (D-ipb-5). GET %s?view=harts.' % _F,
                        columns='processor,title,isa,harts_text,harts_note,controller,clock_text,clock_citation,openness,boards,notes', data_path=_F + '?view=harts')],
             min_height=360),
        _row(2, [_table('bg-parallelism-kinds', 0, 6, 'Kinds of parallelism inside a chip (the RISC-V book\'s sections) and what each does to the budget', 'HardwareMission',
                        description='One row = one kind, cited to its section of Patterson & Hennessy, Computer Organization and Design RISC-V Edition (2nd ed.; the table of contents '
                                    'read, the bodies named in to_read). budget_effect says the honest thing: instruction- and data-level kinds change an atom\'s CYCLES (measured counts '
                                    'already include them); a hardware thread IS a hart (its own column pair); multicore = one pair per core, assignable separately unless LOCKSTEP '
                                    '(then mirrors); two chips = the links rows. GET %s?view=parallelism-kinds.' % _F,
                        columns='name,level,title,book_section,budget_effect,example,citation,to_read', data_path=_F + '?view=parallelism-kinds'),
                 _table('bg-parallelism', 6, 6, 'Parallelism facts per processor: pipeline, issue width, hardware threads, vector, lockstep', 'HardwareMission',
                        description='Every number cited or -1; lockstep = yes | no | n/a (one core) | configurable | unverified (the datasheet to read is named). A chip whose harts run in '
                                    'lockstep gets ONE assignable stream and mirror rows. GET %s?view=parallelism.' % _F,
                        columns='processor,multicore_model,amp_with,multicore_citation,pipeline_stages,issue_width,hw_threads_per_core,vector,lockstep,summary,citation,to_read', data_path=_F + '?view=parallelism')],
             min_height=360),
        _row(3, [_table('bg-tiers', 0, 12, 'Scheduler tiers: bare C -> FreeRTOS -> FreeRTOS-SMP -> Zephyr, and how each pins a task', 'HardwareMission',
                        description='ipb-8: the level between FreeRTOS and Zephyr is FreeRTOS-SMP - the FreeRTOS project\'s own SMP kernel (MIT), with the ESP-IDF variant on the S3. '
                                    'multicore_model above decides placement: on an smp chip a task may be `any` (null affinity: booked on every hart, the best split beside it); '
                                    'amp harts never share a task set; single-core chips refuse `any` by name. GET %s?view=tiers.' % _F,
                        columns='tier,title,kernel,license,affinity_api,citation,to_read', data_path=_F + '?view=tiers')], min_height=220)],
        description='The fact rows the budget stands on. RISC-V is the basis (his ruling 2026-10-27); other ISAs are adaptation rows shown as exceptions.')


BUDGET_PAGES = [
    _page('budget', 'budget',
          'Polling + interrupt budget - two columns per program counter (hart). ' + _INTRO + ' Use it two ways: the Bench tab analyses the real boards on a bench '
          '(a board with a Mission gets that Mission\'s plan; the others show their facts with empty columns); the Plan tab budgets a Mission\'s Task Plan. The hart\'s standard '
          'PollCycle is the worst case of every poll and every interrupt once (ipb-6). Each hart of a chip is assignable on its own (hart_of, isr_hart_of) unless the chip runs its '
          'cores in lockstep - then one stream and mirrors. Every task carries an affinity (its hart, `any` on an smp chip, `mirror` under lockstep) and a reason word (owns-interrupt <vector>, polls-peripheral <name>, latency, isolation, by-default). Knobs (scan_deadline_ms, poll_divider, expected_rate_hz, hart_of, isr_hart_of, harts, lockstep, affinity, affinity_reason) go to POST .../budget/knobs '
          'and hold per process. The doors: GET /api/benches/<bench>/budget, GET /api/missions/<name>/budget, GET /api/hart-facts.',
          'HardwareMission', [], title='Budget', tabs=[_bench_tab(), _plan_tab(), _facts_tab()]),
]
