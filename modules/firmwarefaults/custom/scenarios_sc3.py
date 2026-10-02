"""
@module firmwarefaults.custom.scenarios_sc3

THE sc-3 SCENARIOS AS ROWS (FIRMWARE_SCENARIO_PLAN.md §3a scenarios 6–7, §9 sc-3; D-sc-4 RULED 2026-10-02: the RTOS board is
the ESP32-C3). sc-1 wrote these two down as recipes that were not-yet-forcible on the UNO; here they become FORCIBLE on the
C3's twin (Espressif's QEMU fork, `qemu-esp32c3`), each a BEFORE/AFTER pair of board's C3 FirmwareVariants that differ in one
build flag (board.custom.variants_c3):

  priority-inversion-mutex   S6  c3-prio-inversion (binary semaphore)  → c3-prio-inversion-mutex (priority inheritance)
  two-lock-deadlock          S7  c3-two-lock (opposite order)          → c3-two-lock-ordered (lock ordering)
  two-lock-deadlock-backoff  S7  c3-two-lock (opposite order)          → c3-two-lock-backoff (timed second take + back-off)

THE FORCING — step `hold-lock-order`: the recipe's offsets (ticks after a common round start, vTaskDelay to an absolute tick)
are written into the image's `polari` params partition (polari_c3.h polari_params_t), so the SAME binary runs every
interleaving with no rebuild. Seed 0 = the recipe's own values (the forced interleaving); seed k > 0 draws each `seeded` knob
uniformly from its range with splitmix64(k) — the statistics tier's stimulus. A host command (a SimRigState command's pwm_duty)
steers the app's steer slot on a running twin; the runner uses the partition (a run is then a function of image + params).

OBSERVE: what decides — `h-blocking-bounded` (H's worst wait for R vs the bound = L's critical section + one 1 ms tick of
slack) and `wait-for-acyclic` (the wait-for graph rebuilt from the FreeRTOS trace hooks: a cycle = deadlock, at the instant
it closed; every round completed = progress).
"""
import json
import struct

J = json.dumps
SIM = 'qemu-esp32c3'
BOARD = 'esp32-c3'
ICOUNT_SHIFT = 3                 # -icount shift=3: 2^3 ns of virtual time per instruction (Espressif's documented value)
INSTR_PER_S = 1e9 / (1 << ICOUNT_SHIFT)
PARAMS_OFFSET = 0x110000         # partitions.csv `polari` (the C3 template)
PARAMS_MAGIC = 0x33435350        # "PSC3"
SLACK_US = 1000                  # one FreeRTOS tick at CONFIG_FREERTOS_HZ=1000: the bound's stated slack

PI_SLOTS = ('h_off_ticks', 'm_off_ticks', 'l_cs_us', 'm_busy_us', 'period_ticks', 'deadline_us')
LOCK_SLOTS = ('t1_gap_ticks', 't2_start_ticks', 't2_gap_ticks', 'hold_us', 'period_ticks', 'stall_ms')


def _s(name, title, description, before, after, fault_class, fault, breaks, technique, expected, kind, seconds, notes=''):
    return {'name': name, 'title': title, 'description': description, 'target_board': BOARD, 'before_variant': before,
            'after_variant': after, 'fault_class': fault_class, 'fault': fault, 'breaks': breaks, 'technique': technique,
            'expected_observable': expected, 'observable_kind': kind, 'window_cycles': int(seconds * INSTR_PER_S), 'run_seconds': seconds,
            'seed_policy': 'per-run', 'seed': 0, 'simulator': SIM, 'status': 'runnable',
            'provenance': 'sc-3 (FIRMWARE_SCENARIO_PLAN.md §3a S6/S7; sc-1 wrote the recipes)',
            'notes': ('window_cycles = virtual INSTRUCTIONS at -icount %d (QEMU is instruction-level, not cycle-accurate — plan §2b); %s'
                      % (ICOUNT_SHIFT, notes)).strip()}


SC3_SCENARIOS = [
    _s('priority-inversion-mutex', 'Scenario 6 — priority inversion on the ESP32-C3 (FreeRTOS)',
       'L (priority 2) takes R and runs a 3 ms critical section; H (4) asks for R 1 tick later and blocks; M (3) wakes 2 ticks after '
       'the round start and runs 10 ms of CPU. BEFORE (c3-prio-inversion: R is a binary semaphore — no owner, no inheritance) M '
       'preempts L and H waits for M\'s whole run. AFTER (c3-prio-inversion-mutex: a FreeRTOS mutex) the kernel raises L to 4 while H '
       'waits (traceTASK_PRIORITY_INHERIT), M cannot run, H waits at most the rest of L\'s section. 10 rounds per run.',
       'c3-prio-inversion', 'c3-prio-inversion-mutex', 'PriorityInversionFault', 'priority-inversion', 'high-task-waits-cs',
       'priority-inheritance', 'BEFORE: H\'s worst wait ≫ L\'s section (≈ M\'s run) → refuted. AFTER: H\'s worst wait ≤ L\'s section + 1 tick, '
       'INHERIT/DISINHERIT in the trace → witnessed.', 'h-blocking-bounded', 0.5,
       notes='the FreeRTOS inside ESP-IDF v5.5.5 DOES inherit on a mutex — measured here (plan §3a had it unverified)'),
    _s('two-lock-deadlock', 'Scenario 7 — two tasks, two locks, opposite order → deadlock (FreeRTOS on the ESP32-C3)',
       'T1 takes A, yields 2 ticks (the forced preemption point), takes B; T2 starts 1 tick later, takes B, yields 1 tick, takes A. '
       'BEFORE (c3-two-lock) both block for ever — the wait-for graph closes T1 → B → T2 → A → T1 — and the telemetry task, which '
       'snapshots under A, stops. AFTER (c3-two-lock-ordered: T2 also takes A before B) every round completes.',
       'c3-two-lock', 'c3-two-lock-ordered', 'DeadlockFault', 'two-lock-deadlock', 'locks-one-order', 'lock-ordering',
       'BEFORE: a cycle in the wait-for graph at a named µs/tick, both tasks Blocked, telemetry stops → refuted. AFTER: no cycle, all '
       'rounds done → witnessed.', 'wait-for-acyclic', 1.9),
    _s('two-lock-deadlock-backoff', 'Scenario 7, the other remedy — a timed second take with back-off',
       'The same opposite-order tasks; AFTER (c3-two-lock-backoff) each task\'s second take waits at most 5 ms, then gives its first '
       'lock back, backs off (T1 1 tick, T2 3 ticks) and retries: the cycle can form for a moment but never persists.',
       'c3-two-lock', 'c3-two-lock-backoff', 'DeadlockFault', 'two-lock-deadlock', 'locks-one-order', 'try-lock-backoff',
       'BEFORE: deadlock → refuted. AFTER: every round completes, the back-offs counted → witnessed (a transient cycle broken by a '
       'timeout is reported beside it).', 'wait-for-acyclic', 1.9),
]


def _step(scenario, order, args, notes):
    return {'name': '%s#%d' % (scenario, order), 'scenario': scenario, 'order': order, 'kind': 'hold-lock-order', 'args_json': J(args),
            'condition_json': J({}), 'forcible': True, 'not_forcible_reason': '', 'notes': notes}


_PI = {'slots': list(PI_SLOTS), 'params': {'h_off_ticks': 1, 'm_off_ticks': 2, 'l_cs_us': 3000, 'm_busy_us': 10000, 'period_ticks': 40,
                                            'deadline_us': 5000},
       'seeded': {'h_off_ticks': [0, 3], 'm_off_ticks': [0, 4]}, 'window_ms': 1000, 'rounds': 10,
       'tasks': [{'name': 'L', 'prio': 2, 'takes': ['R'], 'at_tick': 0, 'holds_us': 3000}, {'name': 'H', 'prio': 4, 'takes': ['R'], 'at_tick': 'h_off'},
                 {'name': 'M', 'prio': 3, 'busy_us': 10000, 'at_tick': 'm_off'}],
       'measure': 'H blocked µs per round (t_acq − t_req, esp_timer) and who ran meanwhile (the switch-in trace)',
       'before': 'xSemaphoreCreateBinary (no inheritance)', 'after': 'xSemaphoreCreateMutex (priority inheritance)'}
_LOCK = {'slots': list(LOCK_SLOTS), 'params': {'t1_gap_ticks': 2, 't2_start_ticks': 1, 't2_gap_ticks': 1, 'hold_us': 500, 'period_ticks': 50,
                                                'stall_ms': 300},
         'seeded': {'t1_gap_ticks': [0, 3], 't2_start_ticks': [0, 4], 't2_gap_ticks': [0, 2]}, 'window_ms': 1500, 'rounds': 10,
         'tasks': [{'name': 'T1', 'prio': 3, 'takes': ['A', 'B'], 'gap': 't1_gap'}, {'name': 'T2', 'prio': 3, 'takes': ['B', 'A'], 'gap': 't2_gap',
                                                                                    'starts': 't2_start'}],
         'measure': 'the wait-for graph from the trace hooks (BLOCK/TAKE/GIVE per lock); a cycle = deadlock at the instant it closed',
         'before': 'T2 takes B then A', 'after': 'T2 takes A then B (ordering) | the second take times out + back-off'}
SC3_STEPS = [
    _step('priority-inversion-mutex', 1, _PI, 'the offsets go into the polari params partition; seed 0 = these values'),
    _step('two-lock-deadlock', 1, _LOCK, 'the gaps go into the polari params partition; seed 0 = these values'),
    _step('two-lock-deadlock-backoff', 1, _LOCK, 'the same recipe as two-lock-deadlock'),
]

OBSERVE = {
    'priority-inversion-mutex': {'slots': PI_SLOTS, 'cost_what': 'flash + DRAM (binary semaphore → mutex); H\'s worst wait AFTER − BEFORE'},
    'two-lock-deadlock': {'slots': LOCK_SLOTS, 'cost_what': 'flash + DRAM; T1\'s mean round time (ROUND → DONE) AFTER − BEFORE where both finish'},
    'two-lock-deadlock-backoff': {'slots': LOCK_SLOTS, 'cost_what': 'flash + DRAM; back-offs per run; T1\'s mean round time'},
}


def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31), x


def knobs_for(args, seed):
    """The recipe's knobs for one seed: seed 0 = the recipe; seed k draws each seeded knob uniformly in [lo, hi] (splitmix64)."""
    p = dict(args['params'])
    if int(seed) == 0:
        return p
    state = int(seed) * 0x2545F4914F6CDD1D & 0xFFFFFFFFFFFFFFFF
    for k in sorted(args.get('seeded', {})):
        lo, hi = args['seeded'][k]
        z, state = splitmix64(state)
        p[k] = lo + (z % (hi - lo + 1))
    return p


def params_bytes(args, seed):
    """polari_params_t (polari_c3.h): magic, version, seed, window_ms, rounds, a[8] — little-endian, 52 bytes."""
    p = knobs_for(args, seed)
    a = [int(p[k]) for k in args['slots']] + [0] * (8 - len(args['slots']))
    return struct.pack('<IIIII8i', PARAMS_MAGIC, 1, int(seed), int(args['window_ms']), int(args['rounds']), *a), p
